# ESTADO.md — Lista M3U: puesta al día para cualquier agente

> Léelo completo antes de trabajar, junto con `AGENTS.md` (cómo trabajar) y `REGLAS.md`
> (reglas vigentes de ambos proyectos). App hermana: `SPxMM3R1/vibem3u` (su `ESTADO.md`
> cubre la app). **Al terminar cualquier cambio, actualiza este archivo en el mismo commit**:
> la sección «Hoy» si cambió el estado y una línea nueva en «Bitácora».

Última actualización: **2026-10-08** (UTC).

## Hoy, en una mirada

- **Limpieza completa Nauta preparada y validada**: 533 revisados con resolver real de APK v0.5.81 y decodificación FFmpeg; tres rondas independientes para fallos, controles ESPN 1 Chile/DSports 2 HD correctos en las tres. 394 conservados, 139 retirados permanentemente (39 HTTP 404, 4 nombres ausentes y 96 placas de actualización, no señal válida). Fox Deportes (304) y HBO Xtreme (361) se recuperaron y se conservaron. Informe completo `NAUTA_CANALES_ELIMINADOS_20261008.md`, evidencia segura `contracts/nauta-validation-20261008.json`; snapshot inicial intacto. Layout/inventario/listas/presentación sincronizados, bajas excluidas contra reaparición, sin ocultar ni renumerar supervivientes. 253 filas anteriores/selección/presentación no Nauta intactas; EPG conserva alcance 46/0 Nauta. 303 Python (copia del contrato omitida por ruta, hashes iguales aparte), 41 JS, contrato 394 Nauta y bundle correctos. Proyección real con catálogo integrado de app: 394 Nauta/455 visibles/0 descartes. Sin cambios de app/APK (contraparte `e3d2ee2` / v0.5.81). Pendiente en esta entrada: push main y comprobar runner/estado remoto. Disponibilidad puntual desde PC, no garantía futura ni prueba de TV física.

- **Nauta publicado y comprobado después del runner**: importación `b33cebf`, runner `37718537821` success, estado generado `a5081dd`; Raw fijado al SHA coincide con listas/layout/presentación. Conservadas las 533 filas en prueba y números 87–619; proyección real de app: 594 visibles, 0 descartes. Pruebas Nauta repetidas después del runner: cuatro correctas; EPG 46/0 Nauta. Editor web `37718537777` success. APK 0.5.81/190 y firma/checksum ya verificados antes del catálogo. EPG automática `37718727029` en curso al comprobar, sin ampliar alcance; no se necesita para Nauta. Cierra los pendientes de las entradas siguientes; disponibilidad de todas las señales y TV física no demostradas.

- **APK Nauta publicada y verificada antes de este catálogo**: VibeM3U `e3d2ee2`, versión/tag `0ef0331` / `v0.5.81` (190); CI `37717793042` y Release `37718148346` success. Release pública no draft/prerelease, APK 2.720.775 bytes, SHA256 `dfb24e1a397aa4b029d41ba082414787beee0076ded5869e7c2c00258c1f2ca5`, descarga/firma compatible verificadas. Nuevas referencias requieren actualizar la TV a 0.5.81+. Publicar este catálogo ahora; comprobar estado remoto y conservación de las filas tras el runner. Sin prueba física local: ADB sin dispositivo y no hay ejecutable emulator en el SDK C: verificado.

- **Validación Nauta**: 301 Python (una prueba de copia omitida por ubicación del clon; hashes idénticos comprobados aparte), 41 JS y bundle temporal correctos. Parser real VibeM3U + catálogo integrado acepta 533 referencias, 0 incompatibles. Alcance EPG conservado en 46 canales (ningún Nauta). Java real + FFmpeg dieron contenido ESPN 1 Chile 360p24 y DSports 2 HD 720p60; TV Pública/South Park devolvieron placa de actualización, no señal válida. El resolver excluye temporalmente ese origen. Catálogo completo no significa todas las señales operativas; sin estabilidad ni TV física demostradas. Contraparte funcional VibeM3U `e3d2ee2`; entregar APK 0.5.81/190 antes de estas filas.

- **Nauta preparado 2026-10-07**: snapshot de 18 categorías/páginas, 536 recursos y 533 nombres exactos distintos (el proveedor varía entre consultas). 533 filas nuevas al final de Lista 1, en prueba/sin EPG, sin renumerar ni cambiar las filas anteriores o selección Highfly/TvVoo. URI internas públicas, sin enlaces/IDs opacos/credenciales. Snapshot `contracts/nauta-trial-channels-20261007.json`, contrato `nauta_reference.py` y tests; APK 0.5.81 debe estar publicada antes del catálogo. No se reintroduce CNCVerse. Publicación y prueba física pendientes en esta entrada.

- **France 24 inglés publicado y verificado**: cambio `1073380`, runner `37539066258` success, estado `c76d52f`; no modificó catálogo/streams ni membresía. Raw/blob iguales para ambas listas/layout/presentación, proyección app antes y después: 18 Español → 19 English, mismos 77 visibles y T13 respaldado. Editor web `37539066224` success. EPG automática `37539349779` disparada con el alcance habitual; inglés conserva prueba/sin EPG. Sin APK. Cierra el pendiente de la entrada siguiente.
- **France 24 inglés reubicado**: la fila existente activa/en prueba `France24.fr@English` pasa del 62 al 19, inmediatamente después de Español (18); Al Jazeera = 20, BBC = 21. `assignChannelPosition` desplaza +1 todos los demás activos con número anterior >=19, también Highfly/TvVoo y respaldo T13 (histórico 217, ahora 218); vínculos por identidad intactos. No duplica, no oficializa ni agrega EPG; estado de prueba, stream y logo conservados. Layout/presentación/Lista 1/alias/inventario sincronizados y selección idéntica. Históricos intactos, registro separado de inserción. 312 Python/41 JS, bundle/contrato y proyección real app 0.5.73 `94dd35b`: mismos 77 visibles, proveedor y respaldo correctos. Sin APK nueva. Pendiente en este punto: publicar y comprobar salida remota/runner.
- **Rwnd ya publicado y verificado**: código `45c217f`; workflow completo `37537954410` success; XML `43d110a`, generación 22:04:37 UTC. Raw fijado al SHA coincide con blob Git: solo 3 bloques Live, 0 descripciones/subtítulos/otros metadatos, 17,98 h futuras al verificar 22:05:31 UTC. El lector XMLTV real de app 0.5.73 muestra Live con sinopsis vacía. Sin APK nueva ni prueba física; caché de TV no observado, revalidación mínima de EpgRepository 5 minutos. Esta entrada cierra el pendiente de la siguiente; no se reparó Meganoticias/007 aquí.
- **Rwnd, continuidad sin EPG**: eliminada asociación errónea `us2 / Rewind.TV.us2`. El runner ya no copia programación fresca ni publicada para `RewindTV.cl@SD`; genera solo bloques `Live` sin sinopsis, subtítulos, categorías ni otros metadatos de programa. La guía reutilizada también se limpia y se excluyen donantes/bloqueos manuales. Cinco regresiones nuevas; 309 Python/41 JS. Sin modificar stream, logo, número, selección ni app; contraparte VibeM3U 0.5.73 `94dd35b`, sin APK ni commit hermano nuevo. Pendiente en este punto: publicar main, regenerar EPG y verificar XML remoto/lector real.
- **ESPN 2 Sur publicada y verificada**: código `58d95b4`; regeneración completa `37535307432` correcta; XML `a2b1a02`. GitHub Raw fijado al SHA y lector XMLTV real de app 0.5.73: 76 programas, más de 55 h futuras, a las 18:20 Chile `ESPN Compact` con descripción final masculina Premier Pádel Rotterdam 17:45–18:45. UTC 20:45–21:45 sin desplazamiento; identidad estable preservada. No APK nueva ni reproducción propia en TV afirmada. Esta verificación cierra el pendiente de publicación de la entrada siguiente.
- **ESPN 2 Sur (32), corrección de guía**: ambos alias TvVoo ES/AR usan `uy1 / [ESP2LS].ESPN.2.uy`. Su descripción de ESPN Compact anuncia final masculina Premier Pádel Rotterdam 17:45–18:45 Chile, consistente con foto del usuario de Tapia/Coello–Stupaczuk/Sanz a las 18:20 y torneo/primer set corroborados por FIP. Se contrastaron 51 registros ESPN en seis guías regionales: Chile anuncia fútbol; ESPN 2 HD UY anuncia tenis. No es prueba de país exclusivo ni cambio horario; sin fotograma nuevo del proveedor en este entorno. Retirado respaldo Bolivia no confirmado, última EPG publicada permanece como fallback. Tres regresiones; 304 Python/41 JS. Solo runner/test/docs; canal, identidad, selección, alias, números, resolutores y app intactos; contraparte VibeM3U 0.5.73 `94dd35b`. Pendiente en este punto: publicar código y regeneración EPG, verificar XML remoto y lector real.
- **EPG ESPN 5 ya publicada y comprobada**: código `00897ab`, XML `8196fd0`, ejecución completa `37403016586` correcta. 67 programas y más de 72 h futuras; actual Rumanía–Suecia 23–01 Chile, no boxeo. Lector EPG real de app 0.5.73 probado con ese XML: conserva identidad y horario absoluto, muestra UEFA Nations League. Intento parcial anterior `37402866106` conservó la EPG porque había huecos/cobertura insuficiente en la base; se recuperó con regeneración completa, sin tocar lógica de renovación ni inventar programación.
- **ESPN 5 (35), EPG corregida**: `WinPlusFutbol.co@Direct181` pasa a `uy1 / ESPN.5.HD.uy`. La anterior `[ESPN5SD].ESPN.5.uy` publicaba boxeo/títulos portugueses y no coincidía con la secuencia observada Francia–Bélgica → Rumanía–Suecia. Guías UY1/CO1 coinciden 21–23 / 23–01 Chile; fotograma ESPN 5 en español con previa de Rumanía. No cambio de stream, identidad, logo, número ni región declarada; no offset horario. Dos tests de mapeo y reemplazo de guía anterior, 301 Python/41 JS. Publicar código y regenerar `epgshare` en GitHub, comprobar salida; app 0.5.73 `94dd35b` no requiere APK nuevo.
- **APK compatible verificado antes del catálogo**: VibeM3U `94dd35b` / tag `v0.5.73`, Android CI `37399927443` y Release `37400308175` verdes; firma compatible comprobada por workflow, Release pública no draft/prerelease, APK 2.717.639 bytes, SHA-256 `10cb0b63f150c1c71cb8fff465d949cdb70bdb143a78d647c78f3d8e265c6f4c`. Instalar 0.5.73 para usar el 217 como respaldo; no se afirma reproducción en TV física. La publicación de catálogo usa commit separado y se verifica después del runner.
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

- **2026-10-08, depuración Nauta autorizada**: auditoría completa 21:01–21:07 UTC, sin guardar URLs/IDs opacos/headers/credenciales. Prueba HLS y vídeo, descartando placas mediante huellas de cuatro imágenes con título visualmente examinado. 394 disponibles / 139 bajas comprobadas tres veces; entradas retiradas, no ocultas, numeración y resto editorial preservados. Evidencia completa y lista pública de bajas versionadas, seis tests Nauta incluidos en 303 Python; 41 JS y parser/proyección real de app correctos. Orden runner → app → publicación y verificación de runner automático; app sin commit nuevo ni release. Un intento diagnóstico de parser con `resolver-catalog.json` remoto excedió el límite de aliases de la app; la app carga exclusivamente `app/src/main/assets/resolver_catalog.json`, que pasó la comprobación. No se afirma fallo de producción por ese diagnóstico ni se modifica fuera de alcance.

- **2026-10-07, cierre remoto Nauta**: catálogo `b33cebf` publicado después del APK, editor `37718537777` y runner completo `37718537821` verdes. `a5081dd` conserva 533 referencias, estado en prueba, números y layout; Raw y proyección de clases reales comprobados otra vez. EPG conserva 46 canales sin Nauta; runner automático de EPG disparado, no forma parte de la validación de nuevos canales en prueba. App contraparte `e3d2ee2`, tag `0ef0331`, documentación `2bfa14b`. Este cierre documental se publica también, sin cambio de app/catálogo/EPG.

- **2026-10-07, compuerta APK cumplida**: Release Nauta `37718148346` success; APK exacta descargada de GitHub y comprobada con apksigner/aapt/SHA256 (0.5.81/190, firma estable). Se habilita publicación de las 533 filas en el commit separado de Lista M3U, manteniendo la EPG previa y todos los nuevos en prueba.

- **2026-10-07, compatibilidad Nauta**: 301 Python/41 JS, copia compartida verificada por hash, contrato de resolutores válido (533 Nauta). Parser y proyección publicados de VibeM3U reconocen 533 Nauta, números únicos 87–619, total 594 visibles; ningún proveedor descartado. App funcional `e3d2ee2`, versión/tag `0ef0331` / 0.5.81/190, Android CI `37717793042` success en compilación y pruebas instrumentadas. Release `37718148346` se comprueba antes de subir este catálogo. No tocar la selección Highfly/TvVoo ni ampliar EPG: 46 en alcance, todos los nuevos en prueba.

- **2026-10-07, Nauta**: importación completa autorizada junto a resolver Android. Nuevas filas mediante `editor-core.addRow` y presentación por `buildPresentationOverrides`; filas previas intactas. Los nombres exactos repetidos son alternativas de resolución. IDs opacos, headers y URLs viven solo en RAM; `notWebReady` no equivale a DRM en Android. Orden de validación runner → app, publicación APK compatible → Lista 1; EPG actual intacta.


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
- **2026-10-05**: a pedido del usuario, el 81 (TVN3 [Mediastream], `TVN3.cl@Mediastream`, en prueba) va
  a la papelera: era el mismo stream de TVN3 (011) sin el sufijo `?PlaylistM3UCL`.
- **2026-10-05**: respaldos directos múltiples (`backupm3u` en el layout, app 0.5.72): lista ordenada
  de tvg-id de otras filas M3U de la misma señal que la app prueba después de la propia (y de la
  preferida, si hay). Editor: `setBackupM3u`, validación (hasta 8, sin repetir, filas M3U
  existentes), sección «Respaldos directos» en el inspector y etiquetas «+ N respaldos» / «Dentro
  de NNN». A pedido del usuario: TVN (01) ← 73 y 74; Canal 13 (004) ← 85 (después del 079 y su
  propia señal). El runner no cambia: las filas siguen publicadas en Lista 1 (en prueba) y la app
  las oculta.
- **2026-10-05**: a pedido del usuario, el 38 (Fox Sports 1, `FoxSports1.us@Direct`, en prueba) va
  a la papelera con `setRowState` del editor; el resto conserva número y orden.
- **2026-10-05**: a pedido del usuario, el 120 (Sky Sports F1 UK de TvVoo, agregado el 04-10 para
  comparar con Highfly; daba lo mismo) va a la papelera con `setRowState` del editor. Los activos
  conservan número y orden; las filas en papelera que estaban intercaladas quedan al final (la
  convención del editor: activos, ocultos y papelera).
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
