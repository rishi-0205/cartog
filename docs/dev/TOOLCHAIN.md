# Toolchain pins and minimums (E3/S7)

Cartog calls five external executables. Their versions are not vendored, so
this file records the versions Cartog is tested against ("pinned") and the
floor that `cartog doctor` enforces (`cartog/core/toolchain.py`).

| Tool | Pinned / tested | Minimum | Checked by |
|---|---|---|---|
| Node.js | 22.13.0 | 18.0.0 | `node --version` |
| mermaid-cli (`mmdc`) | 12.0.0 | 10.0.0 | `mmdc --version` |
| `scip-python` | 0.6.6 | 0.6.0 | `scip-python --version` |
| `scip-typescript` | 0.4.0 | 0.3.0 | `scip-typescript --version` |
| `madge` | 8.0.0 | 6.0.0 | `madge --version` |

`doctor` prints `PASS` when the installed version meets the minimum and a
`WARN` row of the form `<version> (below minimum v<minimum>)` otherwise. A tool
that is absent stays `MISSING`.

The browser libraries shipped inside `map.html` are pinned twice:

* version and licence in `cartog/render/assets/VENDOR_LOCK.json`;
* content by the `sha256` in that file, recomputed by
  `tests/test_security.py::test_vendor_asset_hashes_match_lock`.

| Vendored file | Upstream | Version | Licence |
|---|---|---|---|
| `cytoscape.min.js` | cytoscape | 3.34.4 | MIT |
| `cytoscape-expand-collapse.js` | cytoscape-expand-collapse | 4.1.1 | MIT |
| `cytoscape-fcose.js` | cytoscape-fcose | 2.2.0 | MIT |
| `layout-base.js` | layout-base | 2.0.1 | MIT |
| `cose-base.js` | cose-base | 2.2.0 | MIT |

To upgrade a vendored file: replace it, update `version` and `sha256` in
`VENDOR_LOCK.json`, run `pytest tests/test_security.py -k vendor -q`, and
regenerate `map.html` goldens if the new library changes output.
