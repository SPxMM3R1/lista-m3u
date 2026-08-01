# Lista M3U para Android TV

Repositorio publico de la lista M3U principal para Android TV. La lista se
actualiza automaticamente cada tres horas mediante GitHub Actions.

## URLs para el reproductor

Lista M3U:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/m3u.m3u`

Guia de programacion XMLTV:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/epg.xml`

## Funcionamiento

Cada ejecucion:

- renueva el enlace temporal de TVN;
- prueba los 13 streams y sus logos PNG;
- busca reemplazos verificados en fuentes oficiales si un canal falla;
- genera NHK World sin la pista de subtitulos CC activada por defecto;
- actualiza la guia EPG con las parrillas disponibles;
- verifica que los archivos publicados en GitHub sigan accesibles;
- publica `channel-status.json` como artefacto de la ejecucion.

La guia conserva datos vigentes si una fuente externa falla temporalmente.

La ejecucion tambien puede iniciarse manualmente desde la pestaña **Actions**
con el workflow **Actualizar M3U y EPG**. La opcion `force_epg_refresh`
fuerza la descarga de la guia externa.

## Canales

TVN, Mega, CHV, Canal 13, T13, 24 Horas, La Red, DW Espanol, France 24
Espanol, Euronews Espanol, NHK World Japan, Al Jazeera English y Red Bull TV.
