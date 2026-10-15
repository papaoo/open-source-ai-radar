// Zero-dependency three-axis radar chart (Impact / Velocity / Health) rendered
// as inline SVG — no charting library, matching the site's "Radar" theme.

export type RadarValues = { impact: number; velocity: number; health: number };

export type RadarOptions = {
  size?: number;        // overall pixel size (square)
  showLabels?: boolean; // axis name labels at vertices
  labels?: [string, string, string]; // order: impact, velocity, health
  color?: string;       // stroke color (CSS value)
};

const DEFAULT_LABELS: [string, string, string] = ["Impact", "Velocity", "Health"];

/** Normalize a 0-100 value, clamped, guarding against NaN. */
function clamp(v: number): number {
  const n = Number(v);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(100, n));
}

/** Vertex coordinate for axis `i` at radius ratio `r` (0-1). */
function vertex(cx: number, cy: number, radius: number, i: number, r: number): [number, number] {
  const angle = -Math.PI / 2 + (i * 2 * Math.PI) / 3;
  return [cx + Math.cos(angle) * radius * r, cy + Math.sin(angle) * radius * r];
}

function pointsStr(cx: number, cy: number, radius: number, ratios: number[]): string {
  return ratios
    .map((ratio, i) => vertex(cx, cy, radius, i, ratio).map((p) => p.toFixed(1)).join(","))
    .join(" ");
}

/**
 * Build an SVG string for a triangular 3-axis radar.
 * Missing/zero axes render as a degenerate shape but never crash (useful when a
 * project lacks historical scoring data).
 */
export function radarSvg(values: RadarValues, opts: RadarOptions = {}): string {
  const size = opts.size ?? 220;
  const showLabels = opts.showLabels ?? true;
  const labels = opts.labels ?? DEFAULT_LABELS;
  const color = opts.color ?? "var(--accent)";

  const cx = size / 2;
  const cy = size / 2;
  const pad = showLabels ? size * 0.16 : size * 0.06;
  const radius = size / 2 - pad;

  const v = [clamp(values.impact), clamp(values.velocity), clamp(values.health)];
  const ratios = v.map((x) => x / 100);

  const gridLevels = [0.25, 0.5, 0.75, 1];
  let grid = "";
  for (const lv of gridLevels) {
    grid += `<polygon points="${pointsStr(cx, cy, radius, [lv, lv, lv])}" fill="none" stroke="var(--border)" stroke-width="1" opacity="${lv === 1 ? 0.9 : 0.5}"/>`;
  }

  let axes = "";
  for (let i = 0; i < 3; i++) {
    const [x, y] = vertex(cx, cy, radius, i, 1);
    axes += `<line x1="${cx.toFixed(1)}" y1="${cy.toFixed(1)}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="var(--border)" stroke-width="1" opacity="0.6"/>`;
  }

  const dataPoly = `<polygon points="${pointsStr(cx, cy, radius, ratios)}" fill="var(--accent-muted)" stroke="${color}" stroke-width="2" stroke-linejoin="round"/>`;

  let dots = "";
  for (let i = 0; i < 3; i++) {
    const [x, y] = vertex(cx, cy, radius, i, ratios[i]);
    dots += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3" fill="${color}"/>`;
  }

  let labelSvg = "";
  if (showLabels) {
    for (let i = 0; i < 3; i++) {
      const [x, y] = vertex(cx, cy, radius + pad * 0.6, i, 1);
      const anchor = Math.abs(x - cx) < 2 ? "middle" : x > cx ? "start" : "end";
      labelSvg += `<text x="${x.toFixed(1)}" y="${(y + 4).toFixed(1)}" text-anchor="${anchor}">${escapeXml(labels[i])} ${Math.round(v[i])}</text>`;
    }
  }

  return `<svg class="radar-chart" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Impact ${Math.round(v[0])}, Velocity ${Math.round(v[1])}, Health ${Math.round(v[2])}">${grid}${axes}${dataPoly}${dots}${labelSvg}</svg>`;
}

/** Compact label-free radar for cards / dense lists. */
export function miniRadarSvg(values: RadarValues, size = 56): string {
  return radarSvg(values, { size, showLabels: false });
}

export type RadarSeries = { name: string; values: RadarValues; color: string };

/**
 * Overlay several three-axis radars in one chart (compare page). Each series
 * draws a translucent polygon in its own color, with a legend underneath.
 */
export function overlayRadarSvg(
  series: RadarSeries[],
  opts: { size?: number; labels?: [string, string, string] } = {},
): string {
  const size = opts.size ?? 260;
  const labels = opts.labels ?? DEFAULT_LABELS;
  const cx = size / 2;
  const cy = size / 2;
  const pad = size * 0.16;
  const radius = size / 2 - pad;

  let grid = "";
  for (const lv of [0.25, 0.5, 0.75, 1]) {
    grid += `<polygon points="${pointsStr(cx, cy, radius, [lv, lv, lv])}" fill="none" stroke="var(--border)" stroke-width="1" opacity="${lv === 1 ? 0.9 : 0.5}"/>`;
  }
  let axes = "";
  for (let i = 0; i < 3; i++) {
    const [x, y] = vertex(cx, cy, radius, i, 1);
    axes += `<line x1="${cx.toFixed(1)}" y1="${cy.toFixed(1)}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="var(--border)" stroke-width="1" opacity="0.6"/>`;
  }
  let labelSvg = "";
  for (let i = 0; i < 3; i++) {
    const [x, y] = vertex(cx, cy, radius + pad * 0.6, i, 1);
    const anchor = Math.abs(x - cx) < 2 ? "middle" : x > cx ? "start" : "end";
    labelSvg += `<text x="${x.toFixed(1)}" y="${(y + 4).toFixed(1)}" text-anchor="${anchor}">${escapeXml(labels[i])}</text>`;
  }

  let polys = "";
  for (const s of series) {
    const v = [clamp(s.values.impact), clamp(s.values.velocity), clamp(s.values.health)];
    const ratios = v.map((x) => x / 100);
    polys += `<polygon points="${pointsStr(cx, cy, radius, ratios)}" fill="${s.color}" fill-opacity="0.14" stroke="${s.color}" stroke-width="2" stroke-linejoin="round"/>`;
  }

  const legend = series
    .map(
      (s) =>
        `<span class="radar-legend__item"><span class="radar-legend__swatch" style="background:${s.color}"></span>${escapeXml(s.name)}</span>`,
    )
    .join("");

  return `<svg class="radar-chart" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Compare radar">${grid}${axes}${polys}${labelSvg}</svg><div class="radar-legend">${legend}</div>`;
}

function escapeXml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
