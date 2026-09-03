# Solución Vavoo/TvVoo para VibeM3U

Documento de traspaso técnico para el proyecto independiente `VibeM3U`.

Fecha de revisión: 2026-09-02

Repositorio de la lista: `SPxMM3R1/lista-m3u`
Repositorio de la aplicación: `VibeM3U`

Este documento describe el problema observado en reproducción, la solución
recomendada para la APK y los criterios que deben cumplirse antes de publicar
una nueva versión. No contiene tokens, claves, URLs firmadas ni respuestas
temporales de los proveedores.

## Resumen ejecutivo

Los canales no dejaron de existir todos al mismo tiempo. Se separaron cuatro
casos:

1. Las URLs HLS debajo de las entradas TvVoo son temporales. Una muestra de las
   URLs publicadas respondió `HTTP 410 Gone`. Un reproductor genérico que ignore
   `x-resolver-*` las verá como caídas.
2. El endpoint externo de TvVoo continúa entregando candidatos. Una prueba
   fresca distribuida por países y categorías obtuvo HLS reproducible en 22 de
   24 canales probados.
3. El modo Vavoo propio tiene un fallo de transporte común: `vavoo.to` y
   `kool.to` presentan un certificado TLS vencido. La app falla antes de leer el
   catálogo porque su cliente HTTP valida TLS estrictamente.
4. El catálogo público de Lista M3U contiene 222 claves de alias TvVoo, pero la
   APK actual limita el objeto de aliases a 128 claves. La opción de actualizar
   resolutores puede rechazar el catálogo remoto completo.

La solución estable recomendada es hacer que VibeM3U resuelva TvVoo en el
momento de reproducir, renueve una fuente cuando caduque, acepte el catálogo
completo y mantenga Vavoo propio como fallback experimental mientras el
certificado del proveedor no esté corregido.

## Estado comprobado

### Lista M3U

La lista externa actual contiene aproximadamente:

- 230 canales totales.
- 220 entradas con `x-resolver="tvvoo"`.
- 222 aliases en `resolver-catalog.json`.
- Aliases explícitos publicados en la M3U para los canales dinámicos.

El contrato que deben conservar las entradas TvVoo es:

~~~
#EXTINF:-1 tvg-id="ID_ESTABLE" tvg-name="Canal" x-resolver="tvvoo" x-resolver-endpoint="https://tvvoo.hayd.uk/stream/tv" x-resolver-ids="alias-1;alias-2" x-resolver-refresh="on_play" x-resolver-recipe="bounded-payload-v1" group-title="PRUEBA - Deportes",Canal
https://respaldo-temporal.example/hls/index.m3u8
~~~

La URL de respaldo no debe tratarse como identidad permanente del canal. Los
aliases, `tvg-id` y los atributos `x-resolver-*` sí son parte estable del
contrato.

### Última ejecución del actualizador

En la última ejecución de canales revisada:

- 172 señales fueron renovadas.
- 2 señales fueron recuperadas.
- 48 señales quedaron temporalmente no disponibles.
- El conjunto revisado fue de 222 candidatos.

Las corridas de GitHub Actions terminaron correctamente. Eso no garantiza que
una URL firmada continúe viva hasta la siguiente ejecución: la duración de la
sesión y la revocación dependen del proveedor.

### Prueba fresca de TvVoo

La prueba solicitó candidatos nuevos y validó la cadena completa:

~~~
endpoint de candidatos
  -> playlist master
  -> variante HLS
  -> primer segmento
~~~

Resultado de una muestra de 24 canales:

- 22 con HLS reproducible.
- 1 sin candidato actual para el alias probado.
- 1 con candidato, pero con fallo de validación HLS.

Conclusión: TvVoo no presenta una caída global. La app debe resolver una fuente
nueva y no reutilizar la URL firmada que fue publicada horas antes.

### Prueba de Vavoo propio

Con validación TLS normal:

~~~
www.vavoo.tv  -> HTTP 200
www.vypn.net  -> HTTP 200
vavoo.to      -> error de verificación de certificado
kool.to       -> error de verificación de certificado
~~~

En una prueba aislada de diagnóstico, sin aceptar esa configuración para
producción, el catálogo volvió a entregar resultados y se obtuvieron fuentes
HLS reproducibles para DAZN F1 y Sky Sports F1 Alemania. Esto indica que el
servicio no está necesariamente vacío; el bloqueo principal es el certificado
vencido de los hosts del catálogo.

## Causa según el modo de reproducción

### Reproductor IPTV genérico

Si el reproductor solo lee la línea HLS de la M3U, el resultado será inestable:

~~~
M3U descargada
  -> URL HLS firmada antigua
  -> HTTP 410
  -> Source error
~~~

Ningún cron de GitHub puede convertir esas URLs efímeras en URLs permanentes.
Para esos reproductores solo se puede ofrecer una URL reciente de respaldo,
pero la reproducción fiable requiere un resolutor dentro del player o un relay.

### VibeM3U con TvVoo externo

Debe funcionar si se cumplen estas condiciones:

- La APK contiene el resolver flexible de los commits `95f4ea2` y `77811f9`.
- El grupo de resolutores TvVoo está habilitado.
- La app usa los `x-resolver-ids` de la M3U.
- Se selecciona `Automático` o `TvVoo externo`.
- La app no intenta reproducir primero la URL estática caducada.

### VibeM3U con Vavoo propio

Puede fallar todo el grupo porque la sesión directa no llega a completar el
flujo `ping -> catálogo -> resolve`. En la fuente actual, `VavooSessionClient`
utiliza `TokenHttpClient`, que no tiene un fallback específico para un
certificado vencido.

## Arquitectura recomendada

### Orden de resolución

~~~
1. x-resolver explícito
2. tvg-id exacto
3. sufijo estable de tvg-id
4. host permitido
5. URL directa como último fallback
~~~

Cuando exista `x-resolver="tvvoo"`, la app debe preferir la resolución fresca
antes de probar la URL debajo de `#EXTINF`.

### Flujo de reproducción

~~~
canal M3U
  -> identificar proveedor
  -> obtener aliases explícitos
  -> solicitar candidatos frescos
  -> validar master, variante y segmento
  -> crear fuente Media3 con cabeceras de reproducción
  -> reproducir sin persistir la URL temporal
~~~

### Flujo de renovación

~~~
reproducción
  -> 401/403/404/410 o fallo de segmento
  -> invalidar fuente en memoria
  -> resolver una vez más
  -> validar HLS
  -> reanudar o informar indisponibilidad temporal
~~~

No se deben realizar reintentos indefinidos ni reutilizar una URL que ya
respondió `410`.

## Archivos de VibeM3U implicados

La implementación debe revisarse en estos archivos del repositorio de la app:

~~~text
app/src/main/java/cl/streambox/tv/TvVooStreamResolver.java
app/src/main/java/cl/streambox/tv/VavooStreamResolver.java
app/src/main/java/cl/streambox/tv/VavooSessionClient.java
app/src/main/java/cl/streambox/tv/TokenHttpClient.java
app/src/main/java/cl/streambox/tv/ResolverCatalog.java
app/src/main/java/cl/streambox/tv/ResolverCatalogRepository.java
app/src/main/java/cl/streambox/tv/ResolverDefinition.java
~~~

La lista M3U y VibeM3U siguen siendo repositorios independientes. La lista
publica datos, aliases, EPG, logos y URLs de respaldo; la APK contiene la
lógica ejecutable de resolución, validación y reproducción.

## Cambios necesarios en VibeM3U

### 1. TvVoo externo como camino principal

En modo `Automático`, usar el orden:

~~~
TvVoo externo
  -> Vavoo propio solo si está habilitado y disponible
  -> URL HLS estática como último respaldo
~~~

La preferencia explícita del usuario debe seguir respetándose. Si el usuario
selecciona solamente Vavoo propio, no se debe cambiar silenciosamente a otro
proveedor; se puede informar que el motor no está disponible.

### 2. Renovación ante fuente caducada

Los siguientes resultados deben invalidar la fuente actual:

- HTTP 401.
- HTTP 403.
- HTTP 404.
- HTTP 410.
- Fallo de master playlist.
- Fallo de variante.
- Fallo del primer segmento.

Política recomendada:

- Presupuesto inicial de resolución: 10–12 segundos.
- Una sola renovación automática por apertura.
- Máximo de dos ciclos completos de resolución por canal.
- Si ambos fallan, mostrar el motivo concreto y liberar el estado sensible.

### 3. Mantener los aliases de la M3U como autoridad

Cuando `x-resolver-ids` exista, no añadir aliases antiguos de la APK por delante
ni cambiar el orden publicado por Lista M3U.

Prioridad:

~~~
x-resolver-ids de la M3U
  > compatibilityAliases del catálogo
  > compatibilidad integrada en la APK
~~~

Los aliases deben deduplicarse después de leerlos, sin doble codificación de
los valores URL-encoded.

### 4. Aumentar el límite del catálogo

La APK actual limita `compatibilityAliases` a 128 claves, pero el catálogo de
Lista M3U tiene 222. Deben separarse los límites de coincidencias de los límites
del mapa de aliases.

Propuesta:

~~~java
MAX_ALIAS_CHANNELS = 512;
MAX_ALIASES_PER_CHANNEL = 12;
MAX_TOTAL_ALIAS_VALUES = 4096;
MAX_CATALOG_BYTES = 256 * 1024;
~~~

La validación debe conservar:

- tamaño máximo del archivo;
- máximo de proveedores;
- longitud máxima de cada clave y alias;
- hosts de configuración permitidos;
- recetas permitidas;
- esquema compatible;
- rechazo atómico de catálogos inválidos.

No basta con borrar el límite. El catálogo remoto debe seguir siendo datos
declarativos y nunca código ejecutable.

### 5. Actualizar el catálogo de forma segura

La app puede revisar el catálogo cada 24 horas, además de conservar el botón
manual `Opciones > Resolutores > Actualizar resolutores`.

Flujo:

~~~
descargar
  -> comprobar HTTPS
  -> validar tamaño
  -> validar JSON y schemaVersion
  -> validar providers y engines
  -> validar hosts y aliases
  -> comparar catalogVersion
  -> guardar con reemplazo atómico
~~~

Si falla cualquier comprobación, mantener el catálogo anterior y continuar la
reproducción con la configuración instalada.

### 6. Vavoo propio estable

La versión estable debe mantener validación TLS normal. El orden recomendado es:

1. HTTPS estricto contra el endpoint primario.
2. HTTPS estricto contra un host alternativo oficialmente publicado.
3. Fallback a TvVoo externo si el modo automático lo permite.
4. Informar que Vavoo propio está temporalmente bloqueado por el certificado.

No utilizar HTTP para el ping, la firma, el catálogo ni la resolución de Vavoo.

### 7. Vavoo propio experimental

Si se decide añadir compatibilidad temporal para el certificado vencido, debe
existir un cliente separado y una política explícita. Nunca se debe desactivar
TLS de toda la aplicación.

Requisitos mínimos:

- Solo en la variante experimental.
- Desactivado por defecto.
- Solo para hosts exactos permitidos.
- Solo para rutas exactas de ping, catálogo y resolución.
- Activación únicamente ante un error de certificado vencido.
- No aceptar cualquier error TLS como motivo de bypass.
- No usar fallback HTTP para la sesión de autenticación.
- No persistir tokens, firmas ni respuestas de sesión.
- No escribir URLs firmadas en logs, analytics o preferencias.
- Desactivar automáticamente la compatibilidad cuando el certificado vuelva a
  ser válido.
- Preferir pinning de clave pública previamente verificada.
- Mantener un interruptor de emergencia para apagar el modo desde el catálogo
  seguro o desde una nueva versión de la APK.

Esta variante debe mostrar una advertencia interna de que reduce la garantía de
autenticidad del transporte y no debe convertirse automáticamente en el modo
estable.

### 8. Relay opcional

Un relay puede ser una alternativa si el proveedor no corrige su certificado,
pero debe resolver solamente la sesión y los candidatos. No debe retransmitir el
vídeo completo salvo que se acepte el coste de ancho de banda.

El relay tendría que incorporar:

- rate limiting;
- límites por IP y canal;
- validación estricta de hosts;
- bloqueo de redirecciones privadas;
- respuestas sin caché persistente;
- eliminación de tokens y URLs firmadas de los logs;
- protección contra abuso;
- expiración corta de las respuestas.

No es la primera opción porque añade infraestructura y una nueva dependencia
operativa. GitHub Actions no debe utilizarse como relay de reproducción.

## Política de caché y datos sensibles

La app no debe persistir:

- URLs HLS firmadas;
- tokens;
- `serverKey`;
- firmas de sesión;
- query strings de autorización;
- respuestas completas de resolución;
- cabeceras sensibles.

La URL dinámica puede vivir solamente en memoria durante la reproducción. Al
cambiar de canal, cerrar la sesión o recibir un error de expiración, debe
liberarse.

El sanitizador de caché puede conservar los atributos `x-resolver-*` y sustituir
la URL persistente por un placeholder no reproducible, siempre que el resolver
vuelva a solicitar la fuente al abrir el canal.

## Pruebas de aceptación

La nueva APK no debería publicarse hasta pasar estas pruebas.

### Pruebas de catálogo

- Instalar el catálogo con 222 aliases sin recibir `Demasiados aliases`.
- Rechazar JSON inválido sin borrar el catálogo anterior.
- Rechazar un engine desconocido sin desactivar los demás proveedores.
- Rechazar hosts fuera de la allowlist.
- Comparar versiones sin permitir retrocesos.

### Pruebas de M3U

- Conservar todos los atributos `x-resolver-*`.
- Usar aliases explícitos como autoridad.
- No duplicar aliases después de decodificar y recodificar.
- Mantener `tvg-id` aunque cambie la URL HLS.
- No convertir Pluto ni canales directos en TvVoo por coincidencias de nombre.

### Pruebas de reproducción

- Resolver un canal TvVoo con la URL estática caducada y reproducirlo mediante
  un candidato nuevo.
- Recibir `410`, invalidar la URL y resolver nuevamente.
- Rechazar un candidato cuyo master responde 200 pero cuyo primer segmento
  falla.
- Conservar cabeceras de reproducción solo en memoria.
- Liberar el estado sensible después de cambiar de canal.

### Pruebas de degradación

- TvVoo sin candidatos: probar el siguiente alias y luego informar la causa.
- TvVoo externo temporalmente inaccesible: mantener el fallback controlado.
- Vavoo propio con certificado inválido: no bloquear los canales directos ni
  los de TvVoo.
- Catálogo remoto caído: utilizar el catálogo instalado anteriormente.
- Proveedor desconocido: mantener el canal como directo o no disponible, sin
  bloquear la carga completa de la M3U.

### Pruebas de seguridad

- Confirmar que no se desactiva TLS globalmente.
- Confirmar que no se aceptan redirecciones a localhost, LAN o metadata service.
- Confirmar que los logs no contienen tokens ni URLs firmadas.
- Confirmar que el modo Vavoo experimental queda deshabilitado en la APK estable.
- Confirmar que los límites de tamaño, aliases y tiempo siguen activos.

## Cambios que requieren nueva APK

Requieren compilar y publicar una nueva versión de VibeM3U:

- aumentar el límite de aliases;
- renovar automáticamente tras 401/403/404/410;
- cambiar el orden de fallback de resolutores;
- añadir actualización automática del catálogo;
- modificar la política TLS de Vavoo;
- añadir pinning o cliente experimental;
- cambiar el comportamiento de caché de la sesión;
- agregar nuevos hosts permitidos.

No requieren nueva APK si el motor ya existe:

- cambiar un alias estable;
- corregir el nombre o logo del canal;
- corregir una asociación EPG;
- agregar un canal que ya utilice el contrato TvVoo actual;
- renovar la URL HLS de respaldo de la M3U.

## Plan de implementación propuesto

### Fase 1: corrección estable mínima

1. Aceptar 222 aliases en `ResolverCatalog` con límites separados.
2. Hacer TvVoo externo prioritario en modo automático.
3. Resolver antes de usar la URL estática.
4. Renovar una vez después de 401/403/404/410 o fallo HLS.
5. Mantener la URL estática únicamente como último fallback.
6. Ejecutar pruebas unitarias y de contrato en GitHub Actions.

### Fase 2: robustez operativa

1. Actualizar el catálogo cada 24 horas con instalación atómica.
2. Mostrar errores de resolución diferenciados.
3. Añadir métricas locales no sensibles de proveedor, etapa y duración.
4. Confirmar que el catálogo anterior sobrevive a una actualización inválida.
5. Verificar la APK real instalada, no solo el código fuente.

### Fase 3: Vavoo experimental

1. Mantener Vavoo propio separado del cliente HTTP general.
2. Añadir compatibilidad limitada solo en la variante experimental.
3. Validar certificado, host, ruta y clave pública.
4. Mantener TvVoo como fallback.
5. Publicar la variante experimental separada de la estable.

## Resultado esperado

Con la solución completa:

~~~
URL estática caducada
  -> no rompe el canal
  -> VibeM3U usa x-resolver-ids
  -> TvVoo entrega una fuente fresca
  -> HLS se valida de extremo a extremo
  -> Media3 reproduce
~~~

Y cuando Vavoo propio tenga un problema de certificado:

~~~
Vavoo propio bloqueado por TLS
  -> no bloquea la app
  -> no bloquea TvVoo
  -> no bloquea canales directos
  -> se conserva el catálogo anterior
  -> se informa la indisponibilidad del motor
~~~

## Decisión recomendada

Para producción:

~~~
TvVoo externo prioritario
+ aliases explícitos de la M3U
+ renovación al detectar expiración
+ catálogo de aliases ampliado
+ caché sin URLs de sesión
+ TLS estricto
+ Vavoo propio como fallback solo cuando sea válido
~~~

Para la APK experimental:

~~~
Todo lo anterior
+ motor Vavoo propio
+ compatibilidad TLS acotada
+ pinning de clave pública
+ interruptor de emergencia
+ sin desactivar TLS global
~~~

La lista M3U no puede hacer permanente una fuente firmada ni corregir el
certificado de un proveedor. La parte dinámica debe resolverse dentro de
VibeM3U, justo antes de reproducir.
