# ESTADO.md — Lista M3U: puesta al día para cualquier agente

> Léelo completo antes de trabajar, junto con `AGENTS.md` (cómo trabajar) y `REGLAS.md`
> (reglas vigentes de ambos proyectos). App hermana: `SPxMM3R1/vibem3u` (su `ESTADO.md`
> cubre la app). **Al terminar cualquier cambio, actualiza este archivo en el mismo commit**:
> la sección «Hoy» si cambió el estado y una línea nueva en «Bitácora».

Última actualización: **2026-10-03**.

## Hoy, en una mirada

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
- **Tests**: 269 Python (`python -m unittest discover -s tests -p "test_*.py"`) y 34 JS
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
