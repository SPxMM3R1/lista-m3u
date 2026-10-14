# Oficialización de pruebas — 2026-10-13

Pedido «Todas las pruebas»: 247 activos en prueba de Lista 1 pasan a definitivos sin mover ni borrar filas ni alterar respaldos; 38 referencias Nauta exactas se agregan a la excepción cerrada (42 con las cuatro históricas). A 2026-10-14, los logos comprobados son 234 y 13 siguen pendientes. Cinco nuevas coincidencias de EPG confirmadas en emulador se publicaron y verificaron en Raw: la cifra sube de 57 a 62 asignadas y quedan 185 pendientes. No afirmar EPG/logo completo: definitivo es estado editorial, no prueba de guía/estabilidad. Sin Live de relleno, canales nuevos, selector Android, cambios de app ni APK. Contrato contracts/trial-officialization-20261013.json; pendientes por identidad en esta bitácora. Mantener futuras altas en prueba y no oficializar referencias Nauta fuera de las 42 exactas sin pedido explícito.

## Alcance y límites

Usuario: «puedes pasar todos los canales ... a definitivo y darles logo y EPG»; aclaración: «Todas las pruebas» = todos los activos en prueba de Lista 1, no ocultos/papelera ni todo el inventario.

Matched means exact curated national/regional source with continuous 12h at validation; Total Conexion region is supported by prior SDT/operator evidence. A FreeEPG Guatemala feed was fetched on 2026-10-14; its current XML had 155 channel IDs, including exact current IDs for Canal 13/Trecevisión, Canal 3, Canal 7/Televisiete, Canal Antigua and Guatevisión, each with 109.39–110.14 continuous hours. The five local names explicitly contain GUA; no region was inferred from IP. The FreeEPG country page lists 160 channels and itself cautions there is no completeness guarantee: https://free-epg.de/countries/gt. The feed also had stale duplicate IDs for four channels; only the IDs with continuous current data were mapped. This is not proof of synchrony of every programme in physical TV. Other unknown regional feeds remain pending; no other region is assigned by similarity and no continuity Live is fabricated. Definitive remains an editorial state, not proof of availability or complete guide.

Región de Total Conexión: SDT/operador colombiano documentado en la investigación del 12-10, no inferida por geolocalización de IP. Para canales panregionales de Discovery se compararon CL/MX y coincidieron todos los tramos/títulos de las próximas 12 h. No es prueba contemporánea del contenido de todos los programas en cada señal ni TV física. Logos reales PNG/SVG, archivos sin modificar; referencias/hashes en el contrato. No se publican tokens ni enlaces temporales.

Validación complementaria local y publicación remota parcial completadas el 2026-10-14. El estado editorial «definitivo» no acredita que las 247 filas tengan guía ni logo: GitHub Raw confirma 234 logos; quedan 13 pendientes. La publicación EPG anterior tenía 57 mapas y 190 pendientes. La continuación visual agregó cinco asignaciones: el contrato cuenta 62 guías y 185 pendientes; run `38613423120` publicó salida `09e19e6` y Raw confirmó los cinco IDs en `epg.xml` y fuera de `epg-pending.json`.

## Seguimiento de publicación — 2026-10-14

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
| 391 | ESPN 6 [IP 45.171.64.30] · señal 2 | logos/catalogue/espn-6-lam.png | PENDIENTE: regional_feed_not_identified |
| 392 | France24 [IP 45.171.64.30] | logos/france24.svg | PENDIENTE: regional_feed_not_identified |
| 393 | Golden [IP 45.171.64.30] | logos/catalogue/golden-mx.png | PENDIENTE: regional_feed_not_identified |
| 394 | Golf Channel HD [IP 45.171.64.30] | logos/catalogue/golfchannellatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 395 | Guatevision - GUA [IP 45.171.64.30] | logos/catalogue/guatevision-gt.png | gt/Guatevision.gt (109.39 h) |
| 396 | H2 [IP 45.171.64.30] | logos/catalogue/history2latinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 397 | HBO XTREME [IP 45.171.64.30] | logos/catalogue/hboxtremelatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 398 | History Channel [IP 45.171.64.30] | logos/catalogue/history-channel-lam.png | PENDIENTE: regional_feed_not_identified |
| 399 | History HD [IP 45.171.64.30] | logos/catalogue/history-channel-lam.png | PENDIENTE: regional_feed_not_identified |
| 400 | Home Garden Latino [IP 45.171.64.30] | logos/catalogue/hgtvlatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 401 | LIFE TIME [IP 45.171.64.30] | logos/catalogue/lifetimelatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 402 | La voz de Maria [IP 45.171.64.30] | logos/catalogue/lavozdemaria-do.png | PENDIENTE: regional_feed_not_identified |
| 403 | AyM Sports [IP 45.171.64.30] | logos/catalogue/aymsports-mx.png | PENDIENTE: regional_feed_not_identified |
| 404 | Multicinema [IP 45.171.64.30] | PENDIENTE | PENDIENTE: regional_feed_not_identified |
| 405 | Fox Sports [IP 45.171.64.30] | logos/fox-sports.svg | PENDIENTE: regional_feed_not_identified |
| 406 | A3Cine [IP 45.171.64.30] | PENDIENTE | PENDIENTE: regional_feed_not_identified |
| 407 | Pasiones HD [IP 45.171.64.30] | logos/catalogue/pasioneslatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 408 | Pregon Infirmativo [IP 45.171.64.30] | PENDIENTE | PENDIENTE: regional_feed_not_identified |
| 409 | La Red TV [IP 45.171.64.30] | logos/catalogue/laredtv-gt.png | PENDIENTE: regional_feed_not_identified |
| 410 | RCN Novelas [IP 45.171.64.30] | logos/catalogue/rcnnovelas-co.png | co1/RCN.Novelas.co |
| 411 | Radio renecer [IP 45.171.64.30] | PENDIENTE | PENDIENTE: regional_feed_not_identified |
| 412 | SEMILLITAS [IP 45.171.64.30] | logos/catalogue/semillitastv-us.png | PENDIENTE: regional_feed_not_identified |
| 413 | SONY [IP 45.171.64.30] | logos/catalogue/sonychannelandes-us.png | PENDIENTE: regional_feed_not_identified |
| 414 | SPACE [IP 45.171.64.30] | logos/catalogue/space-ar.png | PENDIENTE: regional_feed_not_identified |
| 415 | Sony Movies HD [IP 45.171.64.30] | logos/catalogue/sonymovieslatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 416 | Studio Universal [IP 45.171.64.30] | logos/catalogue/studiouniversallatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 417 | Studio Universal HD [IP 45.171.64.30] | logos/catalogue/studiouniversallatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 418 | TBN Enlace [IP 45.171.64.30] | logos/catalogue/enlace-cr.png | PENDIENTE: regional_feed_not_identified |
| 419 | TNT Novelas [IP 45.171.64.30] | logos/catalogue/tntnovelas-us.png | PENDIENTE: regional_feed_not_identified |
| 420 | TD+2 HD CR [IP 45.171.64.30] | logos/catalogue/tdmas2-cr.png | PENDIENTE: regional_feed_not_identified |
| 421 | TD+HD CR [IP 45.171.64.30] | logos/catalogue/tdmas-cr.png | PENDIENTE: regional_feed_not_identified |
| 422 | TLC [IP 45.171.64.30] | logos/catalogue/tlclatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 423 | Discovery Channel [IP 45.171.64.30] · señal 2 | logos/catalogue/discoverychannellatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 424 | TNT Series [IP 45.171.64.30] | logos/catalogue/tntserieslatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 425 | Telemundo [IP 45.171.64.30] | logos/catalogue/telemundointernacional-us.png | PENDIENTE: regional_feed_not_identified |
| 426 | Telemundo HD [IP 45.171.64.30] | logos/catalogue/telemundointernacional-us.png | PENDIENTE: regional_feed_not_identified |
| 427 | Televida RD [IP 45.171.64.30] | logos/catalogue/televida-do.png | PENDIENTE: regional_feed_not_identified |
| 428 | UNIVERSAL COMEDY HD [IP 45.171.64.30] | logos/catalogue/universalcomedy-us.png | PENDIENTE: regional_feed_not_identified |
| 429 | UNIVERSAL CRIME HD [IP 45.171.64.30] | logos/catalogue/universalcrime-us.png | PENDIENTE: regional_feed_not_identified |
| 430 | UNIVERSAL PREMIERE HD [IP 45.171.64.30] | logos/catalogue/universalpremiere-us.png | PENDIENTE: regional_feed_not_identified |
| 431 | UNIVERSAL PREMIERE O HD [IP 45.171.64.30] | logos/catalogue/universalpremiere-us.png | PENDIENTE: regional_feed_not_identified |
| 432 | Universal [IP 45.171.64.30] | logos/catalogue/universaltvlatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 433 | Univision HD [IP 45.171.64.30] | logos/catalogue/univisionlatinamerica-mx.png | PENDIENTE: regional_feed_not_identified |
| 434 | WARNER HD [IP 45.171.64.30] | logos/catalogue/warnerchannel-us.png | PENDIENTE: regional_feed_not_identified |
| 435 | Warner [IP 45.171.64.30] | logos/catalogue/warnerchannel-us.png | PENDIENTE: regional_feed_not_identified |
| 436 | ZooMoo [IP 45.171.64.30] | logos/catalogue/zoomoo-sg.png | PENDIENTE: regional_feed_not_identified |
| 437 | ctv [IP 45.171.64.30] | PENDIENTE | PENDIENTE: regional_feed_not_identified |
| 438 | la liga [IP 45.171.64.30] | PENDIENTE | PENDIENTE: regional_feed_not_identified |
| 439 | Discovery World HD [IP 168.196.127.137] | logos/catalogue/discoveryworld-us.png | cl/Canal.Discovery.World.Latinoamérica.cl |
| 440 | TELEHIT LATINIO [IP 190.61.47.54] | logos/catalogue/telehitmusica-mx.png | PENDIENTE: regional_feed_not_identified |
| 441 | UNIVERSAL CINEMA ESTE HD [IP 168.196.127.137] | logos/catalogue/universalcinema-us.png | PENDIENTE: regional_feed_not_identified |
| 442 | A&E-IXP [IP 138.59.177.78] | logos/catalogue/a-and-e-ar.png | PENDIENTE: regional_feed_not_identified |
| 443 | AMC-IXP [IP 138.59.177.78] | logos/catalogue/amclatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 444 | ANIMAL PLANET-IXP [IP 138.59.177.78] | logos/catalogue/animalplanetlatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 445 | BABY TV-IXP [IP 138.59.177.78] | logos/catalogue/babytv-uk.png | PENDIENTE: regional_feed_not_identified |
| 446 | CINEMAX-IXP [IP 138.59.177.78] | logos/catalogue/cinemaxlatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
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

- 358 pruebas Python, 19 omitidas previstas por `M3U_RUNNER_TESTS=1`; el recuento incluye la nueva regresión para las cinco guías confirmadas en emulador. No se modificó JavaScript.
- `update_m3u.py --validate-public-lists-only`: partición válida de Lista 1 292, Lista 2 0 y catálogo canónico 2.056.
- Bundle temporal del editor: 629 filas y 487 logos. Los 106 archivos registrados para esta oficialización mantienen los SHA-256 del contrato.
- Comparación editorial contra `4efa5286`: exactamente las 247 marcas de prueba se retiraron; los demás campos, orden, nombres, identidad, altas/bajas, respaldos y selección se conservaron.
- Smoke JVM de la primera publicación usando el parser y catálogo del tag publicado VibeM3U `v0.5.95` (incluida la clase `DynamicSourceReference` de `e395b9d`): las 247 identidades, nombres y URLs entran una sola vez y la proyección queda en 303 canales visibles. Ese smoke precede a los dos PNG de Guatemala; no se compiló una APK ni se repitió el smoke de app para esos assets, tampoco se probó en TV física.
- Las 51 fuentes EPG de la primera validación produjeron 4.017 programas reales. Con Guatemala, un build local aislado sobre cinco IDs exactos produjo 537 programas sin relleno `Live`. Luego, la captura del emulador de Fox Sports 2 México (#40) a las 09:16 Santiago / 12:16 UTC mostró `#FOXGOL`/CONCACAF W; el feed MX1 coincidió con `Fox Gol Femenil`. El commit `dfa52e1` asignó `Canal.Fox.Sports.2.(México).mx`; `Actualizar EPG` run `38565913595` terminó success y publicó la salida `56d27af`. GitHub Raw confirma el canal con fuente `mx1`, 60 programas y fuera de `epg-pending.json`. La continuación local asigna otras cinco identidades exactas (detalladas arriba), llevando el contrato a 62/247 y dejando 185 pendientes; el workflow todavía debe publicar esta tanda y Raw debe confirmarla. No se publican títulos `Live` inventados.
- No se modificaron la aplicación ni la selección de resolutores. La rama se actualizó desde `aec3847` para incorporar cinco commits automáticos del runner antes de la publicación.

## Publicación

La continuación visual se publicó en el commit `4bf7ef9`; el workflow [Actualizar EPG 38613423120](https://github.com/SPxMM3R1/lista-m3u/actions/runs/38613423120) terminó `success` y generó `09e19e6`. Raw se comprobó directamente en `epg.xml`, los cinco `epg/canales/<tvg-id>.xml` y `epg-pending.json`: #143, #145, #151, #160 y #252 tienen respectivamente 73, 36, 61, 38 y 66 programas, coberturas futuras continuas de 53,88–62,72 h y ya no están pendientes. Total publicado: 62/247 canales asignados a guía; 185 permanecen pendientes. Los 247 canales sí están en estado editorial definitivo, pero eso no acredita que todos tengan guía; 13 logos también siguen pendientes.

### Publicación inicial — Fox Sports 2 México (#40)

El commit de asignación `dfa52e1` se publicó en `main`; el workflow [Actualizar EPG 38565913595](https://github.com/SPxMM3R1/lista-m3u/actions/runs/38565913595) terminó `success` y generó `56d27af`. Se verificó GitHub Raw en `epg.xml`, el fragmento `epg/canales/Nauta.7b8890eac450f9cc89b06b84@Nauta.xml` y `epg-pending.json`: Fox Sports 2 #40 tiene fuente `mx1`, 60 programas y no está pendiente. La EPG local del mismo ID cubría 64,44 h. ESPN Plus HD #107 queda pendiente porque la fuente AR1 disponible no contiene la identidad ESPN Premium mostrada por el emulador. No completar por aproximación.
