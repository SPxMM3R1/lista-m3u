const LAYOUT_FIELDS = [
  "kind", "provider", "catalogKey", "providerResourceId", "resolverSlug",
  "tvgId", "name", "group", "category", "country", "countryKey",
  "aliases", "resolverAliases", "identityState", "sourceList", "logoPath",
  "logoOverride", "order", "number", "state",
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
    const visibleFields = [row.name, row.group, row.category, row.country, row.countryKey, row.alias, row.aliases, row.resolverAliases];
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

export function renumber(layout) {
  const current = structuredClone(layout);
  current.channels.filter((row) => row.state === "active").sort(compareRows)
    .forEach((row, index) => { row.number = index + 1; });
  return current;
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
  root.orders ??= {};
  root.logos ??= {};
  const notPurged = layout.channels.slice().sort(compareRows);
  const channelIds = [...new Set(notPurged.map(stableId).filter(Boolean))];
  if (channelIds.length) root.orders["channel-catalog.m3u"] = channelIds;
  const directActive = notPurged.filter((row) => row.kind === "m3u" && row.state === "active");
  const directMain = directActive.filter((row) => row.sourceList === "1.m3u").map(stableId);
  const directExternal = directActive.filter((row) => row.sourceList === "2.m3u").map(stableId);
  root.orders["m3u.m3u"] = [...new Set(directMain)];
  root.orders["m3u-externa.m3u"] = [...new Set(directExternal)];
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
  }
  return result;
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
  return { added, removed, reordered, stateChanges, assignmentChanges, numberChanges, logoChanges, providerReferenceChanges, providerSelectionChanged: priorSelection !== nextSelection, logoMapChanged };
}

export function formatJson(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}

export async function gitBlobSha(content) {
  const body = new TextEncoder().encode(String(content));
  const header = new TextEncoder().encode(`blob ${body.byteLength}\0`);
  const blob = new Uint8Array(header.byteLength + body.byteLength);
  blob.set(header, 0);
  blob.set(body, header.byteLength);
  const digest = await crypto.subtle.digest("SHA-1", blob);
  return [...new Uint8Array(digest)]
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}
