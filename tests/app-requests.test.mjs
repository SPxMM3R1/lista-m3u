import test from "node:test";
import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import { applyRequests, parseRequest } from "../scripts/apply_app_requests.mjs";

if (!globalThis.crypto) globalThis.crypto = webcrypto;

function documents() {
  return {
    layout: {
      schemaVersion: 1,
      excludedM3u: [],
      channels: [
        { kind: "m3u", tvgId: "0104", name: "TVN", group: "Nacionales", sourceList: "1.m3u", order: 1, number: 1, state: "active" },
        { kind: "m3u", tvgId: "0105", name: "Mega", group: "Nacionales", sourceList: "1.m3u", order: 2, number: 2, state: "active" },
        { kind: "provider", sourceList: "1.m3u", provider: "tvvoo", catalogKey: "spain|vavoo_EUROSPORT%202%7Cgroup%3Aes",
          providerResourceId: "spain|vavoo_EUROSPORT%202%7Cgroup%3Aes", identityState: "canonical",
          name: "EUROSPORT 2", group: "España", order: 3, number: 3, state: "active" },
      ],
    },
    selection: { schemaVersion: 1, source: "vibem3u-android", sources: [] },
    presentation: { schema: 1, orders: { "m3u.m3u": ["0104", "0105"], "1.m3u": ["0104", "0105"] }, logos: {}, names: {} },
  };
}

const request = (rowKey, extra = {}) => JSON.stringify({ schema: 1, action: "trash", rowKey, name: "x", ...extra });

test("un pedido de papelera deja la fila en «deleted» igual que el editor", async () => {
  const result = await applyRequests(documents(), [{ file: "a.json", text: request("m3u:0104") }]);
  assert.equal(result.applied.length, 1);
  const tvn = result.layout.channels.find((row) => row.tvgId === "0104");
  assert.equal(tvn.state, "deleted");
  assert.equal(tvn.number, 1, "el número del canal no cambia");
  // Desde 2026-10-18 las filas TvVoo/Highfly también van en el orden de su lista.
  assert.deepEqual(result.presentation.orders["m3u.m3u"], ["0105", "spain|vavoo_EUROSPORT%202%7Cgroup%3Aes"]);
  assert.deepEqual(result.presentation.orders["1.m3u"], ["0105", "spain|vavoo_EUROSPORT%202%7Cgroup%3Aes"]);
  assert.ok(result.presentation.excluded_m3u.includes("0104"));
});

test("también sirve para filas TvVoo y Highfly por su catalogKey", async () => {
  const key = "provider:tvvoo:spain|vavoo_EUROSPORT%202%7Cgroup%3Aes";
  const result = await applyRequests(documents(), [{ file: "a.json", text: request(key) }]);
  assert.equal(result.layout.channels.find((row) => row.kind === "provider").state, "deleted");
  assert.equal(result.selection.sources.find((source) => source.provider === "tvvoo").channels.length, 0);
});

test("pedidos inválidos, repetidos o de filas inexistentes se omiten sin tocar nada", async () => {
  const result = await applyRequests(documents(), [
    { file: "a.json", text: "{no es json" },
    { file: "b.json", text: JSON.stringify({ schema: 1, action: "delete-forever", rowKey: "m3u:0104" }) },
    { file: "c.json", text: request("m3u:no-existe") },
    { file: "d.json", text: request("m3u:0105") },
    { file: "e.json", text: request("m3u:0105") },
  ]);
  assert.equal(result.applied.length, 1);
  assert.equal(result.skipped.length, 4);
  assert.equal(result.layout.channels.find((row) => row.tvgId === "0104").state, "active");
});

test("parseRequest rechaza claves con formato ajeno al editor", () => {
  assert.equal(typeof parseRequest(request("tvvoo:x")), "string");
  assert.equal(typeof parseRequest(request("provider:desconocido:x")), "string");
  assert.deepEqual(parseRequest(request("m3u:0104")), { rowKey: "m3u:0104", name: "x" });
});

test("publicar desde el editor conserva las bajas hechas en la app mientras estaba abierto", async () => {
  const { mergeRemoteDeletions } = await import("../site/editor-core.mjs");
  const original = documents().layout;
  const local = structuredClone(original);
  local.channels[1].displayName = "Mega HD"; // edición del editor en otra fila
  local.channels[2].state = "hidden"; // el editor decidió otra cosa para EUROSPORT 2
  local.channels.push({ kind: "m3u", tvgId: "0200", name: "Nuevo", group: "x", sourceList: "1.m3u",
    order: 4, number: 4, state: "active" });
  const { layout: remote } = await applyRequests(documents(), [
    { file: "a.json", text: request("m3u:0104") },
    { file: "b.json", text: request("provider:tvvoo:spain|vavoo_EUROSPORT%202%7Cgroup%3Aes") },
  ]);
  remote.channels.push({ ...local.channels[3], state: "deleted" });
  const { layout, applied } = mergeRemoteDeletions(original, local, remote);
  const state = (id) => layout.channels.find((row) => (row.tvgId ?? row.catalogKey).startsWith(id)).state;
  assert.deepEqual(applied, ["TVN"]);
  assert.equal(state("0104"), "deleted");
  assert.equal(state("spain"), "hidden", "lo decidido en esta sesión gana");
  assert.equal(state("0200"), "active", "una fila nueva del editor no se toca");
  assert.equal(layout.channels.find((row) => row.tvgId === "0105").displayName, "Mega HD");
  assert.equal(layout.channels.find((row) => row.tvgId === "0104").number, 1);
});

test("el sello del layout coincide con el de las pruebas Python y se renueva al publicar", async () => {
  const { approveLayout, layoutApprovalDigest } = await import("../site/editor-core.mjs");
  const fixture = {
    schemaVersion: 1,
    excludedM3u: ["PublicDirect.x"],
    channels: [{ kind: "m3u", tvgId: "0104", name: "TVN «HD» ñandú | 24/7", group: "Nacionales",
      sourceList: "1.m3u", order: 1, number: 1, state: "deleted" }],
  };
  const digest = "002cce3d08ee144e979dbb8bed8f1fe3959af44aaf0d6c60eb05574d2020bf4a";
  assert.equal(await layoutApprovalDigest(fixture), digest);
  const stale = { ...fixture, approval: { source: "app", sha256: "viejo" } };
  assert.deepEqual((await approveLayout(stale, "editor")).approval, { source: "editor", sha256: digest });
});

function promoteDocuments() {
  const base = documents();
  base.layout.channels = [
    { kind: "m3u", tvgId: "L1", name: "Fuente", displayName: "Cine", group: "Cine", sourceList: "1.m3u", order: 1, number: 1, state: "active" },
    { kind: "m3u", tvgId: "P", name: "Fuente P", displayName: "Canal", group: "Películas", sourceList: "2.m3u", logoPath: "logos/p.png", trial: true, order: 2, number: 2, state: "active" },
    { kind: "m3u", tvgId: "Z", name: "Otro", group: "Noticias", sourceList: "2.m3u", order: 3, number: 3, state: "active" },
    { kind: "m3u", tvgId: "B1", name: "Fuente B1", group: "Misceláneos", sourceList: "2.m3u", logoPath: "logos/b.png", order: 4, number: 4, state: "deleted" },
    { kind: "m3u", tvgId: "B2", name: "Fuente B2", group: "Misceláneos", sourceList: "2.m3u", order: 5, number: 5, state: "deleted" },
  ];
  base.presentation = { schema: 1, orders: {}, logos: {}, names: {}, info_lines: { P: '#EXTINF:-1 tvg-id="P",Canal' } };
  base.backups = { schema: 1, updated: "2026-01-01", channels: {
    A: { display_name: "A", backups: [] },
    P: { display_name: "Canal", list: "Lista 2", number: 2, source_name: "Fuente P", guide: { source: "g", source_id: "1" },
      principal_quality: { kbps: 100 }, backups: [
        { tvg_id: "B1", source_name: "Fuente B1", quality: { kbps: 300 } },
        { tvg_id: "B2", source_name: "Fuente B2", quality: { kbps: 200 } },
      ] },
    C: { display_name: "C", backups: [] },
  } };
  base.overrides = { channels: { P: { source: "g", source_id: "1" }, B1: { source: "vieja", source_id: "9" } } };
  base.l2Map = { count: 1, channels: { P: { source: "g", source_id: "1" } } };
  return base;
}
const promote = (rowKey, backupTvgId) => JSON.stringify({ schema: 1, action: "promote-backup", rowKey, name: "x", backupTvgId });

test("promover un respaldo: la señal va a la papelera y el respaldo toma su lugar", async () => {
  const result = await applyRequests(promoteDocuments(), [{ file: "a.json", text: promote("m3u:P", "B1") }]);
  assert.equal(result.skipped.length, 0);
  assert.equal(result.applied[0].promoted, "B1");
  const row = (id) => result.layout.channels.find((item) => item.tvgId === id);
  assert.equal(row("P").state, "deleted");
  assert.equal(row("B1").state, "active");
  assert.equal(row("B1").number, 2, "conserva el número");
  assert.equal(row("Z").number, 3, "los demás no se corren");
  assert.equal(row("B1").displayName, "Canal");
  assert.equal(row("B1").group, "Películas");
  assert.equal(row("B1").logoPath, "logos/p.png");
  assert.equal(row("B1").trial, true);
  assert.equal(row("B2").state, "deleted", "el otro respaldo sigue siendo respaldo");
  assert.deepEqual(Object.keys(result.backups.channels), ["A", "B1", "C"], "misma posición en el archivo");
  const entry = result.backups.channels.B1;
  assert.deepEqual(entry.backups.map((item) => item.tvg_id), ["B2"], "la señal anterior no queda de respaldo");
  assert.equal(entry.source_name, "Fuente B1");
  assert.equal(entry.principal_quality.kbps, 300);
  assert.deepEqual(entry.guide, { source: "g", source_id: "1" });
  assert.deepEqual(result.overrides.channels, { B1: { source: "g", source_id: "1" } }, "la guía sigue al canal");
  assert.deepEqual(result.l2Map.channels, { B1: { source: "g", source_id: "1" } });
  assert.equal(result.presentation.info_lines.B1, '#EXTINF:-1 tvg-id="B1",Canal');
  assert.ok(result.presentation.excluded_m3u.includes("P"));
  assert.ok(!result.presentation.excluded_m3u.includes("B1"));
});

test("promover el último respaldo deja el canal sin entrada de respaldos", async () => {
  const base = promoteDocuments();
  base.backups.channels.P.backups.pop();
  const result = await applyRequests(base, [{ file: "a.json", text: promote("m3u:P", "B1") }]);
  assert.equal(result.applied.length, 1);
  assert.deepEqual(Object.keys(result.backups.channels), ["A", "C"]);
});

test("un respaldo ajeno o sin fila se omite sin tocar nada", async () => {
  const base = promoteDocuments();
  base.backups.channels.P.backups.push({ tvg_id: "SIN-FILA", quality: {} });
  const result = await applyRequests(base, [
    { file: "a.json", text: promote("m3u:P", "Z") },
    { file: "b.json", text: promote("m3u:P", "SIN-FILA") },
    { file: "c.json", text: promote("m3u:Z", "B1") },
  ]);
  assert.equal(result.applied.length, 0);
  assert.equal(result.skipped.length, 3);
  assert.equal(result.layout.channels.find((item) => item.tvgId === "P").state, "active");
  assert.ok("P" in result.backups.channels);
});

test("parseRequest exige un respaldo válido para promover y solo en filas M3U", () => {
  assert.equal(parseRequest(promote("provider:tvvoo:x", "B1")), "respaldo inválido");
  assert.equal(parseRequest(promote("m3u:P", "con espacio")), "respaldo inválido");
  assert.equal(parseRequest(JSON.stringify({ schema: 1, action: "promote-backup", rowKey: "m3u:P" })), "respaldo inválido");
  assert.deepEqual(parseRequest(promote("m3u:P", "B1")), { rowKey: "m3u:P", name: "x", backupTvgId: "B1" });
});
