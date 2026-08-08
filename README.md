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

- comprueba los streams, los primeros segmentos multimedia y los logos PNG;
- renueva las senales publicas con tokens que caducan;
- genera wrappers HLS con audio separado para Mega, La Red y NHK World;
- genera wrappers HLS de una sola variante para las fuentes que ya traen audio
  embebido, fijando la maxima calidad disponible hasta 1080p;
- deja como maestro directo las fuentes que no declaran audio de forma segura,
  normalmente en 720p, en vez de publicar un wrapper que pueda quitar sonido;
- actualiza la guia EPG con las parrillas disponibles;
- publica `channel-status.json` como artefacto de cada ejecucion.

TVN, Mega y Meganoticias Ahora usan el resolutor publico de Cloudflare. TVN y
Meganoticias obtienen sus tokens al abrir la senal y devuelven una redireccion
HLS temporal; Mega entrega su master oficial con referencias HTTPS para evitar
bloqueos de trafico mixto en Android TV. No se necesita dejar este PC
encendido.

La guia conserva datos vigentes si una fuente externa falla temporalmente. La
ejecucion tambien puede iniciarse manualmente desde la pestana **Actions** con
el workflow **Actualizar M3U y EPG**.

Los logos locales de NTV, TVN3, CHV Deportes, France 24, NHK World y XITE se
publican como PNG RGBA de alta resolucion para que sean compatibles con el
reproductor Android TV. Sus fuentes vectoriales se conservan en `logos/svg`;
la M3U no apunta a SVG.

## Orden de la lista

1. Nacionales normales
2. Noticias
3. Miscelaneos nacionales
4. Internacionales

## Canales

La lista contiene 21 canales: TVN,
Mega, CHV, Canal 13, La Red, 24 Horas, T13, CHV Noticias, NTV, TVN3,
CHV Deportes, DW Espanol, France 24 Espanol, Euronews Espanol, NHK World
Japan, Al Jazeera English, Red Bull TV, XITE Hits Germany, M1 y M2.

## Resolutor cloud

El workflow **Deploy Cloudflare resolver** despliega `cloudflare-resolver`,
guarda su URL en la variable `M3U_RESOLVER_BASE_URL` y conecta TVN, Mega y
Meganoticias. Requiere configurar una vez los secretos
`CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ACCOUNT_ID`.
