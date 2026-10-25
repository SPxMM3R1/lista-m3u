# Revisión de los servidores (IP) de Lista 1 — 2026-10-25

Pedido: «Revisa las ip de la lista 1 y vee si en esos servidores puedes encontrar as señales qe n tengamos».

Método: se extrajeron los `host:puerto` numéricos de las filas HTTP de `m3u.m3u` (Lista 1) y se
consultó **solo el endpoint público documentado** de Astra HTTP Play (`/playlist.m3u8`) en esos
`host:puerto` ya publicados. No se barrieron puertos, no se usaron credenciales y no se recorrieron
IP fuera de las ya publicadas. Las respuestas se compararon contra `channel-catalog.m3u` (por URL
exacta y por nombre normalizado) y cada candidata se probó con ffmpeg (video y audio decodificados)
en dos pasadas, más fotogramas para identificar el contenido.

## Universo revisado

Lista 1 hoy tiene 78 filas: 30 con URL HTTP en **12 hosts numéricos** y el resto son filas de
resolutor (TVN, Highfly, TvVoo, Nauta), que no exponen catálogo.

| Servidor | Entradas del catálogo | Ya en nuestro catálogo | Sin match | Abren con ffmpeg |
|---|---|---|---|---|
| `138.59.227.20:8000` | 163 | 152 | 11 | 2 |
| `158.172.217.18:8000` | 79 | 70 | 9 | 0 |
| `177.234.218.66:8084` | 83 | 80 | 3 | 2 |
| `181.224.200.5:2277` | 48 | 46 | 2 | 0 |
| `181.78.12.119:16123` | 104 | 104 | 0 | — |
| `181.78.14.26:4000` | 137 | 135 | 2 | 0 |
| `181.78.211.244:8000` | 114 | 114 | 0 | — |
| `190.108.83.69:8000` | 146 | 141 | 5 | 1 (+2 radio) |
| `190.110.96.238:8000` | 129 | 122 | 7 | 1 |
| `200.7.99.59:8000` | 174 | 172 | 2 | 0 (+1 radio) |
| `15.204.246.24:8080` (TVN) | sin catálogo (404) | — | — | — |
| `31.43.191.202:8008` (Eurosport 1 ES) | sin catálogo (404) | — | — | — |

Total: **1.177 entradas** publicadas por esos 10 servidores; 1.136 ya están en el inventario con la
misma URL y 19 más coinciden por nombre. Quedaron 41 sin match, de las que **solo 6 decodifican
video** y, tras identificar el contenido, **2 son señales que no tenemos**.

## Hallazgo: 2 señales nuevas

### 1. `13-LAJA 5 TV` — chilena (Canal 5 Laja, Biobío)

- URL: `http://190.110.96.238:8000/play/a071/index.m3u8`
- Verificación: 1280x720 con audio. Dos fotogramas (3 s y 25 s) muestran el mismo partido en vivo,
  marcador **Laja 3–1 Maipú**, reloj 5:02, estadio CMPC y el logo del **5**.
- No existe en el catálogo (`laja` = 0 coincidencias). Entra en la excepción permanente del usuario
  («haz excepción con todo lo chileno»).
- Identidad propuesta: `PublicDirect.94882052190dee29904d1424`
  (SHA256 de `13-LAJA 5 TV||190.110.96.238:8000/play/a071/index.m3u8`).

### 2. `A G WEST` — canal de cine del oeste

- URL: `http://190.108.83.69:8000/play/a0c9/index.m3u8`
- Verificación: 1920x1080 con audio. Dos fotogramas (3 s y 25 s) muestran la misma película con el
  rótulo **«ESTÁS VIENDO EL OESTE LOCO (1967)»** y el logo **WEST** arriba a la derecha.
- No existe en el catálogo (solo hay `Galavision West`, otro canal).
- Identidad propuesta: `PublicDirect.2b469d67b84bfe52f2dc17af`.

## Descartadas (con motivo)

| Nombre en el servidor | Servidor | Motivo |
|---|---|---|
| `GEN HD2` | `138.59.227.20:8000` | Es GEN de Paraguay y **ya tenemos GEN en ese mismo servidor** (`/play/a0fk/`). |
| `ALCATEL TELEVICENTRO TVC` | `177.234.218.66:8084` | Es Televicentro (logo TVC); ya hay 6 copias en el catálogo. |
| `zzfsefd` | `177.234.218.66:8084` | El fotograma es **Discovery Channel** («Todos contra Ed Stafford»); ya lo tenemos. |
| `Foz de Yguazu` | `138.59.227.20:8000` | No es canal: es una **cámara de tránsito** (marca `catve.com`) y no tiene audio. |
| `RADIO BETHEL`, `EMISORAS //RADIO` | `190.108.83.69`, `200.7.99.59` | Solo audio (radio), sin video. |
| 14 entradas más (Canal 8 Villarrica, Farra Play Tv, Mbocayaty Tv, Monumental Tv Digital, Natalicio Tv, SNT IPTV, Teleclasica, Tv Eventos HD, Tv Max Oviedo, Farra Play, GOL TV, NETPLAY HD, e40, UP) | varios | El servidor devuelve **404 Not Found** en las dos pasadas: están listadas pero ya no se publican. |

## Conclusión

Los servidores de Lista 1 son el mismo tipo de panel que ya indexamos: 1.155 de 1.177 entradas ya
están en el inventario. No hay un catálogo escondido con decenas de canales nuevos; lo único nuevo
que realmente abre son **2 señales**, una de ellas chilena.

Nada se dio de alta: queda a la espera de aprobación explícita.
