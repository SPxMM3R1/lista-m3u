# Canales directos adicionales — 2026-10-12

Origen de ESPN3 Sur: http://181.78.12.119:16123/play/ch18/index.m3u8. Incorporado originalmente desde iptv-org en 1ae8fb9; no es el Win Sports que anuncia el catálogo de origen. ESPN5 Sur sale de ch19. Los 62 Total Conexión previos ya están publicados en bb0dbec y se conservaron.

Búsqueda ampliada: 229 endpoints públicos exactos de 75 servidores. 155 muestras con vídeo decodificado; 120 altas tras revisión visual, audio decodificado y deduplicación de nombres de la búsqueda. Las alternativas a canales existentes conservan identidad independiente y no se enlazan como backup automáticamente.

Fuente: https://iptv-org.github.io/api/streams.json (metadatos: https://iptv-org.github.io/api/channels.json). No se escanearon IP, puertos ni rutas adivinadas. Sin autenticación, credenciales, URL firmadas o DRM. No se garantiza la autorización de redistribución de terceros por ser enlaces públicos; son pruebas técnicas, no señales oficiales ni disponibilidad 24/7.

Estado: Lista 1, en prueba, sin EPG y sin mantenimiento automático. No se cambiaron números/órdenes anteriores, bajas, selección Highfly/TvVoo, resolutores o app. Sin APK ni commit hermano nuevo.

Validación previa a publicar: 332 tests Python (19 omitidos por las condiciones documentadas del catálogo vivo), 54 tests JavaScript, materialización editorial dirigida sin red y bundle del editor con 509 filas/381 logos. Comparación con el commit anterior: filas, numeración, tombstones, selección y registros M3U previos intactos; 120 altas exactas; alias `1.m3u` idéntico a `m3u.m3u`; las nuevas identidades no entran a `main_playlist_channels()` para EPG. Smoke JVM con el parser M3U Android del diagnóstico existente: 120 entradas únicas, nombres y URLs intactos. Este último es compatibilidad de sintaxis, no compilación de la APK actual ni prueba de reproducción en dispositivo.

Los fotogramas/segmentos de diagnóstico quedan fuera de Git, en outputs/public-direct[-broader]-20261012 del chat coordinador. El registro seguro versionado contiene codecs, resolución, audio, fecha de muestra, fuente, exclusiones y números.

| Número | Canal | Vídeo observado | Audio |
|---:|---|---|---|
| 226 | AXN [IP 181.78.8.199] | 1920×1080, 30000/1001 fps, h264 | aac |
| 227 | BabyFirst Spanish [IP 181.78.106.127] | 544×480, 30000/1001 fps, h264 | aac |
| 228 | Bandamax [IP 181.78.106.127] | 1920×1080, 60000/1001 fps, h264 | ac3 |
| 229 | bitMe [IP 181.119.66.28] | 1920×1080, 30/1 fps, h264 | aac |
| 230 | Cablenoticias [IP 181.78.211.244] | 1920×1080, 30000/1001 fps, h264 | mp2 |
| 231 | Canal 3 [IP 181.119.177.253] | 544×480, 30000/1001 fps, h264 | aac |
| 232 | Canal RCN [IP 181.78.17.228] | 1920×1080, 60000/1001 fps, h264 | mp2 |
| 233 | Canal TRO [IP 190.61.47.54] | 720×480, 60000/1001 fps, h264 | mp2 |
| 234 | Caracol HD2 [IP 181.78.14.26] | 1920×1080, 60000/1001 fps, h264 | mp2 |
| 235 | Cinecanal [IP 181.119.66.28] | 1920×1080, 30000/1001 fps, h264 | aac |
| 236 | De Pelicula [IP 181.119.66.28] | 1920×1080, 60000/1001 fps, h264 | aac |
| 237 | Disney Channel [IP 181.78.8.199] | 1920×1080, 30/1 fps, h264 | aac |
| 238 | Disney Jr. [IP 181.78.14.26] | 1280×720, 30000/1001 fps, h264 | mp2 |
| 239 | Distrito Comedia [IP 181.119.66.28] | 1920×1080, 30/1 fps, h264 | aac |
| 240 | Enlace [IP 181.78.106.127] | 544×480, 30000/1001 fps, h264 | aac |
| 241 | ESPN 3 [IP 181.78.197.59] | 1920×1080, 30000/1001 fps, h264 | aac, aac |
| 242 | FX [IP 181.119.66.28] | 1920×1080, 30000/1001 fps, h264 | aac |
| 243 | Gamavision [IP 181.78.211.244] | 720×480, 60000/1001 fps, h264 | mp2 |
| 244 | Globovision [IP 181.78.8.199] | 720×480, 30000/1001 fps, mpeg2video | mp2 |
| 245 | La Tele Tuya [IP 181.78.8.199] | 720×480, 30000/1001 fps, h264 | aac_latm |
| 246 | Meridiano TV [IP 181.78.8.199] | 720×480, 60000/1001 fps, h264 | aac_latm |
| 247 | National Geographic [IP 181.119.66.28] | 1920×1080, 30000/1001 fps, h264 | aac |
| 248 | NTN24 [IP 181.78.8.199] | 1920×1080, 50/1 fps, h264 | aac |
| 249 | Nuestra Tele Internacional [IP 181.78.8.199] | 1920×1080, 50/1 fps, h264 | aac |
| 250 | RCN HD2 [IP 181.78.14.26] | 1920×1080, 60000/1001 fps, h264 | mp2 |
| 251 | RCN Novelas [IP 181.78.8.199] | 1920×1080, 60000/1001 fps, h264 | aac |
| 252 | Sony Channel Andes [IP 181.119.66.28] | 1920×1080, 60000/1001 fps, h264 | aac |
| 253 | Star Channel [IP 181.119.66.28] | 1920×1080, 30000/1001 fps, h264 | aac |
| 254 | Teleantioquia [IP 181.78.82.130] | 1920×1080, 30000/1001 fps, h264 | mp2 |
| 255 | Telecafe [IP 181.78.82.130] | 720×480, 30000/1001 fps, h264 | mp2 |
| 256 | Teleislas [IP 181.78.211.244] | 720×480, 30000/1001 fps, mpeg2video | mp2 |
| 257 | Telemetro [IP 181.78.121.15] | 1920×1080, 30000/1001 fps, h264 | ac3 |
| 258 | Telesur [IP 181.78.211.244] | 720×480, 60000/1001 fps, h264 | mp2 |
| 259 | Televen [IP 181.78.8.199] | 720×480, 30000/1001 fps, h264 | mp2 |
| 260 | Universal TV [IP 181.119.66.28] | 1920×1080, 30000/1001 fps, h264 | mp2 |
| 261 | Vea Canal [IP 181.78.106.127] | 704×480, 60000/1001 fps, h264 | ac3 |
| 262 | Venevision [IP 181.78.8.199] | 1920×1080, 60000/1001 fps, h264 | aac_latm |
| 263 | A24 [IP 138.59.227.20] | 528×480, 60000/1001 fps, h264 | aac |
| 264 | AMC Series [IP 45.171.64.30] | 544×480, 30000/1001 fps, h264 | aac |
| 265 | Animal Planet [IP 190.128.214.97] | 1920×1080, 30/1 fps, h264 | mp2 |
| 266 | Aunar [IP 190.128.214.97] | 720×576, 50/1 fps, h264 | aac, aac_latm |
| 267 | AyM Sports [IP 168.196.127.137] | 544×480, 30000/1001 fps, h264 | aac |
| 268 | Az Corazon [IP 200.115.120.1] | 544×480, 60000/1001 fps, h264 | aac |
| 269 | Azteca 7 [IP 187.245.231.226] | 1280×720, 30/1 fps, h264 | aac |
| 270 | Azteca Internacional [IP 167.249.23.102] | 544×480, 60000/1001 fps, h264 | aac |
| 271 | Bolivia TV [IP 190.181.61.93] | 1920×1080, 30000/1001 fps, h264 | mp2 |
| 272 | Canal 1 [IP 38.134.250.110] | 720×480, 60000/1001 fps, h264 | mp2 |
| 273 | Canal 4 Posadas [IP 190.128.214.97] | 1280×720, 25/1 fps, h264 | aac |
| 274 | Canal 56 Quiero TV [IP 45.5.118.152] | 1920×1080, 30000/1001 fps, h264 | aac |
| 275 | Canal Capital [IP 190.61.47.54] | 720×480, 30000/1001 fps, h264 | mp2 |
| 276 | Canal Institucional [IP 190.61.47.54] | 720×480, 60000/1001 fps, h264 | mp2 |
| 277 | Canal N [IP 190.108.91.206] | 720×480, 60000/1001 fps, h264 | mp2 |
| 278 | Caracol Internacional [IP 138.59.177.78] | 720×480, 60000/1001 fps, h264 | mp2 |
| 279 | Caras TV [IP 190.61.90.17] | 544×480, 25/1 fps, h264 | aac |
| 280 | Cartoon Network [IP 158.172.217.18] | 720×480, 30000/1001 fps, mpeg2video | mp2, mp2 |
| 281 | Chikitoonz [IP 45.70.201.81] | 1920×1080, 30000/1001 fps, h264 | aac |
| 282 | Citytv Bogota [IP 190.61.47.54] | 720×480, 30000/1001 fps, mpeg2video | mp2 |
| 283 | Claro Cinema [IP 158.172.217.18] | 720×480, 30000/1001 fps, mpeg2video | mp2 |
| 284 | Claro Sports 2 [IP 45.171.64.30] | 544×480, 30000/1001 fps, h264 | aac |
| 285 | CNC Medellin [IP 138.94.3.106] | 1280×720, 30000/1001 fps, h264 | aac |
| 286 | CNN Chile [IP 190.110.96.238] | 720×480, 30000/1001 fps, mpeg2video | mp2 |
| 287 | Cronica TV [IP 190.128.214.97] | 720×576, 50/1 fps, h264 | aac, aac_latm |
| 288 | Discovery Channel [IP 45.171.64.30] | 544×480, 30000/1001 fps, h264 | aac, aac |
| 289 | Discovery Kids [IP 38.134.250.110] | 1920×1080, 30000/1001 fps, h264 | aac |
| 290 | Discovery Science [IP 45.171.64.30] | 544×480, 30000/1001 fps, h264 | aac, aac |
| 291 | Discovery Theater [IP 181.224.200.5] | 1920×1080, 60000/1001 fps, h264 | mp2 |
| 292 | Discovery Turbo [IP 38.134.250.110] | 1920×1080, 30/1 fps, h264 | aac |
| 293 | Educanal [IP 190.128.214.97] | 1920×1080, 30000/1001 fps, h264 | aac |
| 294 | E! [IP 72.1.184.5] | 1920×1080, 30000/1001 fps, h264 | aac |
| 295 | El Trece [IP 190.108.83.69] | 720×480, 60000/1001 fps, h264 | mp2 |
| 296 | El Trece Internacional [IP 200.7.99.59] | 720×480, 60000/1001 fps, h264 | mp2 |
| 297 | Encuentro [IP 138.59.227.20] | 528×480, 60000/1001 fps, h264 | aac |
| 298 | ESPN 2 [IP 190.61.47.54] | 1280×720, 60000/1001 fps, h264 | mp2, mp2, ac3, ac3 |
| 299 | ESPN Premium [IP 190.128.214.97] | 1920×1080, 30000/1001 fps, h264 | mp2 |
| 300 | Exa TV [IP 190.61.90.17] | 544×480, 30000/1001 fps, h264 | aac |
| 301 | Exitosa TV [IP 170.244.209.30] | 720×480, 60000/1001 fps, h264 | mp2 |
| 302 | Film & Arts [IP 200.115.120.1] | 544×480, 30000/1001 fps, h264 | aac, aac |
| 303 | Food Network [IP 168.196.127.137] | 720×480, 60000/1001 fps, h264 | aac |
| 304 | Fox Sports [IP 138.59.227.20] | 1920×1080, 60000/1001 fps, h264 | aac |
| 305 | Golden [IP 181.224.200.5] | 1920×1080, 60000/1001 fps, h264 | mp2 |
| 306 | Golden Edge [IP 181.224.200.5] | 720×480, 60000/1001 fps, h264 | mp2 |
| 307 | Golden Plus [IP 45.5.118.152] | 544×480, 60000/1001 fps, h264 | aac, aac |
| 308 | HBO 2 [IP 45.171.64.30] | 1920×1080, 60000/1001 fps, h264 | aac, aac |
| 309 | HBO Family [IP 45.171.64.30] | 1920×1080, 60000/1001 fps, h264 | aac, aac |
| 310 | HGTV [IP 38.87.224.19] | 720×480, 60000/1001 fps, h264 | mp2 |
| 311 | Hola! TV [IP 168.196.127.137] | 544×480, 30000/1001 fps, h264 | aac |
| 312 | Juntos TV [IP 45.70.201.81] | 1920×1080, 60000/1001 fps, h264 | aac |
| 313 | La Kalle [IP 200.122.223.13] | 1440×1080, 60000/1001 fps, h264 | mp2 |
| 314 | Latele [IP 190.128.214.97] | 1920×1080, 50/1 fps, h264 | aac_latm |
| 315 | MC [IP 168.196.127.137] | 544×480, 30000/1001 fps, h264 | aac |
| 316 | MusicTop [IP 190.128.214.97] | 1920×1080, 25/1 fps, h264 | aac |
| 317 | Nanduti [IP 190.128.214.97] | 1920×1080, 25/1 fps, h264 | aac |
| 318 | Popu TV [IP 190.108.83.69] | 1920×1080, 60000/1001 fps, h264 | mp2 |
| 319 | Productiva TV [IP 190.128.214.97] | 1280×720, 30000/1001 fps, h264 | aac |
| 320 | Raizal TV [IP 200.122.223.13] | 1920×1080, 60000/1001 fps, h264 | mp2 |
| 321 | RCN Mas [IP 45.226.205.96] | 1920×1080, 30000/1001 fps, h264 | aac |
| 322 | Regional TV Yaguaron [IP 190.128.214.97] | 1280×720, 30000/1001 fps, h264 | aac |
| 323 | Rumbo Minero TV [IP 45.70.201.81] | 1280×720, 30000/1001 fps, h264 | aac |
| 324 | Sun Channel [IP 168.196.127.137] | 544×480, 30000/1001 fps, h264 | aac, aac |
| 325 | TCM [IP 45.171.64.30] | 544×480, 60000/1001 fps, h264 | aac, aac |
| 326 | TC Television [IP 177.234.218.66] | 720×480, 30000/1001 fps, mpeg2video | ac3 |
| 327 | Tele Amiga [IP 200.122.223.13] | 1920×1080, 30000/1001 fps, h264 | mp2 |
| 328 | Telecaribe [IP 38.134.250.110] | 720×480, 60000/1001 fps, h264 | mp2 |
| 329 | Telefe [IP 45.173.231.22] | 720×480, 30000/1001 fps, mpeg2video | mp2 |
| 330 | Telefe Internacional [IP 190.108.83.69] | 720×480, 60000/1001 fps, h264 | mp2 |
| 331 | Telefuturo [IP 158.172.217.18] | 1920×1080, 60000/1001 fps, h264 | mp2 |
| 332 | TeleHit [IP 200.115.120.1] | 720×480, 30000/1001 fps, mpeg2video | mp2 |
| 333 | TeleNostalgia [IP 38.134.250.110] | 1920×1080, 30/1 fps, h264 | aac |
| 334 | Telepacifico [IP 190.61.47.54] | 720×480, 60000/1001 fps, h264 | mp2 |
| 335 | Television Publica [IP 190.128.214.97] | 720×576, 50/1 fps, h264 | aac, aac_latm |
| 336 | TLC [IP 38.134.250.110] | 1920×1080, 30/1 fps, h264 | aac |
| 337 | TNT [IP 45.171.64.30] | 1920×1080, 30000/1001 fps, h264 | aac, aac |
| 338 | TNT Series [IP 168.196.127.137] | 1920×1080, 30000/1001 fps, h264 | aac, aac |
| 339 | TUDN [IP 45.5.118.152] | 1280×720, 60/1 fps, h264 | mp2 |
| 340 | TV Aire [IP 190.128.214.97] | 1280×720, 25/1 fps, h264 | aac |
| 341 | TV Peru [IP 181.224.200.5] | 720×480, 60000/1001 fps, h264 | mp2 |
| 342 | TyC Sports USA [IP 45.170.130.224] | 720×480, 30000/1001 fps, mpeg2video | mp2 |
| 343 | Ve Plus Panregional [IP 190.61.114.186] | 1920×1080, 30000/1001 fps, h264 | aac |
| 344 | Willax TV [IP 170.244.209.30] | 720×480, 60000/1001 fps, h264 | mp2 |
| 345 | Zona Latina [IP 45.170.130.224] | 720×480, 30000/1001 fps, mpeg2video | mp2 |

La región no se infiere de la IP ni del nombre publicado: los campos channel/feed del registro son referencias del catálogo externo, no mapeos EPG. Ante señales sin marca clara o imagen corrupta, se omitió la alta. Fallos HTTP/timeout y muestras incompletas son resultados puntuales de esta red, no evidencia de cierre permanente.
