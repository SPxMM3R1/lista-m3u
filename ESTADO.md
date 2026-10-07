# ESTADO.md — Lista M3U: puesta al día para cualquier agente

> Léelo completo antes de trabajar, junto con `AGENTS.md` (cómo trabajar) y `REGLAS.md`
> (reglas vigentes de ambos proyectos). App hermana: `SPxMM3R1/vibem3u` (su `ESTADO.md`
> cubre la app). **Al terminar cualquier cambio, actualiza este archivo en el mismo commit**:
> la sección «Hoy» si cambió el estado y una línea nueva en «Bitácora».

Última actualización: **2026-10-07** (UTC).

## Hoy, en una mirada

- **Cierre CNCVerse 07-10 verificado**: publicación editorial `49a7ce1c92f11491ee8ab51464eb0233c6785734` en main, árbol idéntico al commit local `1fb0f46` (conservado en rama local `work/cncverse-local-equivalente-20261007`). El acceso se restauró con el usuario principal; Git HTTPS falló transitoriamente y se publicó por el conector con hashes de los 11 blobs y árbol verificados, ref con lease y sin force. Después volvió Git y se integraron las salidas automáticas sin perder filas. Runner canales `37691729199` success, editor `37691729201` success, Highfly `37691729071` success, dirigido `37691729058` success; estado generado `1fbab41`. Raw fijado al SHA igual a blobs para ambas Lista 1/layout/presentación, antes y después del runner. Repetidos 319 Python (1 copia omitida por ruta, verificada SHA256 aparte), 41 JS y lector/proyector JVM real: 361 M3U, 310 CNC, 294 altas 219–512, 370 visibles, T13 intacto, cero proveedores descartados. XML publicado: 0 programas CNC. EPG habitual `37691980655` disparada, aún pendiente de cierre en este punto; no se amplía su alcance. No se probó individualmente reproducción de los 310 ni TV física. Contraparte app `826ae676` / 0.5.79 ya publicada, sin APK nueva; caché de app aún local fuera de este cambio.
- **Última petición CNCVerse: inventario completo conocido como pruebas, PUBLICADO / VERIFICADO**. 236 entradas Chile + 74 señales/opciones deportivas, de 31 grupos. 16 estaban activas: se agregan 294 al final, 219–512; 310 CNC activos. Las 228 reincorporaciones antes excluidas responden a esta orden explícita y tienen registro separado, sin alterar auditorías/bajas históricas. 68 grupos deportivos siguen sin localizador identificable o son ambiguos (dos Sky Sports); no se incorporaron como canales ficticios. Todas las nuevas filas `trial: true`, sin EPG ni mantenimiento. Las referencias históricas del 04-10 siguen fechadas; no se garantiza reproducción ni 24/7. Baseline 269 filas previas idéntico, selección/EPG/Lista 2/motores/logos/app intactos. 319 Python/41 JS/bundle y proyección real JVM: 361 M3U, 370 visibles, 310 CNC, T13 respaldado y ninguna fila de proveedor descartada. La generación de bytecode informa un fallo ZIPFS al cerrar el compilador; la ejecución JVM sí pasó, no hubo build APK ni prueba física. Base Lista actualizada fast-forward a `fbc6252` (EPG automática), contraparte app `826ae676` / 0.5.79. Acceso CLI restaurado en esta sesión del 07-10; dry-run de push correcto y pruebas locales repetidas sin fallos. Publicado `49a7ce1`; runner/editor correctos y verificaciones Raw/JVM posteriores completas. La EPG habitual se disparó por separado; ver cierre de publicación arriba.
- **France 24 inglés publicado y verificado**: cambio `1073380`, runner `37539066258` success, estado `c76d52f`; no modificó catálogo/streams ni membresía. Raw/blob iguales para ambas listas/layout/presentación, proyección app antes y después: 18 Español → 19 English, mismos 77 visibles y T13 respaldado. Editor web `37539066224` success. EPG automática `37539349779` disparada con el alcance habitual; inglés conserva prueba/sin EPG. Sin APK. Cierra el pendiente de la entrada siguiente.
- **France 24 inglés reubicado**: la fila existente activa/en prueba `France24.fr@English` pasa del 62 al 19, inmediatamente después de Español (18); Al Jazeera = 20, BBC = 21. `assignChannelPosition` desplaza +1 todos los demás activos con número anterior >=19, también Highfly/TvVoo y respaldo T13 (histórico 217, ahora 218); vínculos por identidad intactos. No duplica, no oficializa ni agrega EPG; estado de prueba, stream y logo conservados. Layout/presentación/Lista 1/alias/inventario sincronizados y selección idéntica. Históricos intactos, registro separado de inserción. 312 Python/41 JS, bundle/contrato y proyección real app 0.5.73 `94dd35b`: mismos 77 visibles, proveedor y respaldo correctos. Sin APK nueva. Pendiente en este punto: publicar y comprobar salida remota/runner.
- **Rwnd ya publicado y verificado**: código `45c217f`; workflow completo `37537954410` success; XML `43d110a`, generación 22:04:37 UTC. Raw fijado al SHA coincide con blob Git: solo 3 bloques Live, 0 descripciones/subtítulos/otros metadatos, 17,98 h futuras al verificar 22:05:31 UTC. El lector XMLTV real de app 0.5.73 muestra Live con sinopsis vacía. Sin APK nueva ni prueba física; caché de TV no observado, revalidación mínima de EpgRepository 5 minutos. Esta entrada cierra el pendiente de la siguiente; no se reparó Meganoticias/007 aquí.
- **Rwnd, continuidad sin EPG**: eliminada asociación errónea `us2 / Rewind.TV.us2`. El runner ya no copia programación fresca ni publicada para `RewindTV.cl@SD`; genera solo bloques `Live` sin sinopsis, subtítulos, categorías ni otros metadatos de programa. La guía reutilizada también se limpia y se excluyen donantes/bloqueos manuales. Cinco regresiones nuevas; 309 Python/41 JS. Sin modificar stream, logo, número, selección ni app; contraparte VibeM3U 0.5.73 `94dd35b`, sin APK ni commit hermano nuevo. Pendiente en este punto: publicar main, regenerar EPG y verificar XML remoto/lector real.
- **ESPN 2 Sur publicada y verificada**: código `58d95b4`; regeneración completa `37535307432` correcta; XML `a2b1a02`. GitHub Raw fijado al SHA y lector XMLTV real de app 0.5.73: 76 programas, más de 55 h futuras, a las 18:20 Chile `ESPN Compact` con descripción final masculina Premier Pádel Rotterdam 17:45–18:45. UTC 20:45–21:45 sin desplazamiento; identidad estable preservada. No APK nueva ni reproducción propia en TV afirmada. Esta verificación cierra el pendiente de publicación de la entrada siguiente.
- **ESPN 2 Sur (32), corrección de guía**: ambos alias TvVoo ES/AR usan `uy1 / [ESP2LS].ESPN.2.uy`. Su descripción de ESPN Compact anuncia final masculina Premier Pádel Rotterdam 17:45–18:45 Chile, consistente con foto del usuario de Tapia/Coello–Stupaczuk/Sanz a las 18:20 y torneo/primer set corroborados por FIP. Se contrastaron 51 registros ESPN en seis guías regionales: Chile anuncia fútbol; ESPN 2 HD UY anuncia tenis. No es prueba de país exclusivo ni cambio horario; sin fotograma nuevo del proveedor en este entorno. Retirado respaldo Bolivia no confirmado, última EPG publicada permanece como fallback. Tres regresiones; 304 Python/41 JS. Solo runner/test/docs; canal, identidad, selección, alias, números, resolutores y app intactos; contraparte VibeM3U 0.5.73 `94dd35b`. Pendiente en este punto: publicar código y regeneración EPG, verificar XML remoto y lector real.
- **EPG ESPN 5 ya publicada y comprobada**: código `00897ab`, XML `8196fd0`, ejecución completa `37403016586` correcta. 67 programas y más de 72 h futuras; actual Rumanía–Suecia 23–01 Chile, no boxeo. Lector EPG real de app 0.5.73 probado con ese XML: conserva identidad y horario absoluto, muestra UEFA Nations League. Intento parcial anterior `37402866106` conservó la EPG porque había huecos/cobertura insuficiente en la base; se recuperó con regeneración completa, sin tocar lógica de renovación ni inventar programación.
- **ESPN 5 (35), EPG corregida**: `WinPlusFutbol.co@Direct181` pasa a `uy1 / ESPN.5.HD.uy`. La anterior `[ESPN5SD].ESPN.5.uy` publicaba boxeo/títulos portugueses y no coincidía con la secuencia observada Francia–Bélgica → Rumanía–Suecia. Guías UY1/CO1 coinciden 21–23 / 23–01 Chile; fotograma ESPN 5 en español con previa de Rumanía. No cambio de stream, identidad, logo, número ni región declarada; no offset horario. Dos tests de mapeo y reemplazo de guía anterior, 301 Python/41 JS. Publicar código y regenerar `epgshare` en GitHub, comprobar salida; app 0.5.73 `94dd35b` no requiere APK nuevo.
- **Última baja: 118, DSports [IP 38]** (`DSports.us@Direct38`): eliminado permanentemente de Lista 1, inventario y editor; exclusión durable evita reposición. Sin renumerar: quedan 77 visibles y los 16 recursos CNCVerse, con respaldo T13 ← 217 intacto. La fila TvVoo antigua en papelera que comparte el número 118 no es el canal activo solicitado y se conserva. Regresión nueva: 299 Python/41 JS y proyección con VibeM3U 0.5.73 (`94dd35b`), sin cambios ni publicación nueva de APK. Los 78 visibles de la decisión anterior son históricos.
- **APK compatible verificado antes del catálogo**: VibeM3U `94dd35b` / tag `v0.5.73`, Android CI `37399927443` y Release `37400308175` verdes; firma compatible comprobada por workflow, Release pública no draft/prerelease, APK 2.717.639 bytes, SHA-256 `10cb0b63f150c1c71cb8fff465d949cdb70bdb143a78d647c78f3d8e265c6f4c`. Instalar 0.5.73 para usar el 217 como respaldo; no se afirma reproducción en TV física. La publicación de catálogo usa commit separado y se verifica después del runner.
- **Última decisión: T13 (9) con respaldo 217; 16 CNCVerse / 78 visibles**. De los 25 números adicionales pedidos, 24 fueron purgados y 349 ya estaba ausente. Registro completo `contracts/channel-number-exclusions-20261006-t13.json`; el registro previo de 40 CNC / 103 visibles es histórico. El 217 sigue activo/en prueba en Lista 1/layout, como recurso del T13, no canal visible aparte. No renumerar ni cambiar los respaldos de Canal 13 (4). Requiere VibeM3U 0.5.73: la 0.5.72 descartaba referencias CNC al construir respaldos. Contraparte `08a7943` / versión `94dd35b`; publicar layout solo tras verificar APK compatible. 298 Python (1 comparación omitida por ruta), 41 JS, contrato, bundle y proyección real con app corregida. Sin modificación editorial de selección Highfly/TvVoo, Lista 2, motores, logos ni EPG; los runners actualizan sus artefactos normales.
- **Estado anterior tras el primer lote: 40 CNCVerse y 103 visibles en la proyección de app**. La orden anterior pidió eliminar 152 números: purgadas 151 filas (TV+ [DPS] 86 y 150 CNCVerse); 188 ya estaba ausente. Registro exacto en `contracts/channel-number-exclusions-20261006.json`. No renumerar los restantes, no ocultar/papelera; IDs excluidos permanentemente evitan reposición. Layout, inventario, Lista 1/alias y presentación sincronizados, demás campos/estados conservados. Los registros de 202 retenidos tras auditoría y 190 tras baja Not 24/7 son históricos, no la membresía actual. Sin cambios de app, selección Highfly/TvVoo, resolutores, Lista 2 ni logos. Validados 296 Python (una copia omitida por ubicación y comparada aparte con CRLF normalizado), 41 JS, contrato, bundle temporal y parser/proyección de app 0.5.72 (`b07c640`); sin APK nuevo. Publicación: comprobar SHA remoto y workflows, no caché Raw.
- **Depuración CNCVerse solicitada por el usuario**: 258 entradas comprobadas con el resolutor Java real de la app 0.5.72 (`b07c640`), enlaces renovados y validación HLS/segmento; repetidos los 57 fallos iniciales. Eliminadas 56 filas (55 sin enlace en ambos intentos y UATV con placa «NO SIGNAL» repetida); quedan 202 CNCVerse. Solo TV, ClickTV y Polar TV se conservaron tras recuperarse. 185 de las retenidas entregaron contenido decodificado observado, 17 solo validaron enlace/segmento dentro del tiempo acotado; no se promete estabilidad continua ni prueba en TV. Números originales preservados (quedan huecos), eliminación permanente, no filas ocultas/papelera; tombstones evitan reimportación. Históricos de 258 altas conservados, bajas documentadas en `contracts/cncverse-link-audit-20261005.json`. No cambios en app, resolutores, EPG, logos ni selección Highfly/TvVoo. Validación local: 294 Python, 41 JS, contrato de resolutores, bundle del editor en temporal y parser/proyección de la app con 202 CNCVerse y 267 canales visibles. Publicación: comprobar el commit remoto y la ejecución de canales/EPG antes de darla por completada.
- **Chile TV y TSN 5 (CNCVerse)**: añadidas las 242 entradas del catálogo elegido por el usuario, más TSN 5. Números 136 (TSN 5) y 137–378 (Chile TV), al final y `trial: true`; fixture exacto `contracts/cncverse-chile-trial-channels.json`, app mínima 0.5.68. Las 15 pruebas anteriores quedan 121–135; sin cambiar filas previas, selección Highfly/TvVoo ni Lista 2. Referencias de búsqueda sin IDs opacos/URL/claves. Sin EPG/país/logo inferidos; no todas las 242 se han probado con video y varias son `[Not 24/7]`. El catálogo reúne regionales, radios con video y señales internacionales además de nacionales, no 242 emisoras nacionales distintas.
- **CNCVerse**: 15 señales de prueba al final de Lista 1 y del orden activo de la app, números 121–135: TNT Sports 1–4, TSN 1–4, D Sports Chile/Argentina, CBS Sports Golazo Network, Premier Sports 1, Fubo Sports 1, FS1 y Tennis Channel 2. Referencias exactas en `contracts/cncverse-trial-channels.json`, sin IDs opacos ni claves; app mínima 0.5.67 (motor ya publicado, commit hermano `f35f874`). Marcadas `trial: true`, sin mantenimiento ni EPG hasta oficialización acordada. Solo logos locales existentes de TNT 1/3 y Premier 1; las demás sin logo asignado. Se conservan las filas previas, números, visibilidad y selección Highfly/TvVoo. Las 15 entregaron fotograma en el diagnóstico del 2026-10-05 UTC y sus etiquetas se reconsultaron antes de incorporarlas; no equivale a prueba en TV, estabilidad o validación del país anunciado.
- **Qué es**: catálogo público de canales, guía EPG y logos que consume la app VibeM3U
  (Android TV), más el runner que los mantiene y el editor web (`site/`).
- **Publicación**: todo corre en GitHub Actions; ningún proceso usa el PC del usuario.
  - Variantes TvVoo: la fecha se renueva cada 24 h tras una consulta correcta aunque
    los alias no cambien, para que la app no descarte respaldos vigentes a los 7 días.
    BT/TNT UK tienen equivalencias explícitas verificadas por imagen; BT ESPN es TNT 4,
    no TNT 1. Rechazados TNT SPORTS ESPN y BT 3 HD (ver `TVVOO_UK_EQUIVALENCIAS.md`).
  - Canales: `update-channels.yml`, un job por proveedor (`direct`, `tvn`, `meganoticias`,
    `highfly`, `tvvoo`) y un job final que arma listas y publica.
  - EPG: `update-epg.yml`, un job por fuente (17 partes, `--list-epg-parts`) y un job final.
  - Highfly: `update-highfly.yml` cada 30 min publica `data/highfly-live.json` (enlace directo
    vigente, sin token). La app lo abre al tiro y usa su resolutor si falla.
- **EPG**: 47 canales. Cada canal mezcla sus fuentes por prioridad (`epg_source_chain`): la de
  más arriba manda donde tiene programas y las demás solo rellenan huecos. Horizonte típico
  30–190 h.
- **Tests**: 319 Python (`python -m unittest discover -s tests -p "test_*.py"`) y 41 JS
  (`node --test tests/editor-core.test.mjs tests/layout-contract.test.mjs`).

## Pendientes y decisiones abiertas

- **EPG pendiente (límite de la fuente, no del runner)**:
  - TVN3 (`1437`): solo existe en Zapping, que desde GitHub entrega ~3 h. Buscado el
    2026-09-30 sin éxito: la página de TVN3 no expone su programación, `estaticos.tvn.cl/epg`
    no tiene ruta para TVN3 y TecnoCentro solo lista «TVN» y «TVN HD».
  - La Red (`0102`) puede figurar como `hueco`: tiene más de 160 h, pero no transmite de
    madrugada. No es falta de guía.
  - MTV Biggest Pop, Flow Latino y Spankin' New: Pluto publica ~13 h y se exigen 24 h.
- **Zapping bloquea a GitHub (403)**: la guía completa (hoy + mañana) no responde ni con
  `X-Forwarded-For` chileno ni por su frontal `cl-apig`. El runner usa el endpoint
  `nowplaying` (anterior, actual y siguientes: ~5 programas). Probado el 2026-09-29.
- **CHV**: su página oficial no publica los noticieros. La oficial solo rellena detrás de
  Zapping y TecnoCentro (`EPG_INCOMPLETE_OFFICIAL_IDS`). Más allá de ~30 h todavía puede
  aparecer un programa estirado sobre el noticiero.
- **Logos**: pendiente de decidir si la coincidencia por nombre exige país (`REGLAS.md` §5).
- Carpeta `experiments/direct_links_lab/` **del usuario, sin commitear**: no tocarla, no
  incluirla en commits y no usar `git stash -u` (se la llevó una vez el 2026-09-29).

## Cómo trabaja el usuario (válido para ambos proyectos)

- Responder siempre en **español de Chile, tuteando**. Nunca en inglés.
- **Diseño**: primero mockup (imagen), y solo con «aplícalo» se toca código, se compila o se
  publica. «Sí» a una pregunta no es «aplícalo».
- **No usar el PC del usuario para automatizar** (nada de tareas programadas ni servicios
  locales): todo en GitHub Actions. Para diagnosticar desde fuera de Chile, usar una rama
  temporal con un workflow `on: push` y borrarla después.
- Antes de afirmar que un canal o fuente «no funciona», comprobarlo más de una vez y decir
  «en este momento».
- Nunca force-push; acciones destructivas solo con confirmación; nunca publicar tokens,
  credenciales ni URL firmadas.
- Versiones de la app: solo sube el último número salvo que el usuario decida otra cosa.

## Entorno de trabajo

- Windows, repos en `D:\Users\SP4MM3R\Documents\Codex\` (`Lista M3U` y `VibeM3U`). Git Bash y
  PowerShell; `gh` CLI autenticado.
- **2026-09-30: el disco D: quedó lleno (0 GB libres)** y git no podía escribir. Si un commit
  falla por espacio, avisar al usuario; no borrar nada suyo para liberar espacio.
- **2026-10-06 UTC**: D: vuelve a estar sin espacio; fetch falló sin poder escribir objetos.
  Baja por números trabajada y validada en clon de Lista M3U en C:
  `C:/Users/SP4MM3R/Documents/Codex/2026-09-20/este-chat-coordina-los-proyectos-lista/work/lista-m3u-bajas-numeros-20261006`.
  El checkout original de D: no está sincronizado con esta publicación; conserva el experimento
  no seguido `experiments/direct_links_lab/`. No tocarlo ni asumir que una copia antigua es autoridad.
- Mockups: HTML renderizado con Edge headless. Lo confiable es PowerShell con
  `Start-Process msedge.exe --headless=new --screenshot=... -Wait` y un `--user-data-dir`
  nuevo por captura.

## Bitácora (más reciente arriba)

- **2026-10-07, cierre publicación CNCVerse**: editorial `49a7ce1` publicado por conector tras restaurar permisos; 11 blobs/árbol idénticos al commit local y ref main comprobada sin force. Runners canales `37691729199`, editor `37691729201`, Highfly y dirigido correctos; integrado `1fbab41` y revalidados 319 Python/41 JS/JVM real, 310 CNC/294 altas finales, mismos respaldos y 0 programas CNC. EPG habitual `37691980655` lanzada aparte, aún pendiente de cierre. Docs de contexto publicadas en el mismo flujo; no app/APK nueva ni pruebas de reproducción de todas las señales.

- **2026-10-07, local**: petición explícita de añadir todo el inventario CNCVerse conocido al final de Lista 1 como pruebas sin EPG. Fixture nuevo `contracts/cncverse-inventory-trials-20261007.json`: baseline inmutable de filas, localizadores exactos/fechas, 294 altas 219–512, 228 reincorporaciones explícitas y 68 grupos pendientes. Dos nombres Sky Sports indistinguibles para el resolutor actual se excluyen, donaciones no son canales y opciones SERVER/Link no se presentan como emisoras distintas. No se persisten metas.id, HLS, claves ni tokens. Cambios vía editor-core + apply_patch: catálogo/ambas Lista 1/layout/presentación; tests históricos descuentan solo las reincorporaciones autorizadas y seis nuevas regresiones cubren baseline, numeración final, 236 Chile, exclusión EPG, tombstones y privacidad. 319 Python, 41 JS, bundle de 563 filas; contrato compartido idéntico por SHA256. Después del runner se ejecutó lector/proyector JVM de app: 361 M3U, 310 CNC, 370 visibles, T13/respaldos preservados. Compilador con error de cierre ZIPFS, ejecución JVM satisfactoria; no Android/TV físico. Sin cambios de VibeM3U ni APK/commit hermano nuevo; cambios de caché de la app ya presentes en el worktree siguen ajenos a esta tarea. Publicación pendiente por autenticación/permisos; no se creó commit sin capacidad de publicar.
- **2026-10-06**: a pedido del usuario, el 68 («ESPN», `ESPN.us@Direct181`) va a la papelera y el
  69 (`ESPN4.br@Direct181`) pasa al 35 como «ESPN 4», oficial y con logo `logos/espn-4.png`
  (tv-logos Brasil recoloreado al rojo de ESPN 3/5). No es Brasil: es ESPN 4 Norte (barra en
  español con horarios MÉX/PAN). Guía `pa1` `Canal.ESPN.4.(Panamá).pa`, comprobada con dos
  cuadros (20:45 NFL, 21:09 Southern Miss vs. Troy); las guías ESPN 4 de UY/CO son del feed Sur.
- **2026-10-06**: pedidos del usuario.
  - Eurosport 1 (63) y 2 (64) de TvVoo España: `backupCountries` = portugal, unitedkingdom,
    france, italy, germany, netherlands. `tvvoo_variants.py` suma, después de las hermanas del
    país, el mismo canal de cada país (uno por país, mejor calidad, nunca BACKUP); la app ya los
    prueba en orden (resuelve por alias, que trae el país). Excepción editorial a «no cruzar países».
  - France 24 English (19) deja de estar en prueba: recibe la guía `France.24.Anglais.fr` ya
    configurada. DSports [IP 15] (118→37) y DSports 2 [IP 187] (120→38) pasan antes de los XITE
    (números libres, nada más se renumera), oficiales y con guía de Colombia (`co1`):
    `DSPORTS.(COL).(DTSC).co` y `DSPORTS.2.HD(DTV2HD).co`, elegidas comparando cuadros de las
    señales (20:34) con la parrilla: son el feed andino. Las pruebas que fijaban el estado
    anterior (France 24 en prueba, DSports 2 en el 120) se actualizaron a este pedido.
- **2026-10-06, cierre France 24**: código editorial `1073380f3c4e22885ec7201e79e49151b0cce305` publicado main, cuatro archivos Raw fijados al SHA iguales a sus blobs Git y lector/proyector 0.5.73 correcto. Runner de canales `37539066258` success: generó `c76d52f` solo para salud/estado; posición/streams/layout/selección sin cambios. Editor web `37539066224` success y EPG habitual `37539349779` disparada, sin oficializar France 24 inglés. Git limpio tras integrar main; documentación de cierre publicada sin force push. No validación física de reproducción ni APK nueva, se reutiliza la fuente existente.
- **2026-10-06, France 24 inglés**: usuario pide incorporarlo después del español; ya existía activo/en prueba en el 62, por lo que se reubica al 19 con editor-core, sin duplicar ni alterar prueba/stream/logo/identidad/membresía. Se informa en el chat antes de aplicar que se conserva prueba; no se interpreta como autorización de oficialización/EPG. Número 18 español conserva posición y activos siguientes suben +1 (incluidos proveedores, respaldo T13 ahora 218), orden editorial y M3U coherentes. Registro `contracts/channel-position-change-20261006-france24.json`; los fixtures históricos de bajas/altas no se reescriben. Tres regresiones nuevas y adaptación de expectativas de números históricos a esta inserción. 312 Python/41 JS, bundle temporal y contrato correctos; lector/proyector real VibeM3U 0.5.73 `94dd35b`: 77 visibles, France24 consecutivos 18/19, sin proveedores descartados y mismo T13/respaldo. Solo Lista M3U, selección y app sin cambios. Publicar en main y verificar runner y archivos remotos; sin APK nueva.
- **2026-10-06, cierre Rwnd**: `45c217f` publicado y todas las fuentes/armado/publicación/verificación Raw de `37537954410` correctos. XML remoto `43d110ad924341d33a9267dfd95fee6bafc0fc53`; hash blob Raw/Git idéntico `6dc7dabb73794ba2c6ea0737f38c3d462990f312`. Tres bloques Live de seis horas, sin sinopsis ni otros metadatos, cobertura futura casi 18 h. Lectura real de EpgParser/EpgProgramme 0.5.73 correcta; no APK, no test en TV física ni renovación de caché observada. Orden validado runner → lector app → publicación/regeneración → XML remoto/lector. Documentación de cierre se publica en el mismo flujo, sin force push ni modificación de los repos originales de D:.
- **2026-10-06, Rwnd**: el usuario pide mantener solo continuidad Live sin EPG/descripciones. Causa: el mapa `us2/Rewind.TV.us2` copiaba una guía ajena y la normalización solo cambiaba el título, conservando sinopsis. Retirado mapa y bloqueadas fuentes/fallback, donantes y bloqueo manual para la identidad; limpieza de metadatos al reutilizar XML. Cinco tests cubren overrides de fuente, guía fresca + publicada, limpieza idempotente sin tocar otros canales, donación y bloqueo manual. Validar primero runner (309 Python/41 JS), después lector XMLTV real de app 0.5.73 `94dd35b`, publicar código y regeneración/verificación EPG. No corrección de reproducción del 007 en este cambio, no APK ni cambios de catálogo.
- **2026-10-06, cierre ESPN 2**: código `58d95b4` publicado main; todas las fuentes y armado/publicación de `37535307432` correctos, XML remoto `a2b1a02`. Raw fijado al SHA y contenido Git coinciden. Parser EpgParser/EpgData/EpgProgramme de VibeM3U 0.5.73 recompilado para verificación JVM: 76 programas de la identidad `spain|vavoo_ESPN%202%7Cgroup%3Aes@TvVoo`, título ESPN Compact, descripción de final masculina de Rotterdam, UTC 20:45–21:45 y 12+ h futuras (aprox. 55 h). No nueva APK, no cambio de reproducción ni prueba de TV física. Orden cumplido: runner/tests reales → lector app → código main → workflow → XML remoto/lector. Documentación de cierre publicada en el mismo flujo, sin force push.
- **2026-10-06, ESPN 2 Sur**: usuario confirma foto contemporánea a las 18:20 Chile y solicita revisar todas las señales Sur. Comparadas guías AR1/CL1/CO1/EC1/PE1/UY1 (51 registros ESPN, 14 variantes ESPN 2, 3 sin programa en la franja; no guía dedicada BO/PY/VE). Coincide `[ESP2LS].ESPN.2.uy`: ESPN Compact, descripción final masculina Rotterdam del 04-10, 17:45–18:45; FIP confirma Tapia/Coello–Stupaczuk/Sanz, primer set 6–3. El chat inicial omitió esa descripción ya disponible: no atribuir hallazgo a una actualización del proveedor. Cambiados solo mapeos heredados ES/AR y retirado respaldo Bolivia no confirmado, sin desplazar hora/renombrar canal/tocar resolutores. Tres tests protegen selección exacta, sustitución de fútbol/tenis viejo, descripción/horas y alias estable de app; 304 Python/41 JS. Contraparte app existente `94dd35b`, sin nueva APK. Publicar main y regenerar todas las fuentes si la base no admite renovación parcial; conservar compuertas y verificar XML publicado/lector Android antes de dar la reparación por cerrada.
- **2026-10-06 UTC, cierre ESPN 5**: publicación del código `00897ab` y regeneración completa correcta `37403016586`, XML remoto `8196fd0`. Guía actual Rumanía–Suecia 23–01 Chile, 67 programas/72+ h; validación primero runner (301 Python/41 JS y armado fresco), después parser XMLTV real de app 0.5.73, sin nueva APK. Se documenta limitación operativa: renovación parcial `37402866106` falló porque la EPG anterior no cubría Lista 1 sin huecos; no publicó nada, por lo que se ejecutaron todas las fuentes existentes. No se desactivaron compuertas ni cambió el mantenimiento o pertenencia de canales. Verificar GitHub Raw fijado al SHA, no caché de main. Documentación de cierre también se publica en el mismo flujo.
- **2026-10-06 UTC**: autorizado «Hazlo» tras diagnóstico de ESPN 5. Corregido solo mapeo de `WinPlusFutbol.co@Direct181` de `[ESPN5SD].ESPN.5.uy` a `ESPN.5.HD.uy`, fuente UY1 ya integrada. Secuencia reportada Francia–Bélgica/Rumanía–Suecia y contraste UY1/CO1, captura 02:01:50 UTC (23:01:50 Santiago) con logo ESPN 5/textos españoles/Rumanía. No inferir país exclusivo por programas compartidos ni nombre SD/HD. Dos regresiones: fuente correcta y guía fresca gana a boxeo publicado sin mover horas o identidad. 301 Python/41 JS; no edición manual XML ni nueva EPG para otras listas, sin app/stream/logo/número/layout/selección. Publicar código separado y regenerar EPG por workflow `fuentes=epgshare`, verificar fuente y programación XML remoto; contraparte app existente `94dd35b`, sin APK.
- **2026-10-06 UTC**: orden «Elimina el 118». Identificado el activo DSports [IP 38] (`DSports.us@Direct38`), sin dependencias de preferida/respaldo. Purga vía editor-core, eliminación del bloque en inventario/Lista 1/alias y exclusiones por ID, números/campos/estados de restantes conservados. 77 visibles, CNC permanece 16; T13/217 intacto. Test de baja permanente y 119 sin renumerar; 299 Python/41 JS, proyección real de app 0.5.73. No cambia selección, Lista 2, EPG, logos, app ni motores; contraparte existente `94dd35b`, sin APK nuevo. Publicación en main y verificación posterior del runner/editor en el mismo flujo; originales D: intactos.
- **2026-10-06 UTC**: el usuario pide «217 backup del t13» y 25 bajas nuevas (329, 345–351, 355, 357, 358, 360–362, 364–367, 369–372, 376–378). 349 ya ausente, purgadas las otras 24 CNC. T13 9 (`0124`) suma el 217 vía `setBackupM3u`; resto de filas/números/estados y bloques conservados, exclusiones durables e históricos intactos. Dos regresiones nuevas: bajas exactas y fuente de respaldo activa/no excluida, 298 Python/41 JS. Proyector app corregido: 16 CNC, 217 dentro de T13, 78 visibles. Se detectó y reparó en VibeM3U que los respaldos solo aceptaban HTTP; corrección `08a7943`, versión 0.5.73 `94dd35b` (331 Android debug/lint/auxiliar correctos). Coordinación: runner/editor primero, app validada y APK publicado antes del catálogo, commits/repos separados; no alta automática ni nueva EPG. D: lleno; ambos originales permanecen intactos, publicaciones desde clones C:.
- **2026-10-06 UTC (05 en Santiago)**: baja explícita por 152 números actuales: 151 eliminados permanentemente, 188 ya ausente. TV+ [DPS] (86) y 150 CNCVerse, sin dependencias de respaldo; quedan 40 CNC y 103 visibles en parser/proyección real de app 0.5.72 `b07c640`. Registro exacto `contracts/channel-number-exclusions-20261006.json`, no nueva clasificación de fallos. Editor-core coordina purga, exclusiones, órdenes y alias; comparación contra HEAD demuestra números, estados, campos y bloques de los restantes conservados. Selección Highfly/TvVoo, Lista 2, resolutores, EPG, logos y auditorías anteriores intactos. 296 Python (1 comparación omitida por ruta del clon y pasada aparte), 41 JS, contrato y bundle temporal correctos. AGENTS actualizado. Trabajo aislado en C: por D: lleno; sin commit hermano ni APK nuevo. Publicar y verificar remoto/workflows en el mismo flujo, sin force push.
- **2026-10-05**: a pedido del usuario, el 81 (TVN3 [Mediastream], `TVN3.cl@Mediastream`, en prueba) va
  a la papelera: era el mismo stream de TVN3 (011) sin el sufijo `?PlaylistM3UCL`.
- **2026-10-05**: orden explícita «Elimina esos not 24 7»: purgadas las 12 CNCVerse restantes anotadas así, números 140, 156, 204, 208, 227, 228, 229, 243, 247, 251, 258 y 265. Quedan 190 CNC y 255 visibles en proyección de app, sin renumerar ni ocultar. Manifest de bajas editoriales separado, auditoría de enlaces intacta; test nuevo y purga/tombstones ampliada a ambas decisiones. 295 Python/41 JS correctos, contrato y editor temporal correctos; contraparte VibeM3U `b07c640`, sin commit de app. No alterar el parser de esas referencias ni borrar canales de otras fuentes por parecido de nombre. Cambios realizados con editor-core, inventario y alias sincronizados; experimento del usuario intacto.
- **2026-10-05**: depuración CNCVerse tras auditar 258 señales, repetir las que fallan y examinar fotogramas. 56 bajas permanentes, 202 retenidas; UATV solo mostró «NO SIGNAL» dos veces, Polar TV volvió y no se borró. Inventario + Lista 1/alias + layout + presentación coherentes; números y selección Highfly/TvVoo intactos, fixtures originales históricos. Auditoría saneada por identidad/resultado en `contracts/cncverse-link-audit-20261005.json`, dos tests nuevos de repetición y purga/tombstone (294 Python/41 JS). Contraparte de lectura/resolución: app 0.5.72 `b07c640`, sin commit ni APK nuevo en VibeM3U. No se tocaron archivos del experimento del usuario.
- **2026-10-05**: respaldos directos múltiples (`backupm3u` en el layout, app 0.5.72): lista ordenada
  de tvg-id de otras filas M3U de la misma señal que la app prueba después de la propia (y de la
  preferida, si hay). Editor: `setBackupM3u`, validación (hasta 8, sin repetir, filas M3U
  existentes), sección «Respaldos directos» en el inspector y etiquetas «+ N respaldos» / «Dentro
  de NNN». A pedido del usuario: TVN (01) ← 73 y 74; Canal 13 (004) ← 85 (después del 079 y su
  propia señal). El runner no cambia: las filas siguen publicadas en Lista 1 (en prueba) y la app
  las oculta.
- **2026-10-05**: el cambio dirigido del 38 falló en `test_cncverse_contract`: `presentation-overrides`
  guarda también `orders["1.m3u"]`/`["2.m3u"]` (alias que escribe el publicador dirigido) y el
  contrato exige que igualen a `m3u.m3u`/`m3u-externa.m3u`; `buildPresentationOverrides` solo
  actualizaba los nombres largos, así que cualquier cambio del editor (también el web) rompía la
  publicación. Ahora copia el orden a los alias cuando existen (prueba nueva en editor-core).
- **2026-10-05**: a pedido del usuario, el 38 (Fox Sports 1, `FoxSports1.us@Direct`, en prueba) va
  a la papelera con `setRowState` del editor; el resto conserva número y orden.
- **2026-10-05**: a pedido del usuario, el 120 (Sky Sports F1 UK de TvVoo, agregado el 04-10 para
  comparar con Highfly; daba lo mismo) va a la papelera con `setRowState` del editor. Los activos
  conservan número y orden; las filas en papelera que estaban intercaladas quedan al final (la
  convención del editor: activos, ocultos y papelera).
- **2026-10-05** (UTC): VibeM3U compatible publicado antes del catálogo: commit/tag `b7bc7af` / `v0.5.68`. Android CI `37261753671` y Release `37262006591` verdes; 23 tests CNCVerse sin errores en debug/experimental/release, instrumentadas y firma compatible aprobadas. APK descargado verificado: 2.714.111 bytes, SHA-256 `cf5ca9392e965b25e0e79f68b84fd1e7bdc64eb5c57d5ebb46cb73fd95d0e199`, coincide con digest GitHub; Release no draft/prerelease. Las entradas Chile necesitan instalar esa versión; el auxiliar local también fue recompilado.
- **2026-10-05** (UTC): proyección de la lista completa verificada con las clases reales de VibeM3U 0.5.68: 258 referencias CNCVerse al final, números 121–378, 328 canales visibles totales y sin filas de proveedor descartadas. Una regresión del URI genérico con los 15 nombres `[Not 24/7]` se corrigió en el commit hermano `b7bc7af`; no eliminar esas entradas ni cambiar sus nombres para evitar el error. Parser, caché y modo Chile comparten el mismo contrato. Los 270 registros editoriales anteriores y los bloques/órdenes M3U previos se conservaron íntegros; quedan 513 filas editoriales (no todas activas) y 42 M3U oficiales en alcance EPG, sin cambios a la selección.
- **2026-10-05** (UTC): el usuario eligió explícitamente todas las 242 entradas de CHILE TV y TSN 5. Se congelan nombres/IDs editoriales independientes del ID opaco, se amplía el contrato del runner a modo `chiletv` y se agregan filas con editor-core, manteniendo números/estados previos y orden de inventario. Total nuevo 243 (136–378), total pruebas CNCVerse 258 (121–378). 292 Python y 39 JS verdes, contrato válido; EPG oficial y selección Highfly/TvVoo intactas. Resolutor hermano ampliado en VibeM3U (`61700ad`, versión `12f69db` / 0.5.68); incorporar membresía solo después del APK compatible. Video real Java: 13C/13 Cultura (2,91 s) y Holvoet (3,95 s); sin afirmación de reproducción de las 242 ni prueba física.
- **2026-10-05** (UTC): incorporadas por petición del usuario 15 señales CNCVerse como pruebas al final de Lista 1 (121–135). Inventario, ambas copias de Lista 1, layout y presentación coordinados mediante `site/editor-core.mjs`; fixture de etiquetas exactas y tres regresiones para orden/numeración, contrato y exclusión EPG. D Sports conserva las banderas del proveedor y Golazo/Tennis Channel 2 usan `Link 1`. Sin tocar Lista 2, selección Highfly/TvVoo, app, resolutores ni canales anteriores. Motor hermano VibeM3U `f35f874` / v0.5.67, ya publicado.
  - Validaciones locales: 290 Python y 39 JS en verde, contrato CNCVerse de 15 referencias correcto; parser M3U y proyección de layout del código publicado de app 0.5.67 aceptan las 15 al final con números 121–135 y no descartan filas de proveedor. No es prueba en dispositivo físico. Los órdenes de presentación de `1.m3u` y `m3u.m3u` permanecen iguales.
- **2026-10-05** (UTC): CNCVerse declarado en `resolver-catalog.json` y validado por el runner (`tests/test_cncverse_contract.py`). Contrato coordinado con VibeM3U `cf106e8` (motor app/auxiliar) y `bde1201` (versión 0.5.67). Sin copiar Bridge ni extensión Cloudstream, sin ID opaco/ClearKey/HLS temporal público; sin cambios de membresía, EPG, logos, Highfly o TvVoo. 287 tests Python/39 JS en verde antes de las pruebas de app; publicación en commits separados. Auxiliar recompilado con Gradle offline; APK se verifica en CI/Release de VibeM3U.
- **2026-10-04**: revisión de F1 UHD (22) y Main Event UHD (25): Highfly exige Premium para las
  dos hojas 4K (`now-34343434`, `now-srr343434`); su API gratuita entrega un marcador
  (`url` www.google.com, «🔒 Upgrade to Premium») en vez de HLS. El runner no estaba roto:
  F1 UHD sigue publicando la FHD gratuita (`now-545445`) como respaldo, según lo decidido el
  03-10; Main Event UHD no tiene hoja gratuita y solo funciona con Premium vinculado en la app
  (Main Event de TvVoo está en el 24). Cambio: `fetch_highfly_stream_urls_for_slug` falla con
  «hoja Highfly bloqueada por Premium» (`highfly_payload_premium_locked`) y `highfly_live.py`
  muestra en el log el motivo de cada hoja sin señal. Hosts Premium (`premium*.highfly.to`)
  responden normal (401 con token de prueba).
- **2026-10-04**: Canal 13 (004) con `preferredM3u` = `Canal13.cl@Direct187` (079, misma señal en
  mejor calidad): VibeM3U 0.5.65 abre primero la 079 y, si falla, la propia del 004; la 079 deja de
  verse sola en la app (sigue publicada en Lista 1, en prueba). Sky Sports F1 UK de TvVoo (FHD, con
  sus hermanas como versiones) vuelve al final, 120, «Sky Sports F1 UK (TvVoo)», para comparar
  con el de Highfly, que va ~3 h diferido (confirmado con capturas y la parrilla oficial de Sky).
- **2026-10-04**: 75 (Mega [VTR]) y 77 (Mega [Movistar]) a la papelera; 70 activos, Lista 1 = 56.
- **2026-10-04**: ESPN 5 Sur (035) con `logos/espn-5.png` (tv-logos Brasil, recoloreado al rojo de
  `espn-3.png`).
- **2026-10-04**: ESPN 3 Sur (033) usa `logos/espn-3.png` (`logoOverride`).
- **2026-10-04**: a pedido del usuario, 63 canales a la papelera (34, 37, 39, 63–66, 70–72, 76, 78,
  80, 82–84, 87–116, 120–123, 125, 127–138; el «165» pedido se tomó como 135). Sin renumerar:
  quedan 72 activos, 16 en prueba; Lista 1 = 58.
- **2026-10-04**: ESPN 3 Sur en un solo canal: el directo «Win Sports [IP 181]» (033, «ESPN 3 Sur»)
  lleva `backupTvVoo` = `arabia|vavoo_ESPN%203%7Cgroup%3Aar`; la fila TvVoo suelta va a la papelera
  y el 036 queda libre. Necesita VibeM3U 0.5.64 (antes se ve solo el directo). «Win+ Fútbol [IP 181]»
  es «ESPN 5 Sur». EPG: ESPN 3 Sur = `Canal.ESPN.3.(Chile).cl` (Argentina de relleno); ESPN 5 Sur =
  `[ESPN5SD].ESPN.5.uy` (nueva fuente `uy1`; el otro ESPN 5 de Uruguay coincide con Colombia/México).
  Títulos EPG: siglas cortas con números quedan en mayúsculas («A3D», «4K») y se suman siglas
  deportivas (NFL, NBA, UFC…); tras «: » la letra va en mayúscula. Editor: campo «Respaldo TvVoo».
- **2026-10-04**: canales «en prueba» y Lista 2 vacía, a pedido del usuario. Todo lo directo de
  Lista 2 pasa a Lista 1 con `trial: true` (75 activos + 13C; los 46 que el usuario tenía en la
  papelera siguen ahí). Lista 1 = 118 (42 oficiales + 76 en prueba); `m3u-externa.m3u`/`2.m3u`
  quedan con solo la cabecera (`external_list_disabled`). Los 46 espejos TvVoo/Highfly salen de
  Lista 2 (la app los toma de los proveedores). En prueba = sin EPG, sin validación ni reparación,
  fuera de la compuerta EPG; «Oficializar» en el editor los vuelve normales. Arreglado de paso: el
  guardado de las 17:39 nombró «ESPN 3» a Win Sports [IP 181], que choca con el canal TvVoo «ESPN 3»
  y rompía canales y cambios dirigidos; queda «ESPN 3 [IP 181]».
- **2026-10-04**: los 69 canales nuevos de Lista 2 (iptv-org, tlink y 13C) entran a la grilla del
  editor como filas M3U de Lista 2, activas, del 68 al 136 (tras los 67 que dejó el usuario).
- **2026-10-04**: a pedido del usuario, también a Lista 2 las 20 transmisiones de iptv-org en
  tlink.cl (fallaban desde EE. UU.; probablemente solo responden en Chile): nacionales, Mega 2,
  Mega Ficción, Meganoticias Ahora, Megatiempo, CDO, ETC TV y otras, con tvg-id `…@tlink`. Y 13C
  (`13C.cl@SD`, ya en el catálogo) pasa a Lista 2.
- **2026-10-04**: 48 transmisiones de iptv-org a Lista 2 (`m3u-externa.m3u`/`2.m3u`) y al
  catálogo, para revisarlas en el editor: respaldos de nacionales (TVN, Mega, Canal 13, 24 Horas,
  TVN3), canales chilenos nuevos (13 Realities, 13 Festival, 13T, T13 En Vivo, TV+, Bío Bío, UCV,
  Vía X, Telecanal, TV Chile, Teletrak, Turf Móvil) y deportes (DSports, DSports 2, Claro Sports,
  TyC, Win Sports, Win+ Fútbol, Movistar Deportes PE, L1 Max, Tigo Sports PY/GT, beIN XTRA ES,
  Golf Channel LA, Azteca Deportes). Solo las que entregaron segmento en una prueba desde GitHub
  Actions (EE. UU.); tvg-id `<id iptv-org>@<origen>`. Las de tlink.cl fallaron desde EE. UU. y no
  se agregaron. Cinco ya existían en el catálogo con otro ID y no se duplicaron.
- **2026-10-04**: ESPN 2 Latam (119) perdió su EPG desde la unión ES+AR: la reconciliación veía
  dos fichas (`Vavoo.es.ESPN2` y `Vavoo.ar.ESPN2`) y dejaba la fila «catalog_match_ambiguous».
  Ahora, si una fila TvVoo toca varias fichas, manda la de su alias estable
  (`_matches_stable_alias`). Verificado: la señal es ESPN 2 Sur (Chile/Argentina); a las 14:34
  UTC daba Azerbaiyán vs. Lituania, igual que `Canal.ESPN.2.(Chile).cl`.
- **2026-10-04**: Eurosport 2 España (ex 163) pasa al 117, junto a Eurosport 1 (116), con
  `logos/eurosport-2.png` (tv-logos, mismo estilo que el 1); los 117–128 se corren +1. ESPN 2
  Latam: las filas ES y AR (misma señal) quedan en una sola, la 119, con los dos alias TvVoo
  como versiones (`resolverAliases`) y `logos/espn-2.png` (tv-logos AR); la fila AR va a la
  papelera y el 121 queda libre.
- **2026-10-03**: 118 y 120 son la misma señal, ESPN 2 Latinoamérica (lo confirmó el usuario):
  ambos se llaman «ESPN 2 Latam» y usan la EPG `Canal.ESPN.2.(Chile).cl`, con Bolivia (`ar1`) de
  relleno. `Vavoo.es.ESPN2@TvVoo` sale de `NO_EPG_CHANNEL_IDS`.
- **2026-10-03**: a pedido del usuario, 51 filas TvVoo a la papelera del editor (129–180 salvo
  163 Eurosport 2 España; incluye TNT Sports ESPN y TNT Sports 5). Sin renumerar: quedan 121
  activos, último 163. Eurosport 1 (116) usa `logos/eurosport-1.png` (el logo del ex 179).
- **2026-10-03**: Main Event como F1 (normal y luego UHD): 24 Sky Sports Main Event (TvVoo),
  25 Main Event UHD, 26 Premier League. Nada más cambió de número.
- **2026-10-03**: el editor ordena por `order`, no por `number`: al mover F1 UHD (22) y Main
  Event UHD (24) solo cambié el número y quedaron al final. Ahora `order` sigue al número en
  todos los activos (ocultos y papelera después). Al reubicar canales por script, actualizar
  ambos campos (o usar `assignChannelPosition` del editor).
- **2026-10-03**: orden pedido por el usuario: 21 Sky Sports F1 · 22 F1 UHD · 23 Tennis ·
  24 **Sky Sports Main Event UHD** (Highfly 4K `now-srr343434`, `SkySportsMainEventUHD.uk`,
  logo recuperado del historial, guía de Main Event) · 25 Premier League y el resto corrido +2.
  Main Event solo existe en 4K en Highfly: sin Premium no tiene respaldo gratuito dentro de
  Highfly (la versión TvVoo sigue aparte en el 26).
- **2026-10-03**: Sky Sports F1 y **Sky Sports F1 UHD** son canales distintos. El editor
  agrupaba «(4k) SKY SPORTS F1» con la FHD y dejó F1 en la hoja 4K, que sin Premium solo entrega
  un aviso «🔒 Upgrade to Premium». Ahora la calidad 4K/UHD/8K de Highfly es una identidad
  propia (`isUltraHighflyName`/`ultraHighflyIdentity` en el editor y `is_uhd` en
  `parse_highfly_live_resolver_map`): F1 vuelve a `now-545445` (FHD gratuita) y F1 UHD
  (`SkySportsF1UHD.uk`, número 179, `now-34343434`) recupera el logo borrado el 13-09. Su
  respaldo gratuito sale solo: el runner publica para la fila UHD la primera hoja con señal de
  sus variantes (la FHD), y la app con Premium prueba antes la 4K. Guía: la misma de F1.
- **2026-10-03**: los 38 canales TvVoo que solo llegaban por `2.m3u`/`m3u-externa.m3u`
  (formato antiguo: tvg-id `…@TvVoo` con varios `x-resolver-ids`) pasan al editor como filas
  de proveedor, con la misma `addRow` del generador y la fila del catálogo oficial de TvVoo de
  cada país (números 141–178, en el orden de la M3U). No cambia ningún número existente: el
  script lo verifica fila por fila. Se conserva el nombre y el logo que mostraban; los logos
  externos de tv-logo se copiaron a `logos/tvvoo/` (algunos son genéricos o de otro país, como
  estaban). Otros 6 ya tenían fila en el editor (2 de ellas borradas por el usuario: Sky F1 UK
  y Sky Sports Mix, que no se reactivaron). Sky Sport 9 Alemania y Eurosport 1 Alemania quedaron
  con su versión vigente («HD (BACKUP)» y «HD»). Pendientes de antes, sin fila en el catálogo
  (sin guía): ESPN, ESPN 3 y ESPN 4 Países Bajos, Fox Sports 3 España, Fox Sports Premium y TNT
  Sports Premium Arabia.
- **2026-10-03**: agregado TNT Sports 5 (TvVoo Reino Unido,
  `unitedkingdom|vavoo_TNT%20SPORTS%205%7Cgroup%3Auk`, número 140) con fila de catálogo
  `Vavoo.uk.TNTSPORTS5@TvVoo` (marca managed) y guía de EPGShare UK1 `TNT.Sports.5.HD.uk`.
  Logo `logos/tvvoo/tnt-sports-5-uk.png` (tv-logo). Comprobado que entrega video en este momento.
  Hecho desde una copia en C: porque el disco D: del usuario quedó lleno.
- **2026-10-03**: agregado TNT Sports ESPN (TvVoo Reino Unido,
  `unitedkingdom|vavoo_TNT%20SPORTS%20ESPN%7Cgroup%3Auk`, número 139) como alternativa mientras
  TNT Sports 1 está caído en el origen de Vavoo (502). Reconcilia con `Vavoo.uk.TNTSPORTESPN@TvVoo`.
  Sin guía: EPGShare UK1 no publica un canal TNT Sports ESPN (solo TNT Sports 1–10), así que no se
  le asignó EPG ajena. TNT Sports 5 existe en TvVoo UK pero respondió de forma intermitente; no se agregó.
- **2026-10-02**: aplicado el cambio de color aprobado de Qello Concerts: las letras
  negras pasan a blanco mediante `fill="#FFFFFF"` en el grupo del SVG original;
  la clase cyan `#03A4D9`, los trazados y la transparencia se conservan. Se regenera
  `logos/qello.png` al tamaño original para que la app y el editor lo consuman por
  la misma ruta. Tres regresiones protegen colores, los 24 trazados originales y
  el tamaño RGBA de 1000×424. No cambia identidad, selección, EPG, numeración ni APK.

- **2026-10-02**: equivalencias BT/TNT UK verificadas con fotogramas reales antes de
  incorporarlas a los respaldos de TNT 1–4. Lista cerrada por país y nombre exacto;
  diez regresiones nuevas. BT SPORT ESPN/HD muestran TNT 4. TNT SPORTS ESPN muestra
  ESPN US y BT SPORT 3 HD rugby en vez del snooker de TNT 3: excluidos. Tres variantes
  BT sin fotograma siguen pendientes. TNT SPORT 1 entrega una placa de error que
  decodifica como video: añadir respaldos no demuestra detección automática de esa
  placa en la app. Evidencia y límites en `TVVOO_UK_EQUIVALENCIAS.md`. Sin cambios de
  selección, numeración, EPG, logos ni APK; VibeM3U 0.5.52 consume el mismo esquema.
  Validados: 266 Python + 34 JS + 3 JVM en verde; parser actual de la app acepta
  el JSON real con 2/2/2/3 respaldos para TNT 1/2/3/4. Sin prueba en la TV.

- **2026-10-02**: corregida la caducidad silenciosa de las variantes TvVoo. El runner
  renueva `generatedAt` cada 24 h aunque los alias sean idénticos; una consulta fallida
  no renueva la fecha de un documento sin cambios conservado como respaldo. Ocho tests
  nuevos cubren el caso de 8 días, el límite de 24 h, errores y fechas inválidas.
  No cambia la app, la selección de canales ni la agrupación por país.
- **2026-10-02**: TNT Sports 1, 2 y 4 sin guía. Una corrida de canales (19b0b2d) les borró
  la marca `x-vibem3u-selection="managed"` y la EPG solo incluía canales con esa marca. Ahora
  `epg_scope_extra_channels` usa la selección vigente (reconciliada) además de la marca, así una
  marca perdida no deja canales elegidos sin guía. Pendiente: averiguar qué paso del runner de
  canales borra la marca. TNT Sports 1 además está caído en la fuente en este momento.
- **2026-10-01**: respaldo real entre versiones del mismo canal TvVoo. TvVoo lista varias
  entradas por canal (MIX, MIX HD, MIX FHD, MIX (BACKUP)), cada una con fuente propia en Vavoo,
  pero la app solo probaba la elegida. `tvvoo_variants.py` publica las hermanas de cada canal
  elegido en `data/tvvoo-variantes.json` (VibeM3U 0.5.50 las usa como respaldo). Reglas por país
  acordadas con el usuario: SPORT ≠ SPORTS. Además, el aviso «Esta identidad ya está vinculada»
  desaparece: las versiones comparten la guía; Sky Sports Tennis suma su alias TvVoo en el
  catálogo. Quedan sin guía «SKY SPORTS F1» de los grupos DE e IT (sin hermana en su país).
- **2026-10-01**: sinopsis para la programación que no tenía. Las oficiales chilenas solo
  dejaban un texto técnico (se borra al publicar), así que TVN, Mega, CHV, Canal 13, La Red,
  24 Horas, T13, CHV Noticias, Meganoticias, NTV, DW Español y France 24 Español no tenían
  ninguna descripción. Ahora Zapping guarda la sinopsis real de cada programa y
  `donate_epg_descriptions` la pasa al programa publicado si coinciden hora y título. Prueba
  con la guía del día: 321 programas pasan a tener sinopsis. Se corrigió además que `dwe` de
  Zapping (DW Español) rellenaba la parrilla de DW English. Siguen sin sinopsis: Arirang
  (Zapping no la publica), Autentic History, M1, M2 y Telehit.
  - Misma fecha: la guía de Zapping da 403 desde GitHub, así que en Actions no llegaban
    sinopsis. Se suma Claro Video (`claro-sinopsis`), que sí responde desde Actions
    (verificado con una rama temporal ya borrada). Con Claro sola, en las próximas 24 h:
    TVN 12/17, Mega 14/18, T13 23/27, 24 Horas 24/30, 13 Cultura 21/25, DW Español 42/50,
    France 24 Español 93/108, Canal 13 10/16. Bajos: CHV, Meganoticias, NTV y La Red
    (Claro tiene otra parrilla para La Red).
- **2026-10-01**: TNT Sports 1–4 (TvVoo Reino Unido) agregados como canales 124–127 con
  `editor-core`. TvVoo publica varias variantes por número; se eligió la que hoy entrega
  video (HLS y segmento verificados): `TNT SPORT 1`, `TNT SPORT 2`, `TNT SPORTS 3`,
  `TNT SPORT 4`. Esas variantes se sumaron primero a `x-resolver-ids` de las filas del
  catálogo (`TNTSports1.uk`, `Vavoo.uk.TNTSPORTS2`, `TNTSports3.uk`,
  `Vavoo.uk.TNTSPORTS4`) para que la selección encuentre su fila y su EPG (EPGShare UK).
  TNT 2 respondió con cortes en las pruebas.
- **2026-09-30**: logo de Sky Sports Premier League con las proporciones del logo real en pantalla (foto del usuario, perspectiva corregida): bloque «Premier League» 727×136 centrado y león dentro del marco. Mismo archivo 870×377, mismo estilo blanco con marco que el resto de Sky.
- **2026-09-30 (estabilidad, tras una revisión externa de Sol)**:
  - `epg-pending.json` distingue `sin-guia`, `guia-corta` y `hueco`.
  - Highfly renueva la fecha de `highfly-live.json` cada 3 h (la app lo descartaba con más de
    24 h aunque los enlaces siguieran vigentes) y corre también al terminar canales y EPG,
    porque GitHub ejecutaba el cron de 30 min cada 4-6 h.
  - Búsqueda de una segunda fuente para TVN3, sin resultado.
- **2026-09-30**: `AGENTS.md` y este `ESTADO.md` pasan a ser la puesta al día obligatoria;
  punteros `CLAUDE.md`, `GEMINI.md` y `.github/copilot-instructions.md` para cualquier
  proveedor de IA. Codex y OpenCode leen `AGENTS.md` directo; `opencode.json`
  hace que OpenCode cargue también `ESTADO.md`.
- **2026-09-29**:
  - CHV: la oficial pasa a relleno detrás de Zapping y TecnoCentro (el noticiero aparecía como
    «Plan Perfecto»).
  - Mezcla general de fuentes por prioridad para todos los canales; la guía anterior solo
    rellena (6 h de pasado máximo); TVN y Mega pasan de ~29 h a ~73 h.
  - Respaldos que continúan guías cortas sin huecos ni duplicados: TecnoCentro continúa a
    Zapping en T13, CHV Noticias, NTV y Meganoticias; EPGShare continúa a DW; 13Go se
    redondea al minuto. Pendientes: de 12 a 4.
  - Runners por partes: canales por proveedor y EPG por fuente.
- **2026-09-28**:
  - Highfly: el runner publica el enlace directo vigente de cada canal (`highfly-live.json`).
  - TVN movió su reproductor fuera de `live.tvn.cl` (host nuevo `*.run.app`).
- **2026-09-27**:
  - EPG sin tope de 18 h (se integra toda la guía real, hasta 8 días).
  - Red Bull Chile vía `X-Forwarded-For` chileno (sin PC).
  - Cada fuente EPG en `epg_sources/<fuente>.py`, con fallos aislados.
  - Sky F1 vuelve a Highfly con alias TvVoo aparte.
  - `REGLAS.md` como documento único de reglas; contrato compartido de filas de proveedor.
  - Grupo propio de concurrencia para la EPG.
- **2026-09-26**:
  - Mantenimiento de canales solo sobre Lista 1.
  - EPG oficial → Zapping → TecnoCentro sin relleno técnico.
  - Editor con selección múltiple.
- **2026-09-25 y antes**: editor web local, logos históricos, Highfly y TvVoo gestionados
  desde el editor, listas 1 y 2.
