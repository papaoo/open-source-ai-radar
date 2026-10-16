// Zero-dependency Cmd/Ctrl+K command palette.
//
// Builds its own overlay DOM on first invocation, indexes the main-nav links
// (read straight from the rendered header) plus a lazily-fetched, compact
// project index (dist/search-index.json). Fuzzy match, arrow-key navigation,
// Enter to go, Esc to close, and a focus trap. Fully static + theme/language
// aware (labels re-render from i18n on `radar:lang`).

import { t, getLang } from "./i18n";

type Item = {
  group: "nav" | "projects";
  label: string;
  sub?: string;
  href: string;
  hay: string;
};

let overlay: HTMLElement | null = null;
let input: HTMLInputElement | null = null;
let listEl: HTMLElement | null = null;
let items: Item[] = [];
let results: Item[] = [];
let active = 0;
let loaded = false;
let open = false;

const BASE = (import.meta.env && (import.meta.env as any).BASE_URL) || "/";

// ── Fuzzy scoring: subsequence match with word-start + contiguous boosts ──
function score(hay: string, needle: string): number {
  if (!needle) return 1;
  const h = hay.toLowerCase();
  const n = needle.toLowerCase();
  const direct = h.indexOf(n);
  if (direct === 0) return 1000;
  if (direct > 0) return 600 - direct;
  let hi = 0;
  let sc = 0;
  for (let i = 0; i < n.length; i++) {
    const c = n[i];
    const found = h.indexOf(c, hi);
    if (found === -1) return -1;
    sc += found === hi ? 10 : 3;
    if (found > 0 && (h[found - 1] === "/" || h[found - 1] === "-" || h[found - 1] === " ")) sc += 8;
    hi = found + 1;
  }
  return sc;
}

function navItems(): Item[] {
  const links = Array.from(document.querySelectorAll<HTMLElement>(".nav-links a[role='menuitem']"));
  return links
    .filter((a) => a.getAttribute("href") !== BASE) // Home is always reachable via logo
    .map((a) => ({
      group: "nav" as const,
      label: a.textContent?.trim() || "",
      href: a.getAttribute("href") || "#",
      hay: (a.getAttribute("href") || "") + " " + (a.textContent || ""),
    }));
}

async function ensureProjects(): Promise<void> {
  if (loaded) return;
  loaded = true;
  try {
    const res = await fetch(`${BASE}search-index.json`);
    const data = await res.json();
    const proj: Item[] = (data.projects || []).map((p: any) => ({
      group: "projects" as const,
      label: p.n,
      sub: p.s != null ? String(p.s) : undefined,
      href: `${BASE}project/${encodeURIComponent(String(p.n).split("/")[0])}/${encodeURIComponent(String(p.n).split("/").slice(1).join("/"))}`,
      hay: `${p.n} ${p.c || ""} ${p.d || ""}`,
    }));
    items = items.concat(proj);
    render(input?.value || "");
  } catch {
    /* index unavailable — nav-only palette */
  }
}

function match(query: string): Item[] {
  const all = navItems().concat(items);
  if (!query.trim()) {
    // Default: show navigation, then a handful of top projects.
    const nav = all.filter((i) => i.group === "nav");
    const proj = all.filter((i) => i.group === "projects").slice(0, 8);
    return nav.concat(proj);
  }
  return all
    .map((i) => ({ i, s: score(i.hay, query) }))
    .filter((x) => x.s >= 0)
    .sort((a, b) => b.s - a.s)
    .slice(0, 30)
    .map((x) => x.i);
}

const SEARCH_ICON =
  '<svg class="pi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>';
const NAV_ICON =
  '<svg class="pi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>';
const REPO_ICON =
  '<svg class="pi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>';

function render(query: string): void {
  if (!listEl) return;
  results = match(query);
  active = 0;
  listEl.textContent = "";
  const lang = getLang();

  if (!results.length) {
    const empty = document.createElement("div");
    empty.className = "palette__group-label";
    empty.textContent = t("cmdk.noResults", lang);
    listEl.appendChild(empty);
    return;
  }

  let lastGroup = "";
  results.forEach((r, idx) => {
    if (r.group !== lastGroup) {
      lastGroup = r.group;
      const g = document.createElement("div");
      g.className = "palette__group-label";
      g.textContent = t(r.group === "nav" ? "cmdk.nav" : "cmdk.projects", lang);
      listEl!.appendChild(g);
    }
    const row = document.createElement("a");
    row.className = "palette__item";
    row.href = r.href;
    row.setAttribute("role", "option");
    row.setAttribute("aria-selected", String(idx === active));
    row.dataset.index = String(idx);
    row.innerHTML = `${r.group === "nav" ? NAV_ICON : REPO_ICON}<span></span>${r.sub ? `<span class="pi-sub"></span>` : ""}`;
    (row.querySelector("span") as HTMLElement).textContent = r.label;
    if (r.sub) (row.querySelector(".pi-sub") as HTMLElement).textContent = r.sub;
    row.addEventListener("click", () => go(r.href));
    row.addEventListener("mousemove", () => setActive(idx));
    listEl!.appendChild(row);
  });
}

function setActive(idx: number): void {
  if (!listEl || !results.length) return;
  active = Math.max(0, Math.min(results.length - 1, idx));
  Array.from(listEl.querySelectorAll<HTMLElement>(".palette__item")).forEach((el) => {
    el.setAttribute("aria-selected", String(Number(el.dataset.index) === active));
  });
  const cur = listEl.querySelector<HTMLElement>(`.palette__item[data-index="${active}"]`);
  cur?.scrollIntoView({ block: "nearest" });
}

function go(href: string): void {
  window.location.href = href;
}

function build(): void {
  const lang = getLang();
  overlay = document.createElement("div");
  overlay.className = "palette-overlay";
  overlay.hidden = true;
  overlay.innerHTML = `
    <div class="palette" role="dialog" aria-modal="true" aria-label="Command palette">
      <div class="palette__input-row">
        ${SEARCH_ICON}
        <input class="palette__input" type="text" autocomplete="off" spellcheck="false" />
        <kbd class="kbd">Esc</kbd>
      </div>
      <div class="palette__list" role="listbox" aria-label="Results"></div>
      <div class="palette__foot">
        <span><kbd class="kbd">↑</kbd><kbd class="kbd">↓</kbd> <span data-hint="nav"></span></span>
        <span><kbd class="kbd">↵</kbd> <span data-hint="open"></span></span>
      </div>
    </div>`;
  document.body.appendChild(overlay);

  input = overlay.querySelector(".palette__input");
  listEl = overlay.querySelector(".palette__list");

  const hintNav = overlay.querySelector('[data-hint="nav"]');
  const hintOpen = overlay.querySelector('[data-hint="open"]');
  if (hintNav) hintNav.textContent = t("cmdk.hintNav", lang);
  if (hintOpen) hintOpen.textContent = t("cmdk.hintOpen", lang);
  if (input) input.placeholder = t("cmdk.placeholder", lang);

  input?.addEventListener("input", () => render(input!.value));
  input?.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive(active + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive(active - 1); }
    else if (e.key === "Enter") { e.preventDefault(); const r = results[active]; if (r) go(r.href); }
    else if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === "Tab") {
      // Focus trap: keep navigation within the dialog.
      e.preventDefault();
      const dir = e.shiftKey ? -1 : 1;
      setActive(active + dir);
    }
  });
  overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) close(); });
}

function show(): void {
  if (!overlay) build();
  open = true;
  overlay!.hidden = false;
  document.body.style.overflow = "hidden";
  // Re-localize labels (in case language changed since build).
  const lang = getLang();
  if (input) input.placeholder = t("cmdk.placeholder", lang);
  const hintNav = overlay!.querySelector('[data-hint="nav"]');
  const hintOpen = overlay!.querySelector('[data-hint="open"]');
  if (hintNav) hintNav.textContent = t("cmdk.hintNav", lang);
  if (hintOpen) hintOpen.textContent = t("cmdk.hintOpen", lang);
  render("");
  if (input) input.value = "";
  ensureProjects();
  requestAnimationFrame(() => input?.focus());
}

function close(): void {
  open = false;
  if (overlay) overlay.hidden = true;
  document.body.style.overflow = "";
}

function toggle(): void {
  if (open) close();
  else show();
}

export function initCommandPalette(): void {
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      toggle();
    }
  });

  // Optional in-page trigger buttons.
  document.addEventListener("click", (e) => {
    const btn = (e.target as Element)?.closest?.("[data-cmdk-open]") as HTMLElement | null;
    if (btn) { e.preventDefault(); show(); }
  });

  // Re-render open palette labels when language flips.
  document.addEventListener("radar:lang", () => {
    if (open && input) render(input.value);
  });
}
