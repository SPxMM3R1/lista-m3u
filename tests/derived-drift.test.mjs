// Deriva de artefactos derivados (2026-10-31): los órdenes publicados en
// presentation-overrides.json deben salir del layout. Pueden faltar filas activas (el runner
// saca del orden las que marca no disponibles), pero nunca sobrar una (fila borrada que se
// sigue publicando) ni cambiar el orden relativo. Arreglo: regenerar con
// buildPresentationOverrides(layout, overrides) y `python targeted_update.py --mode presentation`.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { buildPresentationOverrides } from "../site/editor-core.mjs";

// Excepción vigente: update_m3u.EXTERNAL_RESEARCH_TAIL_CHANNEL_IDS (sondas deportivas de
// 2026-09-13) van al final de Lista 2 a propósito. Si esa regla cambia, actualizar aquí.
const RESEARCH_TAIL = /@Direct(FreeCast|CDN77|Linear|Tubi|45|170)$/;

const read = (path) => JSON.parse(readFileSync(new URL(`../${path}`, import.meta.url), "utf8"));

test("los órdenes de Lista 1 y Lista 2 salen del layout", () => {
  const layout = read("data/channel-editor-layout.json");
  const overrides = read("presentation-overrides.json");
  const generated = buildPresentationOverrides(layout, overrides).orders;
  for (const file of ["m3u.m3u", "m3u-externa.m3u"]) {
    const published = overrides.orders[file];
    const expected = new Set(generated[file]);
    const extra = published.filter((id) => !expected.has(id));
    assert.deepEqual(extra, [], `${file}: filas publicadas que el layout no tiene activas`);
    const ordered = published.filter((id) => !RESEARCH_TAIL.test(id));
    const kept = new Set(ordered);
    assert.deepEqual(ordered, generated[file].filter((id) => kept.has(id)), `${file}: orden distinto al del layout`);
  }
});

test("los alias 1.m3u/2.m3u tienen el mismo orden que m3u.m3u/m3u-externa.m3u", () => {
  const { orders } = read("presentation-overrides.json");
  assert.deepEqual(orders["1.m3u"], orders["m3u.m3u"]);
  assert.deepEqual(orders["2.m3u"], orders["m3u-externa.m3u"]);
});
