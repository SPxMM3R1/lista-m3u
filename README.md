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
- conserva los maestros originales de los canales cuya autenticacion corresponde
  al reproductor;
- publica los maestros HLS originales de cada canal, sin wrappers ni variantes
  generadas por este repositorio;
- prioriza enlaces descubiertos desde las paginas oficiales del emisor al
  reparar una senal; los respaldos conocidos solo se prueban despues;
- actualiza la guia EPG con las parrillas disponibles;
- usa las parrillas oficiales disponibles de TVN y Mega, ademas de las de M1 y
  M2; conserva EPGShare como respaldo cuando el emisor no publica XMLTV o una
  parrilla automatizable;
- publica `channel-status.json` como artefacto de cada ejecucion.

TVN y Meganoticias publican sus maestros `mdstrm` sin `access_token`. Actions
no obtiene tokens, no llama APIs de autenticacion y no sustituye esos enlaces:
la app de reproduccion debe resolver el acceso antes de abrirlos. Mega y La
Red publican sus maestros oficiales directos. No se necesita dejar este PC
encendido.

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

La lista contiene 49 canales despues de retirar 74 entradas seleccionadas de
la fuente mundial. Se conservaron los nacionales, noticias, miscelaneos
chilenos, canales de Espana, senales internacionales en espanol y una
seleccion documental y musical europea.

La EPG usa fuentes XMLTV de Chile, Espana, Francia, Alemania, Polonia,
Letonia y Paises Bajos. M1 y M2 se actualizan desde sus parrillas oficiales
semanales. Las senales espanolas con correspondencia en EPGShare reciben
parrilla real; se marca como `senal continua` cualquier canal que no publique
una parrilla diaria verificable, en vez de presentar esa continuidad como una
guia real.
