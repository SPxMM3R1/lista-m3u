# Investigación de fuentes deportivas y DASH

Fecha de corte: 2026-09-13, zona horaria America/Santiago.

Este informe documenta la búsqueda y las pruebas realizadas para Fox Sports,
ESPN, Eurosport, Sky Sports, TNT Sports y otras señales deportivas. La
investigación distingue entre una página oficial, un canal FAST público, un
índice comunitario y una fuente de reproducción realmente comprobada. No se
guardan tokens, claves, URLs firmadas, sesiones ni licencias DRM.

## Resultado publicado

- `b43e76f`: se añadió `FoxSports.ar@Direct179` a las fuentes externas para
  verificación manual.
- `48d9a9e`: se añadió soporte seguro para fuentes DASH y se publicó
  `MNBSport.mn@DirectDASH` como fuente DASH FTA en la lista externa.
- La publicación remota verificada corresponde a `48d9a9e30055c3a559cfa7904281e03481bfa156`.
- El árbol de trabajo conserva únicamente el directorio local de adjuntos sin
  seguimiento; no se incluyó en ningún commit.

## Método de prueba

Una respuesta HTTP 200 no se considera suficiente. Para HLS se comprobó:

1. descarga de la playlist;
2. reconocimiento de `#EXTM3U`;
3. resolución de la variante o playlist multimedia;
4. descarga de un fragmento multimedia.

Para DASH se comprobó:

1. MPD dinámico por HTTPS;
2. XML y namespaces válidos;
3. una representación de vídeo y una de audio;
4. `Initialization` y fragmentos recientes;
5. ausencia de `ContentProtection`, `pssh`, `laurl`, URLs de licencia y otras
   señales de DRM;
6. ausencia de query string o fragmentos de sesión en la URL persistida.

El nuevo validador está en [update_m3u.py](update_m3u.py) y las pruebas
unitarias en [tests/test_dash_support.py](tests/test_dash_support.py). Las
pruebas unitarias DASH pasan (4/4) y la suite completa pasó (99/99) antes de
la publicación.

## Fuentes publicadas y comprobadas

| Familia | Identificador | Resultado | Tratamiento |
| --- | --- | --- | --- |
| Fox Sports Argentina | `FoxSports.ar@Direct179` | HLS y fragmento válidos durante la comprobación | Añadido a lista 2 como candidato manual; no se etiqueta como oficial. |
| Fox Sports 1 | `FoxSports1.us@Direct`, `FoxSports1.us@DirectTVSEN7` | HLS y fragmento válidos | Se conserva en lista 2 para verificación; la renovación no se convierte en identidad del canal. |
| Fox Sports 2 | `FoxSports2.us@Direct` | HLS y fragmento válidos | Se conserva en lista 2. |
| Fox Deportes | `FoxDeportes.us@Direct23` | HLS y fragmento válidos | Se conserva como fuente directa candidata. |
| ESPN | `ESPN.us@Direct181`, `ESPN4.br@Direct181`, `ESPNU.us@Direct85`, `ESPNews.us@Direct41` | HLS y fragmento válidos en la comprobación | Se conservan como fuentes directas candidatas. |
| Eurosport | `Eurosport4KCzechia.cz@Direct` | HLS y fragmento válidos en la comprobación | Se conserva en lista 2; no se afirma que sea una fuente oficial de WBD. |
| FAST deportivo | beIN SPORTS XTRA y TyC Sports | El feed público FAST/Amagi y el de TyC pasaron la prueba | Las entradas existentes se conservan; no se sustituyen por una URL temporal de un tercero. |
| DASH FTA | `MNBSport.mn@DirectDASH` | MPD dinámico, vídeo 1920x1080, audio y fragmentos recientes válidos en 3 comprobaciones consecutivas | Añadido a lista 2 con `x-stream-format="dash"`. |

La página oficial de MNB publica su directo de MNB Sport en
[mnb.mn/live/tv3](https://www.mnb.mn/live/tv3), y el sitio de MNB identifica
la emisora y sus señales en [mnb.mn](https://www.mnb.mn/). El MPD publicado en
la lista es una fuente clara sin señalización DRM en el momento de la prueba.

## Candidatos investigados y no añadidos

Se probaron candidatos públicos encontrados en índices de IPTV y feeds FAST.
Pasar una comprobación puntual no basta para convertirlos en parte del
catálogo: muchos son comunitarios, geobloqueados, no 24/7 o cambian de origen.

- `Fubo Sports Network` y `FTF Sports`: entregaron HLS y fragmentos, pero no
  se encontró una garantía de que el endpoint concreto sea una fuente oficial
  estable para este proyecto. Quedan como candidatos para una aprobación
  manual posterior.
- `Band Sports` Brasil: varias rutas públicas pasaron la prueba, pero su
  disponibilidad y autorización geográfica no son suficientemente estables
  para publicarlas automáticamente.
- `CBS Sports Golazo Network`: la playlist respondió, pero el fragmento fue
  `403`; queda rechazado.
- beIN SPORTS XTRA en español desde una ruta IP comunitaria: falló la
  comprobación; no se sustituye el feed público existente.
- TyC Sports desde rutas IP comunitarias: hubo fallos intermitentes; solo se
  considera la variante FAST que pasó la prueba completa.

También se revisó [freecasthub/public-iptv](https://github.com/freecasthub/public-iptv),
que declara limitarse a señales públicas y legales. Su playlist deportiva no
aporta un Fox/ESPN/Eurosport/Sky/TNT lineal nuevo, pero sí produjo candidatos
interesantes para una futura lista deportiva gratuita. En la comprobación
actual pasaron Red Bull TV, FIFA+ English, FIFA+ Women, Esport3, Belarus 5,
TJK TV, Stadium, SportsGrid, FUEL TV, World of Freesports y Trace Sport Stars.
No se publicaron automáticamente: varios son regionales, no están disponibles
en Chile o no tienen EPG compatible, y un único pase no demuestra permanencia.
Motorsport.tv, Teledeporte, L'Équipe, ERT Sports, San Marino RTV Sport, RTSH
Sport, TVRI Sport, TDM Sports, RTA Sport y otros fallaron en el momento de la
prueba. MNB Sport apareció allí como HLS no reproducible, mientras que el MPD
HTTPS de MNB publicado en esta lista pasó tres pruebas; por eso se mantuvo la
fuente DASH ya validada y no se reemplazó por una variante peor.

El índice de [iptv-org/iptv](https://github.com/iptv-org/iptv) se usa solo como
descubridor. El propio proyecto mantiene un historial de enlaces rotos y
reclamaciones; en su solicitud de canales deportivos documenta que Eurosport
no se incorporaba por reclamaciones del titular
([issue #1380](https://github.com/iptv-org/iptv/issues/1380)). No se adopta
ninguna URL solo por aparecer en ese repositorio.

## Qué encontré sobre las fuentes oficiales

- Fox Sports mantiene su programación argentina en
  [foxsports.com.ar](https://foxsports.com.ar/), pero su servicio lineal
  internacional no expone allí un MPD/HLS público estable. En Estados Unidos,
  FOX indica que FOX One es el destino de sus señales y que el acceso es por
  proveedor o suscripción
  ([FAQ oficial de FOX](https://www.foxsports.com/fox-sports-fox-one-faqs)).
- ESPN documenta que ESPN, ESPN2, ESPNU, ESPNews y ESPN Deportes se consumen
  desde ESPN.com o la aplicación y que el acceso depende de un proveedor de
  vídeo o suscripción
  ([soporte oficial de ESPN](https://support.espn.com/hc/en-us/articles/115003801331-What-is-live-streaming-on-ESPN-com-or-the-ESPN-app)).
- Sky ofrece sus doce canales y los streams Sky Sports+ mediante una
  membresía de NOW
  ([NOW Sports](https://www.nowtv.com/membership/watch-sky-sports?DCMP=knc-google%3Anc_sports)).
  No aparece un feed público perpetuo que pueda guardarse en M3U.
- En Reino Unido e Irlanda, Eurosport y TNT Sports se integraron como destino
  deportivo premium; en otros países Eurosport continúa dependiendo del
  mercado. Esto está documentado por [Eurosport](https://help.eurosport.com/gb/Answer/Detail/000004679)
  y [Warner Bros. Discovery](https://www.wbd.com/tnt-sports). Por eso no se
  debe tratar un MPD autenticado de TNT/Eurosport como fuente FTA.
- Tubi publica un catálogo FAST deportivo que incluye FOX Sports on Tubi,
  Fox Sports en español, beIN SPORTS XTRA, Fubo Sports, PGA TOUR, NHL,
  DAZN Ringside, Real Madrid y otros
  ([catálogo oficial de Tubi](https://tubitv.com/help-center/Content/articles/24898743777435)).
  Son buenas fuentes para buscar programación y feeds públicos; el catálogo
  no garantiza que cada reproductor web tenga una URL M3U reutilizable ni que
  esté disponible en Chile.

## DASH: qué se puede y qué no se puede hacer

DASH es un formato de transporte; no elimina la autenticación ni el DRM. La
documentación de [MPEG-DASH](https://www.mpeg.org/standards/MPEG-DASH/) y de
[Akamai](https://techdocs.akamai.com/msl/docs/dash) contempla manifiestos
dinámicos, `BaseURL`, segmentos y cifrado/autenticación.

La solución implementada es deliberadamente limitada:

- se acepta un MPD HTTPS claro, sin query ni fragmento persistente;
- se valida el MPD, las representaciones de vídeo/audio, inicialización y
  fragmentos recientes;
- se rechaza automáticamente DRM, licencias, `pssh`, `ContentProtection` y
  MPD con sesión embebida;
- se respeta la redirección solo si sigue siendo segura;
- no se desactiva la verificación TLS;
- no se guardan claves ni se implementa ClearKey/Widevine/PlayReady;
- una URL `.mpd` se marca con `x-stream-format="dash"`; si falta el atributo,
  el parser la infiere por extensión, pero el validador sigue aplicando todas
  las comprobaciones.

Los repositorios comunitarios encontrados muestran repetidamente Fox Sports,
TNT y otros canales DASH acompañados de `ContentProtection` o claves de
licencia. Ese material se clasifica como DRM y no se incorpora. El reproductor
VibeM3U debe resolver una fuente autenticada oficialmente dentro de la app si
el usuario dispone de una suscripción; Lista M3U no debe convertir esa sesión
en un enlace persistente.

## Recomendación operativa

1. Mantener Fox/ESPN/Eurosport/Sky/TNT de origen dinámico en lista 2 salvo que
   el enlace directo pase la prueba de fragmento en varias corridas.
2. Mantener la renovación de TvVoo/Highfly en la aplicación y no en una URL
   estática de GitHub.
3. Ejecutar el chequeo DASH/HLS en cada corrida de canales; un fallo de una
   señal no debe borrar el catálogo completo.
4. Promover una nueva fuente solo después de tres comprobaciones separadas,
   sin query, sin DRM y con una EPG estable o una decisión explícita de dejarla
   como `Live`.
5. Para Fox One, ESPN, NOW/Sky Sports, TNT Sports o HBO Max, usar el flujo
   oficial autenticado de VibeM3U, no extraer ni publicar manifests de sesión.
