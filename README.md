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

TVN y Meganoticias Ahora usan el resolutor publico de Google Cloud Run en
`southamerica-west1` (Santiago). El resolutor obtiene los tokens al abrir la
senal y devuelve una redireccion HLS temporal. No se necesita dejar este PC
encendido. Meganoticias se reincorpora automaticamente a la M3U cuando el
despliegue cloud queda configurado.

La guia conserva datos vigentes si una fuente externa falla temporalmente. La
ejecucion tambien puede iniciarse manualmente desde la pestana **Actions** con
el workflow **Actualizar M3U y EPG**.

## Orden de la lista

1. Nacionales normales
2. Noticias
3. Miscelaneos nacionales
4. Internacionales

## Canales

La lista contiene 20 canales mientras se configura el resolutor cloud: TVN,
Mega, CHV, Canal 13, La Red, 24 Horas, T13, CHV Noticias, NTV, TVN3,
CHV Deportes, DW Espanol, France 24 Espanol, Euronews Espanol, NHK World
Japan, Al Jazeera English, Red Bull TV, XITE Hits Germany, M1 y M2.

## Resolutor cloud

El workflow **Deploy Chile resolver** despliega `cloud-resolver` en Santiago,
guarda su URL en la variable `M3U_RESOLVER_BASE_URL` y vuelve a insertar
Meganoticias en el bloque de noticias. Requiere configurar una vez los secretos
`GCP_WORKLOAD_IDENTITY_PROVIDER` y `GCP_SERVICE_ACCOUNT`. El proyecto se toma
de la variable `GCP_PROJECT_ID` o usa `rugged-episode-148820`.
