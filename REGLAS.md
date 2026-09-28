# Reglas vigentes — Lista M3U + VibeM3U

Documento único y corto con las reglas que rigen hoy. El detalle vive en los documentos
enlazados; si algo de aquí contradice un documento antiguo, manda este. Última revisión:
2026-09-27.

## 1. Repositorios y límites

- **Lista M3U** (`SPxMM3R1/lista-m3u`): catálogo público, runner de canales y EPG, logos y
  editor web (`site/`). **VibeM3U** (`SPxMM3R1/vibem3u`): app Android TV y auxiliar local del
  editor (`local-catalog/`).
- Repos independientes: un commit por repositorio; nunca editar uno desde el otro.
- Nunca publicar tokens, credenciales, URL firmadas ni URL HLS de sesión en JSON, M3U, EPG,
  logs o commits.

## 2. Identidad de canales

- Identidad estable: `tvg-id` (M3U), `catalogKey` (Highfly) y `countryKey|alias` (TvVoo).
- `providerResourceId`, `resolverSlug`, `leaf:` y las URL HLS rotan: nunca son identidad.
- TvVoo: `providerResourceId` = `catalogKey`; `countryKey` = prefijo de `catalogKey`.
  `country` es solo texto visible ("Reino Unido") y nunca se usa como clave.
- Un canal con dos proveedores (Sky F1: Highfly y TvVoo) tiene **una** fila en el catálogo con
  su resolutor real (`x-resolver="highfly"`) y los alias del otro en `x-tvvoo-aliases`. Esos
  alias solo sirven para que una selección TvVoo encuentre la fila (EPG y logo); no la
  vuelven TvVoo. La app reproduce cada selección con su propio proveedor desde el layout.
- Highfly: `resolverSlug` = hoja sin `leaf:`. `identityState` (canonical/provisional) es para
  el runner (EPG y logo); no impide reproducir la fila.
- **Contrato compartido**: `contracts/layout-provider-rows.json`. Lo validan el editor, el
  runner, la app y el auxiliar (copia idéntica en VibeM3U). Cualquier regla nueva de filas
  de proveedor se agrega ahí primero.
- Detalle: `VIBEM3U_ID_CONTRACT_EPG_LOGOS.md`.

## 3. Catálogo editorial

- `data/channel-editor-layout.json`: lo lee **la app directo** (orden, número, visibilidad,
  nombre y logo). Un error ahí puede impedir que la app abra.
- `data/vibem3u-selection.json`: lo lee **el runner**. Debe declarar los mismos canales de
  proveedor activos que el layout (`tests/test_editorial_consistency.py`).
- Publicar layout + selección + presentación juntos, siempre desde el editor (`editor-core`).
- Canales M3U agregados conservan su lista de origen (Lista 1 o 2). Highfly y TvVoo no van a
  ninguna M3U: viven en el layout y la selección.
- Un cambio editorial no requiere APK nueva.

## 4. EPG

- Solo Lista 1 más los canales gestionados con fuente. Prioridad: oficial → Zapping →
  TecnoCentro (Red Bull con respaldo Pluto).
- Sin relleno técnico: sin fuente real, el canal queda pendiente (`epg-pending.json`).
  Única excepción acordada: Rwnd = `Live`.
- Procurar al menos 12 h por canal (mínimo, no tope): se integra toda la guía real que publique
  cada fuente, hasta 8 días. Los pendientes se reintentan en cada ciclo de 6 h.
- **La Red**: solo su guía oficial (`lared.cl`), sin Zapping ni TecnoCentro. Si falla, se
  conserva la última parrilla real. Sus pestañas lun..dom son los próximos 7 días desde hoy.
- **TVN3**: se usa Zapping aunque a veces no calza (decisión del usuario, 27-09).
- No asignar EPG por posición, nombre parecido, bitrate ni URL; ante duda, pendiente.
- La app lee la sinopsis (`<desc>`, máximo 600 caracteres) para el Detalle y la Guía.
- Cada fuente vive en su archivo `epg_sources/<fuente>.py`; las oficiales se declaran en
  `OFFICIAL_EPG_SOURCES` (`update_m3u.py`) con los canales que cubren. Una fuente que falla
  (o revienta) solo afecta a sus canales, que caen a su respaldo. Solo un fallo de EPGShare
  conserva la guía anterior completa. Fuente nueva = archivo nuevo + fila en la tabla + test.

## 5. Logos

1. Orden: logo elegido para la identidad → logo local asociado a esa identidad → alias + país
   con coincidencia única → búsqueda editorial por nombre, país y categoría.
2. Nunca son identidad del logo el nombre con `(FHD)`, el `leaf` ni el archivo remoto.
3. Ante la duda, pendiente: sin logo antes que un logo de otra región.
4. Siempre locales en `logos/` (sin depender de servidores externos). Vectoriales en SVG, el
   resto en PNG. La app solo acepta rutas bajo `logos/`.
5. `logos/history/` solo se usa si el editor lo elige (o lo sugiere y se publica); el runner
   no lo elige solo.
6. Canales adultos sin logo seguro quedan sin logo; no se borran por eso.
7. Logos MTV locales con geometría común (marca 514×308 px en referencia 1280×783, 36 px al
   nombre), sin cambiar colores ni formas.
- El editor sugiere logo a filas sin logo (catálogo → vigente → histórico, por nombre) y
  `tools/assign_channel_logos.py` copia a `logos/tvvoo/` logos reales de `tv-logo/tv-logos`
  (nunca placeholders). Pendiente de decidir: exigir país en la coincidencia por nombre.

## 6. Publicación automática (Lista M3U)

- Canales: cron `0 4,10,16,22` America/Santiago y cada commit editorial. Grupo de
  concurrencia `m3u-publisher` (compartido con cambios dirigidos).
- EPG: cron `0 0,6,12,18` America/Santiago y tras un commit editorial o disparo manual de
  canales (no tras el cron de canales). Grupo propio `m3u-epg`: publica solo archivos de EPG.
- Todos los push integran `main` y reintentan; nunca force-push.
- El Raw de GitHub cachea minutos: verificar con `git show origin/main:<archivo>`.

## 7. App VibeM3U

- Versiones: **cada release sube solo el último número** (0.5.33 → 0.5.34). Subir el del
  medio o el primero lo decide el usuario. Las 0.6.x del 27-09 fueron un error: se retiraron
  con un puente (0.6.2) y la línea siguió en 0.5.33.
- `versionCode` siempre mayor al anterior (Android lo exige).
- Release: commit `chore(release): bump VibeM3U a X.Y.Z` → push → CI verde → tag `vX.Y.Z` →
  workflow "Publicar APK" → verificar tamaño y SHA-256.
- No hay SDK Android local: la app se valida en CI y en la TV.
- Control: OK muestra el OSD; segundo OK o INFO, Detalle del programa; ◀ o GUIDE, Guía
  completa; ▶, fuentes y calidad; OK mantenido o MENU, Opciones.
- Guía: OK corto abre el canal; OK mantenido programa o quita un recordatorio (campana cyan).
  El aviso (300×52 dp, arriba a la derecha) llega con la app cerrada si tiene el permiso
  «Mostrar sobre otras apps»; «Ver» cambia al canal. Se gestionan en Opciones › Interfaz.
- El OSD ocupa el ancho de la pantalla menos 32dp por lado, alineado con el reloj. No se
  cambia su diseño ni su tamaño sin pedirlo el usuario.

## 8. Incidentes que originaron reglas

| Fecha | Qué pasó | Regla |
|---|---|---|
| 26-09 | Sky F1 cambió de proveedor solo en la selección | Layout y selección juntos (§3) |
| 27-09 | Fila TvVoo con `country` visible tumbó la app 0.5.29 | `countryKey` es la clave (§2) |
| 27-09 | F1 Highfly `provisional` desapareció de la TV | `identityState` no bloquea (§2) |
| 27-09 | Fila F1 etiquetada TvVoo siendo Highfly | Alias del otro proveedor aparte (§2) |
| 27-09 | Versiones 0.6.x sin consultar | Solo último número (§7) |
| 27-09 | EPG canceló corridas de canales en espera | Grupo propio de EPG (§6) |
| 27-09 | La Red sin EPG un domingo | Pestañas desde hoy (§4) |
