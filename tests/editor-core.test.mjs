import test from "node:test";
import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import {
  buildPresentationOverrides,
  buildSelectionDocument,
  addRow,
  gitBlobSha,
  moveRow,
  removePermanently,
  rowKey,
  setRowState,
  validateLayout,
  validateProviderCatalog,
} from "../site/editor-core.mjs";

globalThis.crypto ??= webcrypto;

test("GitHub blob preflight hashes use Git's UTF-8 blob format", async () => {
  assert.equal(await gitBlobSha(""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391");
});

function sampleLayout() {
  return {
    schemaVersion: 1,
    channels: [
      { kind: "m3u", tvgId: "0104", name: "TVN", sourceList: "1.m3u", state: "active", order: 1, number: 1 },
      { kind: "provider", provider: "highfly", catalogKey: "SkySportsF1.uk", providerResourceId: "leaf:f1-live", resolverSlug: "f1-live", identityState: "canonical", name: "Sky Sports F1", group: "Sports", category: "Sports", state: "active", order: 2, number: 2 },
      { kind: "provider", provider: "tvvoo", catalogKey: "spain|vavoo_ESPN%201%7Cgroup%3Aes", providerResourceId: "spain|vavoo_ESPN%201%7Cgroup%3Aes", identityState: "canonical", name: "ESPN 1", group: "Sports", category: "Sports", aliases: ["vavoo_ESPN%201%7Cgroup%3Aes"], state: "active", order: 3, number: 3 },
    ],
  };
}

test("one mixed list can reorder M3U, Highfly, and TvVoo rows", () => {
  const layout = sampleLayout();
  const moved = moveRow(layout, rowKey(layout.channels[2]), -2);
  assert.deepEqual(moved.channels.filter((row) => row.state === "active").map((row) => row.name), ["ESPN 1", "TVN", "Sky Sports F1"]);
  assert.deepEqual(validateLayout(moved), []);
});

test("hidden provider rows leave the active selection and remain restorable", async () => {
  const layout = sampleLayout();
  const highflyKey = rowKey(layout.channels[1]);
  const hidden = setRowState(layout, highflyKey, "hidden");
  const selection = await buildSelectionDocument(hidden, { schemaVersion: 1, sources: [] }, "2026-09-22T00:00:00.000Z");
  assert.equal(selection.sources.find((source) => source.provider === "highfly").channels.length, 0);
  assert.equal(hidden.channels.find((row) => rowKey(row) === highflyKey).state, "hidden");
  assert.equal(validateLayout(hidden).length, 0);
});

test("selection keeps catalogKey separate from Highfly resolver references", async () => {
  const selection = await buildSelectionDocument(sampleLayout(), { schemaVersion: 1, sources: [] }, "2026-09-22T00:00:00.000Z");
  const highfly = selection.sources.find((source) => source.provider === "highfly").channels[0];
  const tvvoo = selection.sources.find((source) => source.provider === "tvvoo").channels[0];
  assert.equal(highfly.catalogKey, "SkySportsF1.uk");
  assert.equal(highfly.providerResourceId, "leaf:f1-live");
  assert.equal(highfly.resolverSlug, "f1-live");
  assert.equal(tvvoo.catalogKey, tvvoo.providerResourceId);
  assert.match(selection.selectionSignature, /^sha256:[0-9a-f]{64}$/);
  assert.deepEqual(validateLayout(sampleLayout()), []);
});

test("presentation export writes stable order and local-logo references", () => {
  const layout = sampleLayout();
  layout.channels[0].logoOverride = "logos/tvn.png";
  const result = buildPresentationOverrides(layout, { schema: 1, orders: {}, info_lines: {}, logos: {}, assets: [] });
  assert.deepEqual(result.orders["m3u.m3u"], ["0104"]);
  assert.ok(result.orders["channel-catalog.m3u"].includes("SkySportsF1.uk"));
  assert.equal(result.logos["0104"], "logos/tvn.png");
});

test("direct M3U assignment, visibility, and permanent deletion reach runner outputs", () => {
  const layout = sampleLayout();
  const direct = layout.channels[0];
  direct.sourceList = "2.m3u";
  let presentation = buildPresentationOverrides(layout, { schema: 1, orders: {}, logos: {} });
  assert.deepEqual(presentation.orders["m3u.m3u"], []);
  assert.deepEqual(presentation.orders["m3u-externa.m3u"], ["0104"]);
  assert.deepEqual(presentation.excluded_m3u, []);

  const hidden = setRowState(layout, rowKey(direct), "hidden");
  presentation = buildPresentationOverrides(hidden, presentation);
  assert.deepEqual(presentation.orders["m3u-externa.m3u"], []);
  assert.deepEqual(presentation.excluded_m3u, ["0104"]);

  const purged = removePermanently(hidden, rowKey(direct));
  assert.deepEqual(purged.excludedM3u, ["0104"]);
  presentation = buildPresentationOverrides(purged, presentation);
  assert.deepEqual(presentation.excluded_m3u, ["0104"]);

  const restored = addRow(purged, direct);
  assert.deepEqual(restored.excludedM3u, []);
  assert.deepEqual(buildPresentationOverrides(restored, presentation).excluded_m3u, []);
});

test("M3U-only changes do not rewrite provider selection timestamps", async () => {
  const original = await buildSelectionDocument(sampleLayout(), { schemaVersion: 1, sources: [] }, "2026-09-22T10:00:00.000Z");
  const layout = sampleLayout();
  layout.channels[0].number = 42;
  const next = await buildSelectionDocument(layout, original, "2026-09-23T10:00:00.000Z");
  assert.equal(next.publishedAt, original.publishedAt);
  assert.equal(next.selectionSignature, original.selectionSignature);
});

test("provider import strips any field that is not part of the identity contract", () => {
  const imported = validateProviderCatalog({
    schemaVersion: 1,
    providers: [{
      provider: "highfly",
      channels: [{
        catalogKey: "SkySportsF1.uk",
        providerResourceId: "leaf:f1-live",
        resolverSlug: "f1-live",
        identityState: "canonical",
        name: "Sky Sports F1",
        group: "Sports",
        category: "Sports",
        streamUrl: "https://example.invalid/private.m3u8",
      }],
    }],
  });
  assert.equal(imported.length, 1);
  assert.equal(Object.hasOwn(imported[0], "streamUrl"), false);
  assert.equal(validateLayout({ schemaVersion: 1, channels: [{ ...imported[0], order: 1, number: 1, state: "active" }] }).length, 0);
});
