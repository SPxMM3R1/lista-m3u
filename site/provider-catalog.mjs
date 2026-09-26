const HIGHFLY_MANIFEST_URL = "https://sports.highfly.to/manifest.json";
const HIGHFLY_CATALOG_URL = "https://sports.highfly.to/catalog/sport/sports_live.json";
const TVVOO_MANIFEST_URL = "https://tvvoo.hayd.uk/manifest.json";
const TVVOO_ORIGIN = "https://tvvoo.hayd.uk";
const MAX_MANIFEST_BYTES = 512 * 1024;
const MAX_HIGHFLY_BYTES = 2 * 1024 * 1024;
const MAX_TVVOO_BYTES = 8 * 1024 * 1024;
const REQUEST_TIMEOUT_MS = 20_000;

const COUNTRY_KEYS = {
  al: "albania",
  ar: "arabia",
  bg: "bulgaria",
  bk: "balkans",
  de: "germany",
  es: "spain",
  fr: "france",
  it: "italy",
  nl: "netherlands",
  pl: "poland",
  pt: "portugal",
  ro: "romania",
  ru: "russia",
  tr: "turkey",
  uk: "unitedkingdom",
};

const COUNTRY_LABELS = {
  al: "Albania",
  ar: "Arabia",
  bg: "Bulgaria",
  bk: "Balcanes",
  de: "Alemania",
  es: "España",
  fr: "Francia",
  it: "Italia",
  nl: "Países Bajos",
  pl: "Polonia",
  pt: "Portugal",
  ro: "Rumania",
  ru: "Rusia",
  tr: "Turquía",
  uk: "Reino Unido",
};

function text(value, maximum = 240) {
  return typeof value === "string" ? value.replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, maximum) : "";
}

export function normalizeProviderName(value) {
  return text(value, 512).normalize("NFD").replace(/\p{M}+/gu, "").toLowerCase().replace(/[^a-z0-9]+/g, "");
}

export function cleanHighflyName(value) {
  return text(value).replace(/^\((?:SD|HD|FHD|UHD|4K|8K|HEVC|H\.?265|H\.?264|FULL\s*HD)\)\s*[:\-–]\s*/i, "").trim();
}

function appCompatibleHighflyIdentity(name) {
  const normalized = normalizeProviderName(name);
  if (normalized.includes("skysportsf1") || normalized.includes("skyf1")) return "SkySportsF1.uk";
  if (normalized.includes("skysportstennis") || normalized.includes("skytennis")) return "SkySportsTennis.uk";
  if (normalized.includes("skysportspremierleague") || normalized.includes("skypremierleague")) return "SkySportsPremierLeague.uk";
  if (normalized.includes("skysportsgolf") || normalized.includes("skygolf")) return "SkySportsGolf.uk";
  if (normalized === "espn") return "ESPN.us";
  if (normalized === "marqueesportsnetwork") return "MarqueeSportsNetwork.us";
  if (normalized === "skysport1") return "SkySport1.nz";
  return "";
}

export function highflyIdentity(name, registry = []) {
  const displayName = cleanHighflyName(name);
  const normalized = normalizeProviderName(displayName);
  const registryRows = Array.isArray(registry) ? registry : [];
  const knownKeys = new Set(registryRows.map((row) => text(row?.catalogKey, 160)).filter(Boolean));
  const appKey = appCompatibleHighflyIdentity(displayName);
  if (appKey) return { catalogKey: appKey, identityState: knownKeys.has(appKey) ? "canonical" : "provisional" };

  const matches = new Set(registryRows
    .filter((row) => normalizeProviderName(row?.name) === normalized)
    .map((row) => text(row?.catalogKey, 160))
    .filter(Boolean));
  if (matches.size === 1) return { catalogKey: [...matches][0], identityState: "canonical" };

  // Mirror the app's stable, slug-independent fallback. It remains provisional
  // until Lista M3U has an unambiguous canonical catalogue entry for it.
  const compact = normalized.slice(0, 112) || "unknown";
  return { catalogKey: `Highfly.${compact}`, identityState: "provisional" };
}

export function highflyQualityLabel(rawName) {
  const match = /\((SD|HD|FHD|UHD|4K|8K|HEVC|H\.?265|H\.?264|FULL\s*HD)\)/i.exec(String(rawName ?? ""));
  if (!match) return "Señal";
  const label = match[1].toUpperCase().replace(/\s+/g, "");
  return label.replace(/^H(265|264)$/, "H$1");
}

export function parseHighflyCatalog(document, registry = []) {
  const metas = Array.isArray(document?.metas) ? document.metas : [];
  const grouped = new Map();
  for (const meta of metas) {
    const resourceId = text(meta?.id, 140);
    const rawName = text(meta?.name);
    const name = cleanHighflyName(rawName);
    if (!/^leaf:[a-z0-9][a-z0-9_-]{1,127}$/i.test(resourceId) || !name) continue;
    const identity = highflyIdentity(name, registry);
    let entry = grouped.get(identity.catalogKey);
    if (!entry) {
      const genres = Array.isArray(meta?.genres) ? meta.genres.map((value) => text(value, 80)).filter(Boolean) : [];
      const category = genres.find((value) => normalizeProviderName(value) !== "sportslive") ?? "";
      entry = {
        kind: "provider",
        provider: "highfly",
        catalogKey: identity.catalogKey,
        name,
        group: "Deportes",
        ...(category ? { category } : {}),
        identityState: identity.identityState,
        options: [],
      };
      grouped.set(identity.catalogKey, entry);
    }
    const slug = resourceId.slice("leaf:".length);
    if (!entry.options.some((option) => option.resourceId === resourceId)) {
      entry.options.push({
        resourceId,
        slug,
        quality: highflyQualityLabel(rawName),
        name,
      });
    }
  }
  const result = [];
  for (const entry of grouped.values()) {
    const [primary] = entry.options;
    if (!primary) continue;
    result.push({
      ...entry,
      providerResourceId: primary.resourceId,
      resolverSlug: primary.slug,
    });
  }
  return result;
}

function parsePastedJson(raw, maximumBytes, provider) {
  if (typeof raw !== "string" || !raw.trim()) throw new Error(`Pega primero el JSON de ${provider}.`);
  if (new TextEncoder().encode(raw).byteLength > maximumBytes) {
    const megabytes = maximumBytes / (1024 * 1024);
    const limit = Number.isInteger(megabytes) ? `${megabytes} MiB` : `${Math.ceil(maximumBytes / 1024)} KiB`;
    throw new Error(`El JSON de ${provider} supera el límite de ${limit}.`);
  }
  try {
    return JSON.parse(raw);
  } catch {
    throw new Error(`El texto de ${provider} no es JSON válido.`);
  }
}

export function parseHighflyCatalogJson(raw, registry = []) {
  const document = parsePastedJson(raw, MAX_HIGHFLY_BYTES, "Highfly");
  if (!Array.isArray(document?.metas)) throw new Error("El JSON Highfly debe ser un catálogo con una propiedad metas[].");
  const rows = parseHighflyCatalog(document, registry);
  if (!rows.length) throw new Error("El JSON no contiene canales Highfly reconocibles. Se esperan recursos leaf:* con nombre.");
  return rows;
}

export function parseTvVooManifest(document) {
  if (!Array.isArray(document?.catalogs)) throw new Error("TvVoo no publicó una lista de países reconocible.");
  const countries = [];
  const seen = new Set();
  for (const catalog of document.catalogs) {
    const catalogId = text(catalog?.id, 64).toLowerCase();
    const match = /^vavoo_tv_([a-z]{2})$/.exec(catalogId);
    if (!match || (catalog?.type && catalog.type !== "tv") || seen.has(catalogId)) continue;
    const code = match[1];
    const rawName = text(catalog?.name, 120).replace(/^Vavoo\s+TV\s*[•·-]\s*/i, "");
    countries.push({
      id: catalogId,
      code,
      countryKey: COUNTRY_KEYS[code] ?? (normalizeProviderName(rawName) || code),
      name: COUNTRY_LABELS[code] ?? rawName ?? code.toUpperCase(),
    });
    seen.add(catalogId);
  }
  if (!countries.length) throw new Error("TvVoo no publicó catálogos de televisión disponibles.");
  return countries.sort((left, right) => left.id === "vavoo_tv_es" ? -1 : right.id === "vavoo_tv_es" ? 1 : left.name.localeCompare(right.name, "es"));
}

export function parseTvVooManifestJson(raw) {
  return parseTvVooManifest(parsePastedJson(raw, MAX_MANIFEST_BYTES, "el manifiesto TvVoo"));
}

function decodeAliasPart(value) {
  try {
    // Java URLDecoder treats + as a space; protect a literal plus exactly as
    // TvVooCatalogChannel.canonicalAlias does in VibeM3U.
    return decodeURIComponent(value.replace(/\+/g, "%2B"));
  } catch {
    return value;
  }
}

function encodeAliasPart(value) {
  return encodeURIComponent(value)
    .replace(/[!'()~]/g, (character) => `%${character.charCodeAt(0).toString(16).toUpperCase()}`)
    .replace(/%[0-9a-f]{2}/gi, (escape) => escape.toUpperCase());
}

export function canonicalTvVooAlias(idOrAlias, countryCode) {
  const raw = text(idOrAlias, 1024);
  if (!raw.startsWith("vavoo_")) throw new Error("Identificador TvVoo no válido.");
  let decoded = decodeAliasPart(raw.slice("vavoo_".length));
  const code = text(countryCode, 2).toLowerCase();
  if (!decoded.toLowerCase().includes("|group:")) decoded += `|group:${code}`;
  return `vavoo_${encodeAliasPart(decoded)}`;
}

export function parseTvVooCatalog(document, country) {
  if (!country || !/^vavoo_tv_[a-z]{2}$/.test(country.id ?? "")) throw new Error("El país TvVoo seleccionado no es válido.");
  const metas = Array.isArray(document?.metas) ? document.metas : [];
  const result = [];
  const seen = new Set();
  for (const meta of metas) {
    const rawId = text(meta?.id, 1024);
    const name = text(meta?.name);
    if (!rawId.startsWith("vavoo_") || !name) continue;
    let alias;
    try {
      alias = canonicalTvVooAlias(rawId, country.code);
    } catch {
      continue;
    }
    const catalogKey = `${country.countryKey}|${alias}`;
    if (seen.has(catalogKey)) continue;
    seen.add(catalogKey);
    const genres = Array.isArray(meta?.genres) ? meta.genres.map((value) => text(value, 80)).filter(Boolean) : [];
    const category = genres[0] ?? "";
    result.push({
      kind: "provider",
      provider: "tvvoo",
      catalogKey,
      providerResourceId: catalogKey,
      alias,
      aliases: [alias],
      resolverAliases: [alias],
      country: country.name,
      countryKey: country.countryKey,
      name,
      group: country.name,
      ...(category ? { category } : {}),
      identityState: "canonical",
    });
  }
  return result;
}

export function parseTvVooCatalogJson(raw, country) {
  const document = parsePastedJson(raw, MAX_TVVOO_BYTES, "TvVoo");
  if (!Array.isArray(document?.metas)) throw new Error("El JSON TvVoo debe ser un catálogo regional con una propiedad metas[].");
  const rows = parseTvVooCatalog(document, country);
  if (!rows.length) throw new Error("El JSON no contiene canales TvVoo reconocibles para el país seleccionado.");
  return rows;
}

async function fetchJson(url, maximumBytes, fetchImpl, signal, unavailableMessage) {
  const expectedOrigin = new URL(url).origin;
  const controller = new AbortController();
  const abortFromCaller = () => controller.abort(signal?.reason);
  if (signal?.aborted) abortFromCaller();
  else signal?.addEventListener("abort", abortFromCaller, { once: true });
  const timeout = setTimeout(() => controller.abort(new DOMException("Timeout", "TimeoutError")), REQUEST_TIMEOUT_MS);
  try {
    let response;
    try {
      response = await fetchImpl(url, {
        method: "GET",
        mode: "cors",
        credentials: "omit",
        cache: "no-store",
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
    } catch (error) {
      if (error?.name === "AbortError" || error?.name === "TimeoutError") throw new Error(`${unavailableMessage} La solicitud tardó demasiado; vuelve a intentar.`);
      throw new Error(`${unavailableMessage} Revisa la conexión e inténtalo otra vez.`);
    }
    if (!response.ok) throw new Error(`${unavailableMessage} El catálogo respondió HTTP ${response.status}.`);
    if (response.url && new URL(response.url).origin !== expectedOrigin) throw new Error(`${unavailableMessage} La respuesta cambió de origen y se rechazó por seguridad.`);
    const declaredLength = Number(response.headers?.get?.("content-length") ?? 0);
    if (declaredLength > maximumBytes) throw new Error(`${unavailableMessage} La respuesta excede el tamaño permitido.`);
    let raw;
    if (response.body?.getReader) {
      const reader = response.body.getReader();
      const chunks = [];
      let totalBytes = 0;
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          totalBytes += value.byteLength;
          if (totalBytes > maximumBytes) {
            try { await reader.cancel(); } catch { /* The stream is already too large. */ }
            throw new Error(`${unavailableMessage} La respuesta excede el tamaño permitido.`);
          }
          chunks.push(value);
        }
      } catch (error) {
        if (error?.message?.includes("excede el tamaño permitido")) throw error;
        throw new Error(`${unavailableMessage} No se pudo leer la respuesta.`);
      }
      const bytes = new Uint8Array(totalBytes);
      let offset = 0;
      for (const chunk of chunks) {
        bytes.set(chunk, offset);
        offset += chunk.byteLength;
      }
      raw = new TextDecoder().decode(bytes);
    } else {
      try {
        raw = await response.text();
      } catch {
        throw new Error(`${unavailableMessage} No se pudo leer la respuesta.`);
      }
    }
    if (new TextEncoder().encode(raw).byteLength > maximumBytes) throw new Error(`${unavailableMessage} La respuesta excede el tamaño permitido.`);
    try {
      return JSON.parse(raw);
    } catch {
      throw new Error(`${unavailableMessage} La respuesta no contiene JSON válido.`);
    }
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener("abort", abortFromCaller);
  }
}

export async function loadHighflyCatalog({ fetchImpl = globalThis.fetch, registry = [], signal } = {}) {
  const manifest = await fetchJson(HIGHFLY_MANIFEST_URL, MAX_MANIFEST_BYTES, fetchImpl, signal, "Highfly no está disponible ahora.");
  const hasCatalogResource = Array.isArray(manifest?.resources)
    && manifest.resources.some((resource) => resource?.name === "catalog");
  const hasLiveCatalog = Array.isArray(manifest?.catalogs)
    && manifest.catalogs.some((catalog) => catalog?.id === "sports_live");
  if (!hasCatalogResource || !hasLiveCatalog) throw new Error("Highfly cambió el formato de su catálogo; no se añadieron canales.");
  const document = await fetchJson(HIGHFLY_CATALOG_URL, MAX_HIGHFLY_BYTES, fetchImpl, signal, "Highfly no está disponible ahora.");
  if (!Array.isArray(document?.metas)) throw new Error("Highfly devolvió un catálogo sin canales reconocibles.");
  return parseHighflyCatalog(document, registry);
}

export async function loadTvVooManifest({ fetchImpl = globalThis.fetch, signal } = {}) {
  const document = await fetchJson(TVVOO_MANIFEST_URL, MAX_MANIFEST_BYTES, fetchImpl, signal, "TvVoo no está disponible ahora.");
  return parseTvVooManifest(document);
}

export async function loadTvVooCatalog(catalogId, country, { fetchImpl = globalThis.fetch, signal } = {}) {
  const safeId = text(catalogId, 64).toLowerCase();
  if (!/^vavoo_tv_[a-z]{2}$/.test(safeId) || country?.id !== safeId) throw new Error("El catálogo TvVoo seleccionado no es válido.");
  const url = `${TVVOO_ORIGIN}/catalog/tv/${safeId}.json`;
  const document = await fetchJson(url, MAX_TVVOO_BYTES, fetchImpl, signal, "TvVoo no está disponible ahora.");
  if (!Array.isArray(document?.metas)) throw new Error("TvVoo devolvió un catálogo sin canales reconocibles.");
  return parseTvVooCatalog(document, country);
}
