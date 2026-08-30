# Lista M3U para Android TV

Repositorio publico de la lista M3U principal para Android TV. El mantenimiento
esta separado en dos procesos independientes: uno actualiza canales,
resolutores y salud; el otro construye la EPG sobre el catalogo completo. Ambos
usan ventanas fijas de seis horas y publican sus salidas sin sobrescribirse.

## URLs para el reproductor

Lista M3U:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/m3u.m3u`

Lista M3U externa (TvVoo/Vavoo y Highfly, salvo las excepciones de prueba de la principal):

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/m3u-externa.m3u`

Alias cortos oficiales para el reproductor (sin acortador externo):

- Principal: `https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/1.m3u`
- Externa: `https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/2.m3u`

`1.m3u` y `2.m3u` son copias sincronizadas automáticamente de las dos listas
canónicas. Al estar dentro del repositorio público, usan HTTPS y no tienen un
TTL de acortador; seguirán disponibles mientras se conserve este repositorio y
su rama `main`.

Guia de programacion XMLTV:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/epg.xml`

Catalogo declarativo de resolutores para VibeM3U:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/resolver-catalog.json`

La M3U conserva una URL HLS de respaldo para reproductores externos. VibeM3U
usa los atributos `x-resolver-*` para renovar la fuente justo antes de abrirla:
TVN consulta su pagina oficial; 24 Horas se mantiene como canal directo, TvVoo
usa aliases estables y Highfly usa un slug estable junto al `manifest.json`
configurado. Meganoticias
usa ahora el resolutor oficial porque su CDN exige autorizacion de corta
duracion; Pluto y los canales directos siguen sin resolutor. El catalogo solo
contiene reglas y endpoints HTTPS permitidos; nunca publica respuestas HLS,
tokens, claves ni URLs de sesion.

## Funcionamiento

El proceso de canales (`update-channels.yml` / `run_m3u_6h.py`):

- comprueba los streams, los primeros segmentos multimedia y los logos locales;
- conserva los maestros originales de los canales cuya autenticacion corresponde
  al reproductor;
- publica los maestros HLS originales de cada canal, sin wrappers ni variantes
  generadas por este repositorio;
- prioriza enlaces descubiertos desde las paginas oficiales del emisor al
  reparar una senal; los respaldos conocidos solo se prueban despues;
- no modifica `epg.xml`: la EPG tiene un proceso independiente;
- publica `m3u.m3u` con fuentes directas, resolutores propios de TVN/Meganoticias,
  la familia de señales F1 contigua junto al F1 de Highfly y Sky Sports Tennis;
- publica `m3u-externa.m3u` con TvVoo/Vavoo y el resto de Highfly, sin duplicar canales ni
  dejar que una caída de esos resolutores bloquee la lista principal; la familia
  F1 completa queda contigua en `m3u.m3u` junto al F1 de Highfly;
- solo reemplaza `m3u.m3u` cuando el 100% de sus candidatos tiene cobertura EPG
  XMLTV vigente y validada para al menos 24 horas; si la compuerta falla,
  conserva la versión anterior;
- usa las parrillas oficiales disponibles de TVN y Mega, ademas de las de M1 y
  M2; conserva EPGShare como respaldo cuando el emisor no publica XMLTV o una
  parrilla automatizable;
- integra PLEX1 para las señales FAST de BBC, CBS, Qello, Stingray y XITE, y
  usa las fuentes pequeñas SG1 y NG1 solo para CNA y Africanews,
  respectivamente; no descarga el XML combinado de todos los
  proveedores;
- incorpora la parrilla XMLTV de PlutoTV para MTV Biggest Pop,
  MTV Spankin' New y MTV Flow Latino; las tarjetas repetidas de Pluto
  se deduplican antes de construir la EPG;
- incorpora candidatos de noticias, deportes y música desde los resolutores JSON
  públicos de TvVoo, manteniendo un solo canal lógico por señal y sus aliases
  estables por país. Las señales que no responden se retiran temporalmente de
  las listas públicas, pero permanecen en `channel-catalog.m3u` para volver a
  probarlas en la siguiente corrida;
- incorpora DAZN Darts x Pluto TV y DAZN Heldinnen x Pluto TV como señales FAST
  de producción: sus HLS públicos redirigen al distribuidor Pluto y sus guías
  XMLTV se obtienen desde la fuente pública de Pluto con los IDs oficiales de
  ambos canales. La EPG se actualiza en el proceso independiente;
- cada ejecucion de canales mantiene una validacion paralela separada para las
  listas principal y externa, comprobando maestro/variante/segmento;
- las renovaciones de TvVoo, Highfly y Meganoticias se ejecutan despues de esa
  validacion, agrupadas por proveedor. Una URL dinamica que acaba de validarse
  se reutiliza durante una ventana corta para no repetir consultas; al superar
  el TTL, fallar o cambiar su huella, vuelve a resolverse. Highfly consulta su
  `manifest.json` una sola vez por corrida y conserva los slugs estables;
- los reintentos y tiempos de espera se ajustan por motor: directos, TVN,
  Meganoticias, TvVoo y Highfly tienen limites propios para que un proveedor
  lento no bloquee a los demas. Los candidatos aceptados durante la renovacion
  ya llegan validados a la salida y no se comprueba toda la lista por segunda
  vez;
- usa el mismo enlace HTTP solo cuando el nodo HTTPS responde con certificado
  vencido y la excepcion se limita a los hosts conocidos de Highfly;
- conserva los slugs de Highfly y los aliases de TvVoo como fuentes renovables.
  Si una fuente deja de existir, el actualizador solicita candidatos nuevos,
  valida su HLS y publica el enlace que respondió;
- prioriza la guia oficial de Canal 13 para 13C, manteniendola separada de
  13 Cultura; si la pagina oficial no entrega bloques vigentes, usa Zapping
  como respaldo por canal;
- mantiene Premier Sports 1 y Premier Sports 2 desde los resolutores JSON
  publicos de TvVoo, con renovacion cada 6 horas y guia UK1 real;
- usa la guia publica de Zapping Chile para las senales nacionales donde
  EPGShare/TecnoCentro mostraban desplazamientos o no entregaban una parrilla
  util; sus marcas Unix absolutas se convierten a America/Santiago sin sumar
  horas manualmente;
- publica `channel-status.json` y un informe Markdown como artefactos de cada
  ejecucion; tambien conserva un issue de GitHub con el historial detallado.
- `channel-health-state.json` conserva solo la hora de validacion dinamica y una
  huella irreversible de la URL; no guarda tokens, claves ni URLs de sesion.
- retira temporalmente de la lista publica correspondiente cualquier canal que
  siga fallando despues de validar HLS, reintentar y buscar reparaciones;
  `channel-catalog.m3u` conserva el inventario completo para volver a probarlo
  y reactivarlo en la siguiente ejecucion;
- las sondas antiguas de Sky identificadas con `@Direct` fueron retiradas de
  forma permanente; no se vuelven a publicar aunque el origen las entregue o
  fallen sus comprobaciones;
- si falla simultaneamente al menos el 25% de las fuentes directas, bloquea la
  publicación como posible problema sistémico del runner o de la red; los
  fallos de resolutores se retiran individualmente y se reintentan en la
  siguiente ejecución.

El coordinador `run_m3u_6h.py` conserva `run-state.json`; el coordinador
`run_epg_6h.py` conserva `epg-run-state.json`. Cada estado tiene su propia
ventana fija de seis horas. GitHub Actions es el ejecutor principal desde
ahora. La tarea local queda deshabilitada y los scripts locales se conservan
solamente como respaldo manual; no deben ejecutarse al mismo tiempo que el
cron remoto.

El proceso de canales corre a las 00:00, 06:00, 12:00 y 18:00 (hora de
Santiago). El proceso de EPG corre a las 00:30, 06:30, 12:30 y 18:30. La
compuerta de cada estado evita trabajo duplicado y ambos comparten una cola de
publicacion para no competir por `main`.
GitHub puede iniciar unos minutos despues porque los cron son best effort.

TVN y Meganoticias conservan sus maestros oficiales. Actions no interviene en
la autenticacion de reproduccion; esa responsabilidad corresponde a la app.
Mega y La Red publican sus maestros oficiales directos. El PC no necesita
estar encendido para el mantenimiento normal.

La guia conserva datos vigentes si una fuente externa falla temporalmente. La
ejecucion tambien puede iniciarse manualmente desde la pestana **Actions** con
los workflows **Actualizar canales M3U** o **Actualizar EPG**. El primero
renueva streams y salud; el segundo fuerza la reconstruccion de la guia sobre
`channel-catalog.m3u`.

TVN y TVN3 son señales distintas y nunca comparten parrilla: TVN usa el JSONP
oficial de `tvn.cl` con `tvg-id="0104"`; TVN3 conserva `tvg-id="1437"`, consulta
la guía horaria pública de Zapping/Simply.TV y publica además
`https://www.tvn.cl/tvn3` como referencia oficial de la señal. La consulta tiene
dos niveles: el HTML completo de hoy/mañana y el endpoint público de programa
actual/próximos cuando el HTML aplica restricción geográfica al runner. Las
páginas se procesan por canal para que un fallo independiente no descarte
TVN3. Si ninguna fuente entrega bloques exactos, TVN3 recibe `continuidad tecnica`
explicita en vez de heredar por error la programación de TVN o aceptar el bloque genérico
de 24 horas que publica TVN Play.

Todos los logos de los canales se conservan dentro de `logos/` y la M3U y el
EPG apuntan a las copias publicadas en este repositorio. Los logos vectoriales
se mantienen como SVG y los demas como PNG para conservar la mejor calidad
disponible sin depender de servidores externos.

## Orden de la lista

El orden tematico se construye siempre desde `channel-catalog.m3u`, que
conserva los 150 candidatos aunque alguno quede temporalmente fuera de la M3U
publica por fallar la validacion. `m3u.m3u` y `m3u-externa.m3u` filtran esos
candidatos sin alterar su posicion dentro de su propia salida; cuando un canal
se recupera, vuelve al mismo bloque.

1. Nacionales
2. Noticias nacionales
3. NTV, 13C y RWND (sección posterior a Noticias nacionales)
4. Noticias internacionales
5. Deportes
6. Música
7. Misceláneos

Los seis valores se reflejan tambien en `group-title`. Los canales de
documentales, cultura, entretenimiento y señales internacionales generales
quedan en `Misceláneos`; las señales de conciertos, XITE, MTV, Stingray y
similares quedan en `Música`. NTV, 13C y RWND conservan `Misceláneos` como
grupo, aunque se muestran en una sección propia inmediatamente después de las
noticias nacionales. La clasificación no cambia `tvg-id`, asociaciones
XMLTV, resolutores ni URLs de respaldo.

## Canales

El catalogo contiene 138 candidatos: nacionales, noticias, miscelaneos
chilenos, noticias internacionales, documentales, conciertos, musica y
deportes. `m3u.m3u` es la lista principal de fuentes directas, TVN, Meganoticias,
las señales dinámicas seleccionadas Sky Sports F1 y Sky Sports Tennis;
`m3u-externa.m3u` concentra TvVoo/Vavoo y el resto de Highfly. El numero
visible en cada lista puede ser menor en una ejecucion si algunos candidatos
agotaron sus reintentos; vuelven automaticamente cuando la validacion completa
responde.

Las antiguas sondas directas de Sky (`@Direct`/`(Directo)`) ya no forman parte
de ninguna lista pública. Las señales Sky que permanecen son las que tienen un
resolutor renovable o una fuente seleccionada explícitamente.

TVN y Mega se actualizan desde sus parrillas oficiales cuando estan
disponibles. Para T13 no se encontro una parrilla oficial diaria de la senal
`t13.smil`: la pagina `13.cl/programacion` corresponde a la parrilla general
de Canal 13 y no coincide con esa senal. Por eso T13 usa Zapping como primera
opcion y TecnoCentro como tercera opcion. La EPG de La Red usa exclusivamente
su guia oficial. Si esa pagina no responde o no entrega una parrilla
suficiente, no se sustituye por Zapping, EPGShare ni por otra fuente: se deja
constancia del fallo y se conserva unicamente la cobertura tecnica, marcada
como tal y no presentada como programacion real.
Para 24 Horas no se encontro una parrilla diaria oficial publica y estructurada
en 24horas.cl: se usa Zapping cuando entrega bloques validos y EPGShare01 como
tercera opcion. Un fallo aislado de Zapping no invalida los respaldos por canal.
La EPG usa fuentes XMLTV de Chile, Espana, Francia, Alemania, Reino Unido,
Argentina, Portugal, Nueva Zelanda, Estados Unidos, Polonia, Letonia, Paises
Bajos, PLEX1, PlutoTV, Singapur y Nigeria, junto con la guia publica
de Zapping para senales chilenas seleccionadas. El orden es: fuente oficial
del canal, XMLTV real por pais/proveedor y Zapping u otra fuente secundaria
real. M1, M2 y 13C se actualizan desde sus parrillas oficiales. La EPG
construye sus IDs esperados desde `channel-catalog.m3u`: un
canal retirado temporalmente de la lista publica continua recibiendo EPG y no
causa un error por no aparecer en `m3u.m3u`. La EPG conserva al menos un bloque
para cada canal del catalogo, incluso si fue retirado temporalmente por fallos
HLS. Cuando ninguna fuente real
entrega una parrilla exacta, se usa `continuidad tecnica`, marcada en
`data-guide`; sus bloques visibles se titulan `Live` y se alinean de 00:00 a
23:59 en horario de Santiago. No se presenta como una guia oficial. La siguiente corrida vuelve a intentar la fuente real
y reemplaza esa cobertura cuando aparece. Antes de publicar `m3u.m3u`, el
proceso de canales audita que sus candidatos tengan canal XMLTV, programas y
al menos 24 horas futuras; la lista externa no depende de esta compuerta y se
publica por separado.

Para diagnosticar una fuente sin alterar el historial de salud ni renovar URLs
HLS, se usa el workflow independiente **Actualizar EPG**. Las ventanas de
canales y EPG no ejecutan el proceso contrario.

Se reincorporaron provisionalmente cuatro canales que habian desaparecido sin
una instruccion de borrado: CHV Deportes, 13 Cultura, 13 Go (antes 13 Kids) y Autentic History.
Sus maestros HLS entregaron playlist y primer segmento multimedia durante la
verificacion; si no hay fuente real, el actualizador conserva una marca de
`continuidad tecnica` para no dejar el canal sin bloque EPG. 13C permanece en la lista como canal
distinto y conserva la parrilla oficial de `https://www.13.cl/c/programacion`;
no se reutiliza esa guia para 13 Cultura.

El repositorio `OwnerPlugins/vavoo` se utilizo como referencia de los aliases
Vavoo y de la separacion entre catalogo, resolutor y EPG. No se copiaron sus
URLs `127.0.0.1` ni su proxy local: no funcionarian desde un reproductor
remoto. La lista publica conserva solo las URLs HLS que el resolutor remoto
entrega y que el actualizador puede renovar y validar; tampoco se incorpora la
telemetria opcional del plugin.
La selección actual excluye de forma permanente Bloomberg TV, CNN Polonia, TRT,
DAZN FAST+, RMC y cualquier canal cuyo nombre indique Turquía o Balcanes. El
filtro se aplica también al catálogo de reintento y al catálogo de resolutores,
por lo que esas entradas no reaparecen en las corridas automáticas.

Simply.TV (con punto) se reviso
como proveedor B2B de EPG y metadata:
su portal de entrega requiere autenticacion y la cuenta de prueba gratuita solo
ofrece un grupo limitado de canales. No se incorpora como dependencia del flujo
publico hasta contar con acceso autorizado y confirmar cobertura para estos
canales; si se habilita, se integrara como fuente opcional con credenciales fuera
del repositorio y Zapping/fuentes oficiales como respaldo.
