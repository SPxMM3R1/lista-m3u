# Contrato VibeM3U: Lista 3 de canales Highfly Premium

Fecha de corte: 2026-09-03.

Este documento define el limite entre este repositorio de listas y el proyecto
Android TV VibeM3U. La lista no reproduce ni renueva tokens. Su responsabilidad
es publicar la membresia estable, los identificadores y los metadatos que la
app necesita para resolver cada canal al abrirlo.

## Responsabilidades

| Componente | Responsabilidad |
|---|---|
| Lista M3U | Generar y publicar 3.m3u con todos los canales Premium estables que el catalogo publico declare como leaf:<slug>. |
| VibeM3U | Descargar/cachear 3.m3u, leer el slug y pedir la fuente HLS actual con la credencial configurada justo antes de reproducir. |
| VibeM3U, Lista 4 | Consultar el catalogo protegido para eventos temporales seleccionados. Esos eventos son virtuales, se agregan al final y no se publican en este repositorio. |
| EPG y logos | Permanecen bajo control del runner de Lista M3U. La app consume sus URLs publicas y no reconstruye esos metadatos desde el catalogo protegido. |

Lista 3 y Lista 4 no son la misma cosa:

- 3.m3u es una salida publica, estable y cacheable.
- La Lista 4 es una vista efimera propiedad de la app. Puede cambiar durante
  el dia y no debe entrar a 3.m3u, m3u.m3u, 1.m3u ni 2.m3u.

## Fuentes publicas

El archivo que consume VibeM3U es:

    https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/3.m3u

El runner obtiene la membresia estable desde:

    https://sports.highfly.dev/catalog/sport/sports_live.json

La pagina de configuracion Premium no se usa para generar la lista y nunca se
debe guardar una credencial en este repositorio.

## Contrato de cada entrada de 3.m3u

Cada canal estable debe conservar estos atributos en #EXTINF:

~~~m3u
#EXTINF:-1 tvg-id="SkySportsF1.uk" tvg-name="Sky Sports F1" tvg-country="GB" tvg-logo="https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/logos/sky-sports-f1.png" group-title="Lista 3 · Highfly Premium · Deportes" x-resolver="highfly" x-resolver-id="now-sky-sports-f1-free" x-resolver-manifest="https://sports.highfly.dev/manifest.json" x-resolver-refresh="on_play" x-highfly-premium-stable="true" x-highfly-premium-id="leaf:now-sky-sports-f1-free" x-highfly-premium-kind="estable" x-highfly-premium-list="3",Sky Sports F1
https://leaf.highfly.dev/m3u/now-sky-sports-f1-free/live.m3u8
~~~

Reglas:

1. x-resolver="highfly" selecciona el motor Highfly de VibeM3U.
2. x-resolver-id contiene solamente el slug sin leaf:.
3. x-highfly-premium-id contiene la identidad completa leaf:<slug>.
4. x-highfly-premium-stable="true", x-highfly-premium-kind="estable" y
   x-highfly-premium-list="3" identifican inequívocamente una entrada de
   Lista 3.
5. La URL debajo de #EXTINF es un localizador publico de respaldo. No es la
   URL canonica de autorizacion y no debe llevar query string, token, firma,
   cookie ni identificador de sesion.
6. tvg-id debe ser estable. Para canales ya conocidos se conservan los IDs
   que permiten reutilizar la EPG existente. Para una señal nueva se usa un ID
   determinista que no colisione con Lista 1 ni Lista 2.
7. tvg-logo apunta a un logo versionado dentro de logos/, no al poster
   protegido del proveedor.
8. No agregar el marcador generico x-highfly-premium a una entrada estable.
   Ese marcador y x-highfly-premium-virtual="true" quedan reservados para
   eventos de Lista 4 creados dentro de VibeM3U.

Los atributos desconocidos deben seguir siendo conservados por el parser de
VibeM3U. No cambiar el significado de los nombres sin actualizar ambos
proyectos.

## Generacion y actualizacion

El generador implementado en update_m3u.py:

- acepta unicamente IDs leaf:<slug> seguros del catalogo publico;
- descarta IDs streamed:, sf:, eventos y valores que no sean slugs;
- elimina duplicados por slug;
- aplica un orden determinista, conservando primero las posiciones historicas;
- reutiliza tvg-id, nombre y logo local cuando ya existe una identidad
  conocida;
- escribe una URL leaf publica sin autorizacion;
- valida que todas las entradas tengan los marcadores de Lista 3;
- no copia posters privados, respuestas de streams ni tokens.

Si el catalogo publico cambia:

- un slug estable que desaparece se elimina de la siguiente 3.m3u valida;
- un slug que vuelve a aparecer se agrega nuevamente;
- una respuesta vacia, invalida o una falla transitoria no destruye la lista
  anterior: el runner conserva el ultimo archivo valido y deja el aviso en su
  salida.

Esto permite que la app actualice la membresia de forma transparente usando su
cache, sin hacer una consulta protegida para descubrir canales estables.

Comandos locales de validacion:

    python update_m3u.py --sync-highfly-premium-list
    python update_m3u.py --validate-resolvers-only
    python -m unittest discover -s tests -p "test_*.py"

El workflow debe incluir 3.m3u en snapshots, commit, validacion y verificacion
de GitHub Raw. La actualizacion normal de la M3U principal no debe incorporar
automaticamente la lista 3 a m3u.m3u: son salidas separadas.

## EPG y logos

El runner incluye las entradas validas de 3.m3u en el conjunto usado para
refrescar la EPG. Las cinco identidades historicas conocidas conservan sus
IDs de canal; las nuevas identidades reciben la asociacion que exista en el
catalogo EPG y, si aun no existe una fuente real, quedan con continuidad
tecnica hasta que se agregue un mapeo verificado.

Los logos se resuelven desde este repositorio. No depender de posters del
catalogo Premium para la interfaz de VibeM3U: esos posters pueden ser
temporales, privados o cambiar de formato.

## Flujo de reproduccion esperado en VibeM3U

Para un canal de Lista 3, VibeM3U debe:

1. Leer el slug desde x-highfly-premium-id o x-resolver-id.
2. Leer la credencial Premium configurada por el usuario.
3. Construir en memoria la solicitud protegida de fuente para leaf:<slug>.
4. Obtener la URL HLS actual desde el endpoint Premium.
5. Validar la cadena HLS y entregar la fuente actual a Media3.
6. Descartar la URL temporal al invalidar la reproduccion, cambiar de canal o
   recibir un rechazo de autorizacion.

El token puede formar parte de la URL de solicitud al proveedor porque ese es
el contrato del endpoint Premium, pero nunca debe agregarse a 3.m3u, a una
preferencia, a la cache persistente, a analytics ni a un log. La URL HLS
firmada que devuelva el proveedor tiene el mismo tratamiento efimero.

Cuando la credencial no esta configurada o el endpoint Premium falla, la app
puede probar una vez el localizador leaf publico como respaldo de un canal
estable. Ese fallback no convierte la URL publica en una nueva fuente
persistente y no se aplica a eventos temporales.

## Lista 4: eventos temporales

La Lista 4 no se genera aqui. VibeM3U consulta el catalogo protegido solamente
cuando el usuario activa los eventos, muestra la seleccion y crea entradas en
memoria con:

- una identidad de evento estable durante esa sesion;
- x-highfly-premium="true";
- x-highfly-premium-virtual="true";
- x-highfly-premium-kind="evento";
- x-highfly-premium-list="4";
- un placeholder que nunca se entrega como HLS real.

Los eventos seleccionados se agregan despues de todos los canales de las listas
1, 2 y 3. No se agregan al runner, a la EPG publica ni a un commit.

## Prohibiciones

No hacer ninguna de estas cosas:

- pegar una credencial o access_token en 3.m3u;
- publicar una URL HLS firmada como si fuera el slug;
- usar el formato o el nombre visible del canal como identidad principal;
- copiar eventos temporales a la lista estable;
- sustituir tvg-id por una URL o por un token;
- guardar respuestas Premium en el repositorio;
- modificar VibeM3U desde este proyecto;
- reactivar un proxy, Worker o servidor local para ocultar una renovacion que la
  app puede ejecutar directamente.

El contrato de esta lista es deliberadamente declarativo: si cambia el formato
del catalogo, se modifica el parser del runner y se mantiene la salida M3U.
VibeM3U solo necesita recibir slugs y metadatos estables.
