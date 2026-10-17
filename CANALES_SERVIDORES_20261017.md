# Señales del escaneo de catálogos de servidores — 2026-10-17

4510 señales del escaneo de catálogos agregadas al final de Lista 1, números 503–5012, todas activas/en prueba/sin EPG y sin mantenimiento automático. De 5635 filas nuevas del escaneo, 1018 no pasaron video/audio y 107 ya existían. Sin exclusiones por nombre, por pedido explícito («Agrega todo todo»): se incluyen adultos y placeholders. Registro: contracts/server-catalogues-expansion-20261017.json.

Método: se consultó el endpoint público documentado de HTTP Play de Astra (`/playlist.m3u8`) en las direcciones ya conocidas del inventario; cada fila nueva se verificó con ffmpeg (video en dos pasadas y audio) y los fotogramas quedaron en `outputs/catalog-scan-20261017/bulk-verify/frames/`. La revisión visual fue por muestreo con hojas de contactos; no es prueba de estabilidad ni de región/EPG.

| Rango de números | Señales | Grupo |
|---:|---:|---|
| 503–5011 | 975 | Películas |
| 507–4948 | 98 | Música |
| 508–5012 | 2788 | Misceláneos |
| 512–5006 | 434 | Deportes |
| 524–4955 | 180 | Noticias internacionales |
| 789–4965 | 35 | Adultos |

Descartadas: 880 sin video, 138 sin audio y 107 ya presentes; el detalle completo está en el contrato.

