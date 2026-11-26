/**
 * cli service layer for view.
 *
 * Part of the 'CLI-S-VIEW-01' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * CLI-S-VIEW-01
 */
import { exportHtml } from "../../render/export-html.js";
import { writeFile } from "../../core/output.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the view workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function view(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: CLI-S-VIEW-01 — view cli service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("view: empty input, using defaults");
  }
  try {
        const html = await exportHtml();
        writeFile(`${out}/map.html`, html);
    hops.push("view");
    logger.info("{ name: 'view', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'view' }");
    return { ok: false, hops };
  }
}
