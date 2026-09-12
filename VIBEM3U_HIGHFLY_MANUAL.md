# Contrato VibeM3U: Highfly en la lista principal

Estado: la antigua lista 3 fue retirada el 11 de septiembre de 2026.

## Fuentes públicas

VibeM3U debe cargar únicamente las dos listas del repositorio:

- `https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/1.m3u`
- `https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/2.m3u`

Las señales Highfly seleccionadas manualmente pertenecen a `1.m3u`. No se debe
solicitar ni esperar `3.m3u`.

## Entradas Highfly actuales en la lista 1

La lista principal conserva estas siete identidades:

| `tvg-id` | Nombre | `x-resolver-id` |
|---|---|---|
| `SkySportsF1.uk` | Sky Sports F1 | `f1-3949409` |
| `HighflyPremium.now-sky-sports-f1-2` | Sky Sports F1 UHD | `f1-93930303` |
| `SkySportsTennis.uk` | Sky Sports Tennis | `ten-3930030` |
| `HighflyPremium.4k-sky-sports-main-events` | Sky Sports Main Event UHD | `ml-383892993` |
| `SkySportsPremierLeague.uk` | Sky Sports Premier League | `pl-434343434` |
| `ESPN.us` | ESPN | `us-espn-hd-0` |
| `ESPN2.us` | ESPN 2 | `us-33323323` |

Cada entrada mantiene `x-resolver="highfly"`, el manifiesto final permitido y
`x-resolver-refresh="on_play"`. La URL debajo de `#EXTINF` es solo un respaldo;
VibeM3U debe pedir una fuente nueva antes de reproducir y descartar la URL
temporal al terminar o al recibir un rechazo.

## Renovación y selección

El actualizador consulta el catálogo público
`https://sports.highfly.dev/catalog/sport/sports_live.json` únicamente para
obtener slugs actuales y sincronizar, en conjunto, el `x-resolver-id` y la URL
HLS de respaldo sin token. La consulta no agrega canales, no elimina miembros
manuales y no publica eventos `streamed:`. Si el catálogo falla, se usan los
slugs estáticos conocidos y no se reemplaza una fuente por una URL de upgrade.

Una hoja que el catálogo describe como `Upgrade to Premium` no es una fuente
caducada: el endpoint público devuelve una oferta de autorización, no un HLS.
El actualizador conserva la identidad y el fallback de hoja allow-listed,
marca la entrada como gestionada por la aplicación y deja que VibeM3U resuelva
la reproducción con la autorización Premium en memoria. Nunca se guarda la
URL de upgrade, token, cookie, firma ni respuesta de sesión.

Para añadir otra señal Highfly, la decisión es manual: primero se verifica la
fuente, se elige un `tvg-id` estable, se configura el logo y la EPG, y luego se
agrega la entrada a la lista 1. La aplicación debe reconocer el nuevo
identificador antes de publicarlo. No se debe crear una entrada por cada evento,
calidad o país ni guardar tokens, firmas, URLs de sesión o respuestas Premium.

La credencial Premium se introduce y conserva únicamente en VibeM3U. No forma
parte de la M3U, el catálogo declarativo, la caché del repositorio ni los logs.
