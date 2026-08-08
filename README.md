# Lista M3U para Android TV

Repositorio publico de la lista M3U principal para Android TV. La lista se
actualiza automaticamente cada 15 minutos mediante GitHub Actions.

## URLs para el reproductor

Lista M3U:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/m3u.m3u`

Guia de programacion XMLTV:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/epg.xml`

## Funcionamiento

Cada ejecucion:

- verifica el enlace alternativo de TVN y busca un respaldo oficial si falla;
- usa y redescubre la señal HLS que publica el reproductor oficial de 24 Horas;
- conserva Meganoticias Ahora como endpoint local sin cache, porque su sesion depende de la red chilena y caduca antes que la cache de GitHub Raw;
- prueba todos los streams y sus logos PNG;
- busca reemplazos verificados y maestros de respaldo 1080p/720p si TVN, Mega o La Red fallan;
- comprueba el primer segmento multimedia de los canales con tokens o wrappers;
- comprueba el stream oficial normal de NHK World;
- comprueba que La Red entregue un segmento multimedia actual, renueva su wrapper 1080p y conserva dos rutas HLS oficiales de respaldo;
- genera wrappers HLS de 1080p con audio para Mega, La Red y NHK World;
- fija la variante directa de maxima calidad cuando conserva audio embebido;
- mantiene TVN en un enlace HLS alternativo verificado y conserva la reparacion oficial como respaldo;
- actualiza la guia EPG con las parrillas disponibles;
- verifica que los archivos publicados en GitHub sigan accesibles;
- publica `channel-status.json` como artefacto de la ejecucion.

La guia conserva datos vigentes si una fuente externa falla temporalmente.

Meganoticias Ahora usa el endpoint local `http://192.168.0.165:8787/meganoticias.m3u8`.
El PC debe estar encendido y la TV debe estar en la misma red local. El servidor
se inicia con Windows mediante la tarea `VibeM3U - Servidor M3U local`.

La ejecucion tambien puede iniciarse manualmente desde la pestaña **Actions**
con el workflow **Actualizar M3U y EPG**. La opcion `force_epg_refresh`
fuerza la descarga de la guia externa.

## Canales

La lista contiene 21 canales: los 13 originales de Chile e internacionales,
Meganoticias Ahora, NTV, TVN3, CHV Noticias, CHV Deportes, M1, M2 y XITE Hits
Germany, que superaron la ultima verificacion.
