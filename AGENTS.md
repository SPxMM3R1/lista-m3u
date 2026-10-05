# AGENTS.md — Lista M3U

> Antes de cambiar algo, lee `REGLAS.md`: reglas vigentes de identidad, EPG, logos, catálogo, publicación y versiones (manda sobre documentos antiguos).

Guía para agentes de IA que trabajen en este repositorio (catálogo público, runner de canales/resolutores, EPG y editor web).

## Protocolo de traspaso (obligatorio para cualquier agente)

El usuario cambia de proveedor de IA (Codex, Claude, Gemini, Copilot…) sin aviso: cualquier
agente debe poder retomar el trabajo solo con lo que está en el repositorio.

1. **Al empezar**: lee este archivo, `ESTADO.md` (cómo está todo hoy, pendientes,
   preferencias del usuario y bitácora) y ``REGLAS.md``.
2. **Con cada cambio**, en el mismo commit:
   - actualiza `ESTADO.md`: la sección «Hoy» si cambió el estado y una línea nueva en
     «Bitácora» con la fecha;
   - actualiza este `AGENTS.md` si cambió la forma de trabajar, un comando, un test esperado o
     una regla;
   - si cambió una regla compartida, actualiza `REGLAS.md` (en Lista M3U).
3. **Nunca** dejes información solo en el chat o en la memoria de una herramienta: si otro
   agente la necesitará, va a estos archivos.
4. Codex y OpenCode leen este `AGENTS.md` directo; `opencode.json` además hace que OpenCode
   cargue siempre `ESTADO.md`. `CLAUDE.md`, `GEMINI.md` y `.github/copilot-instructions.md`
   solo apuntan aquí. No se agregan reglas en ninguno de ellos.

## Qué es este repositorio

- Catálogo público que consume VibeM3U (Android TV): `channel-catalog.m3u` (inventario canónico), `m3u.m3u`/`1.m3u` (Lista 1), `m3u-externa.m3u`/`2.m3u` (Lista 2), `epg.xml`, `epg-pending.json`, `resolver-catalog.json`, `logos/`.
- Runner: `update_m3u.py` (canales y resolutores; incluye `build_epg`/`refresh_epg` y la tabla `OFFICIAL_EPG_SOURCES`), `epg_sources/` (una fuente EPG por archivo), `run_m3u_6h.py`, `run_epg_6h.py`, `publish_epg.py`, `targeted_update.py`, `change_plan.py`, `scripts/build_site_data.py`.
- Editor web: `site/` (JS puro). La lógica pura vive en `site/editor-core.mjs` y `site/provider-catalog.mjs` con tests en `tests/editor-core.test.mjs`. Se sirve con el auxiliar `VibeM3U/local-catalog`.
- Datos editoriales publicados: `data/channel-editor-layout.json` (orden, número, visibilidad y logos que lee la app), `data/vibem3u-selection.json` (declaración de proveedores para el runner) y `presentation-overrides.json` (órdenes y exclusiones).

## Límites

- No modificar el checkout de VibeM3U desde aquí ni mover archivos entre repositorios. Un commit por repositorio.
- La identidad pública es `catalogKey` (Highfly) o `countryKey|alias` (TvVoo). `providerResourceId`, `resolverSlug` y las URL HLS son referencias que pueden rotar; nunca usarlas como identidad.
- Nunca escribir tokens, credenciales, URL firmadas ni secretos en JSON, M3U, EPG, logs o commits.
- No publicar sin: tests en verde, diff revisado y estado remoto verificado.

## Cómo trabajar

- Tests obligatorios antes de commitear:
  - `python -m unittest discover -s tests -p "test_*.py"` (294 pruebas, incluidos CNCVerse y diagnóstico Premium).
  - `node --test tests/editor-core.test.mjs tests/layout-contract.test.mjs` (41 pruebas).
- Validar el editor local sin tocar el repo: `python scripts/build_site_data.py --output <carpeta temp>` (solo acepta salidas dentro de la carpeta temporal).
- Commits en español con prefijo: `feat(editor)`, `fix(resolvers)`, `feat(epg)`, `fix(catalogo)`, `chore(...)`.
- Cambios del editor: primero `site/editor-core.mjs` (o `provider-catalog.mjs`) con test, después `site/editor.js`, `site/index.html` y `site/styles.css`.
- `data/channel-editor-layout.json` (lo lee la app) y `data/vibem3u-selection.json` (lo lee el runner) deben declarar los mismos canales de proveedor activos; `tests/test_editorial_consistency.py` lo exige. Si se corrige un proveedor a mano, editar ambos en el mismo commit.
- **Versiones hermanas TvVoo** (`tvvoo_variants.py` → `data/tvvoo-variantes.json`, en el workflow de Highfly): por cada canal TvVoo elegido, las otras entradas del mismo canal y país (HD, FHD, UHD, 4K, SD, HD+, HEVC, H265, (BACKUP n)). La app las prueba si la elegida no entrega video. SPORT y SPORTS no se igualan (en DE/IT «SKY SPORT» es la señal local y «SKY SPORTS» la inglesa); (MATCH TIME), [LIVE DURING EVENTS ONLY], (LOCAL) y RAW no son hermanas; nunca se cruzan países. Una hermana que falta en el catálogo se conserva 3 corridas (TvVoo omite entradas de una consulta a otra). Varias versiones elegidas comparten la ficha del catálogo (guía y logo; nombre/logo personalizado de la primera) y una versión sin ficha usa la de su hermana.
- La app lee `data/channel-editor-layout.json` directo: un error ahí puede impedir que abra. Filas TvVoo con `countryKey` igual al prefijo de `catalogKey` (`country` es solo texto visible); generarlas con `site/editor-core.mjs` y publicar layout + selección + presentación en un solo commit. VibeM3U 0.5.29 o anterior cae al arrancar con cualquier fila TvVoo: la TV debe tener 0.5.30+ antes de publicar una (incidente 98ee25a, 27-09).
- Contrato compartido de filas de proveedor: `contracts/layout-provider-rows.json`. Lo validan el editor (`tests/layout-contract.test.mjs`), el runner (`tests/test_layout_contract.py`), la app y el auxiliar local de VibeM3U (copia idéntica en `VibeM3U/app/src/test/resources/contracts/`). Al cambiar una regla de filas de proveedor, agregar el caso aquí, copiarlo a VibeM3U y dejar los cuatro en verde; `test_vibem3u_copy_is_identical` avisa si las copias difieren.
- Verificación de publicaciones: el Raw de GitHub cachea minutos; comprobar con `git show origin/main:<archivo>` o raw fijado al SHA del commit.
- Vigencia de variantes TvVoo: `generatedAt` se renueva cada 24 h tras consultar con éxito
  los catálogos aunque no cambien los alias (la app descarta el archivo a los 7 días).
  No renovar por fecha solamente si hay errores del proveedor; conservar los respaldos.
- Excepción BT/TNT UK: solo nombres completos verificados por fotograma en
  `TVVOO_UK_EQUIVALENCIAS.md`. BT ESPN corresponde a TNT 4; TNT SPORTS ESPN es ESPN US.
  BT 3 HD queda excluido por contenido distinto; no extender la excepción por sufijos.
  Las exclusiones se aplican también al conservar variantes publicadas antes.

## Publicación automática

- **Depuración CNCVerse (2026-10-05)**: auditadas las 258 pruebas con el resolutor Java de VibeM3U `b07c640` (0.5.72), playlist y segmento; 57 fallos se reconsultaron con enlaces nuevos. Solo TV y ClickTV recuperaron enlace; Polar TV recuperó contenido tras una placa. Se purgaron 56 filas: 55 sin enlace en ambos intentos y UATV con «NO SIGNAL» en dos fotogramas. Quedan 202 CNCVerse, 185 con contenido decodificado observado; 17 con HLS/segmento válidos pero sin captura acotada (no prueba continua en TV). No borrar por timeout de FFmpeg ni por etiqueta `[Not 24/7]` solamente. Evidencia sin secretos en `contracts/cncverse-link-audit-20261005.json`; los fixtures de incorporación conservan las 258 referencias originales como histórico. Los tests filtran las bajas por esa auditoría y preservan los números originales. Bajas con `removeRowsPermanently` de editor-core: retirar también de inventario, ambas listas y órdenes, conservar solo tombstones en `excludedM3u`/`excluded_m3u` para que el runner no las reponga; no esconder ni mandar a papelera. No se tocó selección Highfly/TvVoo, Lista 2, EPG, logos ni resolutores. No requiere APK nuevo. Si el usuario reincorpora una baja tras comprobar que volvió, actualizar explícitamente la decisión editorial y su test; no reactivar automáticamente desde los fixtures históricos.
- Compatibilidad Chile ya entregada: VibeM3U `b7bc7af`, tag `v0.5.68`, CI `37261753671`/Release `37262006591` verdes y APK/checksum verificados. Usar ese commit como contraparte del catálogo; 0.5.67 no acepta las nuevas referencias Chile.
- **Chile TV + TSN 5** (2026-10-05): 243 nuevas pruebas, TSN 5 = 136 y Chile TV = 137–378, después de las 15 CNCVerse previas. Fixture de 242 nombres exactos únicos y TSN 5 en `contracts/cncverse-chile-trial-channels.json`; referencia Chile `chiletv|nombre exacto|auto`, excepción literal `[Not 24/7]`. App/auxiliar 0.5.68+ obligatoria; primero APK compatible, después publicar filas. Validar 292 tests Python, 39 JS y lectura completa con `M3uParser`/`PublishedPlaybackCatalog` (258 CNCVerse al final). No inferir logos ni EPG, no reactivar filas viejas ni alterar selección Highfly/TvVoo. Conservar también el orden del inventario no seleccionado al derivar la presentación con editor-core.
- **Pruebas CNCVerse publicadas** (2026-10-05): 15 señales al final de Lista 1, números 121–135. Referencias exactas auditables en `contracts/cncverse-trial-channels.json`; D Sports usa banderas en la etiqueta, Golazo y Tennis Channel 2 usan `Link 1`. No sustituir esas etiquetas por nombres visibles. Filas M3U activas `trial: true`, fuera de mantenimiento/EPG; no agregarlas a `vibem3u-selection.json` (solo Highfly/TvVoo). La app 0.5.67 ya tiene el motor: no requiere otro APK. No renumerar ni reactivar filas anteriores.
- **CNCVerse** (2026-10-05): `resolver-catalog.json` declara el motor y `update_m3u.py` valida referencias `vibem3u://resolver/cncverse/<ref codificada>`, con `ref = sportsworld|<grupo>|<señal>`. Solo nombres de búsqueda, nunca IDs opacos Stremio, ClearKeys ni enlaces proxy. `tvg-id` termina en `@CNCVerse` y sigue siendo identidad pública. Exige VibeM3U 0.5.67+; esta integración NO cambia canales ni agrega un catálogo automáticamente. Las futuras entradas deben comenzar como `trial: true`: quedan fuera del mantenimiento y EPG hasta validar su fuente y acordar oficialización. No pasar fuentes CNCVerse al job directo ni guardar resultados del puente.
- **Señal preferida** (2026-10-04): una fila M3U puede llevar `preferredM3u` (tvg-id de otra fila M3U activa de la misma señal; campo «Señal preferida» en el editor). La app 0.5.65+ abre esa señal primero, usa la propia de respaldo y no muestra la otra fila sola. Solo es del layout; el runner no lo usa.
- **Respaldo TvVoo** (2026-10-04): una fila M3U puede llevar `backupTvVoo` (catalogKey de la misma señal en TvVoo; campo «Respaldo TvVoo» en el editor). Es solo del layout: la app 0.5.64+ abre el directo y pasa a TvVoo si falla. El runner no lo usa.
- Títulos EPG (`normalize_epg_title`): los títulos en mayúsculas pasan a mayúscula inicial por palabra, salvo siglas (`EPG_TITLE_ACRONYMS`) y códigos cortos con números («A3D»); en todos, la letra tras «: » va en mayúscula.
- `presentation-overrides.json` › `orders`: `1.m3u`/`2.m3u` son alias de `m3u.m3u`/`m3u-externa.m3u` y deben ser idénticos (lo exige `test_cncverse_contract`); `buildPresentationOverrides` del editor los sincroniza.
- Respaldos de un canal M3U en el layout: `backupTvVoo` (catalogKey TvVoo), `preferredM3u` (otra fila que la app abre primero) y `backupm3u` (lista ordenada de filas M3U, hasta 8). La app oculta las filas usadas como preferida o respaldo; el runner las publica igual.
- **Canales en prueba** (2026-10-04): una fila M3U con `trial: true` en `data/channel-editor-layout.json` (botón «Oficializar» en el editor) se publica en `presentation-overrides.json` como `trial_m3u`. El runner la publica tal cual en Lista 1 pero la deja fuera del mantenimiento (no la valida, repara, degrada ni cuenta en la salud), de la EPG (`main_playlist_channels` la excluye) y de la compuerta EPG de Lista 1. `external_list_disabled: true` en el manifiesto deja Lista 2 vacía (`m3u-externa.m3u`/`2.m3u` solo con cabecera). Un nombre visible no puede repetir el nombre de un canal con resolutor (p. ej. «ESPN 3»): rompe el contrato de resolutores.
- Push de un commit editorial (layout/selección/presentación) dispara `update-channels.yml` con `M3U_MAINTENANCE_SCOPE=main` (Lista 2 se conserva; el catálogo recibe igual la reconciliación). Al terminar bien, `update-epg.yml` corre por `workflow_run` (también tras un disparo manual; no tras el cron de canales, porque la EPG tiene su propio cron).
- Canales por cron: `0 4,10,16,22` America/Santiago. EPG por cron: `0 0,6,12,18` America/Santiago, forzada (`EPG_FORCE_REFRESH=true`).
- Puede dispararse a mano: `gh workflow run update-channels.yml -f force_run=true` y `gh workflow run update-epg.yml`.
- Los canales también corren por partes: un job por proveedor (`direct`, `tvn`, `meganoticias`, `highfly`, `tvvoo`; `python update_m3u.py --fetch-channel-part <proveedor> --channel-parts-dir <dir>`) que verifica y renueva solo sus canales; el job final arma listas, salud y reportes con esas partes (`M3U_CHANNEL_PARTS_DIR`). Si falta una parte, o la URL de un canal cambió, el job final verifica ese canal por su cuenta.
- La EPG corre por partes: un job por fuente (`python update_m3u.py --list-epg-parts`), cada uno con 3 intentos, y un job final que arma y publica. Una parte que falla no frena a las demás: sus canales conservan la última parrilla publicada (EPGShare, compartida, conserva la guía completa). Renovar solo algunas: `gh workflow run update-epg.yml -f fuentes=tvn-oficial,red-bull`.
- `update-highfly.yml` pide cron cada 30 min, pero GitHub retrasa los cron frecuentes (en la práctica corre cada 4-6 h); por eso también corre al terminar canales y EPG (`workflow_run`). `data/highfly-live.json` renueva su `generatedAt` cada 3 h aunque los enlaces no cambien: la app lo descarta con más de 24 h.
- `epg-pending.json` trae `channels` (lo usa el coordinador para reintentar) y `details` por canal: `sin-guia`, `guia-corta` (horas que tiene y que se exigen) o `hueco` (tramos sin programa, por ejemplo fuera del aire).
- `deploy-site.yml` publica el editor en GitHub Pages cuando cambian `site/**` o `scripts/build_site_data.py`.

## Reglas funcionales vigentes

- EPG solo para Lista 1 más canales gestionados con fuente (aislados y opcionales). Sin relleno técnico: si no hay fuente, el canal queda pendiente diagnosticado; única excepción acordada: Rwnd = `Live`.
- Zapping bloquea a GitHub (403, también con `X-Forwarded-For` y por `cl-apig`): el runner usa su endpoint `nowplaying` (~5 programas) y TecnoCentro continúa esos canales (`TECNOCENTRO_BACKUP_CHANNELS`). Red Bull Chile se consulta como visita chilena (`X-Forwarded-For`), sin usar el PC del usuario.
- Mezcla por prioridad (`epg_source_chain`): Red Bull → oficial → Zapping → fuente base → TecnoCentro → Pluto → EPGShare de respaldo → guía publicada anterior (solo 6 h hacia atrás). La de más arriba manda donde tiene programas y cada siguiente solo rellena huecos (antes, entre medio o después, recortando bloques que ya estaban al aire). Si una oficial vuelve, recupera sus tramos en la corrida siguiente. Las claves de `replaces` quedan prohibidas para ese canal (La Red solo usa su oficial y lo ya publicado). Si una oficial omite bloques (CHV no publica sus noticieros), se agrega a `EPG_INCOMPLETE_OFFICIAL_IDS` y queda como relleno detrás de Zapping y TecnoCentro. EPGShare continúa guías oficiales cortas vía `EPGSHARE_BACKUP_CHANNELS` (DW). Sinopsis (`donate_epg_descriptions`): la parrilla no cambia, pero si el programa publicado no trae descripción se toma la de otra fuente del mismo canal cuando se superpone al menos a la mitad y el título coincide (sin tildes ni marcas como «(estreno)»; «Chilevisión» = «CHV»; mismo nombre antes de «:» o « - »). Donantes de sinopsis que nunca entran a la parrilla (ids `sinopsis:`): Zapping (`ZAPPING_DESCRIPTION_CHANNELS`; su guía HTML da 403 desde GitHub, así que en Actions casi no aporta) y Claro Video (`claro-sinopsis`, `CLARO_SYNOPSIS_CHANNELS`, la principal en Actions). La clave pública del cliente web de Claro (`authpt`) se lee de clarovideo.com en cada corrida y nunca se guarda en el repo. Si no calza la hora, se acepta el mismo título a menos de 3 h (Claro trae parrillas corridas), nunca el de otro día. Sin coincidencia, el programa queda sin descripción: no se inventa texto. `dwe` de Zapping es DW Español, no DW English.
- Procurar al menos 12 h de programación por canal en cada corrida; los pendientes se reintentan por canal dentro de la corrida y en cada ciclo de 6 h.
- El runner no inventa programación, EPG ni coincidencias: ante ambigüedad, dejar pendiente.

## Documentos de referencia

- `ESTADO.md` (puesta al día: estado de hoy, pendientes, preferencias del usuario y bitácora).
- `VIBEM3U_ID_CONTRACT_EPG_LOGOS.md` (contrato de identidad, EPG y logos).
- `RESOLVER_RECIPE_CONTRACT.md` y `VAVOO_TVVOO_SOLUCIONES_VIBEM3U.md`.
- `LOCAL_CATALOG_EDITOR.md` (editor local y auxiliar).
- `PRODUCT.md` y `README.md` (descripción vigente del producto).
