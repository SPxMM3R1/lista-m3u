# AGENTS.md — Lista M3U

> Antes de cambiar algo, lee `REGLAS.md`: reglas vigentes de identidad, EPG, logos, catálogo, publicación y versiones (manda sobre documentos antiguos).

Guía para agentes de IA que trabajen en este repositorio (catálogo público, runner de canales/resolutores, EPG y editor web).

## Protocolo de traspaso (obligatorio para cualquier agente)

El usuario cambia de proveedor de IA (Codex, Claude, Gemini, Copilot…) sin aviso: cualquier
agente debe poder retomar el trabajo solo con lo que está en el repositorio.

1. **Al empezar**: lee este archivo, `ESTADO.md` (cómo está todo hoy, pendientes,
   preferencias del usuario y bitácora reciente) y `REGLAS.md`. Antes de tocar un tema, lee
   su documento en `docs/` (índice en «Documentos de referencia»).
2. **Con cada cambio**, en el mismo commit:
   - actualiza `ESTADO.md`: la sección «Hoy» si cambió el estado y una línea nueva en
     «Bitácora» con la fecha;
   - actualiza este `AGENTS.md` si cambió la forma de trabajar, un comando, un test esperado o
     una regla;
   - si cambió una regla compartida, actualiza `REGLAS.md` (en Lista M3U).
3. **Documentos cortos** (desde 2026-10-31): `AGENTS.md` ≤ 25 KB y `ESTADO.md` ≤ 60 KB
   (`tests/test_docs_size.py`). Aquí van reglas generales e invariantes; lo de un canal puntual
   va a `docs/decisiones-por-canal.md`, lo de EPG a `docs/epg.md`, lo de respaldos a
   `docs/respaldos.md` y lo ya cerrado a `docs/historial-operativo.md`. En `ESTADO.md`, cuando
   «Hoy» o «Bitácora» crezcan, mueve lo antiguo tal cual a `docs/estado-anterior.md` y
   `docs/bitacora/<año>-<mes>.md`.
4. **Nunca** dejes información solo en el chat o en la memoria de una herramienta: si otro
   agente la necesitará, va a estos archivos.
5. Codex y OpenCode leen este `AGENTS.md` directo; `opencode.json` además hace que OpenCode
   cargue siempre `ESTADO.md`. `CLAUDE.md`, `GEMINI.md` y `.github/copilot-instructions.md`
   solo apuntan aquí. No se agregan reglas en ninguno de ellos.

## Qué es este repositorio

- Catálogo público que consume VibeM3U (Android TV): `channel-catalog.m3u` (inventario canónico), `m3u.m3u`/`1.m3u` (Lista 1), `m3u-externa.m3u`/`2.m3u` (Lista 2), `epg.xml`, `epg-pending.json`, `resolver-catalog.json`, `logos/`.
- Runner: `update_m3u.py` (canales y resolutores; incluye `build_epg`/`refresh_epg`, `EPG_SOURCES` para feeds XMLTV gzip y la tabla `OFFICIAL_EPG_SOURCES`), `epg_sources/` (adaptadores EPG específicos), `epg_fragments.py` y `epg_dispatch.py` (guía por canal), `run_m3u_6h.py`, `run_epg_6h.py` (heredado, solo local), `publish_epg.py`, `targeted_update.py`, `change_plan.py`, `scripts/build_site_data.py`.
- Editor web: `site/` (JS puro). La lógica pura vive en `site/editor-core.mjs` y `site/provider-catalog.mjs` con tests en `tests/editor-core.test.mjs`. Se sirve con el auxiliar `VibeM3U/local-catalog`.
- Datos editoriales publicados: `data/channel-editor-layout.json` (orden, número, visibilidad y logos que lee la app), `data/vibem3u-selection.json` (declaración de proveedores para el runner) y `presentation-overrides.json` (órdenes y exclusiones).
- **Resolutores TvVoo por identidad estable (2026-10-15)**: `resolver_attributes_for()` usa primero `tvg-id` en `TVVOO_STREAM_RESOLVER_IDS_BY_TVG_ID`; el título visible nunca debe convertir una fila directa en TvVoo. La búsqueda heredada por nombre solo sirve para IDs `@TvVoo` no cargados desde el catálogo o cuando no hay catálogo en el checkout. Conservar los alias para las identidades estables y mantener la regresión del ESPN directo en `tests/test_targeted_update.py`.

## Límites

- No modificar el checkout de VibeM3U desde aquí ni mover archivos entre repositorios. Un commit por repositorio.
- La identidad pública es `catalogKey` (Highfly) o `countryKey|alias` (TvVoo). `providerResourceId`, `resolverSlug` y las URL HLS son referencias que pueden rotar; nunca usarlas como identidad.
- Nunca escribir tokens, credenciales, URL firmadas ni secretos en JSON, M3U, EPG, logs o commits.
- No publicar sin: tests en verde, diff revisado y estado remoto verificado.
- **Sello del layout editorial**: todo cambio en `data/channel-editor-layout.json` requiere recalcular `approval.sha256` con `tests.catalog_approval.layout_approval_digest` sobre el JSON actualizado y comprobar que coincide con el valor almacenado y que `approved_by_user(layout)` es verdadero. Un hash viejo hace que CI considere el layout no aprobado y reactive pruebas históricas de catálogo en vivo, cuyos fallos pueden ser ajenos al cambio.

## Cómo trabajar

- **Logos de Lista 2 (2026-10-24)**: el logo de una fila sin logo sale de la imagen de Claro de su guía (`claro_channels` → campo `image`, PNG con fondo transparente, `_t-290x163`); se guarda bajo `logos/lista2/` y se pone en `logoPath` de la fila. Para canales de EPGShare, `<icon src>` del XMLTV. Nunca un icono de otra marca: si no hay uno de la misma señal, la fila queda sin logo y se informa.
- **Agregar un canal Highfly a una fila existente (2026-10-24, TNT Sports 1/2)**: además de la fila del layout (`kind: provider`, `provider: highfly`, `catalogKey`, `resolverSlug`, `providerResourceId: leaf:<slug>`, `backupTvVoo` con la clave TvVoo anterior), hay que sumar el `catalogKey` a `HIGHFLY_RESOLVER_CHANNELS`, a `parse_highfly_live_resolver_map`, al mapa EPG, a `appCompatibleHighflyIdentity` del editor y una entrada en `channel-catalog.m3u` (copiar la de Sky Sports Tennis); si falta la entrada, `validate_playlist_resolvers` falla con «faltan canales Highfly» y el runner no regenera.
- **Nombres oficiales de Lista 2 (2026-10-22)**: unificar variantes de un mismo canal cambia solo `displayName` (nunca `name`, `tvg-id` ni URL) según `contracts/lista2-nombres-oficiales-20261022.json`. Señales regionales (Sur, ARG, Co, Chile, Oeste, Este, Andes) son otra transmisión: no se unen. Al reordenar el bloque Lista 2 usar exactamente la clave de nombre de `tests/test_lista2_order.py` (NFD sin marcas, casefold, sin signos iniciales; empate por `tvgId`, comparación por código, no `Intl.Collator`), si no el test falla.
- **Restauración de bajas de la app (2026-10-17)**: las filas borradas desde la app se rastrean por los commits «Papelera desde la app» (comparación de estados por commit, nunca por nombres). Por pedido explícito se restauraron solo las no Nauta, al final de Lista 2 en orden alfabético; las 37 Nauta eliminadas quedan en papelera (si alguna vez se restauran, solo pueden volver a Lista 1 — regla dura). Los números en conflicto con activos se reasignan por encima del máximo; los libres se conservan. Las filas con salud `temporarily_unavailable` quedan activas pero sin publicar hasta revalidar; las purgadas por bajas definitivas (`channel-number-exclusions-*`) no se recrean sin pedido explícito. Registro: `contracts/app-deleted-restore-20261017.json`.
- **Nauta y M6Foot retirados por completo (2026-10-29, pedido del usuario «Puedes eliminar esos resolutores por completo? 100% Limpio?»)**: se borraron sus 90 filas del layout y del catálogo, sus guías (`epg/canales`, `epg-overrides.json`, `epg-l2-map.json`), su estado de salud, el código del generador (`nauta_reference.py`, `m6foot_reference.py`, validaciones y `apply_editor_nauta_channels`), la fuente Nauta del editor web y sus proveedores en `resolver-catalog.json`. En VibeM3U se quitaron sus resolutores (y el Vavoo directo, que ya no se usaba); `ResolverCatalog` ignora `nauta`/`m6foot` si un catálogo viejo los trae. Los registros de `contracts/` y `data/app-requests/` quedan como historia. No volver a agregarlos sin pedido nuevo.










- Tests obligatorios antes de commitear:
  - `python -m unittest discover -s tests -p "test_*.py"` (412 pruebas, 6 omitidas previstas; incluye contrato, regresiones del editor, EPG visual, RWND y tamaño de `AGENTS.md`/`ESTADO.md`).
  - `node --test tests/*.mjs` (53 pruebas; incluye el flujo de pedidos de la app, la fusión de bajas en el editor y la deriva layout → órdenes de `presentation-overrides.json`).
- Validar el editor local sin tocar el repo: `python scripts/build_site_data.py --output <carpeta temp>` (solo acepta salidas dentro de la carpeta temporal).
- Commits en español con prefijo: `feat(editor)`, `fix(resolvers)`, `feat(epg)`, `fix(catalogo)`, `chore(...)`.
- Cambios del editor: primero `site/editor-core.mjs` (o `provider-catalog.mjs`) con test, después `site/editor.js`, `site/index.html` y `site/styles.css`.
- `data/channel-editor-layout.json` (lo lee la app) y `data/vibem3u-selection.json` (lo lee el runner) deben declarar los mismos canales de proveedor activos; `tests/test_editorial_consistency.py` lo exige. Si se corrige un proveedor a mano, editar ambos en el mismo commit.
- La app lee `data/channel-editor-layout.json` directo: un error ahí puede impedir que abra. Filas TvVoo con `countryKey` igual al prefijo de `catalogKey` (`country` es solo texto visible); generarlas con `site/editor-core.mjs` y publicar layout + selección + presentación en un solo commit. VibeM3U 0.5.29 o anterior cae al arrancar con cualquier fila TvVoo: la TV debe tener 0.5.30+ antes de publicar una (incidente 98ee25a, 27-09).
- Contrato compartido de filas de proveedor: `contracts/layout-provider-rows.json`. Lo validan el editor (`tests/layout-contract.test.mjs`), el runner (`tests/test_layout_contract.py`), la app y el auxiliar local de VibeM3U (copia idéntica en `VibeM3U/app/src/test/resources/contracts/`). Al cambiar una regla de filas de proveedor, agregar el caso aquí, copiarlo a VibeM3U y dejar los cuatro en verde; `test_vibem3u_copy_is_identical` avisa si las copias difieren.
- Verificación de publicaciones: el Raw de GitHub cachea minutos; comprobar con `git show origin/main:<archivo>` o raw fijado al SHA del commit.

## Publicación automática





- `presentation-overrides.json` › `orders`: `1.m3u`/`2.m3u` son alias de `m3u.m3u`/`m3u-externa.m3u` y deben ser idénticos (lo exige el contrato de publicación); `buildPresentationOverrides` del editor los sincroniza.
- **Canales en prueba** (2026-10-04): una fila M3U con `trial: true` en `data/channel-editor-layout.json` (botón «Oficializar» en el editor) se publica en `presentation-overrides.json` como `trial_m3u`. El runner la publica tal cual en Lista 1 pero la deja fuera del mantenimiento (no la valida, repara, degrada ni cuenta en la salud), de la EPG (`main_playlist_channels` la excluye) y de la compuerta EPG de Lista 1. `external_list_disabled: true` en el manifiesto deja Lista 2 vacía (`m3u-externa.m3u`/`2.m3u` solo con cabecera). Un nombre visible no puede repetir el nombre de un canal con resolutor (p. ej. «ESPN 3»): rompe el contrato de resolutores.
- Push de un commit editorial (layout/selección/presentación) dispara `update-channels.yml` con `M3U_MAINTENANCE_SCOPE=main` (Lista 2 se conserva; el catálogo recibe igual la reconciliación). Al terminar bien, `update-epg.yml` corre por `workflow_run` (también tras un disparo manual; no tras el cron de canales, porque la EPG tiene su propio cron).
- Canales por cron: `0 4,10,16,22` America/Santiago. EPG por cron: `0 0,6,12,18` America/Santiago, forzada (`EPG_FORCE_REFRESH=true`).
- Puede dispararse a mano: `gh workflow run update-channels.yml -f force_run=true` y `gh workflow run update-epg.yml`.
- Los canales también corren por partes: un job por proveedor (`direct`, `tvn`, `meganoticias`, `highfly`, `tvvoo`; `python update_m3u.py --fetch-channel-part <proveedor> --channel-parts-dir <dir>`) que verifica y renueva solo sus canales; el job final arma listas, salud y reportes con esas partes (`M3U_CHANNEL_PARTS_DIR`). Si falta una parte, o la URL de un canal cambió, el job final verifica ese canal por su cuenta.
- `update-highfly.yml` pide cron cada 30 min, pero GitHub retrasa los cron frecuentes (en la práctica corre cada 4-6 h); por eso también corre al terminar canales y EPG (`workflow_run`). `data/highfly-live.json` renueva su `generatedAt` cada 3 h aunque los enlaces no cambien: la app lo descarta con más de 24 h.
- Ids Highfly al día (2026-10-15): en cada corrida `highfly_live.py` copia al layout y a `vibem3u-selection.json` el id vigente de cada `catalogKey` (`sync_files`). Solo cambia `resolverSlug`/`providerResourceId`; si el layout tenía un sello válido lo renueva con el mismo origen (no es una decisión del usuario), y si el archivo no tiene el formato exacto no lo toca. Motivo: la app pide Premium con ese id y con uno viejo los UHD perdían el 4K. Un editor abierto desde antes puede volver a publicar el id viejo; la corrida siguiente lo corrige.
- `deploy-site.yml` publica el editor en GitHub Pages cuando cambian `site/**` o `scripts/build_site_data.py`.
- **Alertas de fuentes EPG (2026-10-31)**: `epg-alertas.yml` corre a diario (13:00 UTC) `python epg_dispatch.py alerts`: si una fuente de `epg/estado.json` lleva `ALERT_MIN_FAILURES` (8) o más fallos seguidos, abre o actualiza la issue «Fuentes EPG caídas» (etiqueta `epg-fuentes-caidas`) y la cierra cuando vuelven todas. No escribe en el repo.
- **Deriva layout → órdenes (2026-10-31)**: `tests/derived-drift.test.mjs` (también en `targeted-changes.yml`) exige que los órdenes de Lista 1/2 en `presentation-overrides.json` salgan del layout: puede faltar una fila activa (el runner quita las no disponibles), nunca sobrar una borrada ni cambiar el orden. Excepción declarada: `EXTERNAL_DASH_TAIL_CHANNEL_IDS` (DASH) va al final de Lista 2; las sondas deportivas ya no (2026-10-31).
- **Logos livianos (2026-10-31)**: fuera de `logos/history/`, ningún PNG pasa de 64 KB y uno de más de 512 px debe pesar ≤ 40 KB (`tests/test_logo_size.py`). Un logo nuevo: lado máximo 512 px, `optimize=True` y, si sigue pesado, paleta de 256 colores. Registro con hash original → optimizado: `contracts/logos-optimizados-20261031.json` (la prueba de `trial-officialization` lo acepta).
- `outputs/` está en `.gitignore` (2026-10-31): fotogramas, propuestas y auditorías locales no se publican; lo que deba quedar va a `contracts/` o `docs/`.

## Reglas funcionales vigentes

- **Solo Lista 1 y Lista 2 (2026-10-18)**: toda fila (M3U o TvVoo/Highfly) tiene `sourceList` y queda escrita en su archivo; números 1..N sin huecos, Lista 1 primero (`normalizeLists`). Detalle en `REGLAS.md` §3. Migración: los 13 proveedores (antes «virtuales», números 22–34) pasaron a ser filas de Lista 1; Lista 1 = 56 (1–56), Lista 2 = 4.860 filas de layout (57–4.916). Requiere VibeM3U 0.6.16+ para que el interruptor de la Lista 1 también controle esos canales (versiones anteriores los muestran igual, sin duplicar). Registro: `contracts/two-lists-20261018.json`.

- **Líneas M3U huérfanas (2026-10-24)**: si un canal cambia de identidad o de proveedor (TvVoo → Highfly, M3U → fila de proveedor), su línea vieja en la lista debe ir a `excludedM3u`; si no, la app la muestra al final como canal suelto sin número del catálogo. Caso: `SkySportsRacing.uk` y `Vavoo.uk.TNTSPORTS2@TvVoo`.
- **Al mover canales entre listas, publicar con `targeted_update.py --mode presentation`** (2026-10-25): el mantenimiento programado solo reescribe Lista 1 (`M3U_MAINTENANCE_SCOPE: main`), así que Lista 2 no suelta lo que pasó a Lista 1 y la app lo ve repetido. Además el grupo publicado sale de `info_lines` (línea guardada de la fuente), no del grupo del catálogo: corregir su `group-title` al cambiar de grupo.
- **Pruebas de apertura con ffmpeg (2026-10-25)**: las filas con URL `vibem3u://resolver/...` no se pueden abrir con ffmpeg; nunca mandarlas a la papelera por «no abre» en esas pruebas. Al pedir «si no abre, reintenta un minuto después 3 veces y a la papelera», contar solo URLs `http`.
- **Números que da el usuario con adultos bloqueados (2026-10-25)**: la app oculta los 7 de Adultos (055–061) y compacta, así que desde el 062 su número en la tele es el del catálogo menos 7 (su 78 = catálogo 85). Ubicar siempre por nombre y vecinos.
- **Lista 2 completa por nombre y calidad (2026-10-29, pedido del usuario «Vuelve a reordenar la lista 2 completa. Por nombre, y calidad.»)**: medición nueva de todo Lista 2 en GitHub (`bitrate-lista2`, `contracts/bitrate-lista2-20261029.json`, 2.140 medidos, 2.088 abren) y un solo bloque ordenado por nombre y calidad (resolución, fps, bitrate redondeado a 500 con redondeo de Python); el bloque de recuperados de la papelera ya no va aparte. Nauta y M6Foot se retiraron por completo ese mismo día. Al reordenar en JS, redondear el bitrate como Python (mitades al par) o la prueba falla.
- **Canales de adultos en `adultos.json` (2026-10-24)**: lista pública de tvg-id del grupo «Adultos» (sin Adult Swim). La app VibeM3U (0.6.36) los oculta hasta que se desbloquean con la clave del usuario; la app solo trae la huella PBKDF2 de esa clave. Al agregar un canal de adultos, sumar su tvg-id aquí.
- **Pasar un canal a Lista 1 (2026-10-28)**: además de mover la fila, revisar `group-title` en la línea EXTINF guardada de `presentation-overrides.json` (no se actualiza sola) y que `content_category_for` no lo mande a otra categoría por el nombre (p. ej. «Adult Swim» caía en Adultos).
- Pedidos de la app (desde 2026-10-11): `data/app-requests/*.json` solo los escribe VibeM3U (papelera desde la TV) y los consume `app-requests.yml`. No agregar acciones nuevas sin la contraparte en la app ni aplicar los cambios a mano: todo pasa por `scripts/apply_app_requests.mjs`, que usa editor-core. El workflow regenera las listas sin red en el mismo commit y no encola runners completos; el editor web conserva esas bajas al publicar (`mergeRemoteDeletions`).
- Pruebas del catálogo publicado (desde 2026-10-12): las que leen layout/listas/presentación reales llevan `@live_catalog` (`tests/catalog_approval.py`). Se saltan solas en dos casos: runners y despliegue del editor (`M3U_RUNNER_TESTS=1`) y layout sellado por el usuario (campo `approval` que escriben el editor web y la papelera de la app con `approveLayout`; SHA-256 del contenido, igual en JS y Python). Nadie actualiza bases a mano tras una publicación del usuario. Si un agente cambia el layout por script, el sello deja de coincidir y esas pruebas corren contra `contracts/editorial-baseline-20261012.json`: es la protección, no un error a silenciar. Un agente solo sella con `approveLayout(layout, "chat")` cuando aplica un cambio que el usuario pidió explícitamente en el chat, citándolo en el commit; nunca para silenciar una prueba ni con origen `editor`/`app`.
- Al agregar/quitar registros de `channel-catalog.m3u`: mantener sus IDs en `orders["channel-catalog.m3u"]` y aplicar el orden antes de filtrar particiones. `targeted_update.py` debe volver a parsear el catálogo después de reordenarlo, porque los índices `info_line`/`url_line` anteriores quedan obsoletos; la regresión está en `tests/test_targeted_update.py::test_catalog_filter_reparses_line_offsets_after_presentation_reorder`.

## Documentos de referencia

- `ESTADO.md` (puesta al día: estado de hoy, pendientes, preferencias del usuario y bitácora reciente).
- `docs/decisiones-por-canal.md`: decisiones vigentes de canales puntuales (búscalo por nombre o tvg-id antes de tocar un canal).
- `docs/epg.md`: reglas vigentes de la guía (fuentes, overrides, mapa de Lista 2, workflows).
- `docs/respaldos.md`: reglas vigentes de respaldos (TvVoo, `backups.json`, variantes).
- `docs/historial-operativo.md`, `docs/estado-anterior.md` y `docs/bitacora/`: historia; contexto, no reglas.
- `VIBEM3U_ID_CONTRACT_EPG_LOGOS.md` (contrato de identidad, EPG y logos).
- `RESOLVER_RECIPE_CONTRACT.md` y `VAVOO_TVVOO_SOLUCIONES_VIBEM3U.md`.
- `LOCAL_CATALOG_EDITOR.md` (editor local y auxiliar).
- `PRODUCT.md` y `README.md` (descripción vigente del producto).
