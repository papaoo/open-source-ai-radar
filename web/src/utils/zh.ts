// Build-time loader for machine-translated project descriptions.
//
// `radar translate` writes `data/exports/descriptions.zh.json` as a flat map of
// English source text -> Chinese translation. Pages read it once during the
// static build and emit `data-desc-zh` attributes; the client swaps text on
// language toggle (see lib/i18n applyI18n). If the file is absent (feature not
// run / no network), the map is empty and every page degrades to English.

import { readFileSync } from "fs";
import { join } from "path";

let map: Record<string, string> = {};
try {
  map = JSON.parse(
    readFileSync(join(process.cwd(), "..", "data", "exports", "descriptions.zh.json"), "utf-8"),
  );
} catch {
  map = {};
}

/** Return the cached Chinese translation for an English description, or "". */
export function zhDesc(en?: string | null): string {
  if (!en) return "";
  return map[en] || "";
}

/** True when any translation cache was loaded. */
export const hasZhCache = Object.keys(map).length > 0;
