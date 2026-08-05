# Lista M3U para Android TV

Repositorio publico de la lista M3U principal para Android TV. La lista se
actualiza automaticamente cada hora mediante GitHub Actions.

## URLs para el reproductor

Lista M3U:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/m3u.m3u`

Guia de programacion XMLTV:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/epg.xml`

## Funcionamiento

Cada ejecucion:

- renueva el enlace temporal de TVN directamente desde su pagina oficial;
- prueba todos los streams y sus logos PNG;
- busca reemplazos verificados en fuentes oficiales si un canal falla;
- comprueba el stream oficial normal de NHK World;
- genera wrappers HLS de 1080p con audio para Mega, La Red y NHK World;
- fija la variante directa de maxima calidad cuando conserva audio embebido;
- conserva el maestro cuando el audio HLS es separado y no se puede publicar un wrapper seguro;
- actualiza la guia EPG con las parrillas disponibles;
- verifica que los archivos publicados en GitHub sigan accesibles;
- publica `channel-status.json` como artefacto de la ejecucion.

La guia conserva datos vigentes si una fuente externa falla temporalmente.

La ejecucion tambien puede iniciarse manualmente desde la pestaña **Actions**
con el workflow **Actualizar M3U y EPG**. La opcion `force_epg_refresh`
fuerza la descarga de la guia externa.

## Canales

La lista contiene 16 canales: los 13 originales de Chile e internacionales,
mas M1, M2 y XITE Hits Germany, que superaron la ultima verificacion.
