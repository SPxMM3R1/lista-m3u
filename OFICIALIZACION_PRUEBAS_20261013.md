# Oficialización de pruebas — 2026-10-13

Pedido «Todas las pruebas»: 247 activos en prueba de Lista 1 pasan a definitivos sin mover ni borrar filas ni alterar respaldos; 38 referencias Nauta exactas se agregan a la excepción cerrada (42 con las cuatro históricas). Tras la comprobación adicional de Guatemala: logos comprobados para 234, 13 pendientes; EPG curada para 56 con cobertura continua de al menos 12 h al validar, 191 pendientes por identidad regional no comprobada o fuente insuficiente. No afirmar EPG/logo completo: definitivo es estado editorial, no prueba de guía/estabilidad. Sin Live inventado, canales nuevos, selector Android, cambios de app ni APK. Contrato contracts/trial-officialization-20261013.json; pendientes por identidad en esta bitácora. Mantener futuras altas en prueba y no oficializar referencias Nauta fuera de las 42 exactas sin pedido explícito.

## Alcance y límites

Usuario: «puedes pasar todos los canales ... a definitivo y darles logo y EPG»; aclaración: «Todas las pruebas» = todos los activos en prueba de Lista 1, no ocultos/papelera ni todo el inventario.

Matched means exact curated national/regional source with continuous 12h at validation; Total Conexion region is supported by prior SDT/operator evidence. A FreeEPG Guatemala feed was fetched on 2026-10-14; its current XML had 155 channel IDs, including exact current IDs for Canal 13/Trecevisión, Canal 3, Canal 7/Televisiete, Canal Antigua and Guatevisión, each with 109.39–110.14 continuous hours. The five local names explicitly contain GUA; no region was inferred from IP. The FreeEPG country page lists 160 channels and itself cautions there is no completeness guarantee: https://free-epg.de/countries/gt. The feed also had stale duplicate IDs for four channels; only the IDs with continuous current data were mapped. This is not proof of synchrony of every programme in physical TV. Other unknown regional feeds remain pending; no other region is assigned by similarity and no continuity Live is fabricated. Definitive remains an editorial state, not proof of availability or complete guide.

Región de Total Conexión: SDT/operador colombiano documentado en la investigación del 12-10, no inferida por geolocalización de IP. Para canales panregionales de Discovery se compararon CL/MX y coincidieron todos los tramos/títulos de las próximas 12 h. No es prueba contemporánea del contenido de todos los programas en cada señal ni TV física. Logos reales PNG/SVG, archivos sin modificar; referencias/hashes en el contrato. No se publican tokens ni enlaces temporales.

Validación complementaria local completada el 2026-10-14. El estado editorial «definitivo» no acredita que las 247 filas tengan guía ni logo: siguen pendientes 13 logos y 191 mapas de EPG. Los cinco mapas guatemaltecos se probaron con el runner real a partir del XMLTV consultado hoy; esa prueba de subconjunto no sustituye la generación consolidada ni la ejecución remota.

## Seguimiento de publicación — 2026-10-14

El workflow automático `Actualizar EPG` 38553076460 terminó success, pero su plan seleccionó cero fuentes y solo volvió a unir fragmentos. La comprobación directa de `origin/main:epg.xml` encontró las cinco identidades GT todavía con `data-guide="pendiente de guia"` y sin programas; ese éxito no confirma su cobertura. Tras publicar el sello corregido, se debe ejecutar `Actualizar EPG` manualmente con `fuentes=gt`, comprobar al menos 12 horas continuas para cada identidad y verificar GitHub Raw.

El workflow `Publicar cambios dirigidos` 38552828375 falló con pruebas históricas de catálogo (incluidos `KeyError: 'trial'` y desajustes respecto del baseline) porque `data/channel-editor-layout.json` conservaba un `approval.sha256` obsoleto tras añadir los logos. El sello se recalculó con `tests.catalog_approval.layout_approval_digest`; valor almacenado y calculado coinciden localmente y la suite CI-parity pasó (355 pruebas, 19 omitidas). Publicar y revalidar remotamente antes de considerar cerrado el seguimiento. Esta corrección no altera datos editoriales.

| Número | Canal | Logo | EPG |
|---:|---|---|---|
| 40 | Fox Sports 2 \| HD [Nauta] | logos/catalogue/fox-sports-2-lam.png | PENDIENTE: regional_feed_not_identified |
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
| 143 | AXN HD [Nauta] | logos/catalogue/axnlatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 145 | Cinemax HD [Nauta] | logos/catalogue/cinemaxlatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 146 | Discovery Channel HD [Nauta] | logos/catalogue/discoverychannellatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
| 147 | Discovery Theater HD [Nauta] | logos/catalogue/discoverytheaterlatinamerica-us.png | cl/Canal.Discovery.Theater.(Latinoamérica).cl |
| 148 | Discovery Turbo [Nauta] | logos/catalogue/discoveryturbolatinamerica-us.png | cl/Canal.Discovery.Turbo.(Latinoamérica).cl |
| 149 | Discovery Turbo HD [Nauta] | logos/catalogue/discoveryturbolatinamerica-us.png | cl/Canal.Discovery.Turbo.(Latinoamérica).cl |
| 150 | Discovery World [Nauta] | logos/catalogue/discoveryworld-us.png | cl/Canal.Discovery.World.Latinoamérica.cl |
| 151 | ESPN HD [Nauta] | logos/espn.svg | PENDIENTE: regional_feed_not_identified |
| 152 | ESPN 3 HD [Nauta] | logos/espn-3.png | PENDIENTE: regional_feed_not_identified |
| 153 | ESPN 4 \| Sur [Nauta] | logos/espn-4.png | PENDIENTE: regional_feed_not_identified |
| 156 | Fox Sports HD [Nauta] | logos/fox-sports.svg | PENDIENTE: regional_feed_not_identified |
| 160 | Star Channel HD [Nauta] | logos/catalogue/starchannellatinamerica-us.png | PENDIENTE: regional_feed_not_identified |
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
| 252 | Sony Channel Andes [IP 181.119.66.28] | logos/catalogue/sonychannelandes-us.png | PENDIENTE: regional_feed_not_identified |
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

- 355 pruebas Python, 19 omitidas previstas por `M3U_RUNNER_TESTS=1`; 55 pruebas JavaScript.
- `update_m3u.py --validate-public-lists-only`: partición válida de Lista 1 292, Lista 2 0 y catálogo canónico 2.056.
- Bundle temporal del editor: 629 filas y 487 logos. Los 106 archivos registrados para esta oficialización mantienen los SHA-256 del contrato.
- Comparación editorial contra `4efa5286`: exactamente las 247 marcas de prueba se retiraron; los demás campos, orden, nombres, identidad, altas/bajas, respaldos y selección se conservaron.
- Smoke JVM de la primera publicación usando el parser y catálogo del tag publicado VibeM3U `v0.5.95` (incluida la clase `DynamicSourceReference` de `e395b9d`): las 247 identidades, nombres y URLs entran una sola vez y la proyección queda en 303 canales visibles. Ese smoke precede a los dos PNG de Guatemala; no se compiló una APK ni se repitió el smoke de app para esos assets, tampoco se probó en TV física.
- Las 51 fuentes EPG de la primera validación produjeron 4.017 programas reales. Con la fuente Guatemala, un build local aislado del runner sobre los cinco IDs exactos produjo 537 programas, sin canales pendientes ni títulos/descripciones `Live` de relleno. El test confirma que esos IDs activan solo el feed `gt`. El build consolidado de los 56 mapas todavía debe confirmarse en el workflow; 191 canales siguen pendientes de identidad regional/fuente fiable, y no se publican títulos `Live` inventados.
- No se modificaron la aplicación ni la selección de resolutores. La rama se actualizó desde `aec3847` para incorporar cinco commits automáticos del runner antes de la publicación.

## Publicación

Commit, push y resultados remotos pendientes. La verificación final deberá comprobar los 247 estados definitivos, los 234 logos, los 56 mapas EPG y los 191 casos pendientes después de que terminen los workflows.
