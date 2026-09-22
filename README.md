# Lista M3U para Android TV

![Icono minimalista de VibeM3U](branding/vibem3u-icon.png)

Repositorio publico de la lista M3U principal para Android TV. El mantenimiento
esta separado en dos procesos independientes: uno actualiza canales,
resolutores y salud; el otro construye la EPG sobre el catalogo completo. Ambos
usan ventanas fijas de seis horas y publican sus salidas sin sobrescribirse.

El icono del proyecto se conserva como un recurso independiente de los logos de
canales y no participa en la generación de las listas ni de la EPG.

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

Highfly y TvVoo son fuentes de reproducción exclusivas de VibeM3U. Sus canales
no pertenecen a la lista principal (`m3u.m3u`/`1.m3u`): sus identidades se
conservan en `channel-catalog.m3u` y la aplicación los incorpora desde su
selección local para resolverlos justo al reproducir. El catálogo público de
Highfly solo se consulta para renovar en memoria los slugs declarados por la
app; el runner no promueve una selección de VibeM3U a la membresía pública.

Guia de programacion XMLTV:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/epg.xml`

Catalogo declarativo de resolutores para VibeM3U:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/resolver-catalog.json`

VibeM3U publica su selección de proveedor, sin URLs de reproducción, en
`data/vibem3u-selection.json`. El runner consume ese archivo cuando existe:
cruza Highfly por `catalogKey` y TvVoo por `catalogKey`/alias estable para
validar identidades, EPG, logos y referencias de resolución, pero mantiene esas
familias fuera de `m3u.m3u`/`1.m3u`. Las filas provisionales, ausentes o ambiguas
quedan como `pending` en `channel-status.json`; no se convierten en un `tvg-id`
ni reciben EPG/logo por aproximación. Un cambio en ese archivo dispara el
workflow de canales para actualizar metadatos y el workflow independiente de
EPG para regenerar de inmediato la guía del catálogo canónico completo, sin
volver a publicar una URL dinámica en la lista principal.

El contrato completo de identidades, EPG y logos está en
[VIBEM3U_ID_CONTRACT_EPG_LOGOS.md](VIBEM3U_ID_CONTRACT_EPG_LOGOS.md).

La M3U conserva una URL HLS de respaldo para reproductores externos. VibeM3U
usa los atributos `x-resolver-*` para resolver la fuente justo antes de abrirla:
TVN y Meganoticias conservan sus masters oficiales para que la aplicacion
obtenga la autorizacion al reproducir; 24 Horas se mantiene como canal directo,
TvVoo usa aliases estables y Highfly usa el `manifest.json` configurado junto
con el slug de hoja vigente del catalogo publico. Pluto y los canales directos
siguen sin resolutor. El catalogo solo
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
- TVE Internacional conserva su feed oficial de America en 1080p y prueba la
  variante oficial 576p como respaldo; ambas deben entregar playlist y segmento
  antes de aceptarse;
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
- usa las parrillas oficiales disponibles de TVN y Mega, ademas de las de M1 y
  M2; conserva EPGShare como respaldo cuando el emisor no publica XMLTV o una
  parrilla automatizable;
- integra PLEX1 para las señales FAST de BBC, CBS, Qello, Stingray y XITE; las
  fuentes EPGShare por país se descargan solo cuando un canal del catálogo
  tiene una asociación activa, y no se descarga el XML combinado de todos los
  proveedores;
- incorpora la parrilla XMLTV de PlutoTV para MTV Biggest Pop,
  MTV Spankin' New y MTV Flow Latino; las tarjetas repetidas de Pluto
  se deduplican antes de construir la EPG;
- conserva en `channel-catalog.m3u` las identidades TvVoo incorporadas manualmente
   para noticias, deportes, música/conciertos, películas y adultos, manteniendo
   un solo canal lógico por señal y sus aliases estables por país. El grupo TvVoo `ar` se
   conserva en `channel-catalog.m3u` como inventario de reintento, pero queda
   excluido de la lista externa hasta una selección manual explícita. Las
   señales adultas no se eliminan del catálogo por su temática ni por falta de
   un logo seguro (en ese caso quedan sin logo). Las películas se marcan como
   subtituladas solo si
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
  `manifest.json` y el catalogo publico una vez por corrida; cuando el
  proveedor rota una hoja, consulta
  `stream/sport/leaf:{slug}.json` y solo acepta una HLS HTTPS de
  `papacito.cfd`; si la API informa varios streams, se prueban primero en
  orden descendente de bitrate anunciado y se conserva el primero que supera
  la validación HLS;
- los reintentos y tiempos de espera se ajustan por motor: directos, TVN,
  Meganoticias, TvVoo y Highfly tienen limites propios para que un proveedor
  lento no bloquee a los demas. Los candidatos aceptados durante la renovacion
  ya llegan validados a la salida y no se comprueba toda la lista por segunda
  vez;
- usa el mismo enlace HTTP solo cuando el nodo HTTPS responde con certificado
  vencido y la excepcion se limita a los hosts conocidos de Highfly;
- conserva los identificadores canonicos de Highfly y los aliases de TvVoo como
  fuentes renovables. El slug que cambia el proveedor solo vive en memoria
  durante la corrida; si una fuente deja de existir, el actualizador solicita
  candidatos nuevos, valida su HLS y publica el enlace que respondió. Las
  respuestas de upgrade de Google, URLs de evento y hosts fuera de la lista
  permitida se descartan;
- consulta el catálogo público de Highfly únicamente para validar y renovar en
  memoria los slugs `leaf:` declarados por VibeM3U; ignora eventos temporales
  `streamed:` y no copia URLs firmadas, tokens ni posters del proveedor;
- prioriza la guia oficial de Canal 13 para 13C, manteniendola separada de
  13 Cultura; si la pagina oficial no entrega bloques vigentes, usa Zapping
  como respaldo por canal;
- usa la página oficial de programación de Chilevisión para CHV, con los
  bloques semanales convertidos a XMLTV; si esa página falla, conserva el
  respaldo normal por canal sin mezclar la guía de CHV con otra señal;
- usa las páginas oficiales separadas de DW Español (`DW.de`) y DW English
  (`DWEnglish.de`). `DW.de` no se asocia al registro ambiguo
  `Deutsche.Welle.es` de EPGShare, porque puede entregar la parrilla
  internacional en inglés; si la página oficial en español falla, se conserva
  el canal y se genera solo `Live` técnico, sin reciclar esa guía incorrecta.
  Para `DWEnglish.de`, la entrada `dwe` de Zapping queda como primer fallback
  agregado porque entrega títulos en inglés; el feed letón que solo dice
  “programa no disponible” no se usa. `DW-TV.fr` queda como respaldo XMLTV
  final cuando la página oficial y Zapping no entregan una ventana suficiente;
- Red Bull Español se consulta exclusivamente en la página regional oficial
  `https://www.redbull.tv/es_CL/epg`. La API global no se usa como fallback para
  ese canal, porque puede devolver una parrilla de otra región; si la página
  regional falla, se deja continuidad técnica en vez de publicar una guía
  incorrecta.
- mantiene Premier Sports 1 y Premier Sports 2 desde los resolutores JSON
  publicos de TvVoo, con renovacion cada 6 horas y guia UK1 real;
- resuelve las señales nacionales en este orden: adaptador oficial del canal
  cuando existe (TVN, Mega, CHV, Canal 13, La Red y 13C), luego la entrada
  correspondiente de Zapping y finalmente EPGShare/TecnoCentro. Para
  Meganoticias, que no publica una parrilla XML/HTML diaria estable separada
  en su página oficial, `meganoticias` de Zapping es el fallback operativo;
  nunca se sustituye por la parrilla de Mega. Las marcas Unix de Zapping se
  convierten a America/Santiago sin sumar horas manualmente;
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

Las identidades TvVoo se mantienen manualmente en `channel-catalog.m3u` y sus
aliases se reflejan en `resolver-catalog.json`. El mantenimiento de canales
renueva y valida las fuentes de las identidades existentes; no añade canales
automáticamente ni modifica la membresía de la lista principal. El grupo `ar`
se conserva en el catálogo para reintento, pero permanece fuera de la salida
pública hasta una selección manual explícita.

El coordinador `run_m3u_6h.py` conserva `run-state.json`; el coordinador
`run_epg_6h.py` conserva `epg-run-state.json`. Las ventanas locales de Chile
quedan fijas: canales a las 04:00, 10:00, 16:00 y 22:00; EPG a las 00:00,
06:00, 12:00 y 18:00. Así la primera EPG del día se construye a las 06:00 y
normalmente encuentra terminada la renovación de canales de las 04:00. Cada
estado mantiene su ventana de seis horas. GitHub Actions es el ejecutor
principal desde ahora. La tarea local queda deshabilitada y los scripts locales
se conservan solamente como respaldo manual; no deben ejecutarse al mismo
tiempo que el cron remoto.

Los cambios de `push` ya no fuerzan el mantenimiento completo. El workflow
`Publicar cambios dirigidos` clasifica el diff antes de tocar la red:

- logos, orden y metadatos se validan offline y solo sincronizan las listas o
  aliases afectados;
- un cambio de URL valida únicamente los `tvg-id` modificados y propaga su
  bloque a las listas derivadas, sin renovar Highfly, TvVoo ni el resto del
  catálogo;
- `epg-overrides.json` permite renovar y mezclar solo los canales indicados en
  `epg.xml`, preservando los demás programas;
- cada cambio dirigido exitoso queda registrado para el runner de seis horas:
  `presentation-overrides.json` conserva orden/metadatos/logos, el manifiesto de
  streams conserva una selección manual y `epg-manual-overrides.xml` conserva
  los bloques EPG editados directamente;
- cambios de lógica, contrato, membresía o fuentes globales se prueban y se
  difieren a la siguiente ventana completa.

La corrida completa aplica esos manifiestos después de su normalización
automática. Por eso una decisión editorial, un stream fijado o un bloque EPG
manual no se pierde cuando se renuevan los demás canales. Para liberar una
decisión hay que eliminar su entrada del manifiesto correspondiente; la
próxima ventana vuelve entonces a aplicar las reglas automáticas normales.

Para un cambio de stream se puede editar el bloque del canal en el catálogo o
declararlo en `stream-overrides.json`, por ejemplo:

```json
{
  "channels": {
    "CanalEjemplo.cl": {
      "url": "https://servidor.example/live/master.m3u8",
      "reason": "cambio manual de stream"
    }
  }
}
```

Los streams fijados deben ser URLs durables, sin query, firma ni token de
sesión. Los enlaces efímeros `/sunshine/` se renuevan mediante el resolutor y
no se guardan como una decisión manual permanente.

Para dirigir una fuente EPG se usa `epg-overrides.json` sin incluir tokens ni
URLs de sesión:

```json
{
  "channels": {
    "CanalEjemplo.cl": {
      "source": "sky-oficial",
      "source_id": "4091"
    }
  }
}
```

El clasificador falla cerrado si un cambio mezcla stream y EPG, cambia la
membresía o no permite identificar con seguridad los canales afectados. En
esos casos no publica parcialmente: espera la corrida completa. Las corridas
dirigidas no escriben `run-state.json` ni `epg-run-state.json`, por lo que no
alteran el próximo horario de mantenimiento.

Los horarios anteriores son los horarios reales de GitHub Actions. GitHub puede
iniciar unos minutos después porque los cron son best effort; la compuerta de
seis horas solo protege invocaciones locales o manuales repetidas fuera del
cron. Los procesos comparten una cola de publicación para no competir por
`main`.

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
disponible sin depender de servidores externos. Los logos MTV locales usan una
geometría común: en la referencia de 1280x783 px la marca ocupa 514x308 px y
el espacio vacío hasta el nombre ocupa 36 px (11,69 % de la altura de la
marca). Esa proporción se conserva en `mtv-biggest-pop.svg`,
`mtv-flow-latino.svg`, `mtv-spankin-new.svg` y `mtv-hits.png`, sin cambiar sus
colores, formas ni identificadores de canal.

## Orden de la lista

El orden tematico se construye siempre desde `channel-catalog.m3u`, que
conserva todos los candidatos. `m3u.m3u` contiene la selección manual de
canales directos, TVN y Meganoticias; `m3u-externa.m3u` contiene el complemento
publicable aún no promovido. TvVoo y Highfly quedan fuera de ambas decisiones
de membresía de la lista principal y VibeM3U los añade localmente cuando el
usuario los selecciona. La salud no cambia el reparto manual salvo el traslado
automático y reversible de 13C.

La lista externa conserva todos los canales directos. Para los candidatos con
`x-resolver="tvvoo"`, la política de publicación de la lista 2 conserva solo
las señales deportivas de Sky (incluidas `Sky Sport`, `Sky Sports` y `Sky Super
Tennis`), Fox Sports, Eurosport, ESPN y TNT Sports. Por tanto, Sky Cinema, Sky Nature, Sky
Documentaries y Sky News quedan fuera de la salida externa. También excluye
todas las entradas con aliases `|group:ar`, incluidas las que no muestran la
etiqueta `[TvVoo ar]` en el nombre. El grupo `ar` no se borra
del `channel-catalog.m3u`: quedan fuera de `m3u-externa.m3u` y `2.m3u`, pero
siguen disponibles para EPG, validación y una futura revisión de selección.
Las exclusiones manuales solicitadas para la lista 2 siguen la misma regla:
permanecen en `channel-catalog.m3u` para EPG y reparación, pero se mantienen
fuera de la publicación externa en las siguientes ejecuciones.

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
XMLTV, resolutores ni URLs de respaldo. Dentro de `Música`, el catálogo agrupa
primero todos los canales XITE, después todos los MTV y luego conserva el orden
relativo del resto de señales musicales.

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
para que cada corrida pueda revalidar sus aliases, fuentes y EPG. No se deben mover a
`m3u.m3u` mediante un cambio automático de salud. La excepción controlada es
13C, cuyo traslado y recuperación quedan registrados en
`channel-health-state.json`. Las variantes renombradas
`DAZN F1 España` y `Sky Sports F1 Reino Unido` no se duplican: sus aliases se
mantienen bajo `DAZN F1` y `Sky F1 UK`, respectivamente.

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
La EPG usa fuentes XMLTV de Chile, Espana, México, Francia, Alemania, Reino Unido,
Argentina, Portugal, Nueva Zelanda, Estados Unidos, Polonia, Letonia, Paises
Bajos, PLEX1 y PlutoTV, junto con la guia publica
de Zapping para senales chilenas seleccionadas. El orden es: fuente oficial
del canal, XMLTV real por pais/proveedor y Zapping u otra fuente secundaria
real. Telehit Música usa la fuente EPGShare MX1 con el ID exacto
`Canal.Telehit.Música.mx`. M1, M2 y 13C se
actualizan desde sus parrillas oficiales. La EPG
construye sus IDs esperados desde `channel-catalog.m3u`: un
canal que permanezca en la lista externa continua recibiendo EPG y no causa un
error por no aparecer en `m3u.m3u`. La EPG conserva al menos un bloque para cada
canal del catalogo, incluso si su HLS falla. Cuando ninguna fuente real
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
