// Static endpoint → dist/search-index.json (prerendered at build for
// output:'static'). A compact projection of projects-index.json used by the
// Cmd+K command palette. We cap to the top repos by radar score to keep the
// payload small (~a few hundred KB) while covering everything people search.
import { readFileSync } from 'fs';
import { join } from 'path';

export const prerender = true;

export function GET() {
  let projects: any[] = [];
  try {
    const idx = JSON.parse(
      readFileSync(join(process.cwd(), '..', 'data', 'exports', 'projects-index.json'), 'utf-8')
    );
    projects = idx.projects || [];
  } catch {
    projects = [];
  }

  const top = projects
    .slice()
    .sort((a, b) => (Number(b.radar_score) || 0) - (Number(a.radar_score) || 0))
    .slice(0, 1200)
    .map((p) => ({
      n: p.full_name,
      d: (p.description || '').slice(0, 120),
      s: Math.round((Number(p.radar_score) || 0) * 10) / 10,
      c: p.category || '',
    }));

  return new Response(JSON.stringify({ projects: top }), {
    headers: { 'content-type': 'application/json' },
  });
}
