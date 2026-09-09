# Lista M3U para Android TV

Repositorio publico de la lista M3U principal para Android TV. El mantenimiento
esta separado en dos procesos independientes: uno actualiza canales,
resolutores y salud; el otro construye la EPG exclusivamente para la lista 1
manual. El catalogo completo sigue siendo inventario de validacion y reintento,
no amplia el alcance de XMLTV. Ambos procesos usan ventanas fijas de seis horas
y publican sus salidas sin sobrescribirse.

## URLs para el reproductor

Lista M3U:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/m3u.m3u`

Lista M3U externa (candidatos del catalogo aún no promovidos manualmente):

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/m3u-externa.m3u`

Alias cortos oficiales para el reproductor (sin acortador externo):

- Principal: `https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/1.m3u`
- Externa: `https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/2.m3u`

`1.m3u` y `2.m3u` son copias sincronizadas automáticamente de las dos listas
canónicas. Al estar dentro del repositorio público, usan HTTPS y no tienen un
TTL de acortador; seguirán disponibles mientras se conserve este repositorio y
su rama `main`.

Lista 3 opcional de Highfly Premium (canales estables):

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/3.m3u`

`3.m3u` es una tercera fuente independiente. VibeM3U puede activarla o
desactivarla sin modificar ni mezclar `m3u.m3u`/`1.m3u` con
`m3u-externa.m3u`/`2.m3u`. Publica únicamente identificadores estables
`leaf:<slug>` y una URL HLS sin autorización como respaldo; el token o la
configuración Premium se introducen localmente en VibeM3U y nunca se guardan en
este repositorio ni en la M3U.

Guia de programacion XMLTV:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/epg.xml`

La guia contiene unicamente los canales presentes en `m3u.m3u` (y su alias
`1.m3u`). Los canales de `m3u-externa.m3u`/`2.m3u`, `3.m3u` y
`channel-catalog.m3u` no se agregan a `epg.xml` mientras no sean promovidos
manualmente a la lista 1. Al promover un canal, la siguiente corrida de EPG
incorpora su `tvg-id` estable.

La EPG activa funciona en modo `official-only`. Los bridges oficiales
implementados actualmente son: TVN, La Red, Mega, Canal 13, 13Go, Chilevision,
T13, NHK World, BBC News, Al Jazeera, M1/M2, Red Bull y Autentic History.
Cada uno usa un ID exacto de Lista 1 y rechaza una respuesta sin bloques reales
o sin al menos 24 horas futuras. No se consulta ningún agregador externo, no se
clona ningún repositorio de terceros y no se mezcla una parrilla de otro canal. Sky conserva
un bridge preparado para sus IDs oficiales disponibles; si el proveedor no
entrega un SID público para una señal concreta, esa señal queda en `Live` hasta
que exista una asociación oficial verificable.

Los canales de Lista 1 que no tienen hoy una parrilla oficial pública usable
(por ejemplo DW, France 24, Arirang, XITE, TVE Internacional y las fuentes
Highfly) reciben continuidad técnica `Live` para no bloquear la actualización.
El informe de cada corrida separa `official_programme_ids` de
`technical_ids`; `Live` no se presenta como programación real.

Catalogo declarativo de resolutores para VibeM3U:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/resolver-catalog.json`

La M3U conserva una URL HLS de respaldo para reproductores externos. VibeM3U
usa los atributos `x-resolver-*` para resolver la fuente justo antes de abrirla:
TVN y Meganoticias conservan sus masters oficiales para que la aplicacion
obtenga la autorizacion al reproducir; 24 Horas se mantiene como canal directo,
TvVoo usa aliases estables y Highfly usa un slug estable junto al `manifest.json`
configurado. Pluto y los canales directos siguen sin resolutor. El catalogo solo
contiene reglas y endpoints HTTPS permitidos; nunca publica respuestas HLS,
tokens, claves ni URLs de sesion.

Los canales TvVoo publican además
`x-resolver-recipe="bounded-payload-v1"`. VibeM3U solo activa esa extracción
acotada si `resolver-catalog.json` autoriza exactamente el mismo ID y el modo
`media-signature-v1`; la M3U no puede incorporar código ejecutable. El contrato
para continuar el sistema, sus límites y las validaciones de publicación están
en [RESOLVER_RECIPE_CONTRACT.md](RESOLVER_RECIPE_CONTRACT.md).

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
- usa los `tvg-id` presentes en `m3u.m3u` como membresía manual persistente;
  la única excepción es `13C.cl@SD`, que después de tres fallos consecutivos
  puede pasar temporalmente a la externa y volver automáticamente al recuperar;
- publica `m3u-externa.m3u` como el subconjunto externo que funcionó en la
  validación actual, incluyendo los traslados automáticos reversibles; un canal
  externo que falla se retira temporalmente de esa salida, pero permanece en
  `channel-catalog.m3u` para reintento y reactivación automática;
- al mover manualmente un canal desde la lista externa a `m3u.m3u`, adopta la
  misma protección permanente de todos los miembros de la principal;
- conserva el orden temático definido en `channel-catalog.m3u` en ambas salidas;
- solo reemplaza `m3u.m3u` cuando el 100% de los canales que se van a publicar
  tiene cobertura EPG XMLTV vigente y validada para al menos 24 horas; si la
  compuerta falla, conserva la versión principal anterior y deja los fallos en
  la externa;
- construye la EPG en el workflow independiente con bridges y scrapers de
  fuentes oficiales, todos limitados a los `tvg-id` exactos de Lista 1;
- cada bridge valida su respuesta y sus bloques antes de incorporarlos. Si una
  señal no publica una guía oficial estable, recibe `Live` técnico hasta que
  aparezca una fuente oficial válida; nunca se hereda la parrilla de otro canal;
- conserva los adaptadores oficiales, Zapping, TecnoCentro y las fuentes
  antiguas en el código para auditoría y pruebas unitarias, pero el modo activo
  `official-only` no consulta agregadores ni fuentes históricas;
- una corrida exitosa publica únicamente las parrillas oficiales que
  respondieron y bloques `Live` técnicos para completar Lista 1. No reutiliza
  una guía anterior si no está marcada como generada por fuentes oficiales;
  una falla aislada de un bridge no aborta los demás canales;
- incorpora candidatos de noticias, deportes, música/conciertos, películas y
   adultos desde los catálogos JSON públicos de TvVoo, manteniendo un solo canal
   lógico por señal y sus aliases estables por país. Los adultos solo se
   publican en la lista externa y se muestran bajo `PRUEBA - Adultos`; nunca se
   descartan por su temática ni por falta de un logo seguro (en ese caso quedan
   sin logo). Las películas se marcan como subtituladas solo si
   el propio catálogo aporta una señal explícita como VOST o subtítulos; no se
   inventa una guía ni un idioma. Su lista depende de la
   promoción manual, no del resultado de cada chequeo, y todas permanecen en
   `channel-catalog.m3u` para repararlas;
- conserva en `m3u-externa.m3u` un bloque de candidatos históricos restaurados
  para investigación: aliases regionales de RT, Bloomberg, CNN, DAZN, ESPN,
  Eleven, RMC, Sky, Stingray, TRT, beIN, Arena y Eurosport. Están excluidos
  de la membresía manual de `m3u.m3u`, se renuevan como TvVoo y no se eliminan
  por coincidir con las exclusiones históricas;
- incorpora DAZN Darts x Pluto TV y DAZN Heldinnen x Pluto TV como señales FAST
  de producción: sus HLS públicos redirigen al distribuidor Pluto y sus guías
  XMLTV se obtienen desde la fuente pública de Pluto con los IDs oficiales de
  ambos canales. La EPG se actualiza en el proceso independiente;
- cada ejecucion de canales mantiene pools de validacion paralelos por origen,
  comprobando maestro/variante/segmento; el destino publico se decide despues
  de la comprobacion individual, por lo que una señal sana puede cambiar de
  lista aunque su proveedor original no cambie;
- las renovaciones de TvVoo y Highfly se ejecutan despues de esa validacion,
  agrupadas por proveedor. TVN y Meganoticias quedan para la resolucion de la
  aplicacion al abrir el canal. Una URL dinamica que acaba de validarse
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
- sincroniza `3.m3u` desde el catálogo público de Highfly, pero solo conserva
  entradas estables `leaf:`; ignora eventos temporales `streamed:` y no copia
  URLs firmadas, tokens ni posters del proveedor. La lista 3 se puede cargar o
  desactivar de forma independiente en el reproductor;
- mantiene los IDs de Canal 13, TVN3, 13 Cultura y las señales directas aunque
  no estén presentes en el manifiesto activo; sus programas se vuelven a
  intentar en cada corrida y mientras tanto reciben continuidad técnica
  claramente marcada;
- mantiene Premier Sports 1 y Premier Sports 2 desde los resolutores JSON
  publicos de TvVoo, con renovacion cada 6 horas y guia UK1 real;
- normaliza las fechas XMLTV a `America/Santiago` al construir la salida,
  respetando el offset entregado por cada fuente y sin sumar horas manualmente;
- publica `channel-status.json` y un informe Markdown como artefactos de cada
  ejecucion; tambien conserva un issue de GitHub con el historial detallado.
- `channel-health-state.json` conserva solo la hora de validacion dinamica y una
  huella irreversible de la URL; no guarda tokens, claves ni URLs de sesion.
- reintenta y repara todos los canales, tanto principales como externos; la
  membresía de la lista 1 solo cambia mediante edición manual salvo la política
  reversible de 13C, mientras que la lista 2 publica únicamente los canales
  externos que funcionaron en la última validación; `channel-catalog.m3u`
  conserva el inventario completo para reintentar los que hayan fallado;
- las sondas antiguas de Sky identificadas con `@Direct` fueron retiradas de
  forma permanente; no se vuelven a publicar aunque el origen las entregue o
  fallen sus comprobaciones;
- si falla simultaneamente al menos el 25% de las fuentes directas, bloquea la
  publicación como posible problema sistémico del runner o de la red, sin
  eliminar canales ni cambiar las membresías manuales no gestionadas.

El descubrimiento de catálogo (`discover-tvvoo.yml` / `discover_tvvoo_catalog.py`)
corre una vez al día a las 03:15, separado de los procesos de canales y EPG.
Consulta los catálogos públicos de TvVoo para Reino Unido, Italia, Francia,
Alemania, Portugal, España, Países Bajos, Polonia, Bulgaria, Argentina,
Rumanía y Rusia. Deduplica por señal y alias, descarta regiones y nombres
excluidos (PPV, VOD, TEST/EVENT y las regiones geográficas ya vetadas), exige un
logo HTTPS de un host permitido para las categorías normales y permite que una
señal adulta continúe sin logo si TvVoo no entrega uno confiable. Agrega como
máximo 24 candidatos por ejecución y 240 en total al catálogo externo. Las
señales deportivas se
clasifican también por disciplina —fútbol, rugby, boxeo, motor, ciclismo,
baloncesto, hockey, golf, tenis, carreras, etc.— y la música incluye conciertos,
jazz, rock, pop y señales equivalentes. La información estable queda en
`tvvoo-discovered.json`; nunca se guardan URLs de sesión, tokens ni respuestas
temporales. La lista principal no se modifica. Cuando hay nuevos candidatos,
el descubridor solicita explícitamente el workflow de mantenimiento de canales,
que intenta resolver y validar sus HLS; la EPG los incorpora en su próxima
ejecución independiente sobre el catálogo completo.

El coordinador `run_m3u_6h.py` conserva `run-state.json`; el coordinador
`run_epg_6h.py` conserva `epg-run-state.json`. Cada estado tiene su propia
ventana fija de seis horas. GitHub Actions es el ejecutor principal desde
ahora. La tarea local queda deshabilitada y los scripts locales se conservan
solamente como respaldo manual; no deben ejecutarse al mismo tiempo que el
cron remoto.

Además del cron, un cambio en `m3u.m3u`, `m3u-externa.m3u`,
`channel-catalog.m3u`, `resolver-catalog.json` o en la lógica del actualizador
dispara el workflow de canales inmediatamente y fuerza una corrida. Antes de
publicar, Actions sincroniza el contrato de resolutores, ejecuta el reparador
sobre todo el catálogo y comprueba que la principal conserve exactamente sus
`tvg-id`, que la externa sea su complemento y que ambas adopten los metadatos y
URLs vigentes del catálogo.

El proceso de canales corre a las 00:00, 06:00, 12:00 y 18:00 (hora de
Santiago). El proceso de EPG corre a las 00:30, 06:30, 12:30 y 18:30. Cada
ventana programada fuerza una consulta de enlaces dinamicos de TvVoo y Highfly;
la compuerta de seis horas solo protege
invocaciones locales o manuales repetidas fuera del cron. Los procesos
comparten una cola de publicacion para no competir por `main`.
GitHub puede iniciar unos minutos despues porque los cron son best effort.

La actualizacion de canales sincroniza siempre las URLs y metadatos actuales
con `m3u.m3u`, `m3u-externa.m3u`, sus alias cortos y `channel-catalog.m3u`.
La compuerta de calidad de EPG/logos permanece en el informe para diagnostico,
pero no deja una URL HLS efimera antigua en la lista principal; la EPG se
reconstruye en su proceso independiente.

TvVoo puede entregar algunos HLS `sunshine` con certificado vencido. No se
desactiva TLS de forma global: el fallback sin verificacion se permite solo
para el sufijo CDN conocido y la ruta HLS efimera de TvVoo, mientras que el
endpoint JSON, las fuentes oficiales, la EPG, logos y GitHub mantienen
verificacion normal. Los candidatos HTTPS se prueban despues de su variante
HTTP para evitar publicar un enlace que un reproductor estricto no pueda abrir.

TVN y Meganoticias conservan sus maestros oficiales. Actions no interviene en
la autenticacion de reproduccion; esa responsabilidad corresponde a la app.
Mega y La Red publican sus maestros oficiales directos. El PC no necesita
estar encendido para el mantenimiento normal.

La ejecucion tambien puede iniciarse manualmente desde la pestana **Actions** con
los workflows **Actualizar canales M3U** o **Actualizar EPG**. El primero
renueva streams y salud; el segundo fuerza la reconstruccion de la guia sobre
Lista 1 mediante una sola pasada del combinador.

Para corregir unicamente cabeceras, orden, logos, atributos de resolutor y la
particion exacta de las listas sin hacer sondas ni cambiar la membresia manual,
se puede ejecutar:

```text
python update_m3u.py --sanitize-list1-only
```

La sanitizacion es offline y reversible mediante Git: no retira canales por
fallos de salud, no descubre aliases y no renueva URLs efimeras.

TVN y TVN3 son señales distintas y nunca comparten parrilla: TVN conserva
`tvg-id="0104"`; TVN3 conserva `tvg-id="1437"` y publica además
`https://www.tvn.cl/tvn3` como referencia oficial de la señal. En el modo activo
cada bridge consulta únicamente su página o API oficial; si TVN3 no publica una
parrilla estable, recibe continuidad técnica y se vuelve a probar en la siguiente
corrida. Las páginas se procesan por canal para que un fallo independiente no descarte
TVN3. Si ninguna fuente entrega bloques exactos, TVN3 recibe `continuidad tecnica`
explicita en vez de heredar por error la programación de TVN o aceptar el bloque genérico
de 24 horas que publica TVN Play. Una guía anterior solo puede reutilizarse si fue
generada por el modo oficial.

Todos los logos de los canales se conservan dentro de `logos/` y la M3U y el
EPG apuntan a las copias publicadas en este repositorio. Los logos vectoriales
se mantienen como SVG y los demas como PNG para conservar la mejor calidad
disponible sin depender de servidores externos.

## Orden de la lista

El orden tematico se construye siempre desde `channel-catalog.m3u`, que
conserva todos los candidatos. `m3u.m3u` contiene la selección manual ya
probada; `m3u-externa.m3u` contiene el complemento publicable aún no promovido.
Ambas salidas filtran el mismo catalogo sin alterar la posicion relativa de los
canales. `3.m3u` es una salida separada para las señales estables de Highfly
Premium y no participa en el reparto manual de las listas 1 y 2. La salud no
cambia el reparto manual salvo el traslado automático y reversible de 13C.

La lista externa conserva todos los canales directos. Para los candidatos con
`x-resolver="tvvoo"`, la política de publicación de la lista 2 conserva solo
las familias Sky, Eurosport, ESPN y TNT Sports. Los demás Vavoo no se borran
del `channel-catalog.m3u`: quedan fuera de `m3u-externa.m3u` y `2.m3u`, pero
  siguen disponibles para validación y una futura revisión de selección. No se
  incluyen en `epg.xml` hasta pertenecer a Lista 1.

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

El catalogo contiene los candidatos nacionales, noticias, miscelaneos
chilenos, noticias internacionales, documentales, conciertos, musica y
deportes. `m3u.m3u` es la selección principal editada manualmente; ningún canal
sale de ella por un fallo aislado. `13C.cl@SD` es una excepción controlada:
después de tres fallos consecutivos puede pasar temporalmente a
`m3u-externa.m3u` y vuelve a la principal tras una validación correcta. El
reparador y los resolutores trabajan sobre ambas listas y el catalogo no pierde
ninguna entrada elegible.

Las antiguas sondas directas de Sky (`@Direct`/`(Directo)`) ya no forman parte
de ninguna lista pública. Las señales Sky que permanecen son las que tienen un
resolutor renovable o una fuente seleccionada explícitamente.

Las entradas históricas restauradas para investigación pertenecen al catálogo
externo. Solo las que cumplen la política de publicación y pasan la validación
actual llegan a `m3u-externa.m3u`/`2.m3u`; las que fallan se retiran
temporalmente de esa salida, pero todas se conservan en `channel-catalog.m3u`
para que cada corrida pueda revalidar sus aliases y fuentes. No se deben mover a
`m3u.m3u` mediante un cambio automático de salud. La excepción controlada es
13C, cuyo traslado y recuperación quedan registrados en
`channel-health-state.json`. Las variantes renombradas
`DAZN F1 España` y `Sky Sports F1 Reino Unido` no se duplican: sus aliases se
mantienen bajo `DAZN F1` y `Sky F1 UK`, respectivamente.

La EPG activa construye sus IDs esperados desde `m3u.m3u`/`1.m3u`, no desde la
lista externa ni desde la Lista 3. Un canal de Lista 1 sin bridge oficial no
provoca el fallo de toda la corrida: recibe `continuidad tecnica`, marcada en
`data-guide`, con bloques visibles `Live` de 00:00 a 23:59 en horario de Santiago.
No se presenta como una guía oficial. La siguiente corrida vuelve a probar el
bridge oficial y reemplaza esa cobertura cuando aparece una parrilla válida. Si
una página oficial repite tarjetas o publica intervalos solapados, el constructor
recorta el intervalo posterior o elimina el duplicado; el solapamiento de un canal
no invalida toda la guía.

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
del repositorio y nunca como sustituto de un bridge oficial.
