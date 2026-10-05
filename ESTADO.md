# ESTADO.md — Lista M3U: puesta al día para cualquier agente

> Léelo completo antes de trabajar, junto con `AGENTS.md` (cómo trabajar) y `REGLAS.md`
> (reglas vigentes de ambos proyectos). App hermana: `SPxMM3R1/vibem3u` (su `ESTADO.md`
> cubre la app). **Al terminar cualquier cambio, actualiza este archivo en el mismo commit**:
> la sección «Hoy» si cambió el estado y una línea nueva en «Bitácora».

Última actualización: **2026-10-05** (UTC).

## Hoy, en una mirada

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
- **Tests**: 292 Python (`python -m unittest discover -s tests -p "test_*.py"`) y 39 JS
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
- Mockups: HTML renderizado con Edge headless. Lo confiable es PowerShell con
  `Start-Process msedge.exe --headless=new --screenshot=... -Wait` y un `--user-data-dir`
  nuevo por captura.

## Bitácora (más reciente arriba)

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
