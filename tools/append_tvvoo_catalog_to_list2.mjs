// Agrega el catálogo TvVoo vivo al final de Lista 2, por país (2026-11-17, pedido del usuario).
//
// Fuente: data/tvvoo-catalogo-vivo-20261117.json (snapshot del catálogo vivo de Vavoo, 8.387
// canales en 15 países). Las filas se arman con las mismas funciones que el editor web:
// tvvooCountriesFromInventory / tvvooCatalogFromInventory / parseTvVooCatalog (site/provider-catalog.mjs)
// y la misma fila que addRow + normalizeLists (site/editor-core.mjs).
//
// Reglas:
// - Orden del bloque: Reino Unido, España y luego el resto por nombre en español; dentro de cada
//   país, por nombre sin distinguir mayúsculas. Todas van a sourceList "2.m3u", state "active".
// - Un catalogKey ya presente con estado distinto de "deleted" (p. ej. una fila de Lista 1) se omite.
// - Un catalogKey presente solo como "deleted" se reactiva dentro de este bloque (sin duplicarlo).
// - Logo: el del inventario oficial si coincide país + nombre (contracts/tvvoo-logos-lista2-20261117.json,
//   generado por tools/tvvoo_inventory_logos.py); si no, el genérico del país (logos/tvvoo-paises/<code>.svg).
// - Nombres que el clasificador de adultos (update_m3u.py, ADULT_NAME_PATTERN) reconoce pasan a
//   group «Adultos», como las demás filas de adultos del repo.
// - Idempotente: una segunda ejecución no cambia nada. No quita ninguna fila.
// - Sella el layout con approveLayout(layout, "chat") y valida con validateLayout.
//
// Uso (desde la raíz del repo):  node tools/append_tvvoo_catalog_to_list2.mjs

import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  tvvooCountriesFromInventory,
  tvvooCatalogFromInventory,
  parseTvVooCatalog,
} from "../site/provider-catalog.mjs";
import {
  normalizeLists,
  sanitizeRow,
  validateLayout,
  buildSelectionDocument,
  buildPresentationOverrides,
  approveLayout,
  formatJson,
} from "../site/editor-core.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SNAPSHOT = "data/tvvoo-catalogo-vivo-20261117.json";
const LOGO_MAP = "contracts/tvvoo-logos-lista2-20261117.json";
const LAYOUT = "data/channel-editor-layout.json";
const SELECTION = "data/vibem3u-selection.json";
const PRESENTATION = "presentation-overrides.json";
const REGISTRY = "contracts/lista2-tvvoo-completo-20261117.json";
const LIST = "2.m3u";

// Igual que ADULT_NAME_PATTERN de update_m3u.py (sin «Adult Swim»). Los \b de JS son ASCII;
// los nombres del catálogo son ASCII en la práctica.
const ADULT_NAME_PATTERN = /(?:\badult\b(?!\W*swim)|\berotic(?:a|s)?\b|\bporn(?:o)?\b|\bxxx\b|\bplayboy\b|\bprivate\s+(?:tv|channel|xxx)\b|\bbrazzers\b|\bhustler\b|\bpenthouse\b|\bvenus\b|\bsextreme?\b|\bredlight\b|\bdorcel\b|\bvivid\b|\berotik\b|\bbeate\b|\b18\s*\+)/i;

// Colores de la bandera de cada país para el logo genérico (franjas de izquierda a derecha).
const FLAG_COLORS = {
  al: ["#E41E20", "#000000"],
  ar: ["#006C35", "#FFFFFF", "#000000"],
  bg: ["#FFFFFF", "#00966E", "#D62612"],
  bk: ["#1F4FA3", "#FFFFFF", "#D52B1E"],
  de: ["#000000", "#DD0000", "#FFCE00"],
  es: ["#AA151B", "#F1BF00", "#AA151B"],
  fr: ["#002395", "#FFFFFF", "#ED2939"],
  it: ["#009246", "#FFFFFF", "#CE2B37"],
  nl: ["#AE1C28", "#FFFFFF", "#21468B"],
  pl: ["#FFFFFF", "#DC143C"],
  pt: ["#006600", "#FF0000"],
  ro: ["#002B7F", "#FCD116", "#CE1126"],
  ru: ["#FFFFFF", "#0039A6", "#D52B1E"],
  tr: ["#E30A17", "#FFFFFF", "#E30A17"],
  uk: ["#012169", "#C8102E", "#FFFFFF"],
};

const COUNTRY_CODE_BY_KEY = {
  albania: "al", arabia: "ar", bulgaria: "bg", balkans: "bk", germany: "de", spain: "es",
  france: "fr", italy: "it", netherlands: "nl", poland: "pl", portugal: "pt", romania: "ro",
  russia: "ru", turkey: "tr", unitedkingdom: "uk",
};

async function readJson(relative) {
  return JSON.parse(await readFile(path.join(ROOT, relative), "utf8"));
}

function escapeXml(value) {
  return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function countrySvg(country) {
  const colors = FLAG_COLORS[country.code];
  if (!colors) throw new Error(`Sin colores de bandera para ${country.code}`);
  const width = 400 / colors.length;
  const bands = colors
    .map((color, index) => `<rect x="${(index * width).toFixed(2)}" y="193" width="${width.toFixed(2)}" height="32" fill="${color}"/>`)
    .join("");
  const name = escapeXml(country.name);
  const size = name.length > 14 ? 34 : name.length > 10 ? 40 : 46;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 225" width="400" height="225" role="img" aria-label="${name} TvVoo">
<defs><clipPath id="card"><rect width="400" height="225" rx="28"/></clipPath></defs>
<g clip-path="url(#card)">
<rect width="400" height="225" fill="#0F172A"/>
${bands}
</g>
<text x="200" y="58" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="22" font-weight="700" letter-spacing="6" fill="#94A3B8">TvVoo</text>
<text x="200" y="130" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="${size}" font-weight="700" fill="#F8FAFC">${name}</text>
</svg>
`;
}

function spanishOrder(countries) {
  const first = ["unitedkingdom", "spain"];
  const rank = (country) => {
    const index = first.indexOf(country.countryKey);
    return index === -1 ? 2 : index;
  };
  return [...countries].sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name, "es", { sensitivity: "base" }));
}

function byName(a, b) {
  return a.name.localeCompare(b.name, "es", { sensitivity: "base" }) || (a.catalogKey < b.catalogKey ? -1 : a.catalogKey > b.catalogKey ? 1 : 0);
}

async function main() {
  const layoutText = await readFile(path.join(ROOT, LAYOUT), "utf8");
  const layout = JSON.parse(layoutText);
  const layoutBytesBefore = Buffer.byteLength(layoutText, "utf8");
  if (formatJson(layout) !== layoutText) console.warn("Aviso: el layout no está en el formato canónico; se reescribe igual con formatJson.");
  const selectionOriginal = await readJson(SELECTION);
  const presentationOriginal = await readJson(PRESENTATION);
  const logoMap = (await readJson(LOGO_MAP)).rows;
  const snapshot = (await readJson(SNAPSHOT)).channels;

  // El mapa de logos (tools/tvvoo_inventory_logos.py) usa el país en inglés del inventario
  // («united kingdom»), igual que el snapshot; la etiqueta en español solo se muestra.
  const englishByCountryKey = new Map(snapshot.map((item) => [
    String(item.country).toLowerCase().replace(/[^a-z]/g, ""),
    String(item.country),
  ]));
  const metaFor = (countryKey, name) => {
    const english = englishByCountryKey.get(countryKey);
    return english ? logoMap[`${english.trim().toLowerCase()}|${String(name).trim().toLowerCase()}`] : undefined;
  };

  // Filas del inventario con categoría del inventario oficial cuando la hay (mismo campo que lee el editor).
  const inventory = snapshot.map((item) => {
    const meta = metaFor(String(item.country).toLowerCase().replace(/[^a-z]/g, ""), item.name);
    return meta?.category ? { name: item.name, country: item.country, category: meta.category } : { name: item.name, country: item.country };
  });
  const countries = spanishOrder(tvvooCountriesFromInventory(inventory));

  const candidates = [];
  for (const country of countries) {
    const document = tvvooCatalogFromInventory(inventory, country.code);
    const rows = parseTvVooCatalog(document, country);
    for (const row of rows) {
      candidates.push({ row, country, meta: metaFor(country.countryKey, row.name) });
    }
  }
  // Mismo nombre en el catálogo con otro país: la clave es el país + alias, así que no colisionan.
  const countryRank = new Map(countries.map((country, index) => [country.countryKey, index]));
  candidates.sort((a, b) => (countryRank.get(a.country.countryKey) - countryRank.get(b.country.countryKey)) || byName(a.row, b.row));

  const existingByKey = new Map();
  for (const item of layout.channels) {
    if (item.kind !== "provider" || item.provider !== "tvvoo") continue;
    const list = existingByKey.get(item.catalogKey) ?? [];
    list.push(item);
    existingByKey.set(item.catalogKey, list);
  }

  const stats = {
    snapshotRows: candidates.length,
    perCountry: {},
    addedNew: 0,
    reactivatedDeleted: 0,
    skippedPresent: 0,
    skippedBySourceList: {},
    inventoryLogo: 0,
    genericLogo: 0,
    adultRenamedGroup: 0,
    adultNames: [],
  };

  let nextOrder = Math.max(0, ...layout.channels.map((row) => Number(row.order) || 0)) + 1;
  const appendedKeys = new Set();
  for (const { row, country, meta } of candidates) {
    const key = row.catalogKey;
    const countryStats = (stats.perCountry[country.name] ??= { added: 0, reactivated: 0, skipped: 0 });
    const existing = existingByKey.get(key) ?? [];
    if (existing.some((item) => item.state !== "deleted")) {
      const holder = existing.find((item) => item.state !== "deleted");
      const label = `${holder.state}/${holder.sourceList}`;
      stats.skippedBySourceList[label] = (stats.skippedBySourceList[label] ?? 0) + 1;
      stats.skippedPresent += 1;
      countryStats.skipped += 1;
      continue;
    }
    if (appendedKeys.has(key)) continue;
    appendedKeys.add(key);

    const isAdult = ADULT_NAME_PATTERN.test(row.name);
    const logoPath = meta?.logoPath ?? `logos/tvvoo-paises/${country.code}.svg`;
    if (meta?.logoPath) stats.inventoryLogo += 1;
    else stats.genericLogo += 1;
    if (isAdult) {
      stats.adultRenamedGroup += 1;
      stats.adultNames.push(`${country.name}: ${row.name}`);
    }
    const group = isAdult ? "Adultos" : row.group;

    const deleted = existing.find((item) => item.state === "deleted");
    if (deleted) {
      // Reactivación: se conserva el nombre visible y el logo que el usuario ya eligió.
      const keep = { displayName: deleted.displayName, logoOverride: deleted.logoOverride, logoPath: deleted.logoPath || undefined };
      Object.assign(deleted, sanitizeRow({ ...row, group, category: row.category ?? deleted.category }));
      deleted.sourceList = LIST;
      deleted.state = "active";
      deleted.order = nextOrder++;
      if (keep.displayName !== undefined) deleted.displayName = keep.displayName;
      else delete deleted.displayName;
      if (keep.logoOverride !== undefined) deleted.logoOverride = keep.logoOverride;
      deleted.logoPath = keep.logoPath ?? logoPath;
      stats.reactivatedDeleted += 1;
      countryStats.reactivated += 1;
      continue;
    }

    // Igual que addRow (site/editor-core.mjs), sin clonar el layout 8.000 veces.
    const next = sanitizeRow({ ...row, group, sourceList: LIST, logoPath });
    next.state = "active";
    next.order = nextOrder++;
    next.number = 0;
    layout.channels.push(next);
    stats.addedNew += 1;
    countryStats.added += 1;
  }

  const sealedInput = normalizeLists(layout);
  const problems = validateLayout(sealedInput);
  if (problems.length) {
    console.error(problems.slice(0, 20).join("\n"));
    throw new Error(`El layout no valida (${problems.length} problemas).`);
  }
  const sealed = await approveLayout(sealedInput, "chat");

  const selection = await buildSelectionDocument(sealed, selectionOriginal);
  const presentation = buildPresentationOverrides(sealed, presentationOriginal);

  // Logos genéricos de cada país con filas en el bloque (solo se escriben si cambian).
  await mkdir(path.join(ROOT, "logos/tvvoo-paises"), { recursive: true });
  for (const country of countries) {
    const target = path.join(ROOT, `logos/tvvoo-paises/${country.code}.svg`);
    await writeFileIfChanged(target, countrySvg(country));
  }

  // Registro con el estado final del layout (no con contadores de esta corrida), para que
  // una segunda ejecución lo deje igual.
  const activeList2 = sealed.channels.filter((row) => row.state === "active" && row.sourceList === LIST);
  const blockRows = activeList2.filter((row) => row.kind === "provider" && row.provider === "tvvoo");
  const blockByCountry = {};
  for (const row of blockRows) blockByCountry[row.country] = (blockByCountry[row.country] ?? 0) + 1;
  const registry = {
    schema: 1,
    date: "2026-11-17",
    decision: "Pedido del usuario (2026-11-17): catálogo TvVoo completo al final de Lista 2, por país. Supera «TvVoo fuera de Lista 2 (2026-10-20)» solo para este bloque.",
    source: SNAPSHOT,
    script: "tools/append_tvvoo_catalog_to_list2.mjs",
    list2ActiveTotal: activeList2.length,
    list2NumberRange: activeList2.length ? [Math.min(...activeList2.map((r) => r.number)), Math.max(...activeList2.map((r) => r.number))] : [],
    tvvooBlockRows: blockRows.length,
    tvvooBlockByCountry: blockByCountry,
    tvvooBlockLogoFromInventory: blockRows.filter((row) => String(row.logoPath).startsWith("logos/tvvoo-inventario/")).length,
    tvvooBlockLogoGeneric: blockRows.filter((row) => String(row.logoPath).startsWith("logos/tvvoo-paises/")).length,
    tvvooBlockAdultGroup: blockRows.filter((row) => row.group === "Adultos").length,
    tvvooBlockAdultNames: blockRows.filter((row) => row.group === "Adultos").map((row) => row.name),
    tvvooBlockNotInRunnerCatalog: "Filas sin entrada en channel-catalog.m3u: el runner las deja pendientes (catalog_not_found) hasta que exista su entrada.",
  };

  await writeFile(path.join(ROOT, LAYOUT), formatJson(sealed));
  await writeFile(path.join(ROOT, SELECTION), formatJson(selection));
  await writeFile(path.join(ROOT, PRESENTATION), formatJson(presentation));
  await writeFile(path.join(ROOT, REGISTRY), formatJson(registry));

  const summary = {
    layoutBytesBefore,
    layoutBytesAfter: Buffer.byteLength(formatJson(sealed), "utf8"),
    addedNew: stats.addedNew,
    reactivatedDeleted: stats.reactivatedDeleted,
    skippedPresent: stats.skippedPresent,
    skippedBySourceList: stats.skippedBySourceList,
    inventoryLogo: stats.inventoryLogo,
    genericLogo: stats.genericLogo,
    adultRenamedGroup: stats.adultRenamedGroup,
    perCountry: stats.perCountry,
    tvvooBlockRows: registry.tvvooBlockRows,
    list2NumberRange: registry.list2NumberRange,
    list2ActiveTotal: registry.list2ActiveTotal,
  };
  console.log(JSON.stringify(summary, null, 2));
}

async function writeFileIfChanged(target, content) {
  let current = null;
  try {
    current = await readFile(target, "utf8");
  } catch {
    current = null;
  }
  if (current !== content) await writeFile(target, content, "utf8");
}

await main();
