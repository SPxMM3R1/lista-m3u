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
