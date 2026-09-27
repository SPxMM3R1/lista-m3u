// Contrato compartido de filas de proveedor (contracts/layout-provider-rows.json).
// Los mismos casos los validan el runner (tests/test_layout_contract.py), la app y el
// auxiliar local de VibeM3U. Si alguno cambia de criterio, este archivo lo delata.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { webcrypto } from "node:crypto";
import { buildSelectionDocument, stableId, validateLayout } from "../site/editor-core.mjs";

if (!globalThis.crypto) globalThis.crypto = webcrypto;
const contract = JSON.parse(readFileSync(new URL("../contracts/layout-provider-rows.json", import.meta.url), "utf8"));

for (const item of contract.cases) {
  test(`contrato de filas · ${item.id}`, async () => {
    const layout = { schemaVersion: 1, excludedM3u: [], channels: [item.row] };
    const problems = validateLayout(layout);
    assert.equal(problems.length === 0, item.valid, `${item.why} Problemas: ${problems.join(" | ")}`);
    if (!item.valid) return;
    assert.equal(stableId(item.row), item.stableId);
    const selection = await buildSelectionDocument(layout, { schemaVersion: 1, sources: [] }, "2026-09-28T00:00:00.000Z");
    const channels = selection.sources.flatMap((source) => source.channels);
    assert.deepEqual(channels.map((channel) => channel.catalogKey), [item.stableId]);
  });
}
