# Canales del catálogo comunitario — 2026-10-17

14 señales del catálogo comunitario agregadas al final de Lista 1, números 489–502, todas activas/en prueba/sin EPG y sin mantenimiento automático. De 85 candidatos saneados, 45 ya estaban publicados con el mismo endpoint y 26 no decodificaron video; solo las verificadas con video y audio son altas. Se conservan filas, números, exclusiones y selección; fuentes independientes, sin respaldos automáticos. Registro: contracts/community-catalogue-expansion-20261017.json. VibeM3U existente v0.5.95 (e395b9d); sin commit hermano ni APK.

Fuente: gist público ac1a002b5c442908f134dd4958579ec2 (`iptv.m3u`), consultado el 2026-10-17. El barrido cruzó sus entradas contra los hosts numéricos ya usados por el catálogo y descartó credenciales, query, fragmentos y rutas con tokens; nunca se recorren IP ni puertos fuera de lo publicado.

Verificación: ffmpeg con dos pasadas (reintento de fallos) sobre las 85 URLs saneadas; las 14 altas decodificaron video y audio y se revisaron visualmente en un mosaico. Los fotogramas quedan fuera de Git, en `outputs/direct-ip-expansion-20261017T023049Z/verify-20261017/`.

Estado: Lista 1, en prueba, sin EPG y sin mantenimiento automático. No se cambiaron números/órdenes anteriores, bajas, selección Highfly/TvVoo, resolutores, EPG ni app. Sin APK ni commit hermano nuevo.

| Número | Canal añadido | Grupo | Video observado | Audio |
|---:|---|---|---|---|
| 489 | CNC Medellin [IP 138.94.3.106] | Misceláneos | 1280x720 · h264 | decodificado |
| 490 | History Latin America [IP 15.204.246.24] | Misceláneos | 1920x1080 · h264 | decodificado |
| 491 | Caracol Internacional [IP 167.249.23.102] | Misceláneos | 720x480 · h264 | decodificado |
| 492 | BabyFirst Spanish [IP 168.196.127.137] | Misceláneos | 544x480 · h264 | decodificado |
| 493 | Semillitas TV [IP 168.196.127.137] | Misceláneos | 544x480 · h264 | decodificado |
| 494 | Tigo Sports (Honduras) [IP 168.196.127.137] | Deportes | 720x480 · h264 | decodificado |
| 495 | Discovery Kids Latin America [IP 181.224.200.5] | Misceláneos | 1920x1080 · h264 | decodificado |
| 496 | Cablenoticias [IP 181.78.211.244] | Noticias internacionales | 1920x1080 · h264 | decodificado |
| 497 | TNT Latin America Colombia [IP 181.78.211.244] | Películas | 720x480 · mpeg2video | decodificado |
| 498 | Galavision West [IP 200.115.120.1] | Películas | 720x480 · mpeg2video | decodificado |
| 499 | Guatevision [IP 200.115.120.1] | Misceláneos | 544x480 · h264 | decodificado |
| 500 | Telefe Internacional [IP 200.115.120.1] | Misceláneos | 544x480 · h264 | decodificado |
| 501 | Disney Channel Latin America Mexico [IP 45.166.93.156] | Misceláneos | 544x480 · h264 | decodificado |
| 502 | Nuestra Tele Internacional [IP 45.173.231.22] | Misceláneos | 720x480 · h264 | decodificado |

Notas de fotograma:
- Caracol Internacional [IP 167.249.23.102]: Fotograma de Noticias Caracol en exteriores; marca WIN en sobreimpresión.
- Tigo Sports (Honduras) [IP 168.196.127.137]: Fotograma deportivo con marcas FOX/NCAA; no confirma programa ni región.
- TNT Latin America Colombia [IP 181.78.211.244]: Fotograma de película sin marca clara.
- Galavision West [IP 200.115.120.1]: El fotograma muestra la marca TU MÚSICA; se conserva el nombre del catálogo comunitario, sin corregir ni inferir identidad.

Descartados: 45 candidatos ya publicados con el mismo endpoint (mismo host y ruta en `channel-catalog.m3u`) y 26 sin video decodificado en dos intentos. La región no se infiere de la IP ni del nombre del catálogo comunitario; una muestra positiva no garantiza continuidad.

La autorización y el alcance exactos están en `contracts/community-catalogue-expansion-20261017.json`.

