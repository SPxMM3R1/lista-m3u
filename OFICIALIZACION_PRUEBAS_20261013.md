# Oficialización de pruebas — 2026-10-13

Pedido «Todas las pruebas»: 247 activos en prueba de Lista 1 pasan a definitivos sin mover ni borrar filas ni alterar respaldos; 38 referencias Nauta exactas se agregan a la excepción cerrada (42 con las cuatro históricas). A 2026-10-15, los logos comprobados son 234 y 13 siguen pendientes. El contrato registra 93/247 guías con asignación confirmada y 154 pendientes; de las 93, GitHub publica las 62 anteriores y las 31 `PublicDirect` materializadas por las corridas `38667200138` (commit `890b27a`) y `38668568796` (commit `7058038`). La GitHub Contents API verificó sus 31 fragmentos, ausencia de esos IDs en `epg-pending.json` y 12 h o más. No afirmar EPG/logo completo: definitivo es estado editorial, no prueba de guía/estabilidad. Sin Live de relleno, canales nuevos, selector Android, cambios de app ni APK. Contrato `contracts/trial-officialization-20261013.json`; pendientes por identidad en esta bitácora. Mantener futuras altas en prueba y no oficializar referencias Nauta fuera de las 42 exactas sin pedido explícito.

## Publicación EPG dirigida y reparación del runner (2026-10-15)

La corrida programada `Actualizar EPG` `38667200138` publicó `890b27ac1c492ef2dba2a21a6eb4927bb09c083e`; una segunda corrida `workflow_run`, `38668568796`, publicó `70580389b780701243abe8a002feef4f6abacf4b`. En la verificación más reciente, al instante `2026-10-15T01:59:25Z`, los 31 IDs `PublicDirect` tienen 2.231 eventos, cobertura continua de 22,31–80,01 h y 0/31 pendientes. La GitHub Contents API cotejó índice, pendientes y los 31 fragmentos con `origin/main`; esto no afirma que se haya comprobado la caché CDN de Raw.

El refresh manual anterior `38664866636` falló porque `targeted_update.apply_epg()` usaba todos los IDs de `channel-catalog.m3u` como esperados, aunque esa lista es el inventario canónico y contiene canales fuera de EPG. El runner normal genera solo `epg_scope_channels()`; por eso la validación parcial reclamaba cientos de nodos ajenos. El fix en `targeted_update.py` valida el alcance publicado, solo el subconjunto afectado y los horizontes propios del runner. Sus 24 pruebas dirigidas, la suite local (365 tests, 19 omisiones previstas), JavaScript (42/42) y una reproducción real de esos 31 canales en una copia temporal pasaron. Ese código de reparación sigue pendiente de commit/publicación; la guía de estos 31 no necesita otro despacho ahora.

## Alcance y límites

Usuario: «puedes pasar todos los canales ... a definitivo y darles logo y EPG»; aclaración: «Todas las pruebas» = todos los activos en prueba de Lista 1, no ocultos/papelera ni todo el inventario.

Matched means exact curated national/regional source with continuous 12h at validation; Total Conexion region is supported by prior SDT/operator evidence. A FreeEPG Guatemala feed was fetched on 2026-10-14; its current XML had 155 channel IDs, including exact current IDs for Canal 13/Trecevisión, Canal 3, Canal 7/Televisiete, Canal Antigua and Guatevisión, each with 109.39–110.14 continuous hours. The five local names explicitly contain GUA; no region was inferred from IP. The FreeEPG country page lists 160 channels and itself cautions there is no completeness guarantee: https://free-epg.de/countries/gt. The feed also had stale duplicate IDs for four channels; only the IDs with continuous current data were mapped. This is not proof of synchrony of every programme in physical TV. Other unknown regional feeds remain pending; no other region is assigned by similarity and no continuity Live is fabricated. Definitive remains an editorial state, not proof of availability or complete guide.

Región de Total Conexión: SDT/operador colombiano documentado en la investigación del 12-10, no inferida por geolocalización de IP. Para canales panregionales de Discovery se compararon CL/MX y coincidieron todos los tramos/títulos de las próximas 12 h. No es prueba contemporánea del contenido de todos los programas en cada señal ni TV física. Logos reales PNG/SVG, archivos sin modificar; referencias/hashes en el contrato. No se publican tokens ni enlaces temporales.

Validación complementaria local y publicación remota parcial completadas el 2026-10-14. El estado editorial «definitivo» no acredita que las 247 filas tengan guía ni logo: GitHub Raw confirma 234 logos; quedan 13 pendientes. La publicación EPG anterior tenía 57 mapas y 190 pendientes. La primera continuación visual agregó cinco asignaciones: el contrato llegó a 62 guías y 185 pendientes; run `38613423120` publicó salida `09e19e6` y Raw confirmó los cinco IDs en `epg.xml` y fuera de `epg-pending.json`.

## Seguimiento de publicación — 2026-10-14

### Continuación visual local — diez nuevas coincidencias; publicación pendiente

Se volvieron a revisar las capturas originales y el XMLTV `epgshare` generado a las 18:14 UTC. El emulador está en GMT; las horas XMLTV con `-0500` se convierten primero a UTC. Las nueve asignaciones verificadas desde ese corte quedan así:

| N.º | Señal → guía | Evidencia y normalización XMLTV | Cobertura continua |
| ---: | --- | --- | ---: |
| 372 | Disney → `cl / Canal.Disney.Channel.(Chile).cl` | Captura `163-channel372-decoded.png`, 19:33 UTC, logo Disney Channel y *Star vs. Las Fuerzas del Mal*. XMLTV 14:30–14:59 `-0500` = 19:30–19:59 UTC; mismo título. Guía equivalente, no región física. | 52,45 h |
| 378 | ESPN 2 → `ar1 / Canal.ESPN.2.(Bolivia).ar` | Captura `176-channel378-later.png`, 19:43 UTC, marcador MCI 0–3 PSG, 39:44. XMLTV 13:40–15:55 `-0500` = 18:40–20:55 UTC; Manchester City vs. Paris Saint-Germain. Guía equivalente, no región física. | 52,78 h |
| 380 | ESPN 3 → `mx1 / ESPN.3.mx` | Capturas `179-next-channel-confirm.png` y `180-channel380-later.png`, 19:47 UTC; ESPN 3 VIVO, segmento Step to It sobre Dylan Harper/Spurs. MX1 lleva NBA Today 14:00–15:00 `-0500` = 19:00–20:00 UTC. Guía equivalente. | 57,22 h |
| 381 | ESPN 3 HD → `mx1 / ESPN.3.mx` | Capturas `181-next-channel-confirm.png` y `182-channel381-later.png`, 19:49 UTC; ESPN 3 VIVO, segmento Step to It sobre Kevin Durant/Rockets. Mismo bloque MX1 NBA Today. Guía equivalente. | 57,18 h |
| 391 | ESPN 6 · señal 2 → `co1 / ESPN.6.HD.co` | Captura `202-channel391-osd.png`, 20:16 UTC; el OSD confirma canal/número y el fotograma decodificado muestra gráfica UEFA y SHK 1–1 AEK a 57:42. CO1 cubre `Fútbol UEFA Champions League` 18:40–21:00 UTC y la descripción identifica Shakhtar y AEK; parrilla continua hasta 13:00 UTC del 15-10. Coincidencia del evento; no se infiere región física. | 16,73 h |
| 392 | France24 → `fr / France.24.Espanol.fr` | Captura `204-channel392-later.png`, 20:25 UTC; imagen decodificada con rótulo español «INVITAD@ DEL…». XMLTV `France.24.Espanol.fr` indica «Invitado del día» 20:21–20:30 UTC y cobertura continua 14,08 h. Coincidencia del programa; no se infiere región física. | 14,08 h |
| 396 | H2 → `cl / Canal.History.2.(Chile).cl` | Captura `213-channel396-first.png`, 20:37 UTC, logo H2 y rótulo «EL CÓDIGO DE DIOS». CL ofrece el mismo título 20:05–21:40 UTC; MX1, AR1, CO1, PA1 y GT muestran ese bloque y la misma secuencia. Se usa CL solo como guía equivalente, no como inferencia de región física. | 28,32 h |
| 397 | HBO Xtreme → `cl / Canal.HBO.Xtreme.cl` | Capturas `216-channel397-first.png` y `218-channel397-second-frame.png`, 20:44 UTC; logo HBO Xtreme y escenas distintas de película. La parrilla CL identifica `Te van a matar` (19:20–20:58 UTC); MX1, AR1, PA1 y GT comparten la secuencia/título y CO1 usa el título inglés. CL es guía equivalente, no inferencia de región física. | 58,13 h |
| 398 | History Channel → `pa1 / Canal.History.(Panamá).pa` | Capturas `220-channel398-after-wait.png` y `221-channel398-confirm-current.png`; logo History y rótulo de emisión «MISTERIOS INEXPLORADOS CON DANNY TREJO» en el evento XMLTV exacto 20:55–21:45 UTC. Otros feeds regionales History muestran programas distintos a esa hora; PA1 se usa como guía equivalente, no inferencia de región física. La imagen posterior se congela, así que la asignación no acredita estabilidad. | 27,42 h |
| 406 | A3Cine → `es / A3CINE.es` | Capturas `243-channel406-first.png` y `244-channel406-after-wait.png`; la segunda muestra una composición de escena que coincide con el fotograma descrito para *Ninette* en [Fancine 2005](https://ibdigital.uib.es/greenstone/sites/localsite/collect/fancine/index/assoc/Fancine_/2005_008.dir/Fancine_2005_008.pdf); la ficha oficial de [ICAA](https://infoicaa.mcu.es/CatalogoICAA/es-es/Peliculas/Detalle?Pelicula=126004&q=true) confirma película, año y reparto. XMLTV `A3CINE.es` ofrece *Ninette* 21:00–23:00 UTC al capturar; 84,38 h continuas futuras. Coincidencia visual exacta; no se infiere región física. | 84,38 h |

Estas diez asignaciones verificadas desde el corte anterior se añaden a los ocho confirmados localmente en el lote anterior (#309, #325, #329, #340, #341, #347, #348 y #353). En aquel corte el contrato quedó en 80 asignadas/167 pendientes; 62 estaban en Raw y 18 locales. Desde entonces se agregaron dos coincidencias locales más, descritas abajo. El uso explícito del offset es obligatorio: comparar solo los primeros 14 dígitos sin zona desplaza el evento cinco horas y puede falsear una coincidencia.

**Revalidación de una guía publicada — #410 RCN Novelas:** capturas 256–257 (21:54 UTC) muestran movimiento entre fotogramas y el OSD dice *Lala's spa*, 21:00–22:00 UTC, seguido de *Así es la Vida* a las 22:00. El `epg.xml` de `origin/main` contiene el mismo programa a la misma hora en `co1 / RCN.Novelas.co`, y mantiene horarios contiguos hasta las 13:00 UTC del 15-10 (15,08 h futuras). La asignación ya está publicada; esta prueba confirma su correspondencia visual.

### Dos coincidencias locales nuevas — #416 y #417 Studio Universal

Las capturas 272–274 muestran los créditos animados de Studio Universal; la secuencia continúa en la versión HD #417, donde la captura 275 acredita explícitamente canciones de *Spider-Man: Into the Spider-Verse*. La captura 273 confirma por OSD el canal #416; la 276 confirma #417 (con un reintento HLS al mostrar el OSD). El XMLTV configurado `co1 / Studio.Universal.co` ubica *Spider-Man: Un nuevo universo* de 20:15 a 22:25 UTC del 14-10, por lo que cubre los fotogramas de 22:06 (#416) y 22:09 (#417). La secuencia XMLTV continúa sin huecos hasta las 11:00 UTC del 15-10: 12,90 h desde #416 y 12,85 h desde #417. Son coincidencias de programa/guía, no prueba de región física ni de estabilidad prolongada. Se añaden al contrato y a `epg-overrides.json`; todavía no están publicadas.

### #418 TBN Enlace queda pendiente

Las capturas 281–285 muestran primero un anuncio de Ancient Nutrition dirigido a Costa Rica y luego una cortina de Enlace que dice «Desde Bogotá, Colombia / 11:30 AM». La captura 282 confirma por OSD el canal #418 y solo la categoría «Misceláneos»; tras unos 40 segundos no apareció un título de emisión. No hay fuente XMLTV TBN/Enlace configurada para contrastar un título exacto y la cortina no identifica el programa ni la procedencia del feed. Se conserva `regional_feed_not_identified`; no se asigna guía por la IP ni por el texto regional de la cortina.

### Coincidencia local #419 — TNT Novelas

La señal falló en el primer intento con el error 4007003 (captura 288); al reintentar, el video volvió a decodificar y la captura 290 (22:31 UTC) muestra TNT Novelas y el rótulo en pantalla «QUIEREME SIEMPRE», mientras el OSD confirma el canal #419. El XMLTV configurado `co1 / TNT.Novelas.co` anuncia *Quiéreme siempre* entre 21:50 y 22:43 UTC, cubriendo el fotograma; la programación contigua llega hasta 00:36 UTC del 17-10, 50,08 h desde la validación. CL1, MX1, AR1 y PA1 también contienen el mismo título/evento vigente, por lo que el cotejo no identifica la región física. Se conserva CO1 de manera coherente con la asignación curada del TNT Novelas HD #315; esto es coincidencia de guía, no prueba de origen geográfico ni de estabilidad (el reintento sí queda documentado). La asignación local sigue sin publicar.

### #420 TD+2 HD CR y #421 TD+HD CR permanecen pendientes

#420: capturas 291–293 muestran un panel de conversación deportiva con una gráfica «VISION»; el OSD de la 292 confirma canal 420 y categoría «Deportes», pero no da el título del programa. #421: capturas 294–296 muestran el estudio TDMAX y la gráfica «EL ROL DEL MEDIOCENTRO»; el OSD de la 295 confirma canal 421 y la categoría, pero no demuestra que el texto gráfico sea el título de la emisión completa. El runner no configura una guía XMLTV costarricense/TD+/TDMAX con 12 h futuras para validar cualquiera de las dos. Se conservan pendientes, sin asignar guía solo por categoría o identidad visual del canal.

### #422 TLC permanece pendiente

Capturas 297–300 muestran una escena dramática sin elementos identificadores y después anuncios; la captura 298 OSD confirma canal #422 y únicamente «Misceláneos», con reapertura HLS. Hay siete XMLTV regionales candidatos, pero sin título exacto visible no es posible escoger uno de forma defendible. No se completa por género ni por similitud de escenas.

### #423 Discovery Channel señal 2 y #424 TNT Series permanecen pendientes

En #423, capturas 301–303 muestran una mujer con sombrero blanco, un primer plano con marca TNT y después un anuncio de Protex. La captura 302 confirma por OSD el número 423 y solo la categoría «Misceláneos»; la marca TNT contradice la etiqueta Discovery, pero no identifica por sí sola el feed ni su parrilla. De cuatro XMLTV regionales candidatas no se puede elegir una sin título exacto de emisión y 12 horas futuras continuas.

En #424, capturas 304–306 muestran primero publicidad y luego una escena doméstica sin rótulo/título identificable. El OSD de la captura 305 confirma TNT Series y únicamente la categoría «Películas». Hay cinco parrillas regionales candidatas, ninguna demostrable con el fotograma observado. Ambos canales siguen `regional_feed_not_identified`; no se asigna por IP, logo o categoría.

### Coincidencia local #425 — Telemundo

La captura 307 (22:54:10 UTC) muestra la marca de programa CC/Caso Cerrado y el cintillo «DEMANDANTE Dayamit»; la 308 conserva el mismo segmento. El OSD de la captura 309 confirma el canal 425 y la categoría «Misceláneos», aunque la reproducción ya estaba renegociando el segmento inicial. El XMLTV `co1 / Telemundo.co` ubica *Caso cerrado* de 22:10 a 23:05 UTC y entrega 73,18 h continuas desde el fotograma. CL1, MX1 y PA1 también tienen el bloque equivalente, por lo que no se infiere región física. El feed US2 `Telemundo.Satellite.Feed.us2` no coincide a esa hora (lista «Noticias Telemundo» de 22:30 a 23:00); para el ID público directo #425 se incorpora el override local CO1. No se presenta como prueba de estabilidad del stream, que más tarde mostró una reapertura HLS.

### Coincidencia local #426 — Telemundo HD

Las capturas 310–312 muestran el mismo estudio, presentadora y participantes que el canal SD #425. El OSD de 311 confirma Telemundo HD #426 a las 23:00 UTC, y la 312 a las 23:01 UTC mantiene el juicio; el #425 había mostrado la marca CC/Caso Cerrado y el cintillo «DEMANDANTE Dayamit» seis minutos antes. `co1 / Telemundo.co` mantiene *Caso cerrado* hasta 23:05 UTC y 73,07 h de programación continua desde la validación; CL1/MX1/PA1 contienen bloques equivalentes. US2 presenta *Top Chef VIP* desde las 23:00 UTC y contradice el vídeo. Se aplica la misma fuente coincidente al ID HD, sin inferir región física ni estabilidad del stream.

### #427 Televida RD permanece pendiente

Capturas 313–315 muestran una misa católica con el logo de Televida. El OSD de la 314 confirma el canal #427 y solo la categoría «Misceláneos» (23:04 UTC); no se ve título ni nombre de segmento. El inventario XMLTV curado actual arroja cero fuentes candidatas dominicanas para Televida. Se mantiene `regional_feed_not_identified`: no se asigna «Santa Misa» por inferencia ni se genera continuidad artificial.

### #428 Universal Comedy HD permanece pendiente

Capturas 316–319 y la captura de estado actual confirman por OSD el canal #428; la categoría es solo «Películas». El primer intento muestra el error 5009005 y el reintento alcanza a decodificar una escena policial a 0,9 FPS; los créditos muestran únicamente al productor Richard H. Prince, no el nombre del programa. MX1 programa *Superstore* entre 22:55 y 23:20 UTC, pero no hay elemento visual que permita identificarlo como el contenido del fotograma. Con tres candidatas regionales y reproducción breve/inestable, no se confirma ninguna parrilla; se mantiene `regional_feed_not_identified`, sin asignar por marca, categoría, IP ni crédito parcial.

Al cierre completo de esta auditoría se compararán los registros de programación XMLTV normalizados en todo el horizonte disponible; el usuario pidió recibir pares cuya guía completa sea exactamente idéntica para evaluar respaldos uno a uno. Esta comparación no autoriza a cambiar `backupm3u` ni fusionar filas.

### Coincidencia local #429 — Universal Crime HD

El OSD de la captura 321 confirma #429 a las 23:14 UTC. La secuencia de capturas 322–324 muestra publicaciones de Facebook con los nombres Jim Bidwell y Kristen Wagner, las oficinas administrativas de Monroe County y una ficha forense de Kristen Wagner que indica muerte por ahorcamiento y Stroud Township/Crowe Road. El clip oficial de [Oxygen identifica el caso de Kristen Wagner y Jim Bidwell como *Accident, Suicide, or Murder*, temporada 4, episodio 16](https://www.oxygen.com/accident-suicide-or-murder/season-4/episode-16/videos/kristen-wagners-sister-uncovers-facebook); su [explicación oficial confirma los detalles del depósito de chatarra y la autopsia](https://www.oxygen.com/accident-suicide-or-murder/james-bidwell-killed-kristen-wagner-why-case-explainer).

La XMLTV `uy1 / [UNICR].Universal.Crime.uy` pone *Accidente, suicidio o asesinato* / *Escena del crimen cargada* entre 22:30–23:15 UTC y el mismo programa / *Secretos en el depósito de chatarra* entre 23:15–00:00 UTC, en línea con el caso visible. La parrilla real continúa sin huecos hasta las 12:00 UTC del 15-10: cobertura futura de 12,77 h desde el OSD de 23:14. MX1 lista *Parejas asesinas: Jennifer Smith y Dale Moneypenny* y US2 *Columbo: Short Fuse* a esa hora; ambos se descartan por tratarse de otros casos. Se añade override local UY1 por coincidencia de título/caso, sin inferir ubicación física ni estabilidad. Capturas 323–326 registran reapertura HLS y errores 5009005/3005416; la guía queda asignada, pero el stream no se considera estable.

### Coincidencia local #430 — Universal Premiere HD

El OSD confirma el #430 en la captura 328 (23:20 UTC), y de nuevo en la 331 (23:21 UTC). Las capturas 329 y 332 muestran una chaqueta con identificación FBI y un agente; la captura 334 (23:24 UTC) enseña un tablero de caso: Keith Edmonds, ciudadano británico desaparecido, profesor retirado de Bristol, y una investigación de una estafa romántica en línea que atraía a hombres mayores al extranjero. El resumen de [FBI: International S4E5, «El futuro es promisorio»](https://tv.apple.com/mx/episode/el-futuro-es-promisorio/umc.cmc.5ffwegcxttj858m3t86nfsp3d) describe una trama de secuestro transnacional originada en una aplicación de citas y la investigación del Fly Team; coincide con la evidencia narrativa visible.

De las tres candidatas catalogadas, solo uy1 / [UNIPR].Universal.Premiere.uy lista FBI: International / El futuro es promisorio a las 23:15–00:00 UTC. MX1 Canal.Universal.Premiere.mx y UY1 [UNIPRMH].UNIPRMH.uy listan House MD / House M.D. a la hora ancla, incompatibles con el caso FBI. La guía UY1 continúa en bloques reales contiguos de 45 minutos hasta las 13:30 UTC del 15-10: 14,15 h futuras desde la captura OSD 331. Se añade el override UY1 por coincidencia del caso y del episodio, sin inferir región física. La captura 333 muestra que luego el reproductor falló con 3005416; esta asignación no afirma estabilidad del stream. Evidencia y capturas 327–334 en outputs/epg-audit-20261014-followup/.

### Coincidencia local #431 — Universal Premiere O HD

Las capturas 335–336 confirman por OSD el canal #431 a las 23:26–23:27 UTC y muestran a Hugh Laurie como Gregory House dentro de una escena de House M.D.; el logo de emisión dice Universal Premiere West. La XMLTV UY1 [UNIPRMH].UNIPRMH.uy lista House M.D. / El regreso entre 23:15–00:00 UTC. MX1 Canal.Universal.Premiere.mx también lista House MD en el mismo bloque; la variante UY1 incluye subtítulo de episodio y ofrece una secuencia real sin huecos cada 45 minutos hasta las 13:30 UTC del 15-10 (14,07 h desde el OSD de 23:26). Se asigna UY1 por la coincidencia visible del programa y el detalle actual de su guía, no por inferencia de región. El fotograma no permite verificar por separado el subtítulo El regreso, por lo que queda registrada esa limitación. Capturas 337–338 muestran que luego el stream falló con 3005416 y revalidó el segmento inicial; no se afirma estabilidad.

### #432 Universal permanece pendiente pese a identificar el episodio

Las capturas 339/342 fijan el OSD #432 a las 23:29–23:30 UTC; la 343 decodifica el crédito final «Cassie Reyes and Sean O'Brien» con dirección en Brooklyn. NBC/Peacock identifica ambos personajes en *Law & Order: SVU* S26E19, *Play with Fire Part 2*. El candidato UY1 `[UNTVAR].Universal.TV.uy` ofrece *La ley y el orden: Unidad de Víctimas Especiales / Apertura*; la ficha oficial distingue *Aperture* (S26E21) de *Play with Fire Part 2* (S26E19), por lo que «Apertura» es otro episodio. Las otras cuatro candidatas UY1 `[UNTVM]`, MX1, CO1 y PA1 proponen *Chicago Fire*. Se registra `no_exact_current_programme_match` y no se asigna una guía aproximada. La captura 333 documenta el fallo HLS posterior.

### Coincidencia local #433 — Univision HD

Capturas 349–351 mantienen el canal #433; la 351 muestra el logo Univision y los créditos finales «Yigael Yadin», «Roger Montes» y «Pancho Tello». Los créditos de la serie identifican *La historia de Juana*; UY1 `UNIVISION.HD.uy` y CL `Canal.Univision.(Chile).cl` muestran el título vigente 23:00–00:45 UTC y la misma secuencia continua hasta 15:00 UTC del 15-10: 15,43 h futuras desde el OSD 23:34. Se selecciona UY1 por su identidad exacta «UNIVISION HD» y la coincidencia del programa; CL corrobora el horario equivalente, sin inferir región. US2 `Univision Network HD` lista *La rosa de Guadalupe* y se descarta. Se confirma la serie, no un subtítulo de episodio. La imagen decodifica, pero el reproductor indica 0,6 FPS/reintento 3/3: no se afirma estabilidad. Referencias: [créditos de la serie](https://www.imdb.com/es-es/title/tt31511583/fullcredits/) y [ficha oficial de Univision](https://www.univision.com/shows/la-historia-de-juana/la-historia-de-juana-personajes-actores-elenco-novela-univision).

### Coincidencia local #438 — La Liga

Las capturas `370-channel438-start.png` y `371-channel438-osd-anchor.png` muestran el hashtag `#AlavesAtleti`, el marcador Alavés 1–1 Atlético al minuto 58:26 y el OSD #438 a las 23:54 UTC del 14-10. MX1 `Canal.Sky.Sports.16.mx` contiene exactamente Deportivo Alavés–Atlético de Madrid entre 23:00 y 01:00 UTC; a continuación da Barcelona–Getafe, resúmenes y partidos de LaLiga sin huecos hasta las 12:00 UTC del 15-10. Cobertura futura calculada en la fuente: 12,12 h. Se añade override local por coincidencia del evento; no se infiere la región física ni estabilidad.

### #442 A&E-IXP permanece pendiente

Capturas 376–382 sitúan el OSD a las 00:28–00:30 UTC del 15-10. La 379 solo muestra una promo de *El precio de la historia*; la 381 contiene imagen muy dañada, reintento y un rótulo parcial que parece «¿Quién da más?», y la 382 termina con el error 3004404. Las cinco fuentes A&E disponibles se contradicen en el programa vigente: CL/CO1/PA1 indican *¿Quién da más?* (CL añade Miami; CO1/PA1, *La pista de Barry*), mientras MX1/UY1 tienen *Escuadrón de homicidios*. La promo no identifica el programa en emisión y el fallo impide una segunda comprobación; permanece `no_exact_current_programme_match`, sin asignar por IP.

### Coincidencia local #443 — AMC-IXP / *RoboCop* (2014)

Las capturas `383-channel443-start.png` y `385-channel443-followup.png` muestran la marca AMC y, en la primera, los nombres John Lake y Andre Daniels sobre una pantalla CCTV; el OSD de la segunda confirma #443 a las 00:32 UTC del 15-10. La identificación de esos dos personajes corresponde a *RoboCop* (2014), según los créditos de reparto de [IMDb](https://www.imdb.com/title/tt1234721/). La guía CO1 `AMC.co` programa *RoboCop* de 22:55 UTC del 14-10 a 01:00 UTC del 15-10, seguido de eventos XMLTV contiguos hasta las 13:00 UTC; son 12,47 h futuras. Las guías MX1/UY1 anuncian *Rocky V*, y la AMC Series MX1 contiene otra serie, incompatibles con los nombres y la escena del fotograma. Se añade el override CO1 como guía coincidente, sin inferir ubicación. El player mostró reapertura/reintento HLS; esta asignación no acredita estabilidad.

### Coincidencia local #444 — Animal Planet-IXP / *El acuario*

La captura `389-channel444-later.png` confirma el OSD #444 a las 00:39 UTC del 15-10, el logo Animal Planet Discovery y el rótulo de emisión «el acuario». La fuente CL `Canal.Animal.Planet.(Chile).cl` tiene vigente *El acuario / El trato de la foca* entre 00:36 y 01:24 UTC, y parrilla XMLTV real contigua hasta 13:24 UTC (12,75 h futuras desde la captura). AR1 y PA1 presentan la misma programación; CO1/UY1 también identifican el título y episodio, aunque sus límites horarios están corridos unos 18 minutos; MX1 muestra otro programa y se descarta. Se registra CL como horario equivalente por título/episodio y continuidad, sin inferir la región física del stream. El fotograma está visiblemente degradado; el mapeo no certifica estabilidad de reproducción.

### Coincidencia local #446 — Cinemax-IXP / *Master Z: El legado de Ip Man*

La captura `395-channel446-start.png` confirma OSD #446, «Películas», a las 00:47 UTC del 15-10. `396-channel446-retry.png` muestra la escena final de una comida entre tres personajes; `397-channel446-later.png` presenta el bumper «A continuación: Ip Man 4: El final». La identificación del título actual es una inferencia visual específica: la sinopsis de *Master Z: The Ip Man Legacy* concluye con Tin-Chi, Julia y el hijo compartiendo una comida, y XMLTV PA1 coloca *Master Z El legado de Ip Man* inmediatamente antes de *Ip Man 4 El Final* en el mismo horario (22:36–00:49 y 00:49–03:00 UTC). CL, CO1, GT y MX1 corroboran la misma secuencia, aunque con límites horarios distintos; el bumper próximo encaja mejor con el cambio PA1/GT a 00:49. La guía PA1 ofrece programación contigua hasta 15:09 UTC, 14,37 h futuras desde el OSD. Se escoge como calendario equivalente, no como afirmación de región física. La reproducción se reabrió al menos una vez y la asignación no certifica estabilidad. Referencia del final de la película: [sinopsis de Master Z](https://en.wikipedia.org/wiki/Master_Z:_Ip_Man_Legacy).

### #445 Baby TV-IXP permanece pendiente

Capturas `390`–`392` confirman el OSD #445 y logo BabyTV, pero el reproductor permanece validando el segmento inicial. Tras reabrir el canal, la captura `393` decodifica un fotograma de dibujos animados bajo «Reabriendo fuente HLS»; la `394` vuelve a negro/validación. No hay nombre de programa o episodio visible que permita distinguir la guía correcta por encima de la marca y el género, y una imagen intermitente no acredita estabilidad. Sigue `no_exact_current_programme_match`, sin fuente asignada.

### Capturas revisadas que permanecen pendientes

- #393 Golden [IP 45.171.64.30]: capturas 206, 207 y 208 permanecen en negro con «Validando segmento inicial» tras más de 35 s. No hay fotograma para identificar el programa; queda sin guía.
- #394 Golf Channel HD [IP 45.171.64.30]: captura 209 muestra logo Golf, pero el cintillo informa sobre explotación en Groenlandia y el reproductor avisa que reabre HLS; captura 210 vuelve a validar el segmento inicial. Playback inestable y contenido sin correspondencia defendible; queda sin guía.

- #399 History HD: capturas 223–226 muestran logo History y escenas distintas, pero sin rótulo/título; 225 y 226 repiten el mismo fotograma congelado. Alrededor de 21:02 UTC, CL ofrece «Ciudades Ocultas», MX1/GT «Cazadores de tesoros», CO1 «La evidencia está entre nosotros» y PA1 «Misterios inexplorados con Danny Trejo». Como no se identifica qué feed/programa corresponde, permanece pendiente; no mapear solo por marca.

- #400 Home Garden Latino: capturas 227–229 muestran HGTV y escenas de casa junto a un lago, sin título de programa; 228 y 229 repiten la misma imagen tras ~68 s. A las 21:07 UTC, CO1 HGTV ofrece «Nuestro hogar en las Bahamas», US2 Pacific «Scariest House in America» y US2 «Zillow Gone Wild». No hay prueba visual para elegir entre esas parrillas; queda pendiente.

- #401 LIFE TIME: capturas 230–233 muestran una promo «AMERICA» seguida de anuncios TeveCompras Argentina; no se identifica el programa que interrumpe. AR1/CL/PA1/GT listan «Medicina mortal» a las 21:12 UTC, pero la publicidad local no prueba que ese sea el contenido. Se deja pendiente.

- #402 La voz de Maria: capturas 234–235 (21:15 UTC) muestran fotogramas distintos de un segmento devocional con logo LUM y la marca «3er Plan de Salvación», sin título del programa o episodio. El snapshot EPGShare disponible (generado 18:14:37 UTC) no contiene fuente/canal de República Dominicana ni programa XMLTV activo que coincida exactamente con lo visible; candidateCount 0. La imagen en movimiento confirma que el feed entrega vídeo, pero no permite asignar una parrilla con 12 h futuras. Permanece pendiente; no inferir guía por el logo, el rótulo de segmento ni la IP.

- #403 AyM Sports: capturas 236–237 (21:21–21:22 UTC) muestran distintos fotogramas de un partido de béisbol con marca AyM Sports y marcador 0–2, pero el rótulo es ilegible para confirmar ambos equipos/evento. El snapshot EPGShare (18:14:37 UTC) no contiene una emisión activa que identifique AyM, equipos o evento de béisbol coincidente; candidateCount 0. El [calendario oficial de Yaquis](https://www.yaquis.com.mx/roldejuegos) lista Mayos–Yaquis el 14 de octubre a las 19:10 local, pero la imagen no permite comprobar que se trate de ese juego. Sin fuente/feed exacto y 12 h futuras, queda pendiente.

- #404 Multicinema: capturas 238–240 muestran escenas distintas de una película con marca MC; el OSD solo indica la categoría «Películas», no el título. La captura 239 presenta reintento HLS 3/3 y la 240 recupera a 544×480 / 6,9 FPS, todavía sin título. No se puede vincular a un programa XMLTV ni definir región/fuente; queda pendiente hasta identificar título/feed y comprobar 12 h continuas.

- #405 Fox Sports: capturas 241–242 (21:29–21:32 UTC) muestran FOX VIVO y el rótulo «LIGA DE ASCENSO DE EL SALVADOR», ARU 0–0 IIL; el OSD identifica Fox Sports / Deportes. En EPGShare, la opción MX1 Fox Sports está en «Fox Gol Femenil», y Fox Sports 2 de MX1/GT está en AEW Collision; ninguna coincide con el partido, y no hay fuente XMLTV salvadoreña en el snapshot. El vídeo cambia, pero la captura 242 indica 0,8 FPS/estado rojo, por lo que tampoco acredita estabilidad. Sigue pendiente, sin asignar por marca Fox ni categoría Deportes.
- #407 Pasiones HD: capturas 245–248 muestran la marca Pasiones y dos fases de reapertura HLS. La captura 246 marca 0,6 FPS; después el contenido reaparece, pero las capturas 247–248 repiten exactamente la misma escena y no muestran título/subtítulo que identifique la novela. Sin distinguir el programa ni el feed regional, queda pendiente.
- #408 Pregon Infirmativo: capturas 249–252 muestran escenas monocromáticas distintas y el logo PIT; el OSD confirma el canal 408 y categoría Misceláneos, no el programa. La imagen decodificada no basta para elegir una guía; pendiente.
- #409 La Red TV: capturas 253–255 muestran una entrevista con marca «LA RED TV» y reloj del feed 15:47–15:48; el OSD confirma canal 409, pero no da título de programa. El listado de [La Red TV Guatemala](https://www.gatotv.com/canal/la_red_tv_guatemala) sugiere el bloque «Garra felina - Previa» a las 15:00–16:00 locales el 14-10, pero la entrevista no prueba que ese sea el programa. Tampoco está configurado `sv` como parte XMLTV en el runner, así que no se puede registrar una guía operativa equivalente sin incorporar y validar esa fuente. Pendiente.
- #411 Radio renecer [IP 45.171.64.30]: capturas 258–259 muestran el logo del feed Tv Renacer y contenido audiovisual; el OSD identifica canal 411 y la categoría «Misceláneos», pero no el programa. No hay coincidencia exacta ni una fuente XMLTV regional comprobada con 12 h futuras; permanece pendiente.
- #412 Semillitas [IP 45.171.64.30]: capturas 260–263 muestran la marca Semillitas y dibujos animados. La captura 263 tiene la indicación «Reabriendo fuente HLS», 0,9 FPS y ningún título de programa; el runner no ofrece un candidato XMLTV Semillitas. Queda pendiente hasta identificar el programa/feed y comprobar 12 h futuras.
- #413 Sony [IP 45.171.64.30]: capturas 264–267 muestran escenas de una película con marca Sony. El OSD identifica «Películas», no el título; existen cuatro candidatos regionales, pero no hay evidencia visual para escoger uno. Permanece pendiente.
- #414 Space [IP 45.171.64.30]: capturas 268–269 muestran un anuncio y después una escena de ficción sin título. El OSD solo indica «Películas»; seis parrillas regionales no se pueden distinguir. Pendiente.
- #415 Sony Movies HD [IP 45.171.64.30]: capturas 270–271 muestran escenas de película con marca Sony Movies, pero ningún título. La única parrilla regional candidata no queda confirmada visualmente; pendiente.

Revalidación #395: captura 211 muestra el logo Guatevisión y dos presentadoras en una cocina; a las 20:35 UTC el OSD de la captura 212 muestra «Manos a la obra», coincidente con GT / Guatevision.gt entre 20:30 y 21:30 UTC. Desde el corte de 20:40 UTC, el feed conserva 99,32 h continuas. La asignación ya existente se confirma, aunque el playback luego vuelve a validar el segmento inicial.

- #382 ESPN 6: capturas `184-channel382-later.png` y `185-channel382-second-look.png`; hay una promo y fútbol en vivo, pero no marcador/rótulo que identifique el partido. Las parrillas candidatas disponibles no coinciden a esa hora; pendiente.
- #383 ESPN 6 HD: `186-next-channel-after-382.png` confirma número/nombre; `187-channel383-later.png` muestra promo y “Reabriendo fuente HLS”, no un programa identificable; pendiente.
- #384 EWTN: `188-next-channel-after-383.png` confirma canal; `189-channel384-later.png` muestra Adoración Eucarística en la capilla, pero el snapshot XMLTV no contiene una guía EWTN válida para asignar. No se inventa continuidad Live (solo Rwnd tiene esa excepción); pendiente.
- #385 El Gourmet: `190-next-channel-after-384.png` identifica el canal, pero `191-channel385-later.png` pasa de anuncio a una marca AMC Series; conflicto entre identidad del OSD y contenido, pendiente.
- #386 Exa TV: `192-next-channel-after-385.png` muestra el videoclip de Santana y Grupo Frontera, “Me Retiro”; `193-channel386-later.png` es un anuncio. No identifica el bloque de programación; pendiente.
- #387 FX: `194-next-channel-after-386.png` y `195-channel387-later.png` son promociones cinematográficas sin título de la emisión; pendiente.
- #388 FX HD: `196-next-channel-after-387.png` muestra promo de Cars; `197-channel388-later.png` sigue con promoción cinematográfica y llega a reintento 3/3 (“Reabriendo fuente HLS”); pendiente.
- #389 Film & Arts: `198-next-channel-after-388.png`/`199-channel389-later.png` muestran una película, sin título legible; AR1/MX1 indican *Hunters* y UY1 *Licorice Pizza*. La escena no permite decidir entre fuentes; pendiente.
- #390 Film & Arts HD: `200-next-channel-after-389.png` confirma el canal; `201-channel390-later.png` decodifica una escena de época sin título. Guías disponibles contradictorias; pendiente.

Las capturas están en `outputs/epg-audit-20261014-followup/`. Estas comprobaciones no modifican la M3U ni el catálogo de canales; son evidencia de guía y disponibilidad puntual, no garantía de continuidad futura.

### Continuación de verificación visual — cinco coincidencias adicionales

En una nueva tanda del emulador se cotejó el fotograma en UTC con XMLTV de las fuentes que el runner realmente consume y se midió cobertura futura continua. El contrato registra 62/247 fuentes EPG asignadas y 185 pendientes. El commit `4bf7ef9` se publicó en `main`; `Actualizar EPG` run `38613423120` terminó `success` y publicó el commit de salida `09e19e6`. Se verificaron de forma independiente los cinco fragmentos y sus entradas en `epg.xml`; ninguno aparece en `epg-pending.json`.

| N.º | Señal y guía asignada | Evidencia del emulador/XMLTV | Cobertura comprobada |
| --- | --- | --- | ---: |
| 143 | AXN HD [Nauta] → `cl / Canal.AXN.(Chile).cl` | 17:33 UTC; escena portuaria de *NCIS: Los Ángeles*, en XMLTV 17:30–18:20; las parrillas MX/AR/CO consultadas tenían otro contenido. | 54,62 h |
| 145 | Cinemax HD [Nauta] → `mx1 / Canal.Cinemax.(México).mx` | 17:34 UTC; escena de mujer con vestido azul y perlas en un bar, compatible con *Master Z: The Ip Man Legacy* (MX1, 16:38–18:34); CL/UY/CO listaban otras películas. | 62,38 h |
| 151 | ESPN HD [Nauta] → `mx1 / ESPN.MX.mx` | 17:39 UTC; Inglaterra–Grecia femenino, 4–0 al 72:53 / 7–1 global, rótulo `4 PM MEX`; MX1 lista eliminatorias femeninas 16:00–18:00. | 63,35 h |
| 160 | Star Channel HD [Nauta] → `co1 / STAR.CHANNEL.co` | 17:49 UTC; logo y rótulo explícito «Estás viendo El exótico Hotel Marigold», coincidente con XMLTV 16:26–18:56. CL1 duplica la secuencia; se elige CO1 para reutilizar la guía del Star Channel #195, no como prueba de región física. | 56,08 h |
| 252 | Sony Channel Andes → `co1 / Sony.co` | 18:04 UTC; logo Sony y escena doméstica de *My Wife and Kids*, en XMLTV 17:45–18:15. PA1 ofrece la misma secuencia; CO1 se elige como guía equivalente, no como prueba de región física. | 55,10 h |

Raw al commit `09e19e6` confirma 73 programas/53,88 h para #143 (ahora *NCIS: Los Ángeles*), 36/61,67 h para #145 (*Master Z The Ip Man Legacy*), 61/62,72 h para #151, 38/55,62 h para #160 (*El exótico Hotel Marigold*) y 66/54,88 h para #252 (*Spider-Man: Sin camino a casa*). Las cinco entradas están en la guía unificada y fuera de la lista de pendientes. En la programación legítima de ESPN #151 el título actual de fuente es `Live: SportsCenter AM`; no es un relleno genérico del runner.

Pendientes deliberados tras la inspección: #153 ESPN 4 Sur (boxeo, sin feed Sur inequívoco; no se asigna el candidato Panamá), #156 Fox Sports (resumen de Messi sin coincidencia regional comprobada), #161 Studio Universal (animación sin título/versión identificable), #162–163 Telehit (videos musicales sin título EPG identificable), #200 Golden Edge (fotograma no coincide con las películas candidatas), y #299 ESPN Premium (fútbol juvenil argentino sin canal ESPN Premium correspondiente en la guía AR1 disponible). El #107 ESPN Plus HD también continúa pendiente por la misma falta de ID regional exacto. Ninguno se “completa” por aproximación.

### Verificación visual adicional — Fox Sports 2 México

El emulador mostró el #40 a las 09:16 Santiago / 12:16 UTC con la marca FOX SPORTS 2 y la gráfica `#FOXGOL` de CONCACAF W Championship 2026. El feed MX1 `Canal.Fox.Sports.2.(México).mx` publica `Fox Gol Femenil` en el mismo tramo y, al generar en memoria, el runner produjo 60 programas, 64,44 h futuras, fuente real y cero canales pendientes. El total subió a 57/247 asignados y 190 pendientes. Se publicó la asignación en `dfa52e1`; el dispatch `38565913595` terminó success y GitHub Raw en `56d27af` confirma el fragmento real y la ausencia del canal en `epg-pending.json`.

El #107 ESPN Plus HD presentó en el emulador ESPN Premium y la repetición del encuentro ALD–SAR de la LPF; es un partido finalizado, no una transmisión en vivo de la jornada actual. La guía AR1 disponible no incluye ESPN Premium, y una cartelera externa encontrada no es una fuente de runner vigente. Se mantiene pendiente sin asignar programación por aproximación.

El workflow automático `Actualizar EPG` 38553076460 terminó success, pero su plan seleccionó cero fuentes y solo volvió a unir fragmentos. La comprobación directa encontró las cinco identidades GT sin programas. El primer dispatch manual 38553817527 falló porque `gt` no es una parte válida; los XMLTV gzip de `EPG_SOURCES` se descargan dentro de la parte compartida `epgshare`. El dispatch correcto `fuentes=epgshare` (38553994846) pasó, publicó y verificó Raw en el commit `02696d5`. Los cinco IDs tienen respectivamente 111/76/75/147/126 programas, entre 108,89 y 109,64 horas futuras continuas, cero títulos/descripciones `Live` y ninguno está pendiente.

El workflow `Publicar cambios dirigidos` 38552828375 falló con pruebas históricas de catálogo (incluidos `KeyError: 'trial'` y desajustes frente al baseline) porque el layout conservaba un sello obsoleto tras añadir logos. Se recalculó `approval.sha256`; la suite CI-parity pasó y el reintento `38553811967` terminó success. Una corrida EPG automática duplicada `38554055881` construyó, pero no publicó: `workflow_run` tomó el SHA antiguo `7752d65`, chocó con `02696d5` y no pudo rebasar. No revirtió la EPG ya publicada. El fix `27e35e1` fija los tres checkout EPG a `main` y añade `tests/test_epg_workflow_checkout.py`; la prueba estática pasa (356 Python/19 omitidas), y el dispatch de control 38555183783 (sin fuentes vencidas) pasó en los tres jobs y verificó Raw. No se provocó otro evento `workflow_run` real, así que ese tipo exacto de disparador aún no se volvió a ejercer.

La salida inicial GitHub Raw `8189e53` contenía 9.697 programas totales; sus 56 canales mapeados tenían 4.492 programas, mínimo 36,94 h futuras, cero pendientes y cero relleno `Live`. Para Guatemala, 111/76/75/147/126 programas por canal y 108,74–109,49 h continuas. Los cinco logos están enlazados en `1.m3u` y `m3u.m3u`. La salida posterior `56d27af` incorpora la EPG visual confirmada de Fox Sports 2 #40: el total es 57 canales con mapa exacto y 190 pendientes; quedan además 13 logos por resolver con identidad/fuente exactas.

| Número | Canal | Logo | EPG |
|---:|---|---|---|
| 40 | Fox Sports 2 \| HD [Nauta] | logos/catalogue/fox-sports-2-lam.png | mx1/Canal.Fox.Sports.2.(México).mx; `Fox Gol Femenil`, 64,44 h |
| 96 | ESPN 1 \| Sur [Nauta] | logos/espn.svg | ar1/Canal.ESPN.(Argentina).ar |
| 98 | ESPN 1 \| Chile [Nauta] | logos/espn.svg | cl/Canal.ESPN.(Chile).cl |
| 103 | ESPN HD \| Colombia [Nauta] | logos/espn.svg | co1/ESPN.co |
| 107 | ESPN Plus HD [Nauta] | PENDIENTE | PENDIENTE: regional_feed_not_identified |
| 108 | DSports [Nauta] | logos/catalogue/dsports-lam.png | PENDIENTE: regional_feed_not_identified |
| 109 | DSports HD [Nauta] | logos/catalogue/dsports-lam.png | PENDIENTE: regional_feed_not_identified |
| 110 | Fox Sports Sur [Nauta] | logos/fox-sports.svg | PENDIENTE: regional_feed_not_identified |
| 118 | DSports 2 HD [Nauta] | logos/catalogue/dsports2-lam.png | PENDIENTE: regional_feed_not_identified |
| 121 | DSports 2 [Nauta] | logos/catalogue/dsports2-lam.png | PENDIENTE: regional_feed_not_identified |
| 130 | HBO [Nauta] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 131 | HBO 2 [Nauta] | logos/catalogue/hbo2latinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 132 | HBO 2 HD [Nauta] | logos/catalogue/hbo2latinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 133 | HBO Family [Nauta] | logos/catalogue/hbofamilylatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 134 | HBO Family HD [Nauta] | logos/catalogue/hbofamilylatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 135 | HBO HD [Nauta] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 136 | HBO Mundi [Nauta] | logos/catalogue/hbomundilatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 137 | HBO Plus [Nauta] | logos/catalogue/hbopluslatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 138 | HBO Plus HD [Nauta] | logos/catalogue/hbopluslatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 139 | HBO Plus Oeste HD [Nauta] | logos/catalogue/hbopluslatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 140 | HBO Pop [Nauta] | logos/catalogue/hbopoplatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 141 | HBO Xtreme [Nauta] | logos/catalogue/hboxtremelatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 142 | HBO Xtreme HD [Nauta] | logos/catalogue/hboxtremelatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 143 | AXN HD [Nauta] | logos/catalogue/axnlatinamerica-us.png | cl/Canal.AXN.(Chile).cl (54,62 h) |
| 145 | Cinemax HD [Nauta] | logos/catalogue/cinemaxlatinamerica-us.png | mx1/Canal.Cinemax.(México).mx (62,38 h) |
| 146 | Discovery Channel HD [Nauta] | logos/catalogue/discoverychannellatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 147 | Discovery Theater HD [Nauta] | logos/catalogue/discoverytheaterlatinamerica-us.png | cl/Canal.Discovery.Theater.(Latinoamérica).cl |
| 148 | Discovery Turbo [Nauta] | logos/catalogue/discoveryturbolatinamerica-us.png | cl/Canal.Discovery.Turbo.(Latinoamérica).cl |
| 149 | Discovery Turbo HD [Nauta] | logos/catalogue/discoveryturbolatinamerica-us.png | cl/Canal.Discovery.Turbo.(Latinoamérica).cl |
| 150 | Discovery World [Nauta] | logos/catalogue/discoveryworld-us.png | cl/Canal.Discovery.World.Latinoamérica.cl |
| 151 | ESPN HD [Nauta] | logos/espn.svg | mx1/ESPN.MX.mx (63,35 h) |
| 152 | ESPN 3 HD [Nauta] | logos/espn-3.png | PENDIENTE: regional_feed_not_identified |
| 153 | ESPN 4 \| Sur [Nauta] | logos/espn-4.png | PENDIENTE: regional_feed_not_identified |
| 156 | Fox Sports HD [Nauta] | logos/fox-sports.svg | PENDIENTE: regional_feed_not_identified |
| 160 | Star Channel HD [Nauta] | logos/catalogue/starchannellatinamerica-us.png | co1/STAR.CHANNEL.co (56,08 h; horario duplicado en CL1) |
| 161 | Studio Universal HD [Nauta] | logos/catalogue/studiouniversallatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 162 | Telehit [Nauta] | logos/catalogue/telehit-mx.png | PENDIENTE: regional_feed_not_identified |
| 163 | Telehit HD [Nauta] | logos/catalogue/telehit-mx.png | PENDIENTE: regional_feed_not_identified |
| 164 | ESPN HD [IP 181] | logos/espn.svg | co1/ESPN.co |
| 165 | ESPN 2 HD [IP 181] | logos/espn-2.png | co1/ESPN.2.co |
| 166 | ESPN 4 HD [IP 181] | logos/espn-4.png | co1/ESPN.4.co |
| 167 | ESPN 6 [IP 181] | logos/catalogue/espn-6-lam.png | co1/ESPN.6.HD.co |
| 168 | ESPN 7 [IP 181] | logos/espn-7.png | co1/ESPN.7.HD.co |
| 178 | Telecafé [IP 181] | logos/catalogue/telecafe-co.png | co1/Telecafé.co |
| 192 | Cartoon Network [IP 181] | logos/catalogue/cartoonnetworklatinamerica-us.png | co1/Cartoon.Network.co |
| 194 | Adult Swim [IP 181] | logos/catalogue/adultswimlatinamerica-us.png | co1/AdultSwim.co |
| 195 | Star Channel [IP 181] | logos/catalogue/starchannellatinamerica-us.png | co1/STAR.CHANNEL.co |
| 196 | FX [IP 181] | logos/catalogue/fxlatinamerica-us.png | co1/FX.co |
| 197 | Cinecanal [IP 181] | logos/catalogue/cinecanal-us.png | co1/Cinecanal.co |
| 198 | AMC [IP 181] | logos/catalogue/amclatinamerica-us.png | co1/AMC.co |
| 199 | Golden [IP 181] | logos/catalogue/golden-mx.png | co1/GOLDEN.HD.co |
| 200 | Golden Edge [IP 181] | logos/catalogue/goldenedge-mx.png | PENDIENTE: regional_feed_not_identified |
| 205 | Discovery Channel [IP 181] | logos/catalogue/discoverychannellatinamerica-us.png | co1/Discovery.Channel.co |
| 206 | Investigation Discovery [IP 181] | logos/catalogue/investigationdiscoverylatinamerica-us.png | co1/ID.-.Investigation.Discovery.co |
| 207 | Discovery Turbo [IP 181] | logos/catalogue/discoveryturbolatinamerica-us.png | co1/Discovery.Turbo.co |
| 208 | Discovery Home & Health [IP 181] | logos/catalogue/discoveryhomehealthlatinamerica-mx.png | co1/Discovery.H&H.co |
| 209 | TLC [IP 181] | logos/catalogue/tlclatinamerica-us.png | co1/TLC.co |
| 210 | El Gourmet HD [IP 181] | logos/catalogue/elgourmet-ar.png | co1/El.Gourmet.co |
| 212 | National Geographic [IP 181] | logos/catalogue/nationalgeographiclatinamerica-us.png | co1/National.Geographic.co |
| 226 | AXN [IP 181.78.8.199] | logos/catalogue/axnlatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 252 | Sony Channel Andes [IP 181.119.66.28] | logos/catalogue/sonychannelandes-us.png | co1/Sony.co (55,10 h; horario duplicado en PA1) |
| 286 | CNN Chile [IP 190.110.96.238] | logos/catalogue/cnnchile-cl.png | cl/Canal.CNN.Chile.cl |
| 291 | Discovery Theater [IP 181.224.200.5] | logos/catalogue/discoverytheaterlatinamerica-us.png | cl/Canal.Discovery.Theater.(Latinoamérica).cl |
| 292 | Discovery Turbo [IP 38.134.250.110] | logos/catalogue/discoveryturbolatinamerica-us.png | cl/Canal.Discovery.Turbo.(Latinoamérica).cl |
| 299 | ESPN Premium [IP 190.128.214.97] | logos/catalogue/espn-premium-ar.png | PENDIENTE: regional_feed_not_identified |
| 305 | Golden [IP 181.224.200.5] | logos/catalogue/golden-mx.png | PENDIENTE: regional_feed_not_identified |
| 308 | HBO 2 [IP 45.171.64.30] | logos/catalogue/hbo2latinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 309 | HBO Family [IP 45.171.64.30] | logos/catalogue/hbofamilylatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 310 | Claro Cinema [IP 45.171.64.30] | PENDIENTE | PENDIENTE: regional_feed_not_identified |
| 311 | Claro Musica [IP 45.171.64.30] | logos/catalogue/claromusicatv-co.png | PENDIENTE: regional_feed_not_identified |
| 312 | RHEMA TV [IP 45.171.64.30] | logos/catalogue/rhematv-gt.png | PENDIENTE: regional_feed_not_identified |
| 313 | Space [IP 45.171.64.30] | logos/catalogue/space-ar.png | PENDIENTE: regional_feed_not_identified |
| 314 | Cartoonito [IP 181.78.12.119] | logos/catalogue/cartoonitolatinamerica-us.png | co1/CARTOONITO.co |
| 315 | TNT Novelas HD [IP 181.78.12.119] | logos/catalogue/tntnovelas-us.png | co1/TNT.Novelas.co |
| 316 | CNC [IP 181.78.12.119] | PENDIENTE | PENDIENTE: regional_feed_not_identified |
| 317 | COD Space HD [IP 181.78.12.119] | logos/catalogue/space-ar.png | co1/Space.co |
| 318 | Caracol ERICSON [IP 181.78.12.119] | logos/catalogue/caracoltv-co.png | PENDIENTE: source_missing_or_under_12h |
| 319 | City TV [IP 181.78.12.119] | PENDIENTE | ar1/Canal.City.TV.ar |
| 320 | ESPN CO sd [IP 181.78.12.119] | logos/espn.svg | co1/ESPN.co |
| 321 | Nuestra Tele [IP 181.78.12.119] | logos/catalogue/nuestrateleinternacional-co.png | co1/NUESTRA.TELE.co |
| 322 | RCN (clone) [IP 181.78.12.119] | logos/catalogue/canalrcn-co.png | co1/RCN.co |
| 323 | SRT A&E [IP 181.78.12.119] | logos/catalogue/a-and-e-ar.png | co1/A&E.co |
| 324 | SRT AXN [IP 181.78.12.119] | logos/catalogue/axnlatinamerica-us.png | co1/AXN.co |
| 325 | SRT E! [IP 181.78.12.119] | logos/catalogue/elatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 326 | SRT HISTORY [IP 181.78.12.119] | logos/catalogue/history-channel-lam.png | co1/History.Channel.co |
| 327 | SRT SONY [IP 181.78.12.119] | logos/catalogue/sonychannelandes-us.png | co1/Sony.co |
| 328 | SRT SONY MOVIES [IP 181.78.12.119] | logos/catalogue/sonymovieslatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 329 | SRT lifetime [IP 181.78.12.119] | logos/catalogue/lifetimelatinamerica-us.png | PENDIENTE: source_missing_or_under_12h |
| 330 | SRT televid [IP 181.78.12.119] | logos/catalogue/televid-co.png | co1/TELEVID.co |
| 331 | Space HD [IP 181.78.12.119] | logos/catalogue/space-ar.png | co1/Space.co |
| 332 | TNT HD [IP 181.78.12.119] | logos/catalogue/tntlatinamerica-us.png | co1/TNT.co |
| 333 | Ve plus [IP 181.78.12.119] | logos/catalogue/veplus-ve.png | PENDIENTE: regional_feed_not_identified |
| 334 | srt E-SPORTS MAX [IP 181.78.12.119] | logos/catalogue/esportsmaxtv-ve.png | PENDIENTE: regional_feed_not_identified |
| 335 | srt PLOUS TV [IP 181.78.12.119] | logos/catalogue/ploustv-ve.png | PENDIENTE: regional_feed_not_identified |
| 336 | el mundo del campo [IP 181.78.12.119] | PENDIENTE | PENDIENTE: regional_feed_not_identified |
| 337 | rcn novelas [IP 181.78.12.119] | logos/catalogue/rcnnovelas-co.png | co1/RCN.Novelas.co |
| 338 | Caracol HD (clone) [IP 181.78.12.119] | logos/catalogue/caracoltv-co.png | PENDIENTE: source_missing_or_under_12h |
| 339 | ZOOM (clone) [IP 181.78.12.119] | logos/catalogue/zoom-co.png | PENDIENTE: regional_feed_not_identified |
| 340 | A&E [IP 45.171.64.30] | logos/catalogue/a-and-e-ar.png | PENDIENTE: regional_feed_not_identified |
| 341 | A&E HD [IP 45.171.64.30] | logos/catalogue/a-and-e-ar.png | PENDIENTE: regional_feed_not_identified |
| 342 | AMC [IP 45.171.64.30] | logos/catalogue/amclatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 343 | AMC HD [IP 45.171.64.30] | logos/catalogue/amclatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 344 | AXN [IP 45.171.64.30] | logos/catalogue/axnlatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 345 | AXN HD [IP 45.171.64.30] | logos/catalogue/axnlatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 346 | AZ click HD [IP 45.171.64.30] | logos/catalogue/azclic-mx.png | PENDIENTE: regional_feed_not_identified |
| 347 | Animal Planet [IP 45.171.64.30] | logos/catalogue/animalplanetlatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 348 | Animal Planet HD [IP 45.171.64.30] | logos/catalogue/animalplanetlatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 349 | Azcorazon [IP 45.171.64.30] | logos/catalogue/azcorazon-mx.png | PENDIENTE: regional_feed_not_identified |
| 350 | Azmundo [IP 45.171.64.30] | logos/catalogue/azmundo-mx.png | PENDIENTE: regional_feed_not_identified |
| 351 | BBC World [IP 45.171.64.30] | logos/catalogue/bbcnews-uk.png | PENDIENTE: regional_feed_not_identified |
| 352 | Baby First [IP 45.171.64.30] | logos/catalogue/babyfirst-us.png | PENDIENTE: regional_feed_not_identified |
| 353 | CINECANAL HD [IP 45.171.64.30] | logos/catalogue/cinecanal-us.png | PENDIENTE: regional_feed_not_identified |
| 354 | CNN Internacional [IP 45.171.64.30] | logos/catalogue/cnninternational-us.png | PENDIENTE: regional_feed_not_identified |
| 355 | CNNE [IP 45.171.64.30] | logos/catalogue/cnnenespanol-us.svg | PENDIENTE: regional_feed_not_identified |
| 356 | Canal 13-GUA-e1 [IP 45.171.64.30] | logos/catalogue/canal13-gt.png | gt/Canal13-Trecevision.gt (109.39 h) |
| 357 | Canal 3 - GUA [IP 45.171.64.30] | logos/catalogue/canal3-gt.png | gt/Canal3.gt (110.14 h) |
| 358 | Canal 7 - GUA [IP 45.171.64.30] | logos/catalogue/canal7-gt.png | gt/Canal7-Televisiete.gt (109.39 h) |
| 359 | Canal Antigua - GUA [IP 45.171.64.30] | logos/catalogue/canalantigua-gt.png | gt/CanalAntigua.gt (109.39 h) |
| 360 | Cartoon Network [IP 45.171.64.30] | logos/catalogue/cartoonnetworklatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 361 | Cine Latino [IP 45.171.64.30] | logos/catalogue/cinelatino-mx.png | PENDIENTE: regional_feed_not_identified |
| 362 | CineCanal [IP 45.171.64.30] | logos/catalogue/cinecanal-us.png | PENDIENTE: regional_feed_not_identified |
| 363 | CineMax [IP 45.171.64.30] | logos/catalogue/cinemaxlatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 364 | Kanal D Drama [IP 45.171.64.30] | PENDIENTE | PENDIENTE: regional_feed_not_identified |
| 365 | Concert Channel [IP 45.171.64.30] | logos/catalogue/concertchannel-us.png | PENDIENTE: regional_feed_not_identified |
| 366 | DHE [IP 45.171.64.30] | logos/catalogue/dhe-us.png | PENDIENTE: regional_feed_not_identified |
| 367 | DHE HD [IP 45.171.64.30] | logos/catalogue/dhe-us.png | PENDIENTE: regional_feed_not_identified |
| 368 | DISC THEATHER HD [IP 45.171.64.30] | logos/catalogue/discoverytheaterlatinamerica-us.png | cl/Canal.Discovery.Theater.(Latinoamérica).cl |
| 369 | Discovery Home & Health [IP 45.171.64.30] | logos/catalogue/discoveryhomehealthlatinamerica-mx.png | PENDIENTE: regional_feed_not_identified |
| 370 | Discovery Kids [IP 45.171.64.30] | logos/catalogue/discoverykidslatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 371 | Discovery Turbo [IP 45.171.64.30] | logos/catalogue/discoveryturbolatinamerica-us.png | cl/Canal.Discovery.Turbo.(Latinoamérica).cl |
| 372 | Disney [IP 45.171.64.30] | logos/catalogue/disneychannellatinamerica-ar.svg | PENDIENTE: regional_feed_not_identified |
| 373 | Disney JR [IP 45.171.64.30] | logos/catalogue/disneyjrlatinamerica-ar.svg | PENDIENTE: regional_feed_not_identified |
| 374 | E! [IP 45.171.64.30] | logos/catalogue/elatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 375 | E! Entertairment HD [IP 45.171.64.30] | logos/catalogue/elatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 376 | ESPN [IP 45.171.64.30] | logos/espn.svg | PENDIENTE: regional_feed_not_identified |
| 377 | ESPN 4 HD [IP 45.171.64.30] | logos/espn-4.png | PENDIENTE: regional_feed_not_identified |
| 378 | ESPN 2 [IP 45.171.64.30] | logos/espn-2.png | PENDIENTE: regional_feed_not_identified |
| 379 | ESPN 2 HD [IP 45.171.64.30] | logos/espn-2.png | PENDIENTE: regional_feed_not_identified |
| 380 | ESPN 3 [IP 45.171.64.30] | logos/espn-3.png | PENDIENTE: regional_feed_not_identified |
| 381 | ESPN 3 HD [IP 45.171.64.30] | logos/espn-3.png | PENDIENTE: regional_feed_not_identified |
| 382 | ESPN 6 [IP 45.171.64.30] | logos/catalogue/espn-6-lam.png | PENDIENTE: regional_feed_not_identified |
| 383 | ESPN 6 HD [IP 45.171.64.30] | logos/catalogue/espn-6-lam.png | PENDIENTE: regional_feed_not_identified |
| 384 | EWTN [IP 45.171.64.30] | logos/catalogue/ewtn-us.png | PENDIENTE: regional_feed_not_identified |
| 385 | El Gourmet [IP 45.171.64.30] | logos/catalogue/elgourmet-ar.png | PENDIENTE: regional_feed_not_identified |
| 386 | Exa TV [IP 45.171.64.30] | logos/catalogue/exatv-mx.png | PENDIENTE: regional_feed_not_identified |
| 387 | FX [IP 45.171.64.30] | logos/catalogue/fxlatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 388 | FX HD [IP 45.171.64.30] | logos/catalogue/fxlatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 389 | Film & Arts [IP 45.171.64.30] | logos/catalogue/filmarts-ar.png | PENDIENTE: regional_feed_not_identified |
| 390 | Film & arts HD [IP 45.171.64.30] | logos/catalogue/filmarts-ar.png | PENDIENTE: regional_feed_not_identified |
| 393 | Golden [IP 45.171.64.30] | logos/catalogue/golden-mx.png | PENDIENTE: regional_feed_not_identified |
| 394 | Golf Channel HD [IP 45.171.64.30] | logos/catalogue/golfchannellatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 395 | Guatevision - GUA [IP 45.171.64.30] | logos/catalogue/guatevision-gt.png | gt/Guatevision.gt (109.39 h) |
| 396 | H2 [IP 45.171.64.30] | logos/catalogue/history2latinamerica-us.png | cl/Canal.History.2.(Chile).cl (28,32 h) |
| 397 | HBO XTREME [IP 45.171.64.30] | logos/catalogue/hboxtremelatinamerica-us.png | cl/Canal.HBO.Xtreme.cl (58,13 h) |
| 398 | History Channel [IP 45.171.64.30] | logos/catalogue/history-channel-lam.png | pa1/Canal.History.(Panamá).pa (27,42 h) |
| 399 | History HD [IP 45.171.64.30] | logos/catalogue/history-channel-lam.png | PENDIENTE: no_exact_current_programme_match |
| 400 | Home Garden Latino [IP 45.171.64.30] | logos/catalogue/hgtvlatinamerica-us.png | PENDIENTE: no_exact_current_programme_match |
| 401 | LIFE TIME [IP 45.171.64.30] | logos/catalogue/lifetimelatinamerica-us.png | PENDIENTE: only_advertisement_content_at_validation |
| 402 | La voz de Maria [IP 45.171.64.30] | logos/catalogue/lavozdemaria-do.png | PENDIENTE: no_exact_current_programme_match |
| 403 | AyM Sports [IP 45.171.64.30] | logos/catalogue/aymsports-mx.png | PENDIENTE: regional_feed_not_identified |
| 404 | Multicinema [IP 45.171.64.30] | PENDIENTE | PENDIENTE: programme_title_not_identified |
| 405 | Fox Sports [IP 45.171.64.30] | logos/fox-sports.svg | PENDIENTE: no_exact_current_programme_match |
| 406 | A3Cine [IP 45.171.64.30] | PENDIENTE | es/A3CINE.es (*Ninette*, 84,38 h) |
| 407 | Pasiones HD [IP 45.171.64.30] | logos/catalogue/pasioneslatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 408 | Pregon Infirmativo [IP 45.171.64.30] | PENDIENTE | PENDIENTE: regional_feed_not_identified |
| 409 | La Red TV [IP 45.171.64.30] | logos/catalogue/laredtv-gt.png | PENDIENTE: regional_feed_not_identified |
| 410 | RCN Novelas [IP 45.171.64.30] | logos/catalogue/rcnnovelas-co.png | co1/RCN.Novelas.co |
| 411 | Radio renecer [IP 45.171.64.30] | PENDIENTE | PENDIENTE: regional_feed_not_identified |
| 412 | SEMILLITAS [IP 45.171.64.30] | logos/catalogue/semillitastv-us.png | PENDIENTE: regional_feed_not_identified |
| 413 | SONY [IP 45.171.64.30] | logos/catalogue/sonychannelandes-us.png | PENDIENTE: regional_feed_not_identified |
| 414 | SPACE [IP 45.171.64.30] | logos/catalogue/space-ar.png | PENDIENTE: regional_feed_not_identified |
| 415 | Sony Movies HD [IP 45.171.64.30] | logos/catalogue/sonymovieslatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 416 | Studio Universal [IP 45.171.64.30] | logos/catalogue/studiouniversallatinamerica-us.png | co1/Studio.Universal.co (*Spider-Man: Un nuevo universo*, 12,90 h) |
| 417 | Studio Universal HD [IP 45.171.64.30] | logos/catalogue/studiouniversallatinamerica-us.png | co1/Studio.Universal.co (*Spider-Man: Un nuevo universo*, 12,85 h) |
| 418 | TBN Enlace [IP 45.171.64.30] | logos/catalogue/enlace-cr.png | PENDIENTE: regional_feed_not_identified; capturas 281–285 sin título de emisión |
| 419 | TNT Novelas [IP 45.171.64.30] | logos/catalogue/tntnovelas-us.png | co1/TNT.Novelas.co (*Quiéreme siempre*, 50,08 h; captura 290; región física no inferida) |
| 420 | TD+2 HD CR [IP 45.171.64.30] | logos/catalogue/tdmas2-cr.png | PENDIENTE: sin título exacto ni fuente XMLTV CR/TD+ con 12 h; capturas 291–293 |
| 421 | TD+HD CR [IP 45.171.64.30] | logos/catalogue/tdmas-cr.png | PENDIENTE: «El rol del mediocentro» no se valida como emisión completa ni hay fuente XMLTV CR/TD+; capturas 294–296 |
| 422 | TLC [IP 45.171.64.30] | logos/catalogue/tlclatinamerica-us.png | PENDIENTE: 7 parrillas candidatas; falta título exacto en pantalla; capturas 297–300 |
| 423 | Discovery Channel [IP 45.171.64.30] · señal 2 | logos/catalogue/discoverychannellatinamerica-us.png | PENDIENTE: 4 parrillas candidatas; OSD «Misceláneos», marca TNT y anuncio posterior, sin título exacto; capturas 301–303 |
| 424 | TNT Series [IP 45.171.64.30] | logos/catalogue/tntserieslatinamerica-us.png | PENDIENTE: 5 parrillas candidatas; OSD «Películas», anuncios/escena sin título; capturas 304–306 |
| 425 | Telemundo [IP 45.171.64.30] | logos/catalogue/telemundointernacional-us.png | co1/Telemundo.co (*Caso cerrado*, 73,18 h; captura 307; guías CL1/MX1/PA1 equivalentes, región física no inferida) |
| 426 | Telemundo HD [IP 45.171.64.30] | logos/catalogue/telemundointernacional-us.png | co1/Telemundo.co (*Caso cerrado*, 73,07 h; misma escena del #425; captura 311) |
| 427 | Televida RD [IP 45.171.64.30] | logos/catalogue/televida-do.png | PENDIENTE: cero fuentes XMLTV dominicanas candidatas y sin título visible; OSD «Misceláneos»; capturas 313–315 |
| 428 | UNIVERSAL COMEDY HD [IP 45.171.64.30] | logos/catalogue/universalcomedy-us.png | PENDIENTE: regional_feed_not_identified |
| 429 | UNIVERSAL CRIME HD [IP 45.171.64.30] | logos/catalogue/universalcrime-us.png | PENDIENTE: regional_feed_not_identified |
| 430 | UNIVERSAL PREMIERE HD [IP 45.171.64.30] | logos/catalogue/universalpremiere-us.png | PENDIENTE: regional_feed_not_identified |
| 431 | UNIVERSAL PREMIERE O HD [IP 45.171.64.30] | logos/catalogue/universalpremiere-us.png | PENDIENTE: regional_feed_not_identified |
| 432 | Universal [IP 45.171.64.30] | logos/catalogue/universaltvlatinamerica-us.png | PENDIENTE: episodio visible *SVU S26E19 Play with Fire Part 2*; UY1 lista S26E21 *Apertura* y otras 4 candidatas *Chicago Fire*; capturas 339–343 |
| 433 | Univision HD [IP 45.171.64.30] | logos/catalogue/univisionlatinamerica-mx.png | uy1/UNIVISION.HD.uy (*La historia de Juana*, 15,43 h; captura 351; CL confirma horario equivalente) |
| 434 | WARNER HD [IP 45.171.64.30] | logos/catalogue/warnerchannel-us.png | PENDIENTE: regional_feed_not_identified |
| 435 | Warner [IP 45.171.64.30] | logos/catalogue/warnerchannel-us.png | PENDIENTE: regional_feed_not_identified |
| 436 | ZooMoo [IP 45.171.64.30] | logos/catalogue/zoomoo-sg.png | PENDIENTE: regional_feed_not_identified |
| 437 | ctv [IP 45.171.64.30] | PENDIENTE | PENDIENTE: regional_feed_not_identified |
| 438 | la liga [IP 45.171.64.30] | — | mx1/Canal.Sky.Sports.16.mx (Deportivo Alavés–Atlético de Madrid; 12,12 h; captura 371) |
| 439 | Discovery World HD [IP 168.196.127.137] | logos/catalogue/discoveryworld-us.png | cl/Canal.Discovery.World.Latinoamérica.cl |
| 440 | TELEHIT LATINIO [IP 190.61.47.54] | logos/catalogue/telehitmusica-mx.png | PENDIENTE: regional_feed_not_identified |
| 441 | UNIVERSAL CINEMA ESTE HD [IP 168.196.127.137] | logos/catalogue/universalcinema-us.png | PENDIENTE: regional_feed_not_identified |
| 442 | A&E-IXP [IP 138.59.177.78] | logos/catalogue/a-and-e-ar.png | PENDIENTE: 5 fuentes A&E discrepan; promo no confirma emisión y el stream terminó en error 3004404; capturas 376–382 |
| 443 | AMC-IXP [IP 138.59.177.78] | logos/catalogue/amclatinamerica-us.png | co1/AMC.co (*RoboCop*, 12,47 h; nombres John Lake y Andre Daniels en la captura 383; OSD 00:32 en 385) |
| 444 | ANIMAL PLANET-IXP [IP 138.59.177.78] | logos/catalogue/animalplanetlatinamerica-us.png | cl/Canal.Animal.Planet.(Chile).cl (*El acuario / El trato de la foca*; 12,75 h; captura 389) |
| 445 | BABY TV-IXP [IP 138.59.177.78] | logos/catalogue/babytv-uk.png | PENDIENTE: sin título exacto visible; validación inicial/reapertura HLS en capturas 390–394 |
| 446 | CINEMAX-IXP [IP 138.59.177.78] | logos/catalogue/cinemaxlatinamerica-us.png | pa1/Canal.Cinemax.(Panamá).pa (*Master Z: El legado de Ip Man*; 14,37 h; capturas 395–397; inferido por escena final + bumper del siguiente programa) |
| 447 | Galavision [IP 138.59.177.78] | logos/catalogue/galavision-us.png | PENDIENTE: regional_feed_not_identified |
| 448 | DISCOVERY CHANNEL-IXP [IP 138.59.177.78] | logos/catalogue/discoverychannellatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 449 | DISCOVERY KIDS-IXP [IP 138.59.177.78] | logos/catalogue/discoverykidslatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 450 | DISCOVERY WORLD-IXP [IP 138.59.177.78] | logos/catalogue/discoveryworld-us.png | cl/Canal.Discovery.World.Latinoamérica.cl |
| 451 | DISNEY JR-IXP [IP 138.59.177.78] | logos/catalogue/disneyjrlatinamerica-ar.svg | PENDIENTE: regional_feed_not_identified |
| 452 | DISNEY-IXP [IP 138.59.177.78] | logos/catalogue/disneychannellatinamerica-ar.svg | PENDIENTE: regional_feed_not_identified |
| 453 | ESPN 1 EZ-TRA [IP 138.59.177.78] | logos/catalogue/espn-lam.png | PENDIENTE: regional_feed_not_identified |
| 454 | ESPN 1 IXP [IP 138.59.177.78] | logos/espn.svg | PENDIENTE: regional_feed_not_identified |
| 455 | ESPN 2 IXP [IP 138.59.177.78] | logos/espn-2.png | PENDIENTE: regional_feed_not_identified |
| 456 | ESPN 4 EZ-TRA [IP 138.59.177.78] | logos/espn-4.png | PENDIENTE: regional_feed_not_identified |
| 457 | HBO [IP 138.59.227.20] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 458 | ESPN 1 ENVIO [IP 138.94.3.106] | logos/catalogue/espn-lam.png | PENDIENTE: regional_feed_not_identified |
| 459 | HBO [IP 158.172.217.18] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 460 | HBO HD [IP 167.249.23.102] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 461 | HBO HD [IP 170.244.209.30] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 462 | MPTS 2 ESPN 7 [IP 177.234.218.66] | logos/espn-7.png | PENDIENTE: regional_feed_not_identified |
| 463 | HBO HD [IP 181.119.177.253] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 464 | ESPN 2 HD [IP 181.224.200.5] | logos/espn-2.png | PENDIENTE: regional_feed_not_identified |
| 465 | ESPN [IP 181.78.106.127] | logos/espn.svg | PENDIENTE: regional_feed_not_identified |
| 466 | HBO HD [IP 181.78.197.59] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 467 | ESPN 2 [IP 181.78.211.244] | logos/espn-2.png | PENDIENTE: regional_feed_not_identified |
| 468 | ESPN 2 [IP 181.78.211.244] · señal 2 | logos/espn-2.png | PENDIENTE: regional_feed_not_identified |
| 469 | ESPN 1 [IP 181.78.8.199] | logos/espn.svg | PENDIENTE: regional_feed_not_identified |
| 470 | HBO HD [IP 181.78.82.130] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 471 | ESPN 1 ENVIO [IP 181.79.86.130] | logos/catalogue/espn-lam.png | PENDIENTE: regional_feed_not_identified |
| 472 | HBO HD [IP 187.245.231.226] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 473 | HBO HD [IP 190.108.83.69] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 474 | HBO HD [IP 190.108.91.206] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 475 | Z05-TNT Sports [IP 190.110.96.238] | PENDIENTE | PENDIENTE: regional_feed_not_identified |
| 476 | Red Uno LPZ HD [IP 190.181.61.93] | logos/catalogue/reduno-bo.svg | PENDIENTE: regional_feed_not_identified |
| 477 | HBO HD [IP 190.234.82.52] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 478 | HBO HD [IP 190.60.46.228] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 479 | HISTORY CHANNEL [IP 190.61.114.186] | logos/catalogue/history-channel-lam.png | PENDIENTE: regional_feed_not_identified |
| 480 | HBO HD [IP 190.61.90.17] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 481 | HBO [IP 200.115.120.1] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 482 | CANAL 1 [IP 200.122.223.13] | logos/catalogue/canal1-co.png | co1/Canal.1.co |
| 483 | HBO HD [IP 200.7.99.59] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 484 | ESPN [IP 38.87.224.19] | logos/espn.svg | PENDIENTE: regional_feed_not_identified |
| 485 | HBO HD [IP 45.166.93.156] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 486 | HBO HD [IP 45.173.231.22] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 487 | ESPN (145) [IP 45.189.151.7] | logos/espn.svg | PENDIENTE: regional_feed_not_identified |
| 488 | HBO HD [IP 72.1.184.5] | logos/catalogue/hbolatinamerica-us.png | PENDIENTE: regional_feed_not_identified |

## Validación local (2026-10-14)

- Las pruebas Python y JavaScript se vuelven a ejecutar tras registrar #406 y los canales #407–409; ver el resultado final de esta pasada en el siguiente corte de `ESTADO.md`.
- `update_m3u.py --validate-public-lists-only`: partición válida de Lista 1 292, Lista 2 0 y catálogo canónico 2.056.
- Bundle temporal del editor: 629 filas y 487 logos. Los 106 archivos registrados para esta oficialización mantienen los SHA-256 del contrato.
- Comparación editorial contra `4efa5286`: exactamente las 247 marcas de prueba se retiraron; los demás campos, orden, nombres, identidad, altas/bajas, respaldos y selección se conservaron.
- Smoke JVM de la primera publicación usando el parser y catálogo del tag publicado VibeM3U `v0.5.95` (incluida la clase `DynamicSourceReference` de `e395b9d`): las 247 identidades, nombres y URLs entran una sola vez y la proyección queda en 303 canales visibles. Ese smoke precede a los dos PNG de Guatemala; no se compiló una APK ni se repitió el smoke de app para esos assets, tampoco se probó en TV física.
- Las 51 fuentes EPG de la primera validación produjeron 4.017 programas reales. Con Guatemala, un build local aislado sobre cinco IDs exactos produjo 537 programas sin relleno `Live`. Luego, la captura del emulador de Fox Sports 2 México (#40) a las 09:16 Santiago / 12:16 UTC mostró `#FOXGOL`/CONCACAF W; el feed MX1 coincidió con `Fox Gol Femenil`. El commit `dfa52e1` asignó `Canal.Fox.Sports.2.(México).mx`; `Actualizar EPG` run `38565913595` terminó success y publicó la salida `56d27af`. GitHub Raw confirma el canal con fuente `mx1`, 60 programas y fuera de `epg-pending.json`. En el corte de 20:16 UTC el contrato local contiene trece asignaciones posteriores verificadas (detalladas arriba y en la bitácora), para 75/247 y 172 pendientes; 62 están publicados y estas trece esperan commit, runner y comprobación Raw. No se publican títulos `Live` inventados.
- No se modificaron la aplicación ni la selección de resolutores. La rama se actualizó desde `aec3847` para incorporar cinco commits automáticos del runner antes de la publicación.

## Publicación

La continuación visual se publicó en el commit `4bf7ef9`; el workflow [Actualizar EPG 38613423120](https://github.com/SPxMM3R1/lista-m3u/actions/runs/38613423120) terminó `success` y generó `09e19e6`. Raw se comprobó directamente en `epg.xml`, los cinco `epg/canales/<tvg-id>.xml` y `epg-pending.json`: #143, #145, #151, #160 y #252 tienen respectivamente 73, 36, 61, 38 y 66 programas, coberturas futuras continuas de 53,88–62,72 h y ya no están pendientes. Total publicado: 62/247 canales asignados a guía; 185 permanecen pendientes. Los 247 canales sí están en estado editorial definitivo, pero eso no acredita que todos tengan guía; 13 logos también siguen pendientes.

### Publicación inicial — Fox Sports 2 México (#40)

El commit de asignación `dfa52e1` se publicó en `main`; el workflow [Actualizar EPG 38565913595](https://github.com/SPxMM3R1/lista-m3u/actions/runs/38565913595) terminó `success` y generó `56d27af`. Se verificó GitHub Raw en `epg.xml`, el fragmento `epg/canales/Nauta.7b8890eac450f9cc89b06b84@Nauta.xml` y `epg-pending.json`: Fox Sports 2 #40 tiene fuente `mx1`, 60 programas y no está pendiente. La EPG local del mismo ID cubría 64,44 h. ESPN Plus HD #107 queda pendiente porque la fuente AR1 disponible no contiene la identidad ESPN Premium mostrada por el emulador. No completar por aproximación.
