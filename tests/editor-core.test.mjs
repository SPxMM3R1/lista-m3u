import test from "node:test";
import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import {
  buildPresentationOverrides,
  buildSelectionDocument,
  assignChannelPosition,
  addRow,
  compareRows,
  gitBlobSha,
  moveRow,
  removePermanently,
  rowKey,
  setRowState,
  summarizeChanges,
  validateLayout,
} from "../site/editor-core.mjs";
import {
  canonicalTvVooAlias,
  highflyIdentity,
  loadHighflyCatalog,
  loadTvVooCatalog,
  normalizeProviderName,
  parseHighflyCatalog,
  parseHighflyCatalogJson,
  parseTvVooCatalog,
  parseTvVooCatalogJson,
  parseTvVooManifest,
  parseTvVooManifestJson,
} from "../site/provider-catalog.mjs";

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

test("Highfly keeps a canonical catalogKey when its leaf reference rotates", () => {
  const registry = [{ catalogKey: "SkySportsF1.uk", name: "Sky Sports F1" }];
  const oldRows = parseHighflyCatalog({ metas: [{ id: "leaf:f1-old", name: "(FHD) : SKY SPORTS F1" }] }, registry);
  const newRows = parseHighflyCatalog({ metas: [{ id: "leaf:f1-new", name: "(FHD) : SKY SPORTS F1", logo: "https://private.invalid/logo.png", streamUrl: "https://private.invalid/live.m3u8?token=secret" }] }, registry);

  assert.equal(oldRows[0].catalogKey, "SkySportsF1.uk");
  assert.equal(newRows[0].catalogKey, oldRows[0].catalogKey);
  assert.equal(newRows[0].identityState, "canonical");
  assert.equal(newRows[0].providerResourceId, "leaf:f1-new");
  assert.equal(newRows[0].resolverSlug, "f1-new");
  assert.equal(JSON.stringify(newRows).includes("private.invalid"), false);
  assert.equal(JSON.stringify(newRows).includes("token="), false);
  assert.deepEqual(validateLayout({ schemaVersion: 1, channels: [{ ...newRows[0], order: 1, number: 1, state: "active" }] }), []);
});

test("unknown Highfly names use deterministic provisional identities, never leaf IDs", () => {
  const first = parseHighflyCatalog({ metas: [
    { id: "leaf:rotating-1", name: "Canal Ñuevo" },
    { id: "streamed:event-1", name: "Partido en vivo" },
  ] });
  const second = parseHighflyCatalog({ metas: [{ id: "leaf:rotating-2", name: "Canal Ñuevo" }] });
  const ambiguous = highflyIdentity("Canal Ñuevo", [
    { catalogKey: "CanalA.es", name: "Canal Ñuevo" },
    { catalogKey: "CanalB.es", name: "Canal Ñuevo" },
  ]);

  assert.equal(normalizeProviderName("Canal Ñuevo"), "canalnuevo");
  assert.equal(first[0].catalogKey, "Highfly.canalnuevo");
  assert.equal(second[0].catalogKey, first[0].catalogKey);
  assert.equal(first[0].identityState, "provisional");
  assert.equal(ambiguous.catalogKey, "Highfly.canalnuevo");
  assert.equal(ambiguous.identityState, "provisional");
  assert.equal(highflyIdentity("Sky Sports Golf", []).catalogKey, "SkySportsGolf.uk");
  assert.equal(highflyIdentity("Sky Sports Golf", []).identityState, "provisional");
  assert.equal(first.length, 1, "event IDs are not persistent channel identities");
});

test("TvVoo country manifest omits search and keeps app-compatible country keys", () => {
  const countries = parseTvVooManifest({ catalogs: [
    { id: "vavoo_search_tv", name: "Search", type: "tv" },
    { id: "vavoo_tv_uk", name: "Vavoo TV • United Kingdom", type: "tv" },
    { id: "vavoo_tv_es", name: "Vavoo TV • Spain", type: "tv" },
  ] });

  assert.deepEqual(countries.map((country) => country.id), ["vavoo_tv_es", "vavoo_tv_uk"]);
  assert.equal(countries[0].name, "España");
  assert.equal(countries[1].countryKey, "unitedkingdom");
});

test("TvVoo aliases match VibeM3U encoding for raw, encoded, plus and percent values", () => {
  assert.equal(canonicalTvVooAlias("vavoo_SKY%201|group:uk", "uk"), "vavoo_SKY%201%7Cgroup%3Auk");
  assert.equal(canonicalTvVooAlias("vavoo_SKY%201%7Cgroup%3Auk", "uk"), "vavoo_SKY%201%7Cgroup%3Auk");
  assert.equal(canonicalTvVooAlias("vavoo_CAN+%20NEWS|group:uk", "uk"), "vavoo_CAN%2B%20NEWS%7Cgroup%3Auk");
  assert.equal(canonicalTvVooAlias("vavoo_100%25|group:uk", "uk"), "vavoo_100%25%7Cgroup%3Auk");
});

test("TvVoo catalog rows use country plus canonical alias and drop remote logo URLs", () => {
  const country = { id: "vavoo_tv_es", code: "es", countryKey: "spain", name: "España" };
  const rows = parseTvVooCatalog({ metas: [
    { id: "vavoo_ESPN%201|group:es", name: "ESPN 1", logo: "https://private.invalid/espn.png" },
  ] }, country);

  assert.equal(rows[0].catalogKey, "spain|vavoo_ESPN%201%7Cgroup%3Aes");
  assert.equal(rows[0].providerResourceId, rows[0].catalogKey);
  assert.deepEqual(rows[0].aliases, ["vavoo_ESPN%201%7Cgroup%3Aes"]);
  assert.equal(Object.hasOwn(rows[0], "logo"), false);
  assert.equal(JSON.stringify(rows).includes("private.invalid"), false);
  assert.deepEqual(validateLayout({ schemaVersion: 1, channels: [{ ...rows[0], order: 1, number: 1, state: "active" }] }), []);
});

test("assigning a channel to an occupied number shifts that number and later channels", () => {
  const layout = sampleLayout();
  for (let number = 4; number <= 24; number += 1) {
    layout.channels.push({
      kind: "m3u",
      tvgId: `channel.${number}`,
      name: `Channel ${number}`,
      sourceList: "1.m3u",
      state: "active",
      order: number,
      number,
    });
  }
  const selected = layout.channels[0];
  const existingTwentyOne = layout.channels.find((row) => row.number === 21);
  const existingTwentyTwo = layout.channels.find((row) => row.number === 22);
  const moved = assignChannelPosition(layout, rowKey(selected), 21);

  assert.equal(moved.channels.find((row) => rowKey(row) === rowKey(selected)).number, 21);
  assert.equal(moved.channels.find((row) => rowKey(row) === rowKey(existingTwentyOne)).number, 22);
  assert.equal(moved.channels.find((row) => rowKey(row) === rowKey(existingTwentyTwo)).number, 23);
  assert.deepEqual(validateLayout(moved), []);
  const ordered = moved.channels.filter((row) => row.state === "active").sort(compareRows);
  assert.ok(ordered.indexOf(moved.channels.find((row) => rowKey(row) === rowKey(selected)))
    < ordered.indexOf(moved.channels.find((row) => rowKey(row) === rowKey(existingTwentyOne))));
  const publishedOrder = buildPresentationOverrides(moved, { schema: 1, orders: {}, logos: {} })
    .orders["channel-catalog.m3u"];
  assert.ok(publishedOrder.indexOf(selected.tvgId)
    < publishedOrder.indexOf(existingTwentyOne.tvgId));
});

test("pasted Highfly and TvVoo JSON uses the same stable identity parsers", () => {
  const highfly = parseHighflyCatalogJson(JSON.stringify({ metas: [
    { id: "leaf:rotating-resource", name: "(FHD) : SKY SPORTS F1", streamUrl: "https://private.invalid/live.m3u8?token=secret" },
  ] }), [{ catalogKey: "SkySportsF1.uk", name: "Sky Sports F1" }]);
  assert.equal(highfly[0].catalogKey, "SkySportsF1.uk");
  assert.equal(highfly[0].providerResourceId, "leaf:rotating-resource");
  assert.equal(JSON.stringify(highfly).includes("private.invalid"), false);

  const countries = parseTvVooManifestJson(JSON.stringify({ catalogs: [
    { id: "vavoo_search_tv", name: "Search", type: "tv" },
    { id: "vavoo_tv_es", name: "Vavoo TV • Spain", type: "tv" },
  ] }));
  assert.equal(countries[0].countryKey, "spain");
  const tvvoo = parseTvVooCatalogJson(JSON.stringify({ metas: [
    { id: "vavoo_ESPN%201|group:es", name: "ESPN 1", streamUrl: "https://private.invalid/live.m3u8" },
  ] }), countries[0]);
  assert.equal(tvvoo[0].catalogKey, "spain|vavoo_ESPN%201%7Cgroup%3Aes");
  assert.equal(JSON.stringify(tvvoo).includes("private.invalid"), false);
});

test("pasted provider JSON rejects invalid, wrong-shape and oversized documents", () => {
  assert.throws(() => parseHighflyCatalogJson("{not-json"), /JSON válido/);
  assert.throws(() => parseHighflyCatalogJson("{}"), /metas/);
  assert.throws(() => parseTvVooCatalogJson(JSON.stringify({ metas: [{ id: "vavoo_ESPN", name: "ESPN" }] }), null), /país TvVoo seleccionado/);
  assert.throws(() => parseHighflyCatalogJson(`${JSON.stringify({ metas: [] })}${" ".repeat(2 * 1024 * 1024)}`), /2 MiB/);
  assert.throws(() => parseTvVooManifestJson(`${JSON.stringify({ catalogs: [] })}${" ".repeat(512 * 1024)}`), /512 KiB/);
});

test("provider fetches are fixed-origin, credential-free metadata GETs", async () => {
  const calls = [];
  const respond = (url, body) => ({
    ok: true,
    status: 200,
    url,
    headers: { get: () => null },
    text: async () => JSON.stringify(body),
  });
  const fetchImpl = async (url, options) => {
    calls.push({ url, options });
    if (url === "https://sports.highfly.to/manifest.json") {
      return respond(url, { resources: [{ name: "catalog" }], catalogs: [{ id: "sports_live" }] });
    }
    if (url === "https://sports.highfly.to/catalog/sport/sports_live.json") {
      return respond(url, { metas: [{ id: "leaf:sample-one", name: "Sample One" }] });
    }
    throw new Error("Unexpected endpoint");
  };

  const rows = await loadHighflyCatalog({ fetchImpl });
  assert.equal(rows[0].catalogKey, "Highfly.sampleone");
  assert.deepEqual(calls.map((call) => call.url), [
    "https://sports.highfly.to/manifest.json",
    "https://sports.highfly.to/catalog/sport/sports_live.json",
  ]);
  for (const { options } of calls) {
    assert.equal(options.method, "GET");
    assert.equal(options.mode, "cors");
    assert.equal(options.credentials, "omit");
    assert.equal(options.cache, "no-store");
    assert.equal(Object.hasOwn(options, "body"), false);
  }
});

test("provider responses are size-limited before JSON parsing", async () => {
  const oversized = new Response(
    `${JSON.stringify({ resources: [{ name: "catalog" }], catalogs: [{ id: "sports_live" }] })}${" ".repeat(600 * 1024)}`,
    { status: 200, headers: { "content-type": "application/json" } },
  );

  await assert.rejects(
    loadHighflyCatalog({ fetchImpl: async () => oversized }),
    /excede el tamaño permitido/,
  );
});

test("TvVoo refuses a catalog outside its fixed country-catalog namespace", async () => {
  let called = false;
  await assert.rejects(
    loadTvVooCatalog("https://attacker.invalid/manifest.json", { id: "https://attacker.invalid/manifest.json" }, {
      fetchImpl: async () => { called = true; throw new Error("must not fetch"); },
    }),
    /no es válido/,
  );
  assert.equal(called, false);
});

test("change review counts Highfly locator rotations without counting new rows", () => {
  const before = sampleLayout();
  const after = structuredClone(before);
  after.channels[1].providerResourceId = "leaf:f1-new";
  after.channels[1].resolverSlug = "f1-new";
  const summary = summarizeChanges(before, after, {}, {});

  assert.equal(summary.providerReferenceChanges, 1);
  assert.equal(summary.added, 0);
});
