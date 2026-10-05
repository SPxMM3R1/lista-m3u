const LAYOUT_FIELDS = [
  "kind", "provider", "catalogKey", "providerResourceId", "resolverSlug",
  "tvgId", "name", "group", "category", "country", "countryKey",
  "aliases", "resolverAliases", "identityState", "sourceList", "logoPath",
  "logoOverride", "displayName", "order", "number", "state", "trial", "backupTvVoo", "preferredM3u", "backupm3u",
];

export function stableId(row) {
  const value = row?.kind === "provider" ? row.catalogKey : row?.tvgId;
  return typeof value === "string" ? value : "";
}

export function rowKey(row) {
  const id = stableId(row);
  return row?.kind === "provider" ? `provider:${row.provider}:${id}` : `m3u:${id}`;
}

export function compareRows(a, b) {
  return (Number(a.order) || 0) - (Number(b.order) || 0) || rowKey(a).localeCompare(rowKey(b));
}

export function sanitizeRow(row) {
  const safe = {};
  for (const field of LAYOUT_FIELDS) {
    if (Object.hasOwn(row ?? {}, field)) safe[field] = row[field];
  }
  return safe;
}

export function validateLayout(layout) {
  const problems = [];
  if (layout?.schemaVersion !== 1 || !Array.isArray(layout.channels)) {
    return ["El diseño del catálogo tiene un formato no compatible."];
  }
  if (layout.excludedM3u !== undefined && !Array.isArray(layout.excludedM3u)) {
    problems.push("La lista de exclusiones M3U no tiene un formato válido.");
  }
  const excludedM3u = Array.isArray(layout.excludedM3u) ? layout.excludedM3u : [];
  const excludedIds = new Set();
  for (const rawId of excludedM3u) {
    const id = typeof rawId === "string" ? rawId.trim() : "";
    if (!id || id.length > 512 || /(?:https?:\/\/|\.m3u8?(?:\b|\?)|\.mpd$|[\r\n])/i.test(id)) {
      problems.push("La lista de exclusiones contiene un tvg-id no válido.");
    } else if (excludedIds.has(id)) {
      problems.push(`La exclusión M3U ${id} está duplicada.`);
    }
    excludedIds.add(id);
  }
  const seenIds = new Set();
  const seenPublicIds = new Set();
  const activeNumbers = new Set();
  const seenOrders = new Set();
  const activeRows = layout.channels.filter((row) => row.state === "active");
  for (const row of layout.channels) {
    const id = stableId(row);
    const key = rowKey(row);
    if (!id || seenIds.has(key)) problems.push(`Identidad vacía o repetida: ${id || "sin ID"}.`);
    seenIds.add(key);
    if (id && seenPublicIds.has(id)) problems.push(`La identidad pública ${id} aparece en más de una fuente.`);
    if (id) seenPublicIds.add(id);
    if (row.kind === "m3u" && row.state === "active" && excludedIds.has(id)) {
      problems.push(`${row.name || id}: sigue excluido del catálogo público.`);
    }
    if (!Number.isInteger(row.order) || row.order < 1) problems.push(`${row.name || id}: orden no válido.`);
    else if (seenOrders.has(row.order)) problems.push(`La posición ${row.order} está asignada más de una vez.`);
    else seenOrders.add(row.order);
    if (!Number.isInteger(row.number) || row.number < 1) problems.push(`${row.name || id}: número no válido.`);
    if (!["active", "hidden", "deleted"].includes(row.state)) problems.push(`${row.name || id}: estado no válido.`);
    if (row.trial !== undefined && (row.trial !== true || row.kind !== "m3u")) {
      problems.push(`${row.name || id}: solo un canal M3U puede estar en prueba.`);
    }
    if (row.backupTvVoo !== undefined && (
      row.kind !== "m3u"
      || typeof row.backupTvVoo !== "string"
      || !/^[a-z]+\|vavoo_[^|\s]+%7Cgroup%3A[a-z]{2}$/i.test(row.backupTvVoo)
    )) problems.push(`${row.name || id}: el respaldo TvVoo no es una identidad TvVoo válida.`);
    if (row.preferredM3u !== undefined) {
      const target = layout.channels.find((item) => item.kind === "m3u" && item.tvgId === row.preferredM3u);
      if (row.kind !== "m3u" || typeof row.preferredM3u !== "string" || row.preferredM3u === row.tvgId || !target) {
        problems.push(`${row.name || id}: la señal preferida debe ser otro canal M3U de la lista.`);
      }
    }
    if (row.backupm3u !== undefined) {
      const ids = Array.isArray(row.backupm3u) ? row.backupm3u : [];
      const valid = row.kind === "m3u" && Array.isArray(row.backupm3u) && ids.length > 0 && ids.length <= 8
        && new Set(ids).size === ids.length
        && ids.every((value) => typeof value === "string" && value !== row.tvgId && value !== row.preferredM3u
          && layout.channels.some((item) => item.kind === "m3u" && item.tvgId === value));
      if (!valid) problems.push(`${row.name || id}: los respaldos deben ser otros canales M3U de la lista (hasta 8, sin repetir).`);
    }
    if (row.displayName !== undefined && (
      typeof row.displayName !== "string"
      || !row.displayName.trim()
      || row.displayName.trim().length > 160
      || /(?:https?:\/\/|\.m3u8?(?:\b|\?)|\.mpd(?:\b|\?)|access_token=|token=|signature=|hdnts=|[\r\n])/i.test(row.displayName)
    )) problems.push(`${row.name || id}: el nombre visible en la app no es válido.`);
    if (row.kind === "provider") {
      if (!["highfly", "tvvoo"].includes(row.provider)) problems.push(`${row.name || id}: proveedor no permitido.`);
      if (row.provider === "highfly") {
        const ref = String(row.providerResourceId ?? "");
        const slug = String(row.resolverSlug ?? "");
        if (!id || id.startsWith("leaf:") || id.includes("://") || !/^leaf:[a-z0-9][a-z0-9_-]{1,127}$/i.test(ref) || ref.slice(5) !== slug) {
          problems.push(`${row.name || id}: la identidad Highfly no coincide con su referencia de resolución.`);
        }
      }
      if (row.provider === "tvvoo" && (row.providerResourceId !== id || !id.includes("|") || id.includes("://"))) {
        problems.push(`${row.name || id}: TvVoo debe usar catalogKey como identidad estable.`);
      }
      if (row.provider === "tvvoo" && id.split("|").length !== 2) {
        problems.push(`${row.name || id}: catalogKey TvVoo debe tener país y alias canónico.`);
      }
      if (row.provider === "tvvoo" && row.countryKey && row.countryKey !== id.split("|", 1)[0]) {
        problems.push(`${row.name || id}: countryKey TvVoo debe coincidir con el país de catalogKey.`);
      }
      if (!String(row.identityState ?? "").match(/^(canonical|provisional)$/)) {
        problems.push(`${row.name || id}: falta indicar el estado de identidad.`);
      }
      if (!String(row.name ?? "").trim() || !String(row.group ?? row.category ?? "").trim()) {
        problems.push(`${row.name || id}: falta nombre o grupo del proveedor.`);
      }
    } else if (row.kind !== "m3u" || !String(row.tvgId ?? "").trim()) {
      problems.push(`${row.name || id}: entrada M3U sin tvg-id estable.`);
    } else if (!["1.m3u", "2.m3u"].includes(row.sourceList)) {
      problems.push(`${row.name || id}: selecciona Lista 1 o Lista 2.`);
    }
    const visibleFields = [row.name, row.displayName, row.group, row.category, row.country, row.countryKey, row.alias, row.aliases, row.resolverAliases];
    const flatValues = visibleFields.flatMap((value) => Array.isArray(value) ? value : [value]);
    if (flatValues.some((value) => typeof value === "string" && /(https?:\/\/|\.m3u8?(?:\b|\?)|access_token=|token=|signature=|hdnts=)/i.test(value))) {
      problems.push(`${row.name || id}: no se permiten URLs de reproducción ni credenciales en el catálogo.`);
    }
  }
  for (const row of activeRows) {
    const number = Number(row.number);
    if (activeNumbers.has(number)) problems.push(`El número ${number} está asignado a más de un canal activo.`);
    activeNumbers.add(number);
  }
  return [...new Set(problems)];
}

export function resequence(layout, orderedKeys) {
  const current = structuredClone(layout);
  const lookup = new Map(current.channels.map((row) => [rowKey(row), row]));
  const active = orderedKeys.map((key) => lookup.get(key)).filter((row) => row?.state === "active");
  const activeKeys = new Set(active.map(rowKey));
  const hidden = current.channels.filter((row) => row.state === "hidden").sort(compareRows);
  const deleted = current.channels.filter((row) => row.state === "deleted").sort(compareRows);
  const activeRest = current.channels.filter((row) => row.state === "active" && !activeKeys.has(rowKey(row))).sort(compareRows);
  current.channels = [...active, ...activeRest, ...hidden, ...deleted];
  current.channels.forEach((row, index) => { row.order = index + 1; });
  return current;
}

export function moveRow(layout, key, delta) {
  const active = layout.channels.filter((row) => row.state === "active").sort(compareRows);
  const index = active.findIndex((row) => rowKey(row) === key);
  const next = index + delta;
  if (index < 0 || next < 0 || next >= active.length) return layout;
  const [moving] = active.splice(index, 1);
  active.splice(next, 0, moving);
  return resequence(layout, active.map(rowKey));
}

export function moveRowFiltered(layout, key, delta, isVisible = () => true) {
  const active = layout.channels.filter((row) => row.state === "active").sort(compareRows);
  const visible = active.filter((row) => isVisible(row));
  const index = visible.findIndex((row) => rowKey(row) === key);
  const next = index + delta;
  if (index < 0 || next < 0 || next >= visible.length) return layout;
  const moving = visible[index];
  const target = visible[next];
  const reordered = active.filter((row) => rowKey(row) !== key);
  const targetIndex = reordered.findIndex((row) => rowKey(row) === rowKey(target));
  reordered.splice(targetIndex + (delta > 0 ? 1 : 0), 0, moving);
  return resequence(layout, reordered.map(rowKey));
}

export function setRowState(layout, key, state) {
  const current = structuredClone(layout);
  const row = current.channels.find((item) => rowKey(item) === key);
  if (!row || !["active", "hidden", "deleted"].includes(state)) return current;
  row.state = state;
  const active = current.channels.filter((item) => item.state === "active").sort(compareRows);
  const hidden = current.channels.filter((item) => item.state === "hidden").sort(compareRows);
  const deleted = current.channels.filter((item) => item.state === "deleted").sort(compareRows);
  current.channels = [...active, ...hidden, ...deleted];
  current.channels.forEach((item, index) => { item.order = index + 1; });
  return current;
}

export function addRow(layout, source) {
  const current = structuredClone(layout);
  const key = rowKey(source);
  if (!stableId(source) || current.channels.some((row) => rowKey(row) === key)) return current;
  const active = current.channels.filter((row) => row.state === "active");
  const next = sanitizeRow(source);
  next.state = "active";
  next.order = current.channels.length + 1;
  next.number = Math.max(0, ...active.map((row) => Number(row.number) || 0)) + 1;
  current.channels.push(next);
  if (next.kind === "m3u") {
    current.excludedM3u = (current.excludedM3u ?? []).filter((id) => id !== stableId(next));
  }
  return current;
}

export function renumberFiltered(layout, isVisible = () => true) {
  const current = structuredClone(layout);
  const active = current.channels.filter((row) => row.state === "active").sort(compareRows);
  const reserved = new Set(active.filter((row) => !isVisible(row)).map((row) => Number(row.number)));
  let candidate = 1;
  for (const row of active) {
    if (!isVisible(row)) continue;
    while (reserved.has(candidate)) candidate += 1;
    row.number = candidate;
    candidate += 1;
  }
  return current;
}

export function renumber(layout) {
  return renumberFiltered(layout);
}

export function assignChannelPosition(layout, key, requestedNumber) {
  if (!Number.isSafeInteger(requestedNumber) || requestedNumber < 1) return layout;
  const original = layout.channels.find((row) => rowKey(row) === key);
  if (!original || original.state !== "active" || Number(original.number) === requestedNumber) {
    return layout;
  }

  const current = structuredClone(layout);
  const moving = current.channels.find((row) => rowKey(row) === key);
  current.channels.forEach((row) => {
    if (
      row.state === "active"
      && rowKey(row) !== key
      && Number(row.number) >= requestedNumber
    ) {
      row.number = Number(row.number) + 1;
    }
  });
  moving.number = requestedNumber;
  const activeKeys = current.channels
    .filter((row) => row.state === "active")
    .sort((a, b) => Number(a.number) - Number(b.number) || compareRows(a, b))
    .map(rowKey);
  return resequence(current, activeKeys);
}

export function removePermanently(layout, key) {
  const current = structuredClone(layout);
  const removed = current.channels.find((row) => rowKey(row) === key);
  if (removed?.kind === "m3u") {
    current.excludedM3u = [...new Set([...(current.excludedM3u ?? []), stableId(removed)])];
  }
  current.channels = current.channels.filter((row) => rowKey(row) !== key);
  current.channels.sort((a, b) => {
    const stateRank = { active: 0, hidden: 1, deleted: 2 };
    return (stateRank[a.state] ?? 3) - (stateRank[b.state] ?? 3) || compareRows(a, b);
  });
  current.channels.forEach((row, index) => { row.order = index + 1; });
  return current;
}

export async function buildSelectionDocument(layout, original, publishedAt = new Date().toISOString()) {
  const sources = ["tvvoo", "highfly"].map((provider) => {
    const previous = original.sources?.find((source) => source.provider === provider) ?? { provider };
    const rows = layout.channels
      .filter((row) => row.kind === "provider" && row.provider === provider && row.state === "active")
      .sort(compareRows);
    const channels = rows.map((row, index) => {
      const channel = {
        provider,
        catalogKey: row.catalogKey,
        providerResourceId: row.providerResourceId,
        // Keep the provider's canonical name in the resolver manifest.
        // displayName is presentation-only and must not affect reconciliation.
        name: String(row.name).trim(),
        group: String(row.group || row.category).trim(),
        category: String(row.category || row.group || "").trim(),
        identityState: row.identityState,
        order: index + 1,
      };
      for (const field of ["resolverSlug", "alias", "country", "countryKey"]) {
        if (row[field]) channel[field] = row[field];
      }
      const aliases = row.aliases ?? row.resolverAliases;
      if (Array.isArray(aliases)) channel.aliases = [...new Set(aliases.map(String).filter(Boolean))];
      if (provider === "tvvoo") {
        const stableAlias = String(row.catalogKey).split("|", 2)[1];
        channel.aliases = [...new Set([stableAlias, ...(channel.aliases ?? [])].filter(Boolean))];
        channel.providerResourceId = row.catalogKey;
      }
      return channel;
    });
    return { ...previous, provider, enabled: channels.length > 0, channels };
  });

  const document = {
    ...original,
    schemaVersion: 1,
    publishedAt,
    sources,
  };
  const signatureContent = JSON.stringify(sources.map((source) => ({
    provider: source.provider,
    enabled: source.enabled,
    channels: source.channels.map(({ catalogKey, order, identityState }) => ({ catalogKey, order, identityState })),
  })));
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(signatureContent));
  document.selectionSignature = `sha256:${[...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("")}`;
  if (original.selectionSignature === document.selectionSignature && original.publishedAt) {
    document.publishedAt = original.publishedAt;
  }
  return document;
}

export function buildPresentationOverrides(layout, original) {
  const result = structuredClone(original ?? { schema: 1, orders: {}, info_lines: {}, logos: {}, assets: [] });
  result.schema = 1;
  const root = result.presentation && typeof result.presentation === "object" ? result.presentation : result;
  for (const field of ["orders", "logos", "names"]) {
    if (!root[field] || typeof root[field] !== "object" || Array.isArray(root[field])) root[field] = {};
  }
  const notPurged = layout.channels.slice().sort(compareRows);
  const channelIds = [...new Set(notPurged.map(stableId).filter(Boolean))];
  if (channelIds.length) root.orders["channel-catalog.m3u"] = channelIds;
  const directActive = notPurged.filter((row) => row.kind === "m3u" && row.state === "active");
  const directMain = directActive.filter((row) => row.sourceList === "1.m3u").map(stableId);
  const directExternal = directActive.filter((row) => row.sourceList === "2.m3u").map(stableId);
  root.orders["m3u.m3u"] = [...new Set(directMain)];
  root.orders["m3u-externa.m3u"] = [...new Set(directExternal)];
  // 1.m3u y 2.m3u son alias cortos de las mismas listas: el publicador dirigido guarda su
  // orden aparte y el contrato exige que sea idéntico. Si quedan desfasados, falla la publicación.
  if ("1.m3u" in root.orders) root.orders["1.m3u"] = [...root.orders["m3u.m3u"]];
  if ("2.m3u" in root.orders) root.orders["2.m3u"] = [...root.orders["m3u-externa.m3u"]];
  // Canales en prueba (2026-10-04): se publican en su lista, pero el runner no les busca
  // guía, no los revisa ni los repara hasta que se oficializan.
  root.trial_m3u = [...new Set(directActive.filter((row) => row.trial === true).map(stableId))]
    .sort((a, b) => a.localeCompare(b));
  const excluded = new Set((Array.isArray(root.excluded_m3u) ? root.excluded_m3u : []).map(String));
  for (const id of Array.isArray(layout.excludedM3u) ? layout.excludedM3u : []) excluded.add(String(id));
  for (const row of layout.channels) {
    if (row.kind !== "m3u") continue;
    const id = stableId(row);
    if (row.state === "active") excluded.delete(id);
    else excluded.add(id);
  }
  root.excluded_m3u = [...excluded].sort((a, b) => a.localeCompare(b));
  for (const row of layout.channels) {
    const id = stableId(row);
    if (!id) continue;
    if (row.logoOverride) root.logos[id] = row.logoOverride;
    else if (row.logoOverride === "") delete root.logos[id];
    const displayName = String(row.displayName ?? "").trim();
    if (displayName && displayName !== String(row.name ?? "").trim()) root.names[id] = displayName;
    else delete root.names[id];
  }
  return result;
}

/** Señal preferida de un canal directo: otra fila M3U de la misma señal que se abre primero. */
export function setPreferredM3u(layout, key, tvgId) {
  const current = structuredClone(layout);
  const row = current.channels.find((item) => rowKey(item) === key);
  if (!row || row.kind !== "m3u") return current;
  if (tvgId && tvgId !== row.tvgId) row.preferredM3u = tvgId;
  else delete row.preferredM3u;
  return current;
}

/**
 * Respaldos directos de un canal (0.5.72): otras filas M3U de la misma señal, en el orden en que
 * la app las prueba después de la propia. Una lista vacía los quita.
 */
export function setBackupM3u(layout, key, tvgIds) {
  const current = structuredClone(layout);
  const row = current.channels.find((item) => rowKey(item) === key);
  if (!row || row.kind !== "m3u") return current;
  const ids = [...new Set((tvgIds ?? []).filter((value) => value && value !== row.tvgId && value !== row.preferredM3u))];
  if (ids.length) row.backupm3u = ids.slice(0, 8);
  else delete row.backupm3u;
  return current;
}

/** Respaldo TvVoo de un canal directo (catalogKey de la misma señal); vacío lo quita. */
export function setBackupTvVoo(layout, key, catalogKey) {
  const current = structuredClone(layout);
  const row = current.channels.find((item) => rowKey(item) === key);
  if (!row || row.kind !== "m3u") return current;
  if (catalogKey) row.backupTvVoo = catalogKey;
  else delete row.backupTvVoo;
  return current;
}

/** Marca o quita la marca «en prueba» de un canal M3U. */
export function setTrial(layout, key, trial) {
  const current = structuredClone(layout);
  const row = current.channels.find((item) => rowKey(item) === key);
  if (!row || row.kind !== "m3u") return current;
  if (trial) row.trial = true;
  else delete row.trial;
  return current;
}

export function summarizeChanges(originalLayout, layout, originalPresentation, presentation) {
  const before = new Map((originalLayout.channels ?? []).map((row) => [rowKey(row), row]));
  const after = new Map((layout.channels ?? []).map((row) => [rowKey(row), row]));
  let added = 0;
  let removed = 0;
  let reordered = 0;
  let stateChanges = 0;
  let assignmentChanges = 0;
  let numberChanges = 0;
  let nameChanges = 0;
  let logoChanges = 0;
  let providerReferenceChanges = 0;
  for (const [key, row] of after) {
    if (!before.has(key)) added++;
    else {
      const old = before.get(key);
      if (old.order !== row.order) reordered++;
      if (old.state !== row.state) stateChanges++;
      if (old.sourceList !== row.sourceList) assignmentChanges++;
      if (old.number !== row.number) numberChanges++;
      if (String(old.displayName ?? old.name ?? "").trim() !== String(row.displayName ?? row.name ?? "").trim()) nameChanges++;
      if (old.logoOverride !== row.logoOverride) logoChanges++;
      if (old.provider === "highfly" && row.provider === "highfly"
        && (old.providerResourceId !== row.providerResourceId || old.resolverSlug !== row.resolverSlug)) {
        providerReferenceChanges++;
      }
    }
  }
  for (const key of before.keys()) if (!after.has(key)) removed++;
  const priorSelection = originalLayout.channels.filter((row) => row.kind === "provider" && row.state === "active").length;
  const nextSelection = layout.channels.filter((row) => row.kind === "provider" && row.state === "active").length;
  const logoMapChanged = JSON.stringify(originalPresentation?.logos ?? {}) !== JSON.stringify(presentation?.logos ?? {});
  return { added, removed, reordered, stateChanges, assignmentChanges, numberChanges, nameChanges, logoChanges, providerReferenceChanges, providerSelectionChanged: priorSelection !== nextSelection, logoMapChanged };
}

export function formatJson(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}

// Palabras que describen calidad, respaldo o variante gráfica: no cambian qué canal es.
const LOGO_NOISE_WORDS = new Set([
  "hd", "fhd", "uhd", "sd", "4k", "8k", "hevc", "backup", "logopedia", "transparent",
  "mosca", "color", "dark", "light", "white", "black", "tvvoo",
]);

/** Clave de nombre para cruzar un canal con un archivo de logo ("SKY SPORTS F1 FHD" → "skysportsf1"). */
export function logoNameKey(value) {
  let text = String(value ?? "").trim();
  const file = text.split("/").pop();
  if (file !== text || /\.(png|svg|jpe?g|webp)$/i.test(text)) {
    text = file.replace(/\.(png|svg|jpe?g|webp)$/i, "").replace(/--[0-9a-f]{6,}$/i, "");
  }
  const words = text
    .normalize("NFD").replace(/\p{M}+/gu, "")
    .toLowerCase()
    .replace(/\([^)]*\)/g, " ")
    .split(/[^a-z0-9]+/)
    .filter((word) => word && !LOGO_NOISE_WORDS.has(word));
  return words.join("");
}

/**
 * Logo sugerido para una fila sin logo. Orden: logo local del catálogo para la misma identidad
 * (catalogKey Highfly o alias TvVoo), después un logo vigente con el mismo nombre y por último
 * uno histórico. Nunca devuelve URLs remotas: solo rutas bajo logos/.
 */
export function suggestLogo(row, { catalogLogos = {}, logos = [] } = {}) {
  if (!row) return "";
  const byId = catalogLogos.byId ?? {};
  const byAlias = catalogLogos.byAlias ?? {};
  if (row.kind === "m3u") return byId[row.tvgId] ?? "";
  if (row.provider === "highfly" && byId[row.catalogKey]) return byId[row.catalogKey];
  if (row.provider === "tvvoo") {
    const alias = String(row.catalogKey ?? "").split("|", 2)[1] ?? "";
    for (const candidate of [alias, ...(row.aliases ?? []), ...(row.resolverAliases ?? [])]) {
      if (!candidate) continue;
      let decoded = candidate;
      try { decoded = decodeURIComponent(candidate); } catch { /* alias ya decodificado */ }
      const path = byAlias[candidate] ?? byAlias[decoded];
      if (path) return path;
    }
  }
  const key = logoNameKey(row.name);
  if (!key) return "";
  const matches = logos.filter((path) => typeof path === "string" && logoNameKey(path) === key);
  const rank = (path) => (path.startsWith("logos/history/") ? 1 : 0);
  matches.sort((a, b) => rank(a) - rank(b) || a.length - b.length || a.localeCompare(b));
  return matches[0] ?? "";
}

/** Cambia el estado de varias filas a la vez (selección múltiple del editor). */
export function setRowsState(layout, keys, state) {
  const current = structuredClone(layout);
  if (!["active", "hidden", "deleted"].includes(state)) return current;
  const wanted = new Set(keys);
  for (const row of current.channels) {
    if (wanted.has(rowKey(row))) row.state = state;
  }
  // Igual que setRowState: activos, ocultos y papelera, conservando el orden relativo.
  const byState = (name) => current.channels.filter((item) => item.state === name).sort(compareRows);
  current.channels = [...byState("active"), ...byState("hidden"), ...byState("deleted")];
  current.channels.forEach((item, index) => { item.order = index + 1; });
  return current;
}

/** Elimina definitivamente varias filas; las M3U quedan como tombstone en excludedM3u. */
export function removeRowsPermanently(layout, keys) {
  let current = layout;
  for (const key of new Set(keys)) current = removePermanently(current, key);
  return current === layout ? structuredClone(layout) : current;
}
