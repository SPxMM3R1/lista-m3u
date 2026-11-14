// 2026-11-14: pedidos del usuario «El 087 amc a lista 1 y buscarle un logo blanco» y «116 HBO family a
// lista 1». Ambos pasan de Lista 2 a Lista 1 en «Cine»: HBO Family después de HBO 2 y AMC al final del
// grupo (después de Golden Edge). AMC usa logos/amc-blanco.png (el logo oficial, en blanco).
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { approveLayout, buildPresentationOverrides, formatJson, normalizeLists, validateLayout } from "../../site/editor-core.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const LAYOUT = join(ROOT, "data/channel-editor-layout.json");
const PRESENTATION = join(ROOT, "presentation-overrides.json");
const AMC = "PublicDirect.b8d68bcc53d0374118476dfc";
const HBO_FAMILY = "PublicDirect.c9a179f36540c93c7e6a67b6";
const HBO2 = "PublicDirect.0812ad5e7a912f09fdebd000";
const GOLDEN_EDGE = "PublicDirect.d232b1eca5d8562c42007165";
const CINE = "Cine";
const AMC_LOGO = "logos/amc-blanco.png";
const layout = JSON.parse(readFileSync(LAYOUT, "utf8"));
const find = (id) => layout.channels.find((r) => r.tvgId === id);
const amc = find(AMC), fam = find(HBO_FAMILY), hbo2 = find(HBO2), edge = find(GOLDEN_EDGE);
if (amc.sourceList !== "2.m3u" || fam.sourceList !== "2.m3u") throw new Error("estado inesperado");
for (const r of [amc, fam]) { r.sourceList = "1.m3u"; delete r.trial; r.group = CINE; }
fam.order = hbo2.order + 0.5;
amc.order = edge.order + 0.5;
amc.logoPath = AMC_LOGO;
amc.logoOverride = AMC_LOGO;
layout.channels.sort((a, b) => a.order - b.order);
const approved = await approveLayout(normalizeLists(layout), "chat");
const problems = validateLayout(approved);
if (problems.length) throw new Error(`layout invalido: ${problems.join(" | ")}`);
writeFileSync(LAYOUT, formatJson(approved), "utf8");
const presentation = buildPresentationOverrides(approved, JSON.parse(readFileSync(PRESENTATION, "utf8")));
// La línea EXTINF guardada no se actualiza sola (AGENTS.md, 2026-10-28): grupo y logo.
for (const id of [AMC, HBO_FAMILY]) {
  const line = presentation.info_lines?.[id];
  if (!line) continue;
  let fixed = line.replace(/group-title="[^"]*"/, `group-title="${CINE}"`);
  if (id === AMC) fixed = fixed.replace(/tvg-logo="[^"]*"/, `tvg-logo="https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/${AMC_LOGO}"`);
  presentation.info_lines[id] = fixed;
}
writeFileSync(PRESENTATION, formatJson(presentation), "utf8");
for (const id of [AMC, HBO_FAMILY]) {
  const r = approved.channels.find((x) => x.tvgId === id);
  console.log(r.displayName, r.sourceList, r.number, r.group, r.logoOverride || r.logoPath);
}
