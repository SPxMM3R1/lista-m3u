# Lista M3U para Android TV

Repositorio publico de la lista M3U principal para Android TV. La lista y su
EPG se actualizan mediante un coordinador comun. El limite de seguridad es de
12 horas, pero la siguiente ejecucion puede adelantarse cuando la programacion
real disponible esta a punto de terminar. Ese mismo resultado puede generarse
desde Windows o desde GitHub Actions.

## URLs para el reproductor

Lista M3U:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/m3u.m3u`

Guia de programacion XMLTV:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/epg.xml`

Catalogo declarativo de resolutores para VibeM3U:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/resolver-catalog.json`

La M3U conserva una URL HLS de respaldo para reproductores externos. VibeM3U
usa los atributos `x-resolver-*` para renovar la fuente justo antes de abrirla:
TVN y 24 Horas consultan sus paginas oficiales, TvVoo usa aliases estables y
Highfly usa un slug estable junto al `manifest.json` configurado. Meganoticias
usa ahora el resolutor oficial porque su CDN exige autorizacion de corta
duracion; Pluto y los canales directos siguen sin resolutor. El catalogo solo
contiene reglas y endpoints HTTPS permitidos; nunca publica respuestas HLS,
tokens, claves ni URLs de sesion.

## Funcionamiento

Cada ejecucion completa:

- comprueba los streams, los primeros segmentos multimedia y los logos locales;
- conserva los maestros originales de los canales cuya autenticacion corresponde
  al reproductor;
- publica los maestros HLS originales de cada canal, sin wrappers ni variantes
  generadas por este repositorio;
- prioriza enlaces descubiertos desde las paginas oficiales del emisor al
  reparar una senal; los respaldos conocidos solo se prueban despues;
- actualiza la guia EPG con parrillas XMLTV reales; una entrada que solo
  pueda recibir bloques genericos se rechaza y no se publica;
- si una fuente exacta por canal falla durante una renovacion, conserva solo
  sus bloques reales todavia vigentes de la EPG publicada y nunca los mezcla
  con una fuente fresca ni los sustituye por continuidad inventada;
- calcula en `epg.xml` la proxima ventana usando el fin mas temprano de una
  parrilla real menos seis horas; los bloques de continuidad no adelantan la
  ejecucion;
- usa las parrillas oficiales disponibles de TVN y Mega, ademas de las de M1 y
  M2; conserva EPGShare como respaldo cuando el emisor no publica XMLTV o una
  parrilla automatizable;
- integra PLEX1 para las señales FAST de BBC, Bloomberg, CBS, Qello, Stingray
  y XITE, y usa las fuentes pequeñas TR1, SG1 y NG1 solo para TRT World, CNA y
  Africanews, respectivamente; no descarga el XML combinado de todos los
  proveedores;
- incorpora la parrilla XMLTV de PlutoTV para MTV Classic, MTV Biggest Pop,
  MTV Spankin' New y MTV Flow Latino; las tarjetas repetidas de Pluto
  se deduplican antes de construir la EPG;
- incorpora 65 canales desde los resolutores JSON publicos de TvVoo:
  CNN, MTV Hits, M6 Music, Trace Urban, Sky Sports Main Event, Sky Sports Arena,
  TNT Sports 3, ESPN 3, Eurosport 1, RMC Sport 1, RMC Sport 2, DAZN 2,
  DAZN FAST+, RT France, Sport TV 1, Sport TV 2, Eleven Sports 1 y Eleven
  Sports 2. También incorpora la tanda de validación de Sky Sports
  Action/Cricket/Football/Mix/News/NFL, Sky Sport italiano y Eurosport 2 UK y
  España, además de DAZN Francia, Alemania, España, Portugal e
  Italia. Las señales nuevas de Arena, NFL, Eurosport 2 España y DAZN 2 España
  quedan marcadas como prueba dinámica. La tanda europea del 25 de agosto
  agrega TNT Sports 1, NRJ Hits, MCM, DAZN F1 España, Sport TV 4 y 5, además
  de Sky Sport F1/Golf/Tennis/Premier League y Eurosport 1 de Alemania;
- incorpora DAZN Darts x Pluto TV y DAZN Heldinnen x Pluto TV como señales FAST
  de producción: sus HLS públicos redirigen al distribuidor Pluto y sus guías
  XMLTV se obtienen desde la fuente pública de Pluto con los IDs oficiales de
  ambos canales;
  Cada ejecucion solicita tokens nuevos, valida
  maestro/variante/segmento y usa el mismo enlace HTTP solo cuando el nodo HTTPS
  responde con certificado vencido;
- conserva Sky Sports Racing con Highfly como fuente primaria y aliases Vavoo
  de respaldo. Si el slug Highfly deja de existir, el actualizador solicita un
  alias nuevo a TvVoo, valida su HLS y publica el enlace que respondio;
- prioriza la guia oficial de Canal 13 para 13C, manteniendola separada de
  13 Cultura; si la pagina oficial no entrega bloques vigentes, usa Zapping
  como respaldo por canal;
- mantiene Premier Sports 1 y Premier Sports 2 desde los resolutores JSON
  publicos de TvVoo, con renovacion cada 12 horas y guia UK1 real;
- usa la guia publica de Zapping Chile para las senales nacionales donde
  EPGShare/TecnoCentro mostraban desplazamientos o no entregaban una parrilla
  util; sus marcas Unix absolutas se convierten a America/Santiago sin sumar
  horas manualmente;
- publica `channel-status.json` y un informe Markdown como artefactos de cada
  ejecucion; tambien conserva un issue de GitHub con el historial detallado.

El coordinador `run_m3u_48h.py` conserva `run-state.json` para que el cambio
entre ejecutor local y GitHub sea transparente. Elige la primera de estas
ventanas: el fin de la guia real menos seis horas o el limite de 12 horas desde
la ultima publicacion. Nunca programa dos ejecuciones con menos de seis horas
de separacion. Durante la ventana local hasta el 1 de septiembre de 2026 se
puede registrar `register_local_48h_task.ps1`; la tarea usa un disparador unico
y se vuelve a registrar al terminar cada ejecucion. Desde el 2 de septiembre
GitHub Actions retoma el mismo flujo.

GitHub conserva dos disparadores diarios, a las 00:00 y 12:00 (hora de
Santiago). Cada cron ejecuta una sola validacion coordinada de streams, logos,
EPG y resolutores; la compuerta de `run-state.json` evita trabajo duplicado.
GitHub puede iniciar unos minutos despues porque los cron son best effort.

Durante esta ventana, los cron de GitHub quedan en espera para no consumir cuota.
El programador local contiene un disparador puntual para reactivarlo el 2 de
septiembre de 2026 a las 03:05 (hora local), y luego se deshabilita a si mismo.

TVN y Meganoticias conservan sus maestros oficiales. Actions no interviene en
la autenticacion de reproduccion; esa responsabilidad corresponde a la app.
Mega y La Red publican sus maestros oficiales directos. El PC solo necesita
estar disponible durante la ventana local; despues del 2 de septiembre el
ejecutor vuelve a ser GitHub Actions.

La guia conserva datos vigentes si una fuente externa falla temporalmente. La
ejecucion tambien puede iniciarse manualmente desde la pestana **Actions** con
el workflow **Actualizar M3U y EPG**. `force_run` omite la ventana dinamica y
`force_epg_refresh` fuerza la descarga de las fuentes EPG.
La entrada manual `allow_before_september` solo autoriza pruebas expresas antes
del 2 de septiembre; los disparadores programados permanecen bloqueados.

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

La lista contiene 176 canales: nacionales, noticias, miscelaneos chilenos,
noticias internacionales, documentales, conciertos, musica y deportes.

TVN y Mega se actualizan desde sus parrillas oficiales cuando estan
disponibles. Para T13 no se encontro una parrilla oficial diaria de la senal
`t13.smil`: la pagina `13.cl/programacion` corresponde a la parrilla general
de Canal 13 y no coincide con esa senal. Por eso T13 usa Zapping como primera
opcion y TecnoCentro como tercera opcion. La fuente oficial de La Red tiene
prioridad sobre Zapping y EPGShare; esas fuentes se conservan como
respaldo si la pagina del canal no responde o no entrega 24 horas futuras.
Para 24 Horas no se encontro una parrilla diaria oficial publica y estructurada
en 24horas.cl: se usa Zapping cuando entrega bloques validos y EPGShare01 como
tercera opcion. Un fallo aislado de Zapping no invalida los respaldos por canal.
La EPG usa fuentes XMLTV de Chile, Espana, Francia, Alemania, Reino Unido,
Argentina, Portugal, Nueva Zelanda, Estados Unidos, Polonia, Letonia, Paises
Bajos, PLEX1, PlutoTV, Turquia, Singapur y Nigeria, junto con la guia publica
de Zapping para senales chilenas seleccionadas. El orden es: fuente oficial
del canal, XMLTV real por pais/proveedor y Zapping u otra fuente secundaria
real. M1, M2 y 13C se actualizan desde sus parrillas oficiales. La produccion
no conserva canales cuya unica salida seria `senal continua`; el constructor
 falla antes de publicar si aparece uno. Las excepciones explicitas de TvVoo
 que responden como HLS pero no tienen una guia identificable se publican como
 `sin guía`, sin inventar programas. Puede existir `parrilla real + continuidad`
 cuando la fuente real tiene un horizonte corto: los programas siguen siendo
 reales y la continuidad solo cubre el hueco hasta la proxima actualizacion.

Se reincorporaron provisionalmente nueve canales que habian desaparecido sin
una instruccion de borrado: CHV Deportes, 13 Cultura, 13 Kids, Autentic History,
Reuters, Totalmusic 80s, Totalmusic 2000s, Totalmusic Concerts y Totalmusic
Dance. Sus maestros HLS entregaron playlist y primer segmento multimedia
durante la verificacion, pero no se inventa una parrilla XMLTV: el actualizador
los publica con `data-guide="sin guía"` hasta encontrar una fuente que
identifique exactamente cada senal. 13C permanece en la lista como canal
distinto y conserva la parrilla oficial de `https://www.13.cl/c/programacion`;
no se reutiliza esa guia para 13 Cultura.

El repositorio `OwnerPlugins/vavoo` se utilizo como referencia de los aliases
Vavoo y de la separacion entre catalogo, resolutor y EPG. No se copiaron sus
URLs `127.0.0.1` ni su proxy local: no funcionarian desde un reproductor
remoto. La lista publica conserva solo las URLs HLS que el resolutor remoto
entrega y que el actualizador puede renovar y validar; tampoco se incorpora la
telemetria opcional del plugin.
RT France y DAZN FAST+ se incorporan porque TvVoo devuelve HLS utilizable; sus
canales XMLTV quedan declarados como `sin guía` hasta que exista una parrilla
que identifique esas señales exactas.

Simply.TV (con punto) se reviso
como proveedor B2B de EPG y metadata:
su portal de entrega requiere autenticacion y la cuenta de prueba gratuita solo
ofrece un grupo limitado de canales. No se incorpora como dependencia del flujo
publico hasta contar con acceso autorizado y confirmar cobertura para estos
canales; si se habilita, se integrara como fuente opcional con credenciales fuera
del repositorio y Zapping/fuentes oficiales como respaldo.
