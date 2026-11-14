// 2026-11-14: pedidos del usuario «HBO plus 117 también / HBO pop también / HBO Xtreme también /
// 121 ID a lista 1 / 124 love nature 4k a lista 1 / 122 love nature, el primero que se ve también a
// lista 1. Ese es en español / 125 MTV classic a lista 1 / 132 Star tve a lista 1».
// Ubicados por nombre: la TV del usuario tenía una fila más antes (la HBO Plus que borró desde la app).
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { approveLayout, buildPresentationOverrides, formatJson, normalizeLists, validateLayout } from "../../site/editor-core.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const LAYOUT = join(ROOT, "data/channel-editor-layout.json");
const PRESENTATION = join(ROOT, "presentation-overrides.json");
const DOCS = "Documentales, cultura, historia y naturaleza";
const layout = JSON.parse(readFileSync(LAYOUT, "utf8"));
const find = (id) => { const r = layout.channels.find((x) => x.tvgId === id); if (!r) throw new Error(`no está ${id}`); return r; };
const l1 = (group) => layout.channels.filter((r) => r.sourceList === "1.m3u" && r.group === group);
const after = (anchor, n) => anchor.order + n / 10;
const hboFamily = find("PublicDirect.c9a179f36540c93c7e6a67b6");
const realWild = find("RealWild.us");
const turbo = find("PublicDirect.7e4fe7ff47c91a001130c27b");
const tve = find("TVEInternacionalAmerica.es@HD");
const lastMusic = l1("Música").sort((a, b) => b.order - a.order)[0];
const MOVES = [
  ["PublicDirect.74b1d039a89a6947afe30ac0", "Cine", after(hboFamily, 1)],      // HBO Plus
  ["PublicDirect.ed2f1446ddbf0b5ac126fcdf", "Cine", after(hboFamily, 2)],      // HBO Pop
  ["PublicDirect.e1bd14954343adc40818b7c7", "Cine", after(hboFamily, 3)],      // HBO Xtreme
  ["PublicDirect.edc3a37181c9a6915fb578c6", DOCS, after(realWild, 1)],         // Love Nature (español)
  ["IPTVOrg.LoveNature.ca-4K", DOCS, after(realWild, 2)],                      // Love Nature 4K
  ["PublicDirect.d56376275161ef53614ac137", DOCS, after(turbo, 5)],            // Investigation Discovery
  ["IPTVOrg.MTVClassic.us-BR", "Música", after(lastMusic, 5)],                 // MTV Classic (el primero)
  ["PublicDirect.e221e27dc18d5a97a4054237", "Internacional", after(tve, 5)],   // Star TVE
];
for (const [id, group, order] of MOVES) {
  const r = find(id);
  if (r.sourceList !== "2.m3u") throw new Error(`${r.displayName} no está en Lista 2`);
  r.sourceList = "1.m3u"; delete r.trial; r.group = group; r.order = order;
}
layout.channels.sort((a, b) => a.order - b.order);
const approved = await approveLayout(normalizeLists(layout), "chat");
const problems = validateLayout(approved);
if (problems.length) throw new Error(`layout invalido: ${problems.join(" | ")}`);
writeFileSync(LAYOUT, formatJson(approved), "utf8");
const presentation = buildPresentationOverrides(approved, JSON.parse(readFileSync(PRESENTATION, "utf8")));
for (const [id, group] of MOVES) {
  const line = presentation.info_lines?.[id];
  if (line) presentation.info_lines[id] = line.replace(/group-title="[^"]*"/, `group-title="${group}"`);
}
writeFileSync(PRESENTATION, formatJson(presentation), "utf8");
for (const [id] of MOVES) {
  const r = approved.channels.find((x) => x.tvgId === id);
  console.log(r.number, r.displayName, "·", r.group);
}
