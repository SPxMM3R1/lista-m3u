// 2026-11-14: pedido del usuario «134 stingray a lista 1». La única Stingray publicada en Lista 2 era
// «Stingray Concerts» (`PublicDirect.650a768cd537cb17d491e369`, 132 del layout). Su fotograma lleva la
// marca «Stingray iConcerts» (concierto de The Doobie Brothers) y no es el Qello Concerts de Lista 1
// (que a la misma hora pasaba su tanda). Se llama por su nombre real, con el logo de iConcerts
// (tv-logo/tv-logos, countries/spain/stingray-iconcerts-es.png: blanco y cian, se ve sobre fondo
// oscuro; el anterior era el de Qello, en negro), y queda en Música después de Stingray Classica.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { approveLayout, buildPresentationOverrides, formatJson, normalizeLists, validateLayout } from "../../site/editor-core.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const LAYOUT = join(ROOT, "data/channel-editor-layout.json");
const PRESENTATION = join(ROOT, "presentation-overrides.json");
const ID = "PublicDirect.650a768cd537cb17d491e369";
const NAME = "Stingray iConcerts";
const LOGO = "logos/stingray-iconcerts.png";
const layout = JSON.parse(readFileSync(LAYOUT, "utf8"));
const r = layout.channels.find((x) => x.tvgId === ID);
const classica = layout.channels.find((x) => x.tvgId === "StingrayClassica.ca");
if (r.sourceList !== "2.m3u") throw new Error("estado inesperado");
r.sourceList = "1.m3u"; delete r.trial; r.group = "Música"; r.order = classica.order + 0.5;
r.displayName = NAME; r.logoPath = LOGO; r.logoOverride = LOGO;
layout.channels.sort((a, b) => a.order - b.order);
const approved = await approveLayout(normalizeLists(layout), "chat");
const problems = validateLayout(approved);
if (problems.length) throw new Error(`layout invalido: ${problems.join(" | ")}`);
writeFileSync(LAYOUT, formatJson(approved), "utf8");
const presentation = buildPresentationOverrides(approved, JSON.parse(readFileSync(PRESENTATION, "utf8")));
const line = presentation.info_lines?.[ID];
if (line) presentation.info_lines[ID] = line
  .replace(/group-title="[^"]*"/, 'group-title="Música"')
  .replace(/tvg-logo="[^"]*"/, `tvg-logo="https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/${LOGO}"`)
  .replace(/,[^,]*$/, `,${NAME}`);
writeFileSync(PRESENTATION, formatJson(presentation), "utf8");
const done = approved.channels.find((x) => x.tvgId === ID);
console.log(done.number, done.displayName, done.group, done.logoOverride);
