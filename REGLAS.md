# Reglas vigentes — Lista M3U + VibeM3U

Documento único y corto con las reglas que rigen hoy. El detalle vive en los documentos
enlazados; si algo de aquí contradice un documento antiguo, manda este. Última revisión:
2026-10-10. El estado de hoy y la bitácora están en `ESTADO.md` de cada repositorio.

## 1. Repositorios y límites

- **Lista M3U** (`SPxMM3R1/lista-m3u`): catálogo público, runner de canales y EPG, logos y
  editor web (`site/`). **VibeM3U** (`SPxMM3R1/vibem3u`): app Android TV y auxiliar local del
  editor (`local-catalog/`).
- Repos independientes: un commit por repositorio; nunca editar uno desde el otro.
- Nunca publicar tokens, credenciales, URL firmadas ni URL HLS de sesión en JSON, M3U, EPG,
  logs o commits.

## 2. Identidad de canales

- Nauta es una fuente candidata del editor **local** y se incorpora solo cuando el usuario selecciona explícitamente uno o varios canales candidatos en una acción; no se importa el catálogo completo ni se repone automáticamente. Los no seleccionados no figuran en el layout, inventario canónico, Lista 1/2 ni EPG. Al añadirlos: Lista 1, en prueba y sin EPG. ID editorial determinista por nombre exacto con región/calidad original (`Nauta.<SHA256(nombre exacto)[:24]>@Nauta`); localizador tokenless catálogo + nombre, nunca el ID opaco del addon ni enlace HLS. Las exclusiones de membresía de la lista publicada no deben tombstonear candidatos; las bajas históricas explícitas sí permanecen excluidas del selector. La app consulta los recursos actuales en RAM y valida HLS/segmento. No se infieren logos ni EPG. Compatible con VibeM3U 0.5.81+.

- Nauta base y HD son filas independientes; no emparejarlas ni ocultar una como respaldo de la otra. El localizador Nauta sirve para resolver esa fila al reproducir, no es una URL directa de respaldo.

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

- Excepción explícita BT/TNT **solo UK**: lista cerrada de nombres completos y
  `group:uk`, comprobada con fotogramas el 02-10-2026. Ver
  `TVVOO_UK_EQUIVALENCIAS.md`. BT ESPN → TNT 4; TNT SPORTS ESPN (ESPN US) y BT 3 HD
  (programa distinto) excluidos. No generalizar SPORT=SPORTS ni añadir HD/BACKUP no
  verificados. La retención de tres corridas nunca restaura una entrada rechazada.

- **Versiones hermanas TvVoo** (`tvvoo_variants.py` → `data/tvvoo-variantes.json`, en el workflow de Highfly): por cada canal TvVoo elegido, las otras entradas del mismo canal y país (HD, FHD, UHD, 4K, SD, HD+, HEVC, H265, (BACKUP n)). La app las prueba si la elegida no entrega video. SPORT y SPORTS no se igualan (en DE/IT «SKY SPORT» es la señal local y «SKY SPORTS» la inglesa); (MATCH TIME), [LIVE DURING EVENTS ONLY], (LOCAL) y RAW no son hermanas; nunca se cruzan países. Una hermana que falta en el catálogo se conserva 3 corridas (TvVoo omite entradas de una consulta a otra). Varias versiones elegidas comparten la ficha del catálogo (guía y logo; nombre/logo personalizado de la primera) y una versión sin ficha usa la de su hermana.
- `data/channel-editor-layout.json`: lo lee **la app directo** (orden, número, visibilidad,
  nombre y logo). Un error ahí puede impedir que la app abra.
- `data/vibem3u-selection.json`: lo lee **el runner**. Debe declarar los mismos canales de
  proveedor activos que el layout (`tests/test_editorial_consistency.py`).
- Publicar layout + selección + presentación juntos, siempre desde el editor (`editor-core`).
- Canales M3U agregados conservan su lista de origen (Lista 1 o 2). Highfly y TvVoo no van a
  ninguna M3U: viven en el layout y la selección.
- Los respaldos directos M3U usan identidades estables (`tvg-id`) en `backupm3u`, nunca enlaces HLS
  firmados. Solo se permite como destino otra fila M3U reproducible por HTTP(S); las referencias
  dinámicas de resolutor, incluida Nauta, no son respaldos directos y no deben ocultar una fila.
- Un cambio editorial no requiere APK nueva.
- Vigencia de variantes TvVoo: tras una consulta correcta, renovar `generatedAt` cada
  24 h aunque las variantes no cambien (la app las descarta a los 7 días). Si falló
  algún catálogo, no renovar por fecha solamente un documento sin cambios conservado.

## 4. EPG

- Sinopsis (`donate_epg_descriptions`): la parrilla no cambia, pero si el programa publicado no trae descripción se toma la de otra fuente del mismo canal cuando se superpone al menos a la mitad y el título coincide (sin tildes ni marcas como «(estreno)»; «Chilevisión» = «CHV»; mismo nombre antes de «:» o « - »). Donantes de sinopsis que nunca entran a la parrilla (ids `sinopsis:`): Zapping (`ZAPPING_DESCRIPTION_CHANNELS`; su guía HTML da 403 desde GitHub, así que en Actions casi no aporta) y Claro Video (`claro-sinopsis`, `CLARO_SYNOPSIS_CHANNELS`, la principal en Actions). La clave pública del cliente web de Claro (`authpt`) se lee de clarovideo.com en cada corrida y nunca se guarda en el repo. Si no calza la hora, se acepta el mismo título a menos de 3 h (Claro trae parrillas corridas), nunca el de otro día. Sin coincidencia, el programa queda sin descripción: no se inventa texto. `dwe` de Zapping es DW Español, no DW English.
- Solo Lista 1 más los canales gestionados con fuente.
- Cada canal mezcla sus fuentes por prioridad (`epg_source_chain`): Red Bull → oficial →
  Zapping → fuente base → TecnoCentro → Pluto → EPGShare de respaldo → guía publicada anterior
  (6 h de pasado máximo). La de más arriba manda donde tiene programas; las demás solo
  rellenan huecos antes, entre medio o después, y un bloque que ya estaba al aire se recorta
  desde donde termina la anterior. Si una oficial vuelve, recupera sus tramos en la corrida
  siguiente.
- **CHV**: su oficial no publica los noticieros; queda como relleno detrás de Zapping y
  TecnoCentro (`EPG_INCOMPLETE_OFFICIAL_IDS`).
- Sin relleno técnico: sin fuente real, el canal queda pendiente (`epg-pending.json`).
  Única excepción acordada: Rwnd (`RewindTV.cl@SD`) = solo continuidad `Live`,
  sin fuente EPG, sin fallback de programación y sin descripción, subtítulos,
  categorías ni metadatos de programas. No asociar a Rewind TV de Estados Unidos;
  ni donantes de sinopsis ni bloqueos manuales pueden reintroducir esa guía.
- Procurar al menos 12 h por canal (mínimo, no tope): se integra toda la guía real que publique
  cada fuente, hasta 8 días. Los pendientes se reintentan en cada ciclo de 6 h.
- **La Red**: solo su guía oficial (`lared.cl`), sin Zapping ni TecnoCentro. Si falla, se
  conserva la última parrilla real. Sus pestañas lun..dom son los próximos 7 días desde hoy.
- **TVN3**: se usa Zapping aunque a veces no calza (decisión del usuario, 27-09). Desde GitHub
  Zapping solo entrega su `nowplaying` (~3 h): la guía completa responde 403.
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
- Canales y EPG corren por partes: un job por proveedor y un job por fuente, más un job final
  que arma y publica. Una parte caída no frena al resto (sus canales usan respaldo).
- Todos los push integran `main` y reintentan; nunca force-push.
- Highfly: `update-highfly.yml` corre cada 30 min (y al cambiar el layout) y publica
  `data/highfly-live.json` con la hoja que hoy entrega señal y su enlace directo (sin token).
  La app lo abre al tiro; si falla porque la hoja rotó, usa su resolutor.
- El Raw de GitHub cachea minutos: verificar con `git show origin/main:<archivo>`.

## 7. App VibeM3U

- Versiones: **cada release sube solo el último número** (0.5.33 → 0.5.34). Subir el del
  medio o el primero lo decide el usuario. Las 0.6.x del 27-09 fueron un error: se retiraron
  con un puente (0.6.2) y la línea siguió en 0.5.33.
- `versionCode` siempre mayor al anterior (Android lo exige).
- Release: commit `chore(release): bump VibeM3U a X.Y.Z` → push → CI verde → tag `vX.Y.Z` →
  workflow "Publicar APK" → verificar tamaño y SHA-256.
- SDK Android local 35/36 confirmado el 05-10 (`android info sdk`); la app se publica únicamente tras CI completo y APK verificado. Una validación JVM no sustituye prueba Android/TV.
- Control: OK muestra el OSD; segundo OK o INFO, Detalle del programa; ◀ o GUIDE, Guía
  completa; ▶, fuentes y calidad; OK mantenido o MENU, Opciones.
- Guía: OK corto abre el canal; OK mantenido programa o quita un recordatorio (campana cyan).
  El aviso (300×52 dp, arriba a la derecha) llega con la app cerrada si tiene el permiso
  «Mostrar sobre otras apps»; «Ver» cambia al canal. Se gestionan en Opciones › Interfaz.
- En la Guía, ◀ ▶ mueven el velo cyan entre programas (el canal no se marca) y ▲ desde el
  primer canal va a los filtros por categoría.
- Estilo vigente (0.5.43) en la Guía, el OSD y los menús:
  - fondo oscuro con el video asomando a la derecha;
  - filas tenues y foco con velo cyan;
  - píldoras (lo activo en cyan);
  - reloj con fecha en recuadro gris;
  - logos con tamaño óptico (`LogoFit`).
- No se cambia el diseño sin mockup aprobado con «aplícalo».

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
| 28-09 | Host nuevo de TVN fuera de la lista permitida: la 0.5.37 perdió todos los resolutores | Host nuevo en el mismo cambio + test del catálogo (§7) |
| 29-09 | CHV mostraba «Plan Perfecto» durante el noticiero | Oficial incompleta = relleno (§4) |
| 29-09 | Mega con hueco y programas duplicados al mezclar oficial y respaldo | Mezcla por prioridad con recorte (§4) |
| 30-09 | Cambio de proveedor de IA sin contexto | `AGENTS.md` + `ESTADO.md` siempre al día (ver `AGENTS.md`) |
