// 2026-11-15: pedido del usuario «¿Por qué los Natgeo no están como backups entre ellos?» → «aplícalas».
// Fotogramas simultáneos (2026-11-14): los 4 National Geographic de Lista 2 daban la misma escena
// («Secretos de cuerpos antiguos») con unos segundos de desfase entre servidores, por eso las rondas de
// clones (fotograma al mismo instante) no los unieron. Principal: 5fa93eee (200.7.99.59, 1080p 59,94,
// AC3); los otros tres pasan a respaldo (con los suyos) y salen de la lista.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { approveLayout, buildPresentationOverrides, formatJson, normalizeLists, validateLayout } from "../../site/editor-core.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const LAYOUT = join(ROOT, "data/channel-editor-layout.json");
const PRESENTATION = join(ROOT, "presentation-overrides.json");
const PRINCIPAL = "PublicDirect.5fa93eee31589e2105958c0e";
const MERGED = ["PublicDirect.f753ad9eb3f48c300c6fa4b4", "PublicDirect.8a5d0371ff496197a85a71b8", "PublicDirect.956ee9e1ecd09ce19202225f"];
const layout = JSON.parse(readFileSync(LAYOUT, "utf8"));
for (const id of MERGED) {
  const r = layout.channels.find((x) => x.tvgId === id);
  if (!r || r.state !== "active") throw new Error(`estado inesperado ${id}`);
  r.state = "deleted";
}
const approved = await approveLayout(normalizeLists(layout), "chat");
const problems = validateLayout(approved);
if (problems.length) throw new Error(`layout invalido: ${problems.join(" | ")}`);
writeFileSync(LAYOUT, formatJson(approved), "utf8");
const presentation = buildPresentationOverrides(approved, JSON.parse(readFileSync(PRESENTATION, "utf8")));
writeFileSync(PRESENTATION, formatJson(presentation), "utf8");
const p = approved.channels.find((x) => x.tvgId === PRINCIPAL);
console.log("principal", p.number, p.displayName, p.state);
