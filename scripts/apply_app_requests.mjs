// Pedidos de la app (VibeM3U 0.5.90+): la TV deja un JSON en data/app-requests/ y este script lo
// aplica con las mismas funciones del editor web, para que la TV y el editor no puedan divergir.
//
// «trash»: enviar una fila a la papelera (state = "deleted"), igual que el botón Papelera del
// editor. Desde la papelera del editor se recupera o se borra para siempre. Sus respaldos siguen en
// backups.json colgando de esa fila: al recuperarla vuelven con ella.
// «promote-backup» (VibeM3U 0.6.57): la fila va a la papelera y uno de sus respaldos toma su lugar,
// con el mismo número, nombre, grupo, logo y guía; los demás respaldos pasan al nuevo principal.
//
// Uso: node scripts/apply_app_requests.mjs [--root <repo>]
// Escribe los tres documentos del editor, borra los pedidos procesados (válidos o no) e imprime
// un resumen JSON en la última línea para el mensaje del commit.
import { readFileSync, writeFileSync, readdirSync, unlinkSync, existsSync } from "node:fs";
import { join } from "node:path";
import {
  buildPresentationOverrides,
  buildSelectionDocument,
  approveLayout,
  compareRows,
  formatJson,
  normalizeLists,
  rowKey,
  sanitizeRow,
  setRowState,
  validateLayout,
} from "../site/editor-core.mjs";

export const FILES = {
  layout: "data/channel-editor-layout.json",
  selection: "data/vibem3u-selection.json",
  presentation: "presentation-overrides.json",
};
// Solo cambian al promover un respaldo.
export const PROMOTE_FILES = {
  backups: "backups.json",
  overrides: "epg-overrides.json",
  l2Map: "epg-l2-map.json",
};
export const REQUESTS_DIR = "data/app-requests";
const MAX_REQUEST_BYTES = 4096;

/** Valida un pedido; devuelve {rowKey, name} o un texto de error. */
export function parseRequest(text) {
  if (typeof text !== "string" || text.length > MAX_REQUEST_BYTES) return "pedido demasiado grande";
  let value;
  try {
    value = JSON.parse(text);
  } catch {
    return "JSON inválido";
  }
  if (!value || value.schema !== 1) return "esquema no soportado";
  if (value.action !== "trash" && value.action !== "promote-backup") return `acción no soportada: ${String(value.action)}`;
  const key = typeof value.rowKey === "string" ? value.rowKey.trim() : "";
  if (!/^(m3u:[^\s]{1,512}|provider:(tvvoo|highfly):[^\s]{1,512})$/.test(key)) return "rowKey inválida";
  const name = typeof value.name === "string" ? value.name.replace(/[\u0000-\u001f]/g, " ").trim().slice(0, 120) : "";
  if (value.action === "trash") return { rowKey: key, name };
  const backupTvgId = typeof value.backupTvgId === "string" ? value.backupTvgId.trim() : "";
  if (!key.startsWith("m3u:") || !/^[^\s]{1,512}$/.test(backupTvgId)) return "respaldo inválido";
  return { rowKey: key, name, backupTvgId };
}

/**
 * Promueve el respaldo: cambia la fila en `layout` y mueve guía y respaldos en `documents`.
 * Devuelve un texto si no se puede, sin haber tocado nada.
 */
function promoteBackup(layout, documents, row, backupTvgId) {
  const oldId = row.tvgId;
  const entry = documents.backups?.channels?.[oldId];
  const copy = entry?.backups?.find((item) => item.tvg_id === backupTvgId);
  if (!copy) return `${backupTvgId} no es respaldo de ${oldId}`;
  const next = layout.channels.find((item) => item.kind === "m3u" && item.tvgId === backupTvgId);
  if (!next || next.state !== "deleted") return `el respaldo ${backupTvgId} no tiene fila disponible`;

  Object.assign(next, { state: "active", sourceList: row.sourceList, group: row.group,
    displayName: row.displayName ?? row.name, order: row.order - 0.5 });
  for (const field of ["logoPath", "logoOverride", "country"]) {
    if (row[field] !== undefined) next[field] = row[field];
  }
  if (row.trial) next.trial = true;
  else delete next.trial;
  row.state = "deleted";

  for (const table of [documents.overrides?.channels, documents.l2Map?.channels]) {
    if (table && oldId in table) {
      table[backupTvgId] = table[oldId];
      delete table[oldId];
    }
  }
  if (Number.isInteger(documents.l2Map?.count)) documents.l2Map.count = Object.keys(documents.l2Map.channels).length;

  const infoLine = documents.presentation.info_lines?.[oldId];
  if (infoLine) documents.presentation.info_lines[backupTvgId] = infoLine.replace(`tvg-id="${oldId}"`, `tvg-id="${backupTvgId}"`);

  const rest = entry.backups.filter((item) => item !== copy);
  // Misma posición en el archivo (diff mínimo); sin más respaldos el canal deja de tener entrada.
  documents.backups.channels = Object.fromEntries(Object.entries(documents.backups.channels).flatMap(([id, value]) => {
    if (id !== oldId) return [[id, value]];
    return rest.length ? [[backupTvgId, { ...entry, source_name: copy.source_name, principal_quality: copy.quality, backups: rest }]] : [];
  }));
  documents.backups.updated = new Date().toISOString().slice(0, 10);
  return null;
}

/** El mismo documento que publica el editor web (layoutDocument). */
export function editorLayoutDocument(layout) {
  // Igual que el editor: Lista 1 y luego Lista 2, numeradas sin huecos (2026-10-18).
  return normalizeLists({
    schemaVersion: 1,
    excludedM3u: [...new Set(layout.excludedM3u ?? [])].sort((a, b) => a.localeCompare(b)),
    channels: layout.channels.map(sanitizeRow).sort(compareRows),
  });
}

/** Aplica los pedidos a los documentos; no toca el disco. */
export async function applyRequests(documents, requests) {
  // Copias: un pedido omitido no deja nada a medias.
  documents = structuredClone(documents);
  let layout = documents.layout;
  const applied = [];
  const skipped = [];
  for (const request of requests) {
    const parsed = parseRequest(request.text);
    if (typeof parsed === "string") {
      skipped.push({ file: request.file, reason: parsed });
      continue;
    }
    const row = layout.channels.find((item) => rowKey(item) === parsed.rowKey);
    if (!row) {
      skipped.push({ file: request.file, reason: `no existe ${parsed.rowKey}` });
      continue;
    }
    if (row.state === "deleted") {
      skipped.push({ file: request.file, reason: `${row.name || parsed.rowKey} ya estaba en la papelera` });
      continue;
    }
    const name = row.displayName || row.name || parsed.name;
    if (parsed.backupTvgId) {
      const problem = promoteBackup(layout, documents, row, parsed.backupTvgId);
      if (problem) {
        skipped.push({ file: request.file, reason: problem });
        continue;
      }
      applied.push({ rowKey: parsed.rowKey, name, number: row.number, promoted: parsed.backupTvgId });
      continue;
    }
    layout = setRowState(layout, parsed.rowKey, "deleted");
    applied.push({ rowKey: parsed.rowKey, name, number: row.number });
  }
  const finalLayout = editorLayoutDocument(layout);
  const problems = validateLayout(finalLayout);
  if (problems.length) throw new Error(`El catálogo quedaría inválido: ${problems.join(" | ")}`);
  return {
    applied,
    skipped,
    layout: finalLayout,
    presentation: buildPresentationOverrides(finalLayout, documents.presentation),
    backups: documents.backups,
    overrides: documents.overrides,
    l2Map: documents.l2Map,
    selection: applied.length
      ? await buildSelectionDocument(finalLayout, documents.selection)
      : documents.selection,
  };
}

async function main() {
  const rootIndex = process.argv.indexOf("--root");
  const root = rootIndex > 0 ? process.argv[rootIndex + 1] : process.cwd();
  const dir = join(root, REQUESTS_DIR);
  const files = existsSync(dir)
    ? readdirSync(dir).filter((name) => name.endsWith(".json")).sort()
    : [];
  if (!files.length) {
    console.log(JSON.stringify({ applied: [], skipped: [], files: 0 }));
    return;
  }
  const read = (path) => JSON.parse(readFileSync(join(root, path), "utf8"));
  const documents = { layout: read(FILES.layout), selection: read(FILES.selection), presentation: read(FILES.presentation),
    backups: read(PROMOTE_FILES.backups), overrides: read(PROMOTE_FILES.overrides), l2Map: read(PROMOTE_FILES.l2Map) };
  const requests = files.map((file) => ({ file, text: readFileSync(join(dir, file), "utf8") }));
  const result = await applyRequests(documents, requests);
  if (result.applied.length) {
    // Pedido del usuario desde su TV: se sella igual que una publicación del editor.
    writeFileSync(join(root, FILES.layout), formatJson(await approveLayout(result.layout, "app")));
    writeFileSync(join(root, FILES.presentation), formatJson(result.presentation));
    writeFileSync(join(root, FILES.selection), formatJson(result.selection));
  }
  if (result.applied.some((item) => item.promoted)) {
    const json = (value) => `${JSON.stringify(value, null, 2)}\n`;
    // backups.json va en CRLF (lo escriben así los scripts de Python).
    writeFileSync(join(root, PROMOTE_FILES.backups), json(result.backups).replace(/\n/g, "\r\n"));
    writeFileSync(join(root, PROMOTE_FILES.overrides), json(result.overrides));
    writeFileSync(join(root, PROMOTE_FILES.l2Map), json(result.l2Map));
  }
  for (const file of files) unlinkSync(join(dir, file));
  for (const item of result.applied) {
    const promoted = item.promoted ? ` → principal: ${item.promoted}` : "";
    console.error(`Papelera: ${item.number ?? "-"} ${item.name} (${item.rowKey})${promoted}`);
  }
  for (const item of result.skipped) console.error(`Omitido ${item.file}: ${item.reason}`);
  console.log(JSON.stringify({ applied: result.applied, skipped: result.skipped, files: files.length }));
}

if (import.meta.url === `file://${process.argv[1]}` || process.argv[1]?.endsWith("apply_app_requests.mjs")) {
  main().catch((error) => {
    console.error(error.message);
    process.exit(1);
  });
}
