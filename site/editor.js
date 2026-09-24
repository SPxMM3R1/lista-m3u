import {
  addRow,
  buildPresentationOverrides,
  buildSelectionDocument,
  compareRows,
  formatJson,
  gitBlobSha,
  moveRow,
  removePermanently,
  renumber,
  resequence,
  rowKey,
  sanitizeRow,
  setRowState,
  stableId,
  summarizeChanges,
  validateLayout,
} from "./editor-core.mjs";
import {
  loadHighflyCatalog,
  loadTvVooCatalog,
  loadTvVooManifest,
  parseHighflyCatalogJson,
  parseTvVooCatalogJson,
  parseTvVooManifestJson,
} from "./provider-catalog.mjs";

const REPOSITORY = "SPxMM3R1/lista-m3u";
const BRANCH = "main";
const API = `https://api.github.com/repos/${REPOSITORY}`;
const RAW = `https://raw.githubusercontent.com/${REPOSITORY}/main`;
const FILES = {
  selection: "data/vibem3u-selection.json",
  layout: "data/channel-editor-layout.json",
  presentation: "presentation-overrides.json",
};
const SOURCE_LABELS = {
  "1.m3u": "Lista 1",
  "2.m3u": "Lista 2",
  highfly: "Highfly",
  tvvoo: "TvVoo",
};
const PENDING_REASONS = {
  catalog_not_found: "El runner aún no encuentra esta identidad en el catálogo.",
  identity_provisional: "La identidad es provisional; el runner no la resolverá automáticamente.",
  catalog_identity_already_selected: "Esta identidad ya está vinculada a otro canal seleccionado.",
  catalog_match_ambiguous: "Hay más de una coincidencia posible; no se eligió ninguna.",
  catalog_missing_tvg_id: "La entrada del catálogo no tiene tvg-id.",
};
const LOCAL_MODE = location.protocol === "http:" && ["127.0.0.1", "localhost", "::1"].includes(location.hostname);

const $ = (selector) => document.querySelector(selector);
const elements = {
  activeCount: $("#active-count"),
  activeTabCount: $("#active-tab-count"),
  hiddenTabCount: $("#hidden-tab-count"),
  deletedTabCount: $("#deleted-tab-count"),
  search: $("#search-input"),
  sourceFilter: $("#source-filter"),
  list: $("#channel-list"),
  inspector: $("#inspector"),
  visibleRange: $("#visible-range"),
  publish: $("#publish-button"),
  publishDialog: $("#publish-dialog"),
  publishForm: $("#publish-form"),
  token: $("#github-token"),
  tokenLabel: $(".token-label"),
  tokenHelp: $(".token-help"),
  confirmPublish: $("#confirm-publish"),
  publishError: $("#publish-error"),
  localGithubAuth: $("#local-github-auth"),
  localGithubStatus: $("#local-github-status"),
  connectGithub: $("#connect-github"),
  localMode: $("#local-mode-indicator"),
  publishSummary: $("#publish-summary"),
  changeReview: $("#change-review"),
  reviewList: $("#review-list"),
  toast: $("#toast"),
  logoDialog: $("#logo-dialog"),
  logoGrid: $("#logo-grid"),
  logoSearch: $("#logo-search"),
  logoTitle: $("#logo-dialog-channel"),
  addDialog: $("#add-dialog"),
  availableList: $("#available-list"),
  availableSearch: $("#available-search"),
  providerStatus: $("#provider-catalog-status"),
  tvvooCountryField: $("#tvvoo-country-field"),
  tvvooCountry: $("#tvvoo-country"),
  refreshProviderCatalog: $("#refresh-provider-catalog"),
  manualCatalog: $("#manual-catalog"),
  highflyJsonPanel: $("#highfly-json-panel"),
  highflyCatalogJson: $("#highfly-catalog-json"),
  highflyJsonStatus: $("#highfly-json-status"),
  tvvooJsonPanel: $("#tvvoo-json-panel"),
  tvvooManifestJson: $("#tvvoo-manifest-json"),
  tvvooManifestStatus: $("#tvvoo-manifest-status"),
  tvvooCatalogJson: $("#tvvoo-catalog-json"),
  tvvooJsonStatus: $("#tvvoo-json-status"),
  previewDialog: $("#preview-dialog"),
  previewVideo: $("#preview-video"),
  previewStatus: $("#preview-status"),
  previewError: $("#preview-error"),
};

const PROVIDER_CACHE_MS = 10 * 60 * 1000;
const providerCache = {
  highfly: { rows: [], loadedAt: 0, status: "idle", error: "", pending: null, requestId: 0 },
  tvvoo: { countries: [], loadedAt: 0, status: "idle", error: "", pending: null, requestId: 0, catalogs: new Map() },
};

let state = null;
let activeView = "active";
let sourceFilter = "all";
let addSource = "m3u";
let selectedTvVooCatalogId = "vavoo_tv_es";
let selectedKey = "";
let tokenInMemory = "";
let toastTimer = 0;
let localGithubAuthenticated = false;
let previewPlayer = null;
let previewSessionId = "";
let hlsLoadPromise = null;

function icon(name) {
  const paths = {
    up: '<path d="m5 12 5-5 5 5M10 7v10"/>',
    down: '<path d="m5 8 5 5 5-5M10 3v10"/>',
    plus: '<path d="M10 4v12M4 10h12"/>',
    check: '<path d="m4 10 4 4 8-8"/>',
    warning: '<path d="M10 3 2.5 16h15L10 3Z"/><path d="M10 7.5v4m0 2.2v.1"/>',
    eye: '<path d="M2.5 10s2.7-4.5 7.5-4.5 7.5 4.5 7.5 4.5-2.7 4.5-7.5 4.5-7.5-4.5-7.5-4.5Z"/><circle cx="10" cy="10" r="1.8"/>',
    bin: '<path d="M4 6h12m-10 0 .6 10h6.8L14 6M8 6V4h4v2m-3 3v4m2-4v4"/>',
    play: '<path d="M6 4.5v11l9-5.5-9-5.5Z"/>',
  };
  return `<svg aria-hidden="true" viewBox="0 0 20 20">${paths[name] ?? paths.check}</svg>`;
}

function node(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== "") element.textContent = text;
  return element;
}

function button(label, className, action, symbol = "") {
  const element = document.createElement("button");
  element.type = "button";
  element.className = `button ${className}`.trim();
  element.textContent = label;
  if (symbol) element.insertAdjacentHTML("afterbegin", icon(symbol));
  if (action) element.addEventListener("click", action);
  return element;
}

function clone(value) {
  return structuredClone(value);
}

function sourceFor(row) {
  return row.kind === "provider" ? row.provider : row.sourceList;
}

function sourceName(row) {
  return SOURCE_LABELS[sourceFor(row)] ?? "Sin fuente";
}

function imageUrl(path) {
  if (!path || typeof path !== "string") return "";
  const relative = path.split("/").map(encodeURIComponent).join("/");
  return LOCAL_MODE ? `./${relative}` : `${RAW}/${relative}`;
}

function ensureLocalHlsClient() {
  if (window.Hls) return Promise.resolve();
  if (!hlsLoadPromise) {
    hlsLoadPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "./assets/vendor/hls.min.js";
      script.onload = resolve;
      script.onerror = () => reject(new Error("No se pudo cargar el reproductor HLS local."));
      document.head.append(script);
    }).catch((error) => {
      hlsLoadPromise = null;
      throw error;
    });
  }
  return hlsLoadPromise;
}

function logoPathFor(row) {
  return row.logoOverride || row.logoPath || "";
}

function makeLogo(row, className = "channel-logo") {
  const path = logoPathFor(row);
  if (!path) {
    const fallback = node("span", "logo-fallback", String(row.name ?? "?").trim().slice(0, 1).toLocaleUpperCase("es"));
    fallback.setAttribute("aria-hidden", "true");
    return fallback;
  }
  const image = node("img", className);
  image.src = imageUrl(path);
  image.alt = "";
  image.loading = "lazy";
  image.addEventListener("error", () => image.replaceWith(node("span", "logo-fallback", String(row.name ?? "?").slice(0, 1).toLocaleUpperCase("es"))), { once: true });
  return image;
}

function identityFor(row) {
  return stableId(row);
}

function displayIdentity(row) {
  return row.kind === "provider" ? row.catalogKey : row.tvgId;
}

function rowSearchText(row) {
  return [row.name, row.group, row.category, row.provider, row.sourceList, stableId(row), row.country]
    .filter(Boolean).join(" ").toLocaleLowerCase("es");
}

async function loadJson(path) {
  const response = await fetch(path, { cache: "no-store", credentials: "omit" });
  if (!response.ok) throw new Error(`No se pudo cargar ${path} (${response.status}).`);
  return response.json();
}

function normalizedLoadedLayout(layout, catalog, presentation) {
  const rows = Array.isArray(layout?.channels) ? layout.channels.map((row) => ({ ...row })) : [];
  const metadataByKey = new Map((catalog?.channels ?? []).map((row) => [rowKey(row), row]));
  const logoMap = (presentation?.presentation ?? presentation)?.logos ?? {};
  return {
    schemaVersion: 1,
    excludedM3u: Array.isArray(layout?.excludedM3u) ? [...new Set(layout.excludedM3u.map(String))] : [],
    channels: rows.map((row) => {
      const metadata = metadataByKey.get(rowKey(row)) ?? {};
      const merged = { ...metadata, ...row };
      const identity = identityFor(merged);
      if (!Object.hasOwn(merged, "logoOverride") && logoMap[identity]) merged.logoOverride = logoMap[identity];
      if (!merged.logoPath && metadata.logoPath) merged.logoPath = metadata.logoPath;
      if (!merged.order) merged.order = rows.indexOf(row) + 1;
      if (!merged.number) merged.number = merged.order;
      if (!merged.state) merged.state = "active";
      return sanitizeRow(merged);
    }),
  };
}

async function initialize() {
  try {
    if (LOCAL_MODE) {
      elements.localMode.hidden = false;
      elements.tokenLabel.hidden = true;
      elements.token.hidden = true;
      elements.tokenHelp.hidden = true;
      elements.token.required = false;
      elements.localGithubAuth.hidden = false;
      await refreshLocalStatus();
    }
    const [catalog, logos, layout, selection, presentation, repository, runnerStatus, providerIdentities] = await Promise.all([
      loadJson("./data/catalog.json"),
      loadJson("./data/logos.json"),
      loadJson("./data/layout.json"),
      loadJson("./data/selection.json"),
      loadJson("./data/presentation.json"),
      loadJson("./data/repository.json"),
      loadJson("./data/runner-status.json"),
      loadJson("./data/provider-identities.json"),
    ]);
    const normalizedLayout = normalizedLoadedLayout(layout, catalog, presentation);
    state = {
      catalog: catalog.channels ?? [],
      logos: logos.logos ?? [],
      layout: normalizedLayout,
      originalLayout: clone(normalizedLayout),
      selection,
      presentation,
      originalPresentationBaseline: buildPresentationOverrides(normalizedLayout, presentation),
      repository,
      runnerStatus,
      providerIdentities: Array.isArray(providerIdentities.identities) ? providerIdentities.identities : [],
      numberDraft: "",
      loadingError: "",
    };
    const first = state.layout.channels.filter((row) => row.state === "active").sort(compareRows)[0];
    selectedKey = first ? rowKey(first) : "";
    render();
    document.addEventListener("keydown", handleGlobalKeydown);
  } catch (error) {
    state = { loadingError: error.message };
    elements.visibleRange.textContent = "No se pudo cargar el catálogo.";
    const message = node("li", "empty-state", error.message);
    elements.list.replaceChildren(message);
    showToast(error.message, true);
  }
}

function allRows() {
  if (!state) return [];
  return state.layout.channels.slice().sort(compareRows);
}

function counts() {
  const rows = allRows();
  return {
    active: rows.filter((row) => row.state === "active").length,
    hidden: rows.filter((row) => row.state === "hidden").length,
    deleted: rows.filter((row) => row.state === "deleted").length,
  };
}

function layoutDocument() {
  return {
    schemaVersion: 1,
    excludedM3u: [...new Set(state.layout.excludedM3u ?? [])].sort((a, b) => a.localeCompare(b)),
    channels: state.layout.channels.map(sanitizeRow).sort(compareRows),
  };
}

function currentPresentation() {
  return buildPresentationOverrides(layoutDocument(), state.presentation);
}

function isDirty() {
  if (!state || state.loadingError) return false;
  const layoutChanged = JSON.stringify(layoutDocument()) !== JSON.stringify(state.originalLayout);
  const presentationChanged = JSON.stringify(currentPresentation()) !== JSON.stringify(state.originalPresentationBaseline);
  return layoutChanged || presentationChanged;
}

function sourceMatches(row) {
  return sourceFilter === "all" || sourceFor(row) === sourceFilter;
}

function rowsForView() {
  const query = elements.search.value.trim().toLocaleLowerCase("es");
  return allRows().filter((row) => row.state === activeView && sourceMatches(row) && (!query || rowSearchText(row).includes(query)));
}

function render() {
  if (!state || state.loadingError) return;
  const total = counts();
  elements.activeCount.textContent = String(total.active);
  elements.activeTabCount.textContent = String(total.active);
  elements.hiddenTabCount.textContent = String(total.hidden);
  elements.deletedTabCount.textContent = String(total.deleted);
  document.querySelectorAll(".view-tab").forEach((tab) => {
    const active = tab.dataset.view === activeView;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-pressed", String(active));
  });
  renderRows();
  renderInspector();
  elements.publish.disabled = !isDirty();
  elements.publish.setAttribute("aria-label", isDirty() ? "Publicar los cambios del catálogo en GitHub" : "No hay cambios por publicar");
}

function renderRows() {
  const rows = rowsForView();
  const fragment = document.createDocumentFragment();
  if (!rows.length) {
    const empty = node("li", "empty-state");
    const heading = node("strong", "", activeView === "active" ? "No hay canales que coincidan" : activeView === "hidden" ? "No hay canales ocultos" : "La papelera está vacía");
    const note = node("span", "", activeView === "active" ? "Prueba otra búsqueda o agrega canales disponibles." : "Cuando cambies el estado de un canal, aparecerá aquí.");
    empty.append(heading, note);
    fragment.append(empty);
  } else {
    rows.forEach((row) => fragment.append(renderRow(row)));
  }
  elements.list.replaceChildren(fragment);
  const filtered = rows.length;
  elements.visibleRange.textContent = `${filtered} ${filtered === 1 ? "canal" : "canales"} · ${activeView === "active" ? "ordenados" : activeView === "hidden" ? "ocultos" : "en papelera"}`;
}

function renderRow(row) {
  const item = node("li", `channel-row${row.state === "hidden" ? " is-hidden" : row.state === "deleted" ? " is-deleted" : ""}${rowKey(row) === selectedKey ? " is-selected" : ""}`);
  const number = node("span", "row-number", String(row.number));
  const select = node("button", "channel-select");
  select.type = "button";
  select.setAttribute("aria-pressed", String(rowKey(row) === selectedKey));
  select.setAttribute("aria-label", `Ver detalles de ${row.name}, número ${row.number}, ${sourceName(row)}`);
  const labels = node("span", "channel-labels");
  const name = node("span", "channel-name", row.name);
  const subtitleText = row.kind === "provider" ? `${row.category || row.group || "Proveedor"}${row.identityState === "provisional" ? " · identidad provisional" : ""}` : (row.group || "Canal M3U");
  labels.append(name, node("span", "channel-subtitle", subtitleText));
  select.append(makeLogo(row), labels);
  select.addEventListener("click", () => { selectedKey = rowKey(row); render(); });

  const source = node("span", "source-label", sourceName(row));
  source.dataset.source = sourceFor(row);
  const order = node("span", "row-order");
  const sequence = allRows().filter((item) => item.state === row.state).sort(compareRows);
  const index = sequence.findIndex((item) => rowKey(item) === rowKey(row));
  const up = node("button", "");
  up.type = "button";
  up.innerHTML = icon("up");
  up.disabled = activeView !== "active" || index <= 0;
  up.setAttribute("aria-label", `Subir ${row.name} un lugar`);
  up.addEventListener("click", (event) => { event.stopPropagation(); changeLayout(moveRow(state.layout, rowKey(row), -1)); });
  const down = node("button", "");
  down.type = "button";
  down.innerHTML = icon("down");
  down.disabled = activeView !== "active" || index < 0 || index >= sequence.length - 1;
  down.setAttribute("aria-label", `Bajar ${row.name} un lugar`);
  down.addEventListener("click", (event) => { event.stopPropagation(); changeLayout(moveRow(state.layout, rowKey(row), 1)); });
  order.append(up, down);
  item.append(number, select, source, order);
  return item;
}

function identityStatus(row) {
  if (row.kind !== "provider") return { kind: "confirmed", text: "Identidad de la lista M3U", detail: "El tvg-id se conserva como identidad pública." };
  const statuses = state.runnerStatus?.rows ?? [];
  const result = statuses.find((item) => item.provider === row.provider && item.catalogKey === row.catalogKey);
  if (result?.status === "matched") {
    return { kind: "confirmed", text: "Identidad vinculada por el runner", detail: "La coincidencia de catálogo está confirmada; EPG y logo se verifican por separado." };
  }
  if (result?.status === "pending") {
    return { kind: "pending", text: "Pendiente de resolver", detail: PENDING_REASONS[result.reason] ?? "El runner dejó esta identidad pendiente." };
  }
  if (row.identityState === "provisional") {
    return { kind: "pending", text: "Identidad provisional", detail: "No se tratará el recurso del proveedor como identidad ni se adivinará una coincidencia." };
  }
  return { kind: "pending", text: "A la espera del runner", detail: "La identidad está declarada como estable; falta una validación publicada para esta selección." };
}

function detailPair(label, value, code = false) {
  const wrapper = node("div", "detail-pair");
  const term = node("dt", "", label);
  const description = node("dd");
  description.append(code ? node("code", "", String(value || "—")) : document.createTextNode(String(value || "—")));
  wrapper.append(term, description);
  return wrapper;
}

function renderInspector() {
  const row = allRows().find((item) => rowKey(item) === selectedKey);
  if (!row) {
    elements.inspector.replaceChildren();
    const empty = node("div", "inspector-empty");
    empty.append(node("div", "empty-rule"), node("h2", "", "Elige un canal"), node("p", "", "Su identidad, logo y acciones aparecerán aquí."));
    elements.inspector.append(empty);
    return;
  }
  const fragment = document.createDocumentFragment();
  const top = node("div", "inspector-top");
  const logo = makeLogo(row, "inspector-logo");
  const heading = node("div", "inspector-heading");
  heading.append(node("h2", "specimen-name", row.name));
  const chip = node("span", "source-chip", sourceName(row));
  chip.dataset.source = sourceFor(row);
  heading.append(chip);
  top.append(logo, heading);
  fragment.append(top);

  const specimen = node("div", "specimen-control");
  const sliderLabel = node("label", "control-heading", "Peso del nombre");
  sliderLabel.htmlFor = "font-weight-slider";
  const weightOutput = node("output", "", String(state.fontWeight ?? 560));
  weightOutput.htmlFor = "font-weight-slider";
  sliderLabel.append(weightOutput);
  const range = node("input");
  range.type = "range";
  range.id = "font-weight-slider";
  range.min = "360";
  range.max = "760";
  range.step = "20";
  range.value = String(state.fontWeight ?? 560);
  range.setAttribute("aria-label", "Peso tipográfico de los nombres del catálogo");
  range.addEventListener("input", () => {
    state.fontWeight = Number(range.value);
    document.documentElement.style.setProperty("--font-weight", String(state.fontWeight));
    weightOutput.value = String(state.fontWeight);
    weightOutput.textContent = String(state.fontWeight);
  });
  const rangeEnds = node("div", "range-ends");
  rangeEnds.append(node("span", "", "Ligero"), node("span", "", "Firme"));
  specimen.append(sliderLabel, range, rangeEnds);
  fragment.append(specimen);

  const identity = identityStatus(row);
  const stateBox = node("div", `identity-state${identity.kind === "pending" ? " is-pending" : ""}`);
  stateBox.innerHTML = icon(identity.kind === "pending" ? "warning" : "check");
  stateBox.append(node("span", "", `${identity.text}. ${identity.detail}`));
  fragment.append(stateBox);

  const identityGroup = node("section", "detail-group");
  identityGroup.append(node("h3", "", "Identidad y orden"));
  identityGroup.append(detailPair(row.kind === "provider" ? "catalogKey" : "tvg-id", displayIdentity(row), true));
  if (row.group || row.category) identityGroup.append(detailPair("Categoría", row.category || row.group));
  if (row.country || row.countryKey) identityGroup.append(detailPair("País", row.country || row.countryKey));
  const numberEditor = node("div", "number-editor");
  const numberLabel = node("label", "", "Número en la app");
  numberLabel.htmlFor = "channel-number";
  const numberInput = node("input");
  numberInput.id = "channel-number";
  numberInput.type = "number";
  numberInput.min = "1";
  numberInput.step = "1";
  numberInput.value = String(row.number);
  numberInput.setAttribute("aria-label", `Número de ${row.name} en VibeM3U`);
  numberInput.addEventListener("change", () => {
    const value = Number(numberInput.value);
    if (!Number.isSafeInteger(value) || value < 1) {
      showToast("El número debe ser un entero positivo.", true);
      numberInput.value = String(row.number);
      return;
    }
    const changed = clone(state.layout);
    const target = changed.channels.find((item) => rowKey(item) === rowKey(row));
    if (target) target.number = value;
    changeLayout(changed);
  });
  numberEditor.append(numberLabel, numberInput);
  identityGroup.append(numberEditor);
  if (row.kind === "m3u") {
    const sourceEditor = node("div", "source-editor");
    const sourceLabel = node("label", "", "Lista de publicación");
    sourceLabel.htmlFor = "channel-source-list";
    const sourceSelect = node("select");
    sourceSelect.id = "channel-source-list";
    sourceSelect.setAttribute("aria-label", `Lista de publicación de ${row.name}`);
    for (const [value, label] of [["1.m3u", "Lista 1 · principal"], ["2.m3u", "Lista 2 · externa"]]) {
      const option = node("option", "", label);
      option.value = value;
      option.selected = row.sourceList === value;
      sourceSelect.append(option);
    }
    sourceSelect.addEventListener("change", () => {
      const changed = clone(state.layout);
      const target = changed.channels.find((item) => rowKey(item) === rowKey(row));
      if (target) target.sourceList = sourceSelect.value;
      changeLayout(changed);
    });
    sourceEditor.append(sourceLabel, sourceSelect);
    identityGroup.append(sourceEditor);
  }
  fragment.append(identityGroup);

  const logoGroup = node("section", "detail-group");
  logoGroup.append(node("h3", "", "Logo"));
  const logoChoice = node("div", "logo-choice");
  const logoButton = button("Elegir logo", "button-secondary", () => openLogoDialog(row), "");
  const logoPath = node("span", "logo-path", row.logoOverride || row.logoPath || "Sin logo");
  logoChoice.append(logoButton, logoPath);
  logoGroup.append(logoChoice);
  fragment.append(logoGroup);

  if (row.kind === "m3u") {
    const sourceGroup = node("section", "detail-group");
    sourceGroup.append(node("h3", "", "Fuente de catálogo"));
    sourceGroup.append(detailPair("Lista", sourceName(row)));
    fragment.append(sourceGroup);
  } else {
    const details = node("details", "resolver-details");
    details.append(node("summary", "", "Referencias de resolución"));
    const detail = node("div");
    detail.append(detailPair("providerResourceId", row.providerResourceId, true));
    if (row.provider === "highfly") detail.append(detailPair("resolverSlug", row.resolverSlug, true));
    details.append(detail);
    fragment.append(details);
  }

  const actions = node("div", "inspector-actions");
  if (row.state === "active") {
    if (LOCAL_MODE) actions.append(button("Probar señal", "button-primary", () => previewChannel(row), "play"));
    actions.append(button("Subir", "button-secondary", () => changeLayout(moveRow(state.layout, rowKey(row), -1)), "up"));
    actions.append(button("Bajar", "button-secondary", () => changeLayout(moveRow(state.layout, rowKey(row), 1)), "down"));
    actions.append(button("Ocultar", "button-secondary", () => setState(row, "hidden"), "eye"));
    actions.append(button("A papelera", "button-danger", () => setState(row, "deleted"), "bin"));
  } else if (row.state === "hidden") {
    actions.append(button("Mostrar", "button-secondary", () => setState(row, "active"), "eye"));
    actions.append(button("A papelera", "button-danger", () => setState(row, "deleted"), "bin"));
  } else {
    actions.append(button("Restaurar", "button-secondary", () => setState(row, "active"), "check"));
    actions.append(button("Eliminar definitivamente", "button-danger", () => purgeRow(row), "bin"));
  }
  fragment.append(actions);
  elements.inspector.replaceChildren(fragment);
  document.documentElement.style.setProperty("--font-weight", String(state.fontWeight ?? 560));
}

function setState(row, nextState) {
  activeView = nextState;
  changeLayout(setRowState(state.layout, rowKey(row), nextState));
}

function purgeRow(row) {
  const label = row.name || displayIdentity(row);
  if (!window.confirm(`Eliminar definitivamente ${label} del catálogo editorial? La fuente original no se borra.`)) return;
  const presentationRoot = state.presentation.presentation ?? state.presentation;
  if (presentationRoot.logos) delete presentationRoot.logos[displayIdentity(row)];
  changeLayout(removePermanently(state.layout, rowKey(row)));
  selectedKey = "";
}

function changeLayout(layout) {
  state.layout = layout;
  render();
}

async function previewChannel(row) {
  if (!LOCAL_MODE) return;
  await releasePreview();
  elements.previewError.hidden = true;
  elements.previewVideo.removeAttribute("src");
  elements.previewVideo.load();
  elements.previewVideo.muted = true;
  elements.previewStatus.textContent = `Resolviendo ${row.name} con la implementación de VibeM3U…`;
  elements.previewDialog.showModal();
  try {
    const response = await fetch("/api/resolve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        channel: row,
        sourceList: row.sourceList ?? "",
        tvgId: row.tvgId ?? "",
      }),
      cache: "no-store",
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "No se pudo preparar este canal.");
    previewSessionId = result.sessionId;
    elements.previewStatus.textContent = result.resolver === "direct"
      ? "Fuente de la lista. La dirección temporal se mantiene en el auxiliar local."
      : `Resolución VibeM3U · ${result.resolver}. Reproducción temporal en memoria.`;
    const video = elements.previewVideo;
    await ensureLocalHlsClient();
    if (window.Hls?.isSupported()) {
      previewPlayer = new window.Hls({
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 30,
        maxBufferLength: 18,
        maxMaxBufferLength: 30,
      });
      let mediaRecoveryTried = false;
      let networkRecoveryTried = false;
      previewPlayer.loadSource(result.mediaUrl);
      previewPlayer.attachMedia(video);
      previewPlayer.on(window.Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {
          elements.previewStatus.textContent = "Señal lista. Pulsa reproducir; activa el sonido desde el control del vídeo.";
        });
      });
      previewPlayer.on(window.Hls.Events.ERROR, (_event, data) => {
        if (!data?.fatal) return;
        if (data.type === window.Hls.ErrorTypes.MEDIA_ERROR && !mediaRecoveryTried) {
          mediaRecoveryTried = true;
          elements.previewStatus.textContent = "Intentando recuperar la decodificación…";
          previewPlayer.recoverMediaError();
          return;
        }
        if (data.type === window.Hls.ErrorTypes.NETWORK_ERROR && !networkRecoveryTried) {
          networkRecoveryTried = true;
          elements.previewStatus.textContent = "La conexión se interrumpió; intentando una vez más…";
          previewPlayer.startLoad();
          return;
        }
        const details = [data.type, data.details]
          .filter((value) => typeof value === "string" && /^[a-zA-Z0-9_-]{1,64}$/.test(value))
          .join(" · ");
        const httpStatus = Number.isInteger(data.response?.code) && data.response.code > 0
          ? ` · HTTP ${data.response.code}`
          : "";
        elements.previewError.textContent = `El navegador no pudo reproducir esta señal${details ? ` (${details})` : ""}${httpStatus}. Puede ser una caída del origen o un códec no compatible.`;
        elements.previewError.hidden = false;
        elements.previewStatus.textContent = "La reproducción se detuvo.";
        previewPlayer?.destroy();
        previewPlayer = null;
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = result.mediaUrl;
      video.play().catch(() => {
        elements.previewStatus.textContent = "Señal lista. Pulsa reproducir; activa el sonido desde el control del vídeo.";
      });
    } else {
      throw new Error("Este navegador no tiene soporte HLS para reproducir la vista previa.");
    }
  } catch (error) {
    elements.previewStatus.textContent = "No se pudo iniciar la prueba de señal.";
    elements.previewError.textContent = error.message || "Comprueba conexión, identidad y estado del proveedor.";
    elements.previewError.hidden = false;
  }
}

async function refreshLocalStatus() {
  if (!LOCAL_MODE) return false;
  try {
    const response = await fetch("/api/status", { cache: "no-store", credentials: "omit" });
    if (!response.ok) throw new Error("No se pudo comprobar el auxiliar local.");
    const status = await response.json();
    localGithubAuthenticated = status.githubAuthenticated === true;
    elements.localGithubStatus.textContent = localGithubAuthenticated
      ? "GitHub CLI conectado. La página no recibe ni guarda tu credencial."
      : "GitHub aún no está autorizado en este equipo. Conecta tu cuenta con la ventana segura de GitHub CLI.";
    elements.connectGithub.textContent = localGithubAuthenticated ? "Comprobar GitHub" : "Conectar GitHub";
    return localGithubAuthenticated;
  } catch (error) {
    localGithubAuthenticated = false;
    elements.localGithubStatus.textContent = error.message || "No responde el auxiliar local.";
    return false;
  }
}

async function releasePreview() {
  if (previewPlayer) {
    previewPlayer.destroy();
    previewPlayer = null;
  }
  elements.previewVideo?.pause();
  elements.previewVideo?.removeAttribute("src");
  elements.previewVideo?.load();
  const sessionId = previewSessionId;
  previewSessionId = "";
  if (sessionId) {
    try {
      await fetch("/api/preview/close", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sessionId }),
        cache: "no-store",
      });
    } catch {
      // Session expiration is bounded on the local helper if the browser closes abruptly.
    }
  }
}

function openLogoDialog(row) {
  selectedKey = rowKey(row);
  elements.logoTitle.textContent = `Para ${row.name}`;
  elements.logoSearch.value = "";
  renderLogos();
  elements.logoDialog.showModal();
  elements.logoSearch.focus();
}

function renderLogos() {
  const query = elements.logoSearch.value.trim().toLocaleLowerCase("es");
  const options = state.logos.filter((path) => !query || path.split("/").at(-1).toLocaleLowerCase("es").includes(query));
  const fragment = document.createDocumentFragment();
  options.forEach((path) => {
    const item = node("button", "logo-option");
    item.type = "button";
    item.setAttribute("aria-label", `Usar logo ${path.split("/").at(-1)}`);
    const image = node("img");
    image.src = imageUrl(path);
    image.alt = "";
    image.loading = "lazy";
    image.addEventListener("error", () => item.remove(), { once: true });
    item.append(image, node("span", "", path.split("/").at(-1)));
    item.addEventListener("click", () => {
      const row = allRows().find((candidate) => rowKey(candidate) === selectedKey);
      if (row) {
        const changed = clone(state.layout);
        const target = changed.channels.find((candidate) => rowKey(candidate) === selectedKey);
        if (target) target.logoOverride = path;
        const presentationRoot = state.presentation.presentation ?? state.presentation;
        presentationRoot.logos ??= {};
        presentationRoot.logos[displayIdentity(row)] = path;
        changeLayout(changed);
      }
      elements.logoDialog.close();
    });
    fragment.append(item);
  });
  if (!options.length) fragment.append(node("p", "available-empty", "No hay logos que coincidan con la búsqueda."));
  elements.logoGrid.replaceChildren(fragment);
}

function tvvooCatalogEntry(catalogId) {
  if (!providerCache.tvvoo.catalogs.has(catalogId)) {
    providerCache.tvvoo.catalogs.set(catalogId, { rows: [], loadedAt: 0, status: "idle", error: "", pending: null, requestId: 0 });
  }
  return providerCache.tvvoo.catalogs.get(catalogId);
}

function setJsonStatus(element, message, status = "ready") {
  element.textContent = message;
  element.dataset.state = status;
}

function countText(count, singular, plural) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function setTvVooCountries(countries) {
  elements.tvvooCountry.replaceChildren(...countries.map((country) => {
    const option = node("option", "", country.name);
    option.value = country.id;
    return option;
  }));
  elements.tvvooCountry.value = selectedTvVooCatalogId;
}

function invalidateProviderRequest(source) {
  source.requestId++;
  source.pending = null;
}

function useHighflyJson() {
  try {
    const rows = parseHighflyCatalogJson(elements.highflyCatalogJson.value, state.providerIdentities);
    const source = providerCache.highfly;
    invalidateProviderRequest(source);
    source.rows = rows;
    source.loadedAt = Date.now();
    source.status = "manual";
    source.error = "";
    setJsonStatus(elements.highflyJsonStatus, `${countText(rows.length, "canal cargado", "canales cargados")}. Las identidades provisionales quedarán señaladas para revisión del runner.`);
    refreshHighflyReferences(rows);
    renderAvailable();
  } catch (error) {
    setJsonStatus(elements.highflyJsonStatus, error.message || "No se pudo leer el JSON de Highfly.", "error");
  }
}

function useTvVooManifestJson() {
  try {
    const countries = parseTvVooManifestJson(elements.tvvooManifestJson.value);
    const source = providerCache.tvvoo;
    invalidateProviderRequest(source);
    source.countries = countries;
    source.loadedAt = Date.now();
    source.status = "manual";
    source.error = "";
    if (!countries.some((country) => country.id === selectedTvVooCatalogId)) selectedTvVooCatalogId = countries[0].id;
    setTvVooCountries(countries);
    setJsonStatus(elements.tvvooManifestStatus, `${countText(countries.length, "país cargado", "países cargados")} desde el manifiesto.`);
    renderAvailable();
  } catch (error) {
    setJsonStatus(elements.tvvooManifestStatus, error.message || "No se pudo leer el manifiesto TvVoo.", "error");
  }
}

function useTvVooJson() {
  try {
    const country = providerCache.tvvoo.countries.find((item) => item.id === selectedTvVooCatalogId);
    if (!country) throw new Error("Carga primero el manifiesto TvVoo o actualiza el catálogo para elegir un país.");
    const rows = parseTvVooCatalogJson(elements.tvvooCatalogJson.value, country);
    const catalog = tvvooCatalogEntry(country.id);
    invalidateProviderRequest(catalog);
    catalog.rows = rows;
    catalog.loadedAt = Date.now();
    catalog.status = "manual";
    catalog.error = "";
    setJsonStatus(elements.tvvooJsonStatus, `${countText(rows.length, "canal cargado", "canales cargados")} de ${country.name} desde el JSON.`);
    renderAvailable();
  } catch (error) {
    setJsonStatus(elements.tvvooJsonStatus, error.message || "No se pudo leer el catálogo TvVoo.", "error");
  }
}

function updateAvailableSourceControls() {
  document.querySelectorAll("[data-add-source]").forEach((tab) => {
    const active = tab.dataset.addSource === addSource;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-pressed", String(active));
  });
  elements.tvvooCountryField.hidden = addSource !== "tvvoo";
  elements.refreshProviderCatalog.hidden = addSource === "m3u";
  elements.manualCatalog.hidden = addSource === "m3u";
  elements.highflyJsonPanel.hidden = addSource !== "highfly";
  elements.tvvooJsonPanel.hidden = addSource !== "tvvoo";
  const directCount = state.catalog.filter((row) => row.kind === "m3u").length;
  document.querySelector('[data-source-count="m3u"]').textContent = String(directCount);
  document.querySelector('[data-source-count="highfly"]').textContent = providerCache.highfly.rows.length
    ? String(providerCache.highfly.rows.length)
    : providerCache.highfly.status === "loading" ? "…" : "—";
  document.querySelector('[data-source-count="tvvoo"]').textContent = providerCache.tvvoo.countries.length
    ? `${providerCache.tvvoo.countries.length} países`
    : providerCache.tvvoo.status === "loading" ? "…" : "—";

  if (addSource === "m3u") {
    elements.providerStatus.textContent = `${directCount} canales de Lista 1 y Lista 2 disponibles en el catálogo del repositorio.`;
    elements.providerStatus.dataset.state = "ready";
    return;
  }
  if (addSource === "highfly") {
    const source = providerCache.highfly;
    elements.providerStatus.textContent = source.status === "loading"
      ? "Consultando el catálogo en vivo de Highfly…"
      : source.status === "error"
        ? `${source.error} Usa “Actualizar catálogo” para volver a intentar.`
        : source.status === "manual"
          ? `${countText(source.rows.length, "señal cargada", "señales cargadas")} desde JSON pegado. Puedes reemplazarlas con “Actualizar catálogo”.`
        : source.rows.length
          ? `${countText(source.rows.length, "señal disponible", "señales disponibles")}. Las identidades provisionales requieren validación del runner.`
          : "El catálogo Highfly se consultará automáticamente al abrir esta fuente.";
    elements.providerStatus.dataset.state = source.status === "error" ? "error" : source.status;
    elements.refreshProviderCatalog.disabled = source.status === "loading";
    return;
  }

  const country = providerCache.tvvoo.countries.find((item) => item.id === selectedTvVooCatalogId);
  const catalog = country ? providerCache.tvvoo.catalogs.get(country.id) : null;
  elements.providerStatus.textContent = providerCache.tvvoo.status === "loading"
    ? "Consultando los catálogos regionales de TvVoo…"
    : providerCache.tvvoo.status === "error"
      ? `${providerCache.tvvoo.error} Usa “Actualizar catálogo” para volver a intentar.`
      : !country
        ? "Carga el manifiesto TvVoo o actualiza el catálogo para elegir un país."
        : catalog?.status === "loading"
            ? `Cargando señales de ${country.name}…`
            : catalog?.status === "error"
              ? `${catalog.error} Usa “Actualizar catálogo” para volver a intentar.`
              : catalog?.status === "manual"
                ? `${countText(catalog.rows.length, "canal cargado", "canales cargados")} de ${country.name} desde JSON pegado.`
              : catalog?.rows.length
                ? `${countText(catalog.rows.length, "canal", "canales")} de ${country.name}. Las señales se identifican por país y alias canónico.`
              : "El catálogo del país se consultará automáticamente al elegir TvVoo.";
  elements.providerStatus.dataset.state = providerCache.tvvoo.status === "error" || catalog?.status === "error"
    ? "error"
    : catalog?.status ?? providerCache.tvvoo.status;
  elements.refreshProviderCatalog.disabled = providerCache.tvvoo.status === "loading" || catalog?.status === "loading";
}

function sourceCandidates() {
  if (addSource === "m3u") return state.catalog.filter((row) => row.kind === "m3u");
  if (addSource === "highfly") return providerCache.highfly.rows;
  return tvvooCatalogEntry(selectedTvVooCatalogId).rows;
}

function availableRows() {
  const present = new Set(state.layout.channels.map(rowKey));
  const unique = new Map();
  for (const row of sourceCandidates()) {
    const key = rowKey(row);
    if (key && !present.has(key)) unique.set(key, row);
  }
  const query = elements.availableSearch.value.trim().toLocaleLowerCase("es");
  return [...unique.values()].filter((row) => !query || rowSearchText(row).includes(query));
}

function renderAvailable() {
  updateAvailableSourceControls();
  const fragment = document.createDocumentFragment();
  const rows = availableRows();
  const sourceState = addSource === "highfly"
    ? providerCache.highfly
    : addSource === "tvvoo"
      ? (tvvooCatalogEntry(selectedTvVooCatalogId).status === "idle" ? providerCache.tvvoo : tvvooCatalogEntry(selectedTvVooCatalogId))
      : null;
  if (sourceState?.status === "loading") {
    fragment.append(node("p", "available-empty catalog-loading", "Cargando canales del proveedor…"));
  } else if (sourceState?.status === "error") {
    fragment.append(node("p", "available-empty catalog-error", sourceState.error));
  } else if (!rows.length) {
    const emptyText = addSource === "m3u"
      ? "No hay canales nuevos de las listas M3U con esa búsqueda."
      : "No hay canales nuevos con esa búsqueda. Prueba otro nombre o país.";
    fragment.append(node("p", "available-empty", emptyText));
  } else {
    rows.slice(0, 250).forEach((row) => {
      const item = node("div", "available-row");
      item.append(makeLogo(row));
      item.append(node("span", "available-name", row.name));
      const sourceText = row.provider === "highfly" && row.identityState === "provisional"
        ? "Highfly · provisional"
        : sourceName(row);
      const source = node("span", "source-label", sourceText);
      source.dataset.source = sourceFor(row);
      const add = button("Añadir", "button-secondary", () => {
        const next = addRow(state.layout, row);
        if (next !== state.layout) {
          changeLayout(next);
          const last = state.layout.channels.find((candidate) => rowKey(candidate) === rowKey(row));
          selectedKey = last ? rowKey(last) : selectedKey;
          activeView = "active";
          render();
          renderAvailable();
          elements.addDialog.close();
        }
      });
      item.append(source, add);
      fragment.append(item);
    });
    if (rows.length > 250) fragment.append(node("p", "available-empty", `Hay ${rows.length} opciones; afina la búsqueda para verlas.`));
  }
  elements.availableList.replaceChildren(fragment);
}

function refreshHighflyReferences(rows) {
  const latest = new Map(rows.map((row) => [row.catalogKey, row]));
  const changed = clone(state.layout);
  let updates = 0;
  for (const row of changed.channels) {
    if (row.kind !== "provider" || row.provider !== "highfly") continue;
    const fresh = latest.get(row.catalogKey);
    if (!fresh || (row.providerResourceId === fresh.providerResourceId && row.resolverSlug === fresh.resolverSlug)) continue;
    row.providerResourceId = fresh.providerResourceId;
    row.resolverSlug = fresh.resolverSlug;
    updates++;
  }
  if (updates) {
    changeLayout(changed);
    showToast(`${updates} referencia(s) Highfly renovada(s); la identidad estable se conservó.`);
  }
  return updates;
}

async function ensureHighflyCatalog(force = false) {
  const source = providerCache.highfly;
  if (!force && source.pending) return source.pending;
  if (!force && source.rows.length && Date.now() - source.loadedAt < PROVIDER_CACHE_MS) return source.rows;
  source.status = "loading";
  source.error = "";
  renderAvailable();
  const requestId = ++source.requestId;
  let pending;
  pending = loadHighflyCatalog({ registry: state.providerIdentities })
    .then((rows) => {
      if (source.requestId !== requestId) return source.rows;
      source.rows = rows;
      source.loadedAt = Date.now();
      source.status = "ready";
      refreshHighflyReferences(rows);
      return rows;
    })
    .catch((error) => {
      if (source.requestId !== requestId) return source.rows;
      source.status = "error";
      source.error = error.message || "No se pudo leer el catálogo Highfly.";
      throw error;
    })
    .finally(() => {
      if (source.requestId === requestId && source.pending === pending) {
        source.pending = null;
        renderAvailable();
      }
    });
  source.pending = pending;
  return pending;
}

async function ensureTvVooManifest(force = false) {
  const source = providerCache.tvvoo;
  if (!force && source.pending) return source.pending;
  if (!force && source.countries.length && Date.now() - source.loadedAt < PROVIDER_CACHE_MS) return source.countries;
  source.status = "loading";
  source.error = "";
  renderAvailable();
  const requestId = ++source.requestId;
  let pending;
  pending = loadTvVooManifest()
    .then((countries) => {
      if (source.requestId !== requestId) return source.countries;
      source.countries = countries;
      source.loadedAt = Date.now();
      source.status = "ready";
      if (!countries.some((item) => item.id === selectedTvVooCatalogId)) selectedTvVooCatalogId = countries[0].id;
      setTvVooCountries(countries);
      return countries;
    })
    .catch((error) => {
      if (source.requestId !== requestId) return source.countries;
      source.status = "error";
      source.error = error.message || "No se pudo leer el manifiesto TvVoo.";
      throw error;
    })
    .finally(() => {
      if (source.requestId === requestId && source.pending === pending) {
        source.pending = null;
        renderAvailable();
      }
    });
  source.pending = pending;
  return pending;
}

async function ensureTvVooCatalog(catalogId = selectedTvVooCatalogId, force = false) {
  await ensureTvVooManifest();
  const country = providerCache.tvvoo.countries.find((item) => item.id === catalogId);
  if (!country) throw new Error("El país TvVoo ya no está disponible. Actualiza su catálogo.");
  const catalog = tvvooCatalogEntry(catalogId);
  if (!force && catalog.pending) return catalog.pending;
  if (!force && catalog.rows.length && Date.now() - catalog.loadedAt < PROVIDER_CACHE_MS) return catalog.rows;
  catalog.status = "loading";
  catalog.error = "";
  renderAvailable();
  const requestId = ++catalog.requestId;
  let pending;
  pending = loadTvVooCatalog(catalogId, country)
    .then((rows) => {
      if (catalog.requestId !== requestId) return catalog.rows;
      catalog.rows = rows;
      catalog.loadedAt = Date.now();
      catalog.status = "ready";
      return rows;
    })
    .catch((error) => {
      if (catalog.requestId !== requestId) return catalog.rows;
      catalog.status = "error";
      catalog.error = error.message || "No se pudo leer el catálogo TvVoo.";
      throw error;
    })
    .finally(() => {
      if (catalog.requestId === requestId && catalog.pending === pending) {
        catalog.pending = null;
        renderAvailable();
      }
    });
  catalog.pending = pending;
  return pending;
}

async function selectAddSource(source) {
  addSource = source;
  elements.availableSearch.value = "";
  renderAvailable();
  try {
    if (source === "highfly") await ensureHighflyCatalog();
    else if (source === "tvvoo") {
      await ensureTvVooManifest();
      await ensureTvVooCatalog(selectedTvVooCatalogId);
    }
  } catch {
    // The source panel renders the error and exposes an explicit retry action.
  }
}

async function refreshSelectedProviderCatalog() {
  try {
    if (addSource === "highfly") await ensureHighflyCatalog(true);
    else if (addSource === "tvvoo") {
      await ensureTvVooManifest(true);
      await ensureTvVooCatalog(selectedTvVooCatalogId, true);
    }
  } catch {
    // Error copy is rendered in the dialog; do not hide it behind a toast.
  }
}

function openAddDialog() {
  elements.availableSearch.value = "";
  addSource = "m3u";
  renderAvailable();
  elements.addDialog.showModal();
  elements.availableSearch.focus();
  // Discover both providers without requiring a file import. TvVoo countries
  // are loaded first; individual regional channel lists remain lazy.
  void ensureHighflyCatalog().catch(() => {});
  void ensureTvVooManifest().catch(() => {});
}

function showReview() {
  const doc = layoutDocument();
  const nextPresentation = buildPresentationOverrides(doc, state.presentation);
  const summary = summarizeChanges(state.originalLayout, doc, state.presentation, nextPresentation);
  const validation = validateLayout(doc);
  const statements = [];
  if (summary.added) statements.push(`${summary.added} canal(es) añadidos al orden`);
  if (summary.removed) statements.push(`${summary.removed} canal(es) eliminados definitivamente del orden`);
  if (summary.assignmentChanges) statements.push(`${summary.assignmentChanges} canal(es) movidos entre Lista 1 y Lista 2`);
  if (summary.reordered) statements.push(`${summary.reordered} posición(es) cambiadas`);
  if (summary.stateChanges) statements.push(`${summary.stateChanges} canal(es) ocultos, restaurados o enviados a papelera`);
  if (summary.numberChanges) statements.push(`${summary.numberChanges} número(s) de app modificados`);
  if (summary.logoChanges || summary.logoMapChanged) statements.push(`${Math.max(summary.logoChanges, 1)} elección(es) de logo modificadas`);
  if (summary.providerReferenceChanges) statements.push(`${summary.providerReferenceChanges} referencia(s) de resolución Highfly renovada(s); la identidad estable no cambió`);
  const providerCount = doc.channels.filter((row) => row.kind === "provider" && row.state === "active").length;
  statements.push(`${providerCount} selección(es) Highfly/TvVoo activas; el runner volverá a validarlas`);
  if (validation.length) validation.forEach((issue) => statements.push(`No se puede publicar: ${issue}`));
  if (!statements.length) statements.push("No hay cambios respecto al catálogo cargado.");
  elements.reviewList.replaceChildren(...statements.map((text) => node("li", "", text)));
  elements.changeReview.hidden = false;
  elements.changeReview.scrollIntoView({ behavior: "smooth", block: "start" });
  if (validation.length) showToast(validation[0], true);
  else if (!isDirty()) showToast("No hay cambios por publicar.");
}

async function currentDocuments() {
  const layout = layoutDocument();
  const selection = await buildSelectionDocument(layout, state.selection);
  const presentation = buildPresentationOverrides(layout, state.presentation);
  return {
    [FILES.layout]: formatJson(layout),
    [FILES.selection]: formatJson(selection),
    [FILES.presentation]: formatJson(presentation),
  };
}

async function showPublishDialog() {
  const issues = validateLayout(layoutDocument());
  if (issues.length) {
    showReview();
    return;
  }
  if (!isDirty()) {
    showToast("No hay cambios por publicar.");
    return;
  }
  const summary = summarizeChanges(state.originalLayout, layoutDocument(), state.presentation, currentPresentation());
  const lines = [];
  if (summary.added) lines.push(`${summary.added} canal(es) añadidos`);
  if (summary.removed) lines.push(`${summary.removed} canal(es) retirados definitivamente`);
  if (summary.assignmentChanges) lines.push(`${summary.assignmentChanges} canal(es) cambiados de Lista 1/Lista 2`);
  if (summary.reordered) lines.push(`${summary.reordered} posición(es) cambiadas`);
  if (summary.stateChanges) lines.push(`${summary.stateChanges} cambio(s) de visibilidad o papelera`);
  if (summary.numberChanges) lines.push(`${summary.numberChanges} numeración(es) modificadas`);
  if (summary.logoChanges || summary.logoMapChanged) lines.push("Selección de logos actualizada");
  if (summary.providerReferenceChanges) lines.push(`${summary.providerReferenceChanges} referencia(s) Highfly renovada(s); catalogKey conservado`);
  const activeProviders = state.layout.channels.filter((row) => row.kind === "provider" && row.state === "active").length;
  lines.push(`${activeProviders} canal(es) de Highfly/TvVoo se entregarán al runner`);
  elements.publishSummary.replaceChildren(...lines.map((line) => node("div", "", line)));
  elements.publishError.hidden = true;
  elements.token.value = "";
  if (LOCAL_MODE) await refreshLocalStatus();
  elements.publishDialog.showModal();
  (LOCAL_MODE ? elements.connectGithub : elements.token).focus();
}

function apiHeaders(token) {
  return {
    Accept: "application/vnd.github+json",
    Authorization: `Bearer ${token}`,
    "X-GitHub-Api-Version": "2022-11-28",
    "Content-Type": "application/json",
  };
}

async function apiRequest(path, token, options = {}) {
  let response;
  try {
    response = await fetch(`${API}${path}`, {
      ...options,
      headers: { ...apiHeaders(token), ...(options.headers ?? {}) },
      cache: "no-store",
      credentials: "omit",
    });
  } catch {
    throw new Error("No se pudo conectar con GitHub. Revisa la conexión e inténtalo de nuevo.");
  }
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) throw new Error("GitHub rechazó el token o le falta Contents: Read and write en este repositorio.");
    if (response.status === 409 || response.status === 422) throw new Error("GitHub detectó un cambio concurrente. Recarga el catálogo antes de volver a publicar.");
    throw new Error(`GitHub respondió con error ${response.status}. No se publicó ningún cambio.`);
  }
  return response.status === 204 ? null : response.json();
}

function apiPath(path) {
  return path.split("/").map(encodeURIComponent).join("/");
}

async function currentBlobSha(path, token) {
  try {
    const data = await apiRequest(`/contents/${apiPath(path)}?ref=${encodeURIComponent(BRANCH)}`, token);
    return data.sha;
  } catch (error) {
    if (String(error.message).includes("404")) return null;
    throw error;
  }
}

async function publishAtomically(documents, token) {
  const ref = await apiRequest(`/git/ref/heads/${encodeURIComponent(BRANCH)}`, token);
  const headSha = ref.object?.sha;
  if (!headSha) throw new Error("No se pudo leer la referencia main de GitHub.");
  const expected = state.repository?.fileShas ?? {};
  for (const path of Object.keys(documents)) {
    const actual = await currentBlobSha(path, token);
    if ((expected[path] ?? null) !== actual) {
      throw new Error("El catálogo cambió en GitHub desde que abriste esta página. Recarga antes de publicar para no sobrescribir trabajo ajeno.");
    }
  }
  const baseCommit = await apiRequest(`/git/commits/${headSha}`, token);
  const treeEntries = Object.entries(documents).map(([path, content]) => ({
    path,
    mode: "100644",
    type: "blob",
    content,
  }));
  const tree = await apiRequest("/git/trees", token, {
    method: "POST",
    body: JSON.stringify({ base_tree: baseCommit.tree.sha, tree: treeEntries }),
  });
  const commit = await apiRequest("/git/commits", token, {
    method: "POST",
    body: JSON.stringify({
      message: "Actualiza selección y orden del catálogo VibeM3U",
      tree: tree.sha,
      parents: [headSha],
    }),
  });
  await apiRequest(`/git/refs/heads/${encodeURIComponent(BRANCH)}`, token, {
    method: "PATCH",
    body: JSON.stringify({ sha: commit.sha, force: false }),
  });
  const blobs = new Map(await Promise.all(Object.entries(documents).map(async ([path, content]) => [
    path,
    await gitBlobSha(content),
  ])));
  return { sha: commit.sha, blobs };
}

async function handlePublish(event) {
  event.preventDefault();
  const issues = validateLayout(layoutDocument());
  if (issues.length) {
    elements.publishError.textContent = issues[0];
    elements.publishError.hidden = false;
    return;
  }
  tokenInMemory = LOCAL_MODE ? "" : elements.token.value.trim();
  if (!LOCAL_MODE && !tokenInMemory) return;
  if (LOCAL_MODE && !(await refreshLocalStatus())) {
    elements.publishError.textContent = "Conecta primero GitHub CLI en este equipo.";
    elements.publishError.hidden = false;
    return;
  }
  elements.confirmPublish.disabled = true;
  elements.confirmPublish.textContent = "Publicando…";
  elements.publishError.hidden = true;
  try {
    const documents = await currentDocuments();
    let result;
    if (LOCAL_MODE) {
      const response = await fetch("/api/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          documents,
          expectedShas: state.repository?.fileShas ?? {},
        }),
        cache: "no-store",
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "No se pudo publicar el catálogo desde el auxiliar local.");
      result = { sha: payload.sha, blobs: new Map(Object.entries(payload.blobs ?? {})) };
    } else {
      result = await publishAtomically(documents, tokenInMemory);
    }
    state.layout = layoutDocument();
    state.originalLayout = clone(state.layout);
    state.presentation = JSON.parse(documents[FILES.presentation]);
    state.originalPresentationBaseline = clone(state.presentation);
    state.selection = JSON.parse(documents[FILES.selection]);
    for (const path of Object.keys(documents)) {
      const sha = result.blobs.get(path);
      if (sha) state.repository.fileShas[path] = sha;
    }
    state.repository.revision = result.sha;
    elements.publishDialog.close();
    render();
    showToast(LOCAL_MODE
      ? "Catálogo publicado por el auxiliar local. GitHub Actions validará la selección."
      : "Catálogo publicado. GitHub Actions se encargará de validar la selección.");
    window.setTimeout(() => {
      const existing = $("#commit-link");
      existing?.remove();
      const link = node("a", "text-button", "Ver commit");
      link.id = "commit-link";
      link.href = `https://github.com/${REPOSITORY}/commit/${result.sha}`;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.style.position = "fixed";
      link.style.right = "1.25rem";
      link.style.bottom = "4.5rem";
      document.body.append(link);
      window.setTimeout(() => link.remove(), 8000);
    }, 0);
  } catch (error) {
    elements.publishError.textContent = error.message || (LOCAL_MODE ? "No se pudo publicar desde el auxiliar local." : "No se pudo publicar. No se guardó el token.");
    elements.publishError.hidden = false;
  } finally {
    tokenInMemory = "";
    elements.token.value = "";
    elements.confirmPublish.disabled = false;
    elements.confirmPublish.textContent = "Crear commit";
  }
}

async function downloadBackup() {
  if (!state) return;
  const documents = await currentDocuments();
  const payload = {
    exportedAt: new Date().toISOString(),
    repository: REPOSITORY,
    files: Object.fromEntries(Object.entries(documents).map(([path, content]) => [path, JSON.parse(content)])),
  };
  const blob = new Blob([formatJson(payload)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "vibem3u-channel-editor-backup.json";
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function showToast(message, isError = false) {
  elements.toast.textContent = message;
  elements.toast.style.background = isError ? "#7b1e29" : "#1d2938";
  elements.toast.classList.add("is-visible");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => elements.toast.classList.remove("is-visible"), 4600);
}

function handleGlobalKeydown(event) {
  if (event.key === "/" && !event.metaKey && !event.ctrlKey && !event.altKey && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) {
    event.preventDefault();
    elements.search.focus();
  }
  if (event.key === "Escape" && elements.changeReview && !elements.changeReview.hidden) elements.changeReview.hidden = true;
}

document.querySelectorAll(".view-tab").forEach((tab) => tab.addEventListener("click", () => {
  activeView = tab.dataset.view;
  render();
}));
elements.search.addEventListener("input", renderRows);
elements.sourceFilter.addEventListener("change", () => { sourceFilter = elements.sourceFilter.value; renderRows(); });
$("#add-channel-button").addEventListener("click", openAddDialog);
$("#renumber-button").addEventListener("click", () => changeLayout(renumber(state.layout)));
$("#close-review").addEventListener("click", () => { elements.changeReview.hidden = true; });
document.querySelectorAll("[data-add-source]").forEach((tab) => tab.addEventListener("click", () => selectAddSource(tab.dataset.addSource)));
elements.tvvooCountry.addEventListener("change", () => {
  selectedTvVooCatalogId = elements.tvvooCountry.value;
  renderAvailable();
  void ensureTvVooCatalog(selectedTvVooCatalogId).catch(() => {});
});
elements.refreshProviderCatalog.addEventListener("click", refreshSelectedProviderCatalog);
elements.manualCatalog.addEventListener("toggle", () => {
  elements.addDialog.classList.toggle("has-manual-open", elements.manualCatalog.open);
});
$("#use-highfly-json").addEventListener("click", useHighflyJson);
$("#use-tvvoo-manifest-json").addEventListener("click", useTvVooManifestJson);
$("#use-tvvoo-json").addEventListener("click", useTvVooJson);
elements.availableSearch.addEventListener("input", renderAvailable);
elements.logoSearch.addEventListener("input", renderLogos);
$("#clear-logo").addEventListener("click", () => {
  const row = allRows().find((candidate) => rowKey(candidate) === selectedKey);
  if (row) {
    const changed = clone(state.layout);
    const target = changed.channels.find((candidate) => rowKey(candidate) === selectedKey);
    if (target) target.logoOverride = "";
    const presentationRoot = state.presentation.presentation ?? state.presentation;
    if (presentationRoot.logos) delete presentationRoot.logos[displayIdentity(row)];
    changeLayout(changed);
  }
  elements.logoDialog.close();
});
$("#publish-button").addEventListener("click", showPublishDialog);
elements.publishForm.addEventListener("submit", handlePublish);
$("#close-publish").addEventListener("click", () => elements.publishDialog.close());
elements.connectGithub.addEventListener("click", async () => {
  if (await refreshLocalStatus()) return;
  try {
    const response = await fetch("/api/auth/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
      cache: "no-store",
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "No se pudo abrir GitHub CLI.");
    elements.localGithubStatus.textContent = "Se abrió GitHub CLI en una ventana local. Completa allí la autorización y vuelve a comprobarla.";
    elements.connectGithub.textContent = "Comprobar GitHub";
  } catch (error) {
    elements.localGithubStatus.textContent = error.message || "No se pudo iniciar la autorización de GitHub.";
  }
});
$("#close-preview").addEventListener("click", () => elements.previewDialog.close());
elements.previewDialog.addEventListener("close", () => { void releasePreview(); });
$("#backup-button").addEventListener("click", downloadBackup);
$("#download-export").addEventListener("click", downloadBackup);
elements.publishDialog.addEventListener("close", () => { tokenInMemory = ""; elements.token.value = ""; });

initialize();
