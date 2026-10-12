// Pedidos de la app (VibeM3U 0.5.90+): la TV deja un JSON en data/app-requests/ y este script lo
// aplica con las mismas funciones del editor web, para que la TV y el editor no puedan divergir.
//
// Hoy solo existe «trash»: enviar una fila a la papelera (state = "deleted"), igual que el botón
// Papelera del editor. Desde la papelera del editor se recupera o se borra para siempre.
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
  if (value.action !== "trash") return `acción no soportada: ${String(value.action)}`;
  const key = typeof value.rowKey === "string" ? value.rowKey.trim() : "";
  if (!/^(m3u:[^\s]{1,512}|provider:(tvvoo|highfly):[^\s]{1,512})$/.test(key)) return "rowKey inválida";
  const name = typeof value.name === "string" ? value.name.replace(/[\u0000-\u001f]/g, " ").trim().slice(0, 120) : "";
  return { rowKey: key, name };
}

/** El mismo documento que publica el editor web (layoutDocument). */
export function editorLayoutDocument(layout) {
  return {
    schemaVersion: 1,
    excludedM3u: [...new Set(layout.excludedM3u ?? [])].sort((a, b) => a.localeCompare(b)),
    channels: layout.channels.map(sanitizeRow).sort(compareRows),
  };
}

/** Aplica los pedidos a los documentos; no toca el disco. */
export async function applyRequests(documents, requests) {
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
    layout = setRowState(layout, parsed.rowKey, "deleted");
    applied.push({ rowKey: parsed.rowKey, name: row.displayName || row.name || parsed.name, number: row.number });
  }
  const finalLayout = editorLayoutDocument(layout);
  const problems = validateLayout(finalLayout);
  if (problems.length) throw new Error(`El catálogo quedaría inválido: ${problems.join(" | ")}`);
  return {
    applied,
    skipped,
    layout: finalLayout,
    presentation: buildPresentationOverrides(finalLayout, documents.presentation),
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
  const documents = { layout: read(FILES.layout), selection: read(FILES.selection), presentation: read(FILES.presentation) };
  const requests = files.map((file) => ({ file, text: readFileSync(join(dir, file), "utf8") }));
  const result = await applyRequests(documents, requests);
  if (result.applied.length) {
    // Pedido del usuario desde su TV: se sella igual que una publicación del editor.
    writeFileSync(join(root, FILES.layout), formatJson(await approveLayout(result.layout, "app")));
    writeFileSync(join(root, FILES.presentation), formatJson(result.presentation));
    writeFileSync(join(root, FILES.selection), formatJson(result.selection));
  }
  for (const file of files) unlinkSync(join(dir, file));
  for (const item of result.applied) console.error(`Papelera: ${item.number ?? "-"} ${item.name} (${item.rowKey})`);
  for (const item of result.skipped) console.error(`Omitido ${item.file}: ${item.reason}`);
  console.log(JSON.stringify({ applied: result.applied, skipped: result.skipped, files: files.length }));
}

if (import.meta.url === `file://${process.argv[1]}` || process.argv[1]?.endsWith("apply_app_requests.mjs")) {
  main().catch((error) => {
    console.error(error.message);
    process.exit(1);
  });
}
