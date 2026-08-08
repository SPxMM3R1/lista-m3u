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

- renueva los enlaces temporales de TVN y Meganoticias Ahora desde sus paginas oficiales;
- usa y redescubre la señal HLS que publica el reproductor oficial de 24 Horas;
- prueba todos los streams y sus logos PNG;
- busca reemplazos verificados y maestros de respaldo 1080p/720p si TVN, Mega o La Red fallan;
- comprueba el primer segmento multimedia de los canales con tokens o wrappers;
- comprueba el stream oficial normal de NHK World;
- comprueba que La Red entregue un segmento multimedia actual, renueva su wrapper 1080p y conserva dos rutas HLS oficiales de respaldo;
- genera wrappers HLS de 1080p con audio para Mega, La Red y NHK World;
- fija la variante directa de maxima calidad cuando conserva audio embebido;
- mantiene TVN en su maestro oficial y renueva su access_token cuando deja de responder;
- actualiza la guia EPG con las parrillas disponibles;
- verifica que los archivos publicados en GitHub sigan accesibles;
- publica `channel-status.json` como artefacto de la ejecucion.

La guia conserva datos vigentes si una fuente externa falla temporalmente.

La ejecucion tambien puede iniciarse manualmente desde la pestaña **Actions**
con el workflow **Actualizar M3U y EPG**. La opcion `force_epg_refresh`
fuerza la descarga de la guia externa.

## Canales

La lista contiene 17 canales: los 13 originales de Chile e internacionales,
Meganoticias Ahora, M1, M2 y XITE Hits Germany, que superaron la ultima verificacion.
