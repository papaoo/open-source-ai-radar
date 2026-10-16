// Zero-dependency data-visualization primitives for Open Source AI Radar.
//
// Every function is PURE and returns an HTML/SVG string so it can be rendered
// at build time in Astro frontmatter (no client JS, no chart library). Colors
// are delegated to CSS classes (see viz.css) so charts recolor with the
// light/dark theme automatically; where a dynamic color is needed we return an
// inline rgba computed from a two-stop heat scale.

export type SparkOptions = {
  width?: number;
  height?: number;
  pad?: number;
  area?: boolean;
  dot?: boolean;
  large?: boolean;
};

function clamp01(v: number): number {
  const n = Number(v);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(1, n));
}

function pointsToPath(values: number[], w: number, h: number, pad: number): { pts: string; line: string; area: string; last: [number, number] } {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const innerW = w - pad * 2;
  const innerH = h - pad * 2;
  const step = values.length > 1 ? innerW / (values.length - 1) : 0;
  const coords = values.map((v, i) => {
    const x = pad + i * step;
    const y = h - pad - ((v - min) / range) * innerH;
    return [x, y] as [number, number];
  });
  const line = coords.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const last = coords[coords.length - 1];
  const area = `${pad},${h - pad} ${line} ${last[0].toFixed(1)},${h - pad}`;
  return { pts: line, line, area, last };
}

/** Compact sparkline (table cells / cards). Returns '' for fewer than 2 points. */
export function sparkline(values: number[], opts: SparkOptions = {}): string {
  const clean = (values || []).map(Number).filter((v) => Number.isFinite(v));
  if (clean.length < 2) return "";
  const width = opts.width ?? 64;
  const height = opts.height ?? 22;
  const pad = opts.pad ?? 2;
  const area = opts.area ?? true;
  const dot = opts.dot ?? true;
  const { line, area: areaPts, last } = pointsToPath(clean, width, height, pad);

  const first = clean[0];
  const lastV = clean[clean.length - 1];
  const dir = lastV > first ? "up" : lastV < first ? "down" : "flat";

  let body = "";
  if (area) body += `<polygon class="spark-area spark-${dir}" points="${areaPts}"/>`;
  body += `<polyline class="spark-line spark-${dir}" points="${line}"/>`;
  if (dot) body += `<circle class="spark-dot spark-${dir}" cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="2"/>`;

  const cls = `spark${opts.large ? " spark--lg" : ""}`;
  return `<svg class="${cls}" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">${body}</svg>`;
}

export type TrendOptions = {
  width?: number;
  height?: number;
  pad?: number;
  gradientId?: string;
  color?: string;
};

/** Larger trend/area chart with a soft gradient fill and an end marker. */
export function trendChart(values: number[], opts: TrendOptions = {}): string {
  const clean = (values || []).map(Number).filter((v) => Number.isFinite(v));
  if (clean.length < 2) return "";
  const width = opts.width ?? 640;
  const height = opts.height ?? 160;
  const pad = opts.pad ?? 10;
  const color = opts.color ?? "var(--accent)";
  const gid = opts.gradientId ?? `trend-${Math.random().toString(36).slice(2, 8)}`;
  const { line, area: areaPts, last } = pointsToPath(clean, width, height, pad);

  return `<svg class="spark spark--lg" width="100%" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Trend">
  <defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="${color}" stop-opacity="0.28"/>
    <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
  </linearGradient></defs>
  <polygon points="${areaPts}" fill="url(#${gid})"/>
  <polyline points="${line}" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="3" fill="${color}"/>
</svg>`;
}

export type GaugeOptions = {
  size?: number;
  label?: string;
  color?: string;
  suffix?: string;
};

/** Radial percentage gauge (percentile / health). value is 0-100. */
export function gauge(value: number, opts: GaugeOptions = {}): string {
  const v = Number(value);
  const pct = clamp01((Number.isFinite(v) ? v : 0) / 100);
  const size = opts.size ?? 88;
  const stroke = 6;
  const r = size / 2 - stroke;
  const c = 2 * Math.PI * r;
  const color = opts.color ?? "var(--accent)";
  const label = opts.label ?? "";
  const disp = `${Math.round(pct * 100)}${opts.suffix ?? ""}`;
  return `<svg class="gauge" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="${escapeXml(label || disp)}">
  <circle class="gauge-track" cx="${size / 2}" cy="${size / 2}" r="${r.toFixed(1)}"/>
  <circle class="gauge-arc" cx="${size / 2}" cy="${size / 2}" r="${r.toFixed(1)}" stroke="${color}" stroke-dasharray="${(pct * c).toFixed(1)} ${c.toFixed(1)}" transform="rotate(-90 ${size / 2} ${size / 2})"/>
  <text class="gauge-value" x="50%" y="50%" dy="0.35em" text-anchor="middle" font-size="${(size * 0.26).toFixed(0)}">${escapeXml(disp)}</text>
  ${label ? `<text class="gauge-label" x="50%" y="${size - 6}" text-anchor="middle">${escapeXml(label)}</text>` : ""}
</svg>`;
}

export type Bin = { label: string; count: number };

/** Simple vertical bar histogram from pre-bucketed counts. */
export function histogram(bins: Bin[], opts: { width?: number; height?: number } = {}): string {
  const data = (bins || []).filter((b) => b && Number.isFinite(Number(b.count)));
  if (!data.length) return "";
  const width = opts.width ?? 320;
  const height = opts.height ?? 96;
  const pad = 4;
  const max = Math.max(...data.map((b) => b.count), 1);
  const slot = (width - pad * 2) / data.length;
  const gap = Math.min(4, slot * 0.25);
  const innerH = height - pad * 2 - 12;

  let bars = "";
  let labels = "";
  data.forEach((b, i) => {
    const bh = (b.count / max) * innerH;
    const x = pad + i * slot + gap / 2;
    const y = height - pad - 12 - bh;
    bars += `<rect class="histo-bar" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${(slot - gap).toFixed(1)}" height="${bh.toFixed(1)}" rx="2"><title>${escapeXml(b.label)}: ${b.count}</title></rect>`;
    labels += `<text x="${(x + (slot - gap) / 2).toFixed(1)}" y="${height - pad}" text-anchor="middle">${escapeXml(b.label)}</text>`;
  });
  const axisY = height - pad - 12;
  return `<svg class="histo" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Distribution">
  <line class="histo-axis" x1="${pad}" y1="${axisY}" x2="${width - pad}" y2="${axisY}"/>
  ${bars}${labels}
</svg>`;
}

export type BarItem = { label: string; value: number; display?: string; color?: string };

/** Horizontal distribution bars (language / category). Returns HTML (not SVG). */
export function bars(items: BarItem[], opts: { max?: number } = {}): string {
  const data = (items || []).filter((b) => b && Number.isFinite(Number(b.value)));
  if (!data.length) return "";
  const max = opts.max ?? Math.max(...data.map((b) => b.value), 1);
  const rows = data
    .map((b) => {
      const pct = Math.round(clamp01(b.value / max) * 100);
      const style = b.color ? ` style="background:${b.color};width:${pct}%"` : ` style="width:${pct}%"`;
      const disp = b.display ?? String(b.value);
      return `<div class="bar-row">
      <span class="bar-row__label" title="${escapeXml(b.label)}">${escapeXml(b.label)}</span>
      <span class="bar-row__track"><span class="bar-row__fill"${style}></span></span>
      <span class="bar-row__value">${escapeXml(disp)}</span>
    </div>`;
    })
    .join("");
  return `<div class="bars">${rows}</div>`;
}

/** Linear score meter. */
export function meter(percent: number, tone: "" | "green" | "amber" | "red" = ""): string {
  const pct = Math.round(clamp01((Number(percent) || 0) / 100) * 100);
  return `<span class="meter${tone ? " meter--" + tone : ""}"><i style="width:${pct}%"></i></span>`;
}

export type DeltaOptions = { label?: string; suffix?: string };

/** Colored delta chip with a directional arrow. n is the signed change. */
export function deltaChip(n: number | null | undefined, opts: DeltaOptions = {}): string {
  const val = Number(n);
  const suffix = opts.suffix ?? "";
  const label = opts.label ? ` ${escapeXml(opts.label)}` : "";
  if (!Number.isFinite(val) || val === 0) {
    return `<span class="delta delta--flat">±0${escapeXml(suffix)}${label}</span>`;
  }
  const up = val > 0;
  const arrow = up
    ? `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M8 13V3"/><path d="M3.5 7.5 8 3l4.5 4.5"/></svg>`
    : `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3v10"/><path d="M3.5 8.5 8 13l4.5-4.5"/></svg>`;
  const text = `${up ? "+" : ""}${val.toLocaleString()}${escapeXml(suffix)}`;
  return `<span class="delta delta--${up ? "up" : "down"}">${arrow}${text}${label}</span>`;
}

// ── Heat color scale (two-stop rgba interpolation between CSS-var fallbacks) ──
const HEAT_LO = [99, 102, 241]; // indigo-ish low
const HEAT_HI = [59, 130, 246]; // accent blue high

/** Return an rgba() string for a 0-1 normalized heat value. */
export function heatColor(t01: number, alpha = 0.9): string {
  const f = clamp01(t01);
  const ch = HEAT_LO.map((lo, i) => Math.round(lo + (HEAT_HI[i] - lo) * f));
  return `rgba(${ch[0]}, ${ch[1]}, ${ch[2]}, ${alpha})`;
}

/** Normalized 0-1 position of `value` within [min,max]. */
export function norm(value: number, min: number, max: number): number {
  if (max === min) return 0;
  return clamp01((value - min) / (max - min));
}

function escapeXml(s: string): string {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
