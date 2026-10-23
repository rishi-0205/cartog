"""Unit tests for JavaScript and TypeScript tree-sitter adapter."""

from pathlib import Path
import pytest
import tree_sitter

from cartog.langs import get_adapter, get_adapter_for_path, parse_source_file
from cartog.langs.base import ImportRecord, ProjectContext
from cartog.langs.js_adapter import (
    JsAdapter,
    clean_string_literal,
    extract_nextjs_route_path,
    path_to_js_module_name,
)
from cartog.scan import FileInfo, walk_files


def test_js_adapter_registration():
    """Verify JsAdapter is registered for all JS/TS extensions."""
    adapter_js = get_adapter("javascript")
    adapter_ts = get_adapter("typescript")
    assert adapter_js is not None
    assert adapter_ts is not None
    assert isinstance(adapter_js, JsAdapter)
    assert isinstance(adapter_ts, JsAdapter)

    for ext in (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"):
        ad = get_adapter_for_path(f"src/file{ext}")
        assert ad is not None
        assert isinstance(ad, JsAdapter)


def test_path_to_js_module_name():
    """Verify repo-relative paths convert to dot-separated JS/TS module names."""
    assert path_to_js_module_name("source/index.ts") == "source"
    assert path_to_js_module_name("source/core/Ky.ts") == "source.core.Ky"
    assert (
        path_to_js_module_name(
            "packages/core/src/utils.ts", roots=[".", "packages/core", "packages/web"]
        )
        == "utils"
    )
    assert (
        path_to_js_module_name(
            "packages/core/src/index.ts", roots=[".", "packages/core", "packages/web"]
        )
        == ""
    )
    assert path_to_js_module_name("src/components/Button.tsx") == "components.Button"


def test_js_symbol_extraction():
    """Verify symbol extraction for classes, methods, functions, arrow functions, and decorators."""
    code = b"""
export class KyClient {
  private options: any;

  constructor(opts: any) {
    this.options = opts;
  }

  async get(url: string): Promise<any> {
    return url;
  }
}

export function createClient(opts: any): KyClient {
  return new KyClient(opts);
}

export const helper = (x: number) => x * 2;
export const calc = function(a: number, b: number) { return a + b; };
"""
    adapter = JsAdapter()
    tree = adapter.parse(code, Path("source/core/client.ts"))
    symbols = adapter.extract_symbols(tree, code, "source/core/client.ts")

    sym_dict = {s.name: s for s in symbols}

    assert "KyClient" in sym_dict
    assert sym_dict["KyClient"].kind == "class"
    assert sym_dict["KyClient"].qualified_name == "source.core.client.KyClient"

    assert "constructor" in sym_dict
    assert sym_dict["constructor"].kind == "method"
    assert sym_dict["constructor"].parent == "KyClient"
    assert sym_dict["constructor"].qualified_name == "source.core.client.KyClient.constructor"

    assert "get" in sym_dict
    assert sym_dict["get"].kind == "method"
    assert sym_dict["get"].parent == "KyClient"
    assert sym_dict["get"].attrs.get("async") is True
    assert sym_dict["get"].qualified_name == "source.core.client.KyClient.get"

    assert "createClient" in sym_dict
    assert sym_dict["createClient"].kind == "function"
    assert sym_dict["createClient"].qualified_name == "source.core.client.createClient"

    assert "helper" in sym_dict
    assert sym_dict["helper"].kind == "function"
    assert sym_dict["helper"].qualified_name == "source.core.client.helper"

    assert "calc" in sym_dict
    assert sym_dict["calc"].kind == "function"
    assert sym_dict["calc"].qualified_name == "source.core.client.calc"


def test_js_import_extraction():
    """Verify extraction of ESM imports, re-exports, CommonJS require(), and dynamic import()."""
    code = b"""
import defaultExport from "module-name";
import * as name from "module-name";
import { export1, export2 as alias2 } from "./local.js";
import type { TypeA } from "./types.js";
import "side-effect";

export { name1, name2 } from "./other.js";
export * from "./all.js";

const cjs = require("./cjs-module");
const dyn = import("./dynamic-module");
"""
    adapter = JsAdapter()
    tree = adapter.parse(code, Path("src/index.ts"))
    imports = adapter.extract_imports(tree, code, "src/index.ts")

    specifiers = [i.specifier for i in imports]
    assert "module-name" in specifiers
    assert "./local.js" in specifiers
    assert "./types.js" in specifiers
    assert "side-effect" in specifiers
    assert "./other.js" in specifiers
    assert "./all.js" in specifiers
    assert "./cjs-module" in specifiers
    assert "./dynamic-module" in specifiers

    local_imp = [i for i in imports if i.specifier == "./local.js"][0]
    assert local_imp.kind == "relative"
    assert "export1" in local_imp.names
    assert "export2" in local_imp.names
    assert local_imp.aliases.get("export2") == "alias2"


def test_resolve_relative_with_extension_rewriting():
    """Verify .js -> .ts / .tsx rewriting and extensionless resolution."""
    adapter = JsAdapter()
    context = ProjectContext(
        roots=["."],
        all_files={
            "source/core/Ky.ts",
            "source/core/constants.ts",
            "source/utils/helpers.tsx",
            "source/components/Button/index.tsx",
        },
    )

    # 1. Modern TS ESM .js -> .ts
    rec1 = ImportRecord(specifier="./core/Ky.js", kind="relative")
    res1 = adapter.resolve_import(rec1, "source/index.ts", context)
    assert res1 == "source/core/Ky.ts"

    # 2. .js -> .tsx
    rec2 = ImportRecord(specifier="./utils/helpers.js", kind="relative")
    res2 = adapter.resolve_import(rec2, "source/index.ts", context)
    assert res2 == "source/utils/helpers.tsx"

    # 3. Extensionless file
    rec3 = ImportRecord(specifier="./core/constants", kind="relative")
    res3 = adapter.resolve_import(rec3, "source/index.ts", context)
    assert res3 == "source/core/constants.ts"

    # 4. Directory index resolution
    rec4 = ImportRecord(specifier="./components/Button", kind="relative")
    res4 = adapter.resolve_import(rec4, "source/index.ts", context)
    assert res4 == "source/components/Button/index.tsx"

    # 5. Unresolved
    rec5 = ImportRecord(specifier="./nonexistent.js", kind="relative")
    res5 = adapter.resolve_import(rec5, "source/index.ts", context)
    assert res5 == "unresolved"


def test_resolve_tsconfig_paths_and_workspaces():
    """Verify tsconfig paths alias and monorepo workspace package resolution."""
    adapter = JsAdapter()
    repo_files = {
        "package.json",
        "tsconfig.json",
        "packages/core/package.json",
        "packages/core/src/index.ts",
        "packages/core/src/utils.ts",
        "packages/web/package.json",
        "packages/web/src/app.ts",
        "packages/web/src/index.ts",
    }
    context = ProjectContext(
        target_path="tests/fixtures/ts_monorepo",
        roots=[".", "packages/core", "packages/web"],
        all_files=repo_files,
    )

    # 1. tsconfig paths alias: @core/utils -> packages/core/src/utils.ts
    rec1 = ImportRecord(specifier="@core/utils", kind="from")
    res1 = adapter.resolve_import(rec1, "packages/web/src/app.ts", context)
    assert res1 == "packages/core/src/utils.ts"

    # 2. Monorepo workspace package name: @monorepo/core -> packages/core/src/index.ts
    rec2 = ImportRecord(specifier="@monorepo/core", kind="from")
    res2 = adapter.resolve_import(rec2, "packages/web/src/app.ts", context)
    assert res2 == "packages/core/src/index.ts"

    # 3. External package: express
    rec3 = ImportRecord(specifier="express", kind="from")
    res3 = adapter.resolve_import(rec3, "packages/web/src/app.ts", context)
    assert res3 == "external:express"

    # 4. Scoped external package: @sindresorhus/is
    rec4 = ImportRecord(specifier="@sindresorhus/is", kind="from")
    res4 = adapter.resolve_import(rec4, "packages/web/src/app.ts", context)
    assert res4 == "external:@sindresorhus/is"


def test_express_and_nextjs_patterns():
    """Verify pattern extraction for Express and Next.js routes."""
    adapter = JsAdapter()

    # Express routes
    express_code = b"""
const express = require('express');
const app = express();
const router = express.Router();

app.get('/api/users', getUsers);
app.post('/api/users', async (req, res) => { res.json({ ok: true }); });
router.delete('/items/:id', deleteItem);
app.use('/auth', authRouter);
"""
    tree_exp = adapter.parse(express_code, Path("src/server.js"))
    pats_exp = adapter.extract_patterns(tree_exp, express_code, "src/server.js")
    exp_names = [p["name"] for p in pats_exp]
    assert "GET /api/users" in exp_names
    assert "POST /api/users" in exp_names
    assert "DELETE /items/:id" in exp_names
    assert "USE /auth" in exp_names

    get_route = [p for p in pats_exp if p["name"] == "GET /api/users"][0]
    assert get_route["handler"] == "getUsers"
    assert get_route["url_path"] == "/api/users"

    # Next.js App Router
    next_code = b"""
import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  return NextResponse.json({ ok: true });
}

export async function POST(request: Request) {
  return NextResponse.json({ created: true });
}
"""
    tree_next = adapter.parse(next_code, Path("app/api/items/route.ts"))
    pats_next = adapter.extract_patterns(tree_next, next_code, "app/api/items/route.ts")
    next_names = [p["name"] for p in pats_next]
    assert "GET /api/items" in next_names
    assert "POST /api/items" in next_names


def test_parse_ky_sample():
    """Integration test parsing samples/ky/source/index.ts."""
    ky_index = Path("samples/ky/source/index.ts")
    if not ky_index.is_file():
        pytest.skip("samples/ky is not cloned")

    content = ky_index.read_bytes()
    adapter = get_adapter("typescript")
    assert adapter is not None

    tree = adapter.parse(content, ky_index)
    symbols = adapter.extract_symbols(tree, content, "source/index.ts")
    imports = adapter.extract_imports(tree, content, "source/index.ts")

    assert len(symbols) > 0
    assert len(imports) >= 7

    # Verify Ky is imported from ./core/Ky.js
    ky_imp = [i for i in imports if i.specifier == "./core/Ky.js"]
    assert len(ky_imp) == 1
    assert "Ky" in ky_imp[0].names
