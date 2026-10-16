// Local "pinned projects" watchlist. Pure client-side over localStorage —
// no accounts, no backend (the site stays fully static). Any element with
// class .pin-btn and a data-full-name attribute toggles a pin; state is
// reflected via [data-pinned] and a `radar:pins` event so lists can re-filter.

const STORAGE_KEY = "radar-pins";

function read(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function write(list: string[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  } catch {
    /* storage unavailable (private mode) — degrade silently */
  }
}

export function getPins(): string[] {
  return read();
}

export function isPinned(name: string): boolean {
  return read().includes(name);
}

export function togglePin(name: string): boolean {
  const set = new Set(read());
  const has = set.has(name);
  if (has) set.delete(name);
  else set.add(name);
  write([...set]);
  document.dispatchEvent(new CustomEvent("radar:pins", { detail: { name, pinned: !has } }));
  return !has;
}

export function subscribePins(cb: () => void): void {
  document.addEventListener("radar:pins", cb);
}

function escapeHtml(s: string): string {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
void escapeHtml; // retained for callers that need attribute-safe strings

/** Reflect pin state on every .pin-btn under root and (once) wire a delegated
 *  click handler so dynamically re-rendered buttons keep working. */
export function wirePinButtons(root: ParentNode = document): void {
  refreshButtonStates(root);
  if (!(wirePinButtons as any)._wired) {
    (wirePinButtons as any)._wired = true;
    document.addEventListener("click", (e) => {
      const btn = (e.target as Element)?.closest?.(".pin-btn[data-full-name]") as HTMLElement | null;
      if (!btn) return;
      e.preventDefault();
      e.stopPropagation();
      togglePin(btn.dataset.fullName!);
    });
    subscribePins(() => refreshButtonStates(document));
  }
}

function refreshButtonStates(root: ParentNode): void {
  root.querySelectorAll<HTMLElement>(".pin-btn[data-full-name]").forEach((btn) => {
    const pinned = isPinned(btn.dataset.fullName!);
    btn.dataset.pinned = String(pinned);
    btn.setAttribute("aria-pressed", String(pinned));
  });
}

/** Render a pinned-projects grid (home). Shows/hides the section by emptiness.
 *  Built with DOM nodes (no innerHTML) so tampered localStorage values can
 *  never inject markup. */
export function renderPinnedGrid(sectionSel: string, gridSel: string, base: "/"): void {
  const section = document.querySelector(sectionSel) as HTMLElement | null;
  const grid = document.querySelector(gridSel) as HTMLElement | null;
  if (!section || !grid) return;
  const pins = read();
  section.hidden = pins.length === 0;
  grid.textContent = "";
  for (const name of pins) {
    const [owner, repo] = name.split("/");
    const href = repo ? `${base}project/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}` : `${base}`;
    const link = document.createElement("a");
    link.className = "heat-cell";
    link.href = href;
    link.style.textDecoration = "none";
    link.style.color = "inherit";
    const bar = document.createElement("span");
    bar.className = "heat-cell__bar";
    bar.style.background = "var(--accent)";
    const nameEl = document.createElement("div");
    nameEl.className = "heat-cell__name";
    nameEl.textContent = name;
    const meta = document.createElement("div");
    meta.className = "heat-cell__meta";
    const label = document.createElement("span");
    label.setAttribute("data-i18n", "pin.remove");
    label.textContent = "Remove pin";
    meta.appendChild(label);
    link.append(bar, nameEl, meta);
    grid.appendChild(link);
  }
}
