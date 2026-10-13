# Canales directos adicionales — 2026-10-12

Origen de ESPN3 Sur: http://181.78.12.119:16123/play/ch18/index.m3u8. Incorporado originalmente desde iptv-org en 1ae8fb9; no es el Win Sports que anuncia el catálogo de origen. ESPN5 Sur sale de ch19. Los 62 Total Conexión previos ya están publicados en bb0dbec y se conservaron.

Búsqueda ampliada: 229 endpoints públicos exactos de 75 servidores. 155 muestras con vídeo decodificado; 120 altas iniciales tras revisión visual, audio decodificado y deduplicación de nombres. A la fecha de esta purga, 86 de las otras entradas ya estaban en papelera y 11 seguían activas en pruebas. Por solicitud del usuario, 23 canales colombianos se purgaron permanentemente del inventario. Las alternativas a canales existentes conservan identidad independiente y no se enlazan como backup automáticamente.

Fuente: https://iptv-org.github.io/api/streams.json (metadatos: https://iptv-org.github.io/api/channels.json). No se escanearon IP, puertos ni rutas adivinadas. Sin autenticación, credenciales, URL firmadas o DRM. No se garantiza la autorización de redistribución de terceros por ser enlaces públicos; son pruebas técnicas, no señales oficiales ni disponibilidad 24/7.

Estado actual: de las 120 identidades originales, 23 colombianas se purgaron permanentemente, 86 de las otras identidades ya estaban en papelera y 11 continúan activas en pruebas de Lista 1, sin EPG ni mantenimiento automático. El registro conserva historial técnico, marcando las 23 como retiradas. Se preservan los números de las filas restantes y la selección Highfly/TvVoo; sin cambios de EPG, resolutores o app.

Validación de incorporación original: 332 tests Python (19 omitidos por las condiciones documentadas del catálogo vivo), 54 tests JavaScript, materialización editorial dirigida sin red y bundle del editor con 509 filas/381 logos. Comparación con el commit anterior: filas, numeración, tombstones, selección y registros M3U previos intactos; 120 altas exactas; alias `1.m3u` idéntico a `m3u.m3u`; las nuevas identidades no entran a `main_playlist_channels()` para EPG. Smoke JVM con el parser M3U Android del diagnóstico existente: 120 entradas únicas, nombres y URLs intactos. Este último es compatibilidad de sintaxis, no compilación de la APK actual ni prueba de reproducción en dispositivo.

Validación de esta purga: runner dirigido `targeted_update.py --mode presentation` correcto; contrato de resolutores válido y partición esperada de Lista 1=149, Lista 2=0, inventario=1913. Las pruebas completas pasan: 347 Python (19 omitidas) y 55 JavaScript. Bundle local: 486 filas/381 logos. Auditoría diferencial: los 23 IDs purgados no aparecen en inventario, Lista 1 ni alias; las demás entradas M3U y sus números, selección de proveedores y archivos EPG son idénticos al remoto previo. De las otras 97 identidades, 11 siguen activas en prueba y 86 ya estaban en papelera. No se ejecutó ni cambió la EPG.

### Retirados a petición del usuario

Estas 23 identidades se eliminaron del layout y se añadieron a las exclusiones permanentes del catálogo. Los datos de origen quedan solo como historial de la búsqueda en el registro JSON; el runner/editor no las reimportará automáticamente. Se conservaron los números del resto.

| Número original | Canal | tvg-id |
|---:|---|---|
| 230 | Cablenoticias | PublicDirect.b804a3242510983bcd2a8451 |
| 232 | Canal RCN | PublicDirect.f7581dfc601fe4945e4aa39a |
| 233 | Canal TRO | PublicDirect.dfefecac47a358a0a295a89b |
| 234 | Caracol HD2 | PublicDirect.e4c282490698f9a367208c0e |
| 248 | NTN24 | PublicDirect.065b8e74a7bc4134dac42de2 |
| 249 | Nuestra Tele Internacional | PublicDirect.4aaac8a400eac6f66c722d66 |
| 250 | RCN HD2 | PublicDirect.0b220da8860efb37ce20c6c7 |
| 251 | RCN Novelas | PublicDirect.006c49f2cfe7afdb305243a4 |
| 254 | Teleantioquia | PublicDirect.2242f841e1405e7ca2d2377f |
| 255 | Telecafe | PublicDirect.f6605c233a009ba8793c424b |
| 256 | Teleislas | PublicDirect.ce9edfb96c92708a4ca60a18 |
| 272 | Canal 1 | PublicDirect.e4a4e35ac0fc5608f57e217b |
| 275 | Canal Capital | PublicDirect.3d00b42b6fc798a63d77698f |
| 276 | Canal Institucional | PublicDirect.6c8980b7d504a209a136a75e |
| 278 | Caracol Internacional | PublicDirect.ab5239c18b2d12410e09d809 |
| 282 | Citytv Bogota | PublicDirect.38bd89c76a483162b3098d4d |
| 285 | CNC Medellin | PublicDirect.0a897ca8e20f7d10a280b21f |
| 320 | Raizal TV | PublicDirect.42f1c84a3802598a19ce4ed4 |
| 321 | RCN Mas | PublicDirect.d76d8dd3c1fd6aa84083718b |
| 327 | Tele Amiga | PublicDirect.5e4b74aa176f8a40cccb0a8a |
| 328 | Telecaribe | PublicDirect.de525c8b61d340ddca436806 |
| 333 | TeleNostalgia | PublicDirect.9d462a4134275f651bddf428 |
| 334 | Telepacifico | PublicDirect.7cee7dce1d148574afac1fde |

Los fotogramas/segmentos de diagnóstico quedan fuera de Git, en outputs/public-direct[-broader]-20261012 del chat coordinador. El registro seguro versionado contiene codecs, resolución, audio, fecha de muestra, fuente, exclusiones y números.

### Otras entradas del hallazgo no incluidas en esta purga (97)

La siguiente tabla conserva evidencia técnica de las otras 97 identidades originales; **no significa que las 97 sigan activas**. En el layout actual, 86 están en papelera y 11 permanecen activas en pruebas. Las 23 purgadas aparecen en la sección anterior.

| Número | Canal | Vídeo observado | Audio |
|---:|---|---|---|
| 226 | AXN [IP 181.78.8.199] | 1920×1080, 30000/1001 fps, h264 | aac |
| 227 | BabyFirst Spanish [IP 181.78.106.127] | 544×480, 30000/1001 fps, h264 | aac |
| 228 | Bandamax [IP 181.78.106.127] | 1920×1080, 60000/1001 fps, h264 | ac3 |
| 229 | bitMe [IP 181.119.66.28] | 1920×1080, 30/1 fps, h264 | aac |
| 231 | Canal 3 [IP 181.119.177.253] | 544×480, 30000/1001 fps, h264 | aac |
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
| 252 | Sony Channel Andes [IP 181.119.66.28] | 1920×1080, 60000/1001 fps, h264 | aac |
| 253 | Star Channel [IP 181.119.66.28] | 1920×1080, 30000/1001 fps, h264 | aac |
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
| 273 | Canal 4 Posadas [IP 190.128.214.97] | 1280×720, 25/1 fps, h264 | aac |
| 274 | Canal 56 Quiero TV [IP 45.5.118.152] | 1920×1080, 30000/1001 fps, h264 | aac |
| 277 | Canal N [IP 190.108.91.206] | 720×480, 60000/1001 fps, h264 | mp2 |
| 279 | Caras TV [IP 190.61.90.17] | 544×480, 25/1 fps, h264 | aac |
| 280 | Cartoon Network [IP 158.172.217.18] | 720×480, 30000/1001 fps, mpeg2video | mp2, mp2 |
| 281 | Chikitoonz [IP 45.70.201.81] | 1920×1080, 30000/1001 fps, h264 | aac |
| 283 | Claro Cinema [IP 158.172.217.18] | 720×480, 30000/1001 fps, mpeg2video | mp2 |
| 284 | Claro Sports 2 [IP 45.171.64.30] | 544×480, 30000/1001 fps, h264 | aac |
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
| 322 | Regional TV Yaguaron [IP 190.128.214.97] | 1280×720, 30000/1001 fps, h264 | aac |
| 323 | Rumbo Minero TV [IP 45.70.201.81] | 1280×720, 30000/1001 fps, h264 | aac |
| 324 | Sun Channel [IP 168.196.127.137] | 544×480, 30000/1001 fps, h264 | aac, aac |
| 325 | TCM [IP 45.171.64.30] | 544×480, 60000/1001 fps, h264 | aac, aac |
| 326 | TC Television [IP 177.234.218.66] | 720×480, 30000/1001 fps, mpeg2video | ac3 |
| 329 | Telefe [IP 45.173.231.22] | 720×480, 30000/1001 fps, mpeg2video | mp2 |
| 330 | Telefe Internacional [IP 190.108.83.69] | 720×480, 60000/1001 fps, h264 | mp2 |
| 331 | Telefuturo [IP 158.172.217.18] | 1920×1080, 60000/1001 fps, h264 | mp2 |
| 332 | TeleHit [IP 200.115.120.1] | 720×480, 30000/1001 fps, mpeg2video | mp2 |
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
