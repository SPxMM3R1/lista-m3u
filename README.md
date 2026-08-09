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
- conserva los maestros que requieren token para que la app de reproduccion
  pueda resolverlos;
- publica los maestros HLS originales de cada canal, sin wrappers ni variantes
  generadas por este repositorio;
- actualiza la guia EPG con las parrillas disponibles;
- usa la parrilla oficial de Mega desde `mega.cl/programacion` y conserva
  EPGShare como respaldo;
- publica `channel-status.json` como artefacto de cada ejecucion.

En el modo actual, TVN y Meganoticias publican sus maestros `mdstrm` sin
`access_token`. El actualizador no intenta renovarlos ni sustituirlos: la app
de reproduccion debe obtener el token antes de abrirlos. Mega y La Red
publican sus maestros oficiales directos. No se necesita dejar este PC
encendido.

El modo anterior se puede restaurar sin editar el codigo: configura la
variable de repositorio `M3U_TOKEN_RESOLUTION_MODE` con el valor `cloud` en
GitHub Actions. En ese modo TVN, Mega y Meganoticias vuelven a usar el
resolutor y la renovacion automatica de tokens.

La guia conserva datos vigentes si una fuente externa falla temporalmente. La
ejecucion tambien puede iniciarse manualmente desde la pestana **Actions** con
el workflow **Actualizar M3U y EPG**.

Todos los logos de los canales se conservan dentro de `logos/` y la M3U y el
EPG apuntan a las copias publicadas en este repositorio. Los logos vectoriales
se mantienen como SVG y los demas como PNG para conservar la mejor calidad
disponible sin depender de servidores externos.

## Orden de la lista

1. Nacionales normales
2. Noticias
3. Miscelaneos nacionales
4. Internacionales y canales agregados por region o tema

## Canales

La lista contiene 28 canales despues de retirar 74 entradas seleccionadas de
la fuente mundial. Se conservaron los nacionales, noticias, miscelaneos
chilenos y una seleccion internacional, musical y europea.

La EPG usa fuentes XMLTV de Chile, Espana, Francia, Alemania, Polonia,
Letonia y Paises Bajos. M1 y M2 se actualizan desde sus parrillas oficiales
semanales. Se marca como `senal continua` cualquier canal que no publique una
parrilla diaria verificable, en vez de presentar esa continuidad como una guia
real.

## Resolutor cloud

El workflow **Deploy Cloudflare resolver** despliega `cloudflare-resolver` y
guarda su URL en la variable `M3U_RESOLVER_BASE_URL`. En el modo `cloud`, esa
URL conecta TVN, Mega y Meganoticias; en el modo actual no se usa para la
lista. Requiere configurar una vez los secretos
`CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ACCOUNT_ID`.
