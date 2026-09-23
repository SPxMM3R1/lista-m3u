# Contrato de identidades VibeM3U ↔ Lista M3U

## Objetivo

El editor web de `Lista M3U` crea y publica la selección de canales y sus
identidades de proveedor. `VibeM3U` consume esa selección para incorporar los
canales al orden local y resolverlos al iniciar la reproducción. El runner de
`Lista M3U` usa las mismas identidades para localizar, validar y publicar el
`tvg-id` canónico, la EPG y el logo correspondiente.

El uso de TvVoo y Highfly es app-only: el runner puede reconciliar sus
identidades, EPG, logos y referencias de resolución, pero no los agrega a la
membresía pública de `m3u.m3u`/`1.m3u`. VibeM3U incorpora los canales
seleccionados localmente y renueva su fuente al iniciar la reproducción,
evitando que una caída transitoria del proveedor obligue a regenerar la lista
pública.

La identidad que publique el editor debe permitir reconocer el mismo canal
después de una renovación del catálogo, un cambio de `leaf`, una actualización
de la URL HLS, un cambio de logo o un cambio de posición.

La regla principal es:

```text
catalogKey       = identidad estable del canal
providerResourceId / resolverSlug = localizador actual del proveedor
URL HLS          = resultado temporal de reproducción; nunca es una identidad
```

## Regla obligatoria para Highfly

Para Highfly, `catalogKey` es la identidad estable que se utilizará para
relacionar el canal con el catálogo público, la EPG y el logo.

Ejemplo correcto:

```json
{
  "provider": "highfly",
  "catalogKey": "SkySportsTennis.uk",
  "providerResourceId": "leaf:now-sky-sports-tennis",
  "resolverSlug": "now-sky-sports-tennis",
  "name": "Sky Sports Tennis",
  "group": "Deportes",
  "category": "Tennis",
  "order": 1
}
```

En este ejemplo:

- `SkySportsTennis.uk` permanece igual y sirve para EPG, logo y catálogo.
- `leaf:now-sky-sports-tennis` puede cambiar si Highfly rota su recurso.
- `now-sky-sports-tennis` sirve para solicitar el recurso actual.
- Ninguna URL HLS firmada se incluye en el documento.

Si Highfly cambia el recurso a `leaf:tennis-847291`, el cambio correcto es:

```json
{
  "catalogKey": "SkySportsTennis.uk",
  "providerResourceId": "leaf:tennis-847291",
  "resolverSlug": "tennis-847291"
}
```

El `catalogKey`, el `tvg-id`, la EPG, el logo y la identidad del canal no deben
cambiar por esa rotación.

## Identificadores y responsabilidades

| Campo | Obligatorio | Uso | ¿Puede cambiar? |
|---|---:|---|---:|
| `provider` | Sí | Motor que resolverá el canal (`highfly`, `tvvoo`) | No para el mismo canal |
| `catalogKey` | Sí | Clave estable para EPG, logo, catálogo y reconciliación | No |
| `providerResourceId` | Sí para Highfly | Recurso actual del proveedor, por ejemplo `leaf:abc123` | Sí |
| `resolverSlug` | Sí para Highfly | Slug usado por el endpoint de resolución | Sí |
| `name` | Sí | Nombre visible y pista editorial | Sí, con revisión |
| `countryKey` | Recomendado | Desambiguación regional | Solo con migración explícita |
| `category` | Recomendado | Grupo y búsqueda editorial | Sí |
| `order` | Recomendado | Orden elegido en la aplicación | Sí |
| `aliases` | Recomendado | Búsqueda controlada de una EPG o logo existente | Sí, sin cambiar `catalogKey` |
| `identityState` | Recomendado | `canonical` o `provisional` | Sí al confirmar la identidad |

## Cómo debe construirse `catalogKey`

### Canal que ya existe en Lista M3U

Debe utilizarse exactamente el identificador canónico que ya tiene el
catálogo de `Lista M3U`.

Ejemplos:

```text
SkySportsF1.uk
SkySportsTennis.uk
SkySportsPremierLeague.uk
```

Esto permite localizar directamente:

```text
tvg-id de la M3U
channel id de epg.xml
mapa de logos
fuente de EPG configurada
```

No se debe crear otra ID porque cambie el `leaf` o porque el nombre visible
venga con una etiqueta como `(FHD)` o `4K`.

### Canal nuevo que todavía no existe en Lista M3U

El editor debe publicar una identidad determinista. La prioridad es:

1. ID canónica proporcionada por Highfly, si existe.
2. Alias canónico estable definido por el proyecto.
3. Fallback determinista derivado del proveedor, región y nombre normalizado.

El fallback debe marcarse como provisional:

```json
{
  "provider": "highfly",
  "catalogKey": "Highfly.SkySportsExample.uk",
  "identityState": "provisional",
  "name": "Sky Sports Example",
  "countryKey": "uk"
}
```

Una ID provisional no debe convertirse automáticamente en un `tvg-id` público
ni recibir una EPG por coincidencia aproximada. El runner debe revisarla y
confirmarla antes de publicarla como identidad canónica.

## Lo que no debe usarse como `catalogKey`

Nunca usar como identidad estable:

```text
leaf:now-sky-sports-tennis
now-sky-sports-tennis
https://leaf.highfly.dev/...m3u8
https://...m3u8?token=...
1001
1002
el nombre visible sin región ni proveedor
```

Los números secuenciales pueden cambiar cuando se inserta o elimina un canal.
El nombre solo puede repetirse en distintas regiones. El `leaf` y la URL HLS
son datos de resolución, no de identidad.

## Formato del archivo de selección

El archivo que publica el editor web y consume VibeM3U es:

```text
data/vibem3u-selection.json
```

La estructura mínima es:

```json
{
  "schemaVersion": 1,
  "sources": [
    {
      "provider": "highfly",
      "enabled": true,
      "channels": [
        {
          "provider": "highfly",
          "catalogKey": "SkySportsTennis.uk",
          "providerResourceId": "leaf:now-sky-sports-tennis",
          "resolverSlug": "now-sky-sports-tennis",
          "name": "Sky Sports Tennis",
          "group": "Deportes",
          "category": "Tennis",
          "countryKey": "uk",
          "identityState": "canonical",
          "order": 1
        }
      ]
    }
  ]
}
```

El runner debe aceptar campos adicionales sin romperse, pero no debe considerar
una URL HLS, un token o una contraseña como parte válida de la selección.

## Cómo buscar la EPG

El runner buscará la programación en este orden:

1. Coincidencia exacta de `catalogKey` con el catálogo canónico de Lista M3U.
2. Coincidencia exacta de `catalogKey` con `EPG_PROGRAMME_SOURCES` o el mapa
   equivalente de fuentes.
3. Mapa editorial explícito para una migración conocida.
4. Coincidencia exacta y única por `provider + countryKey + aliases`.
5. Coincidencia exacta y única por nombre normalizado, solo como último
   recurso y siempre dejando evidencia en el reporte.

No se debe asignar EPG por:

- posición en la lista;
- coincidencia parcial ambigua;
- bitrate;
- `providerResourceId` rotatorio;
- URL de reproducción;
- similitud aproximada entre dos países.

La salida pública debe conservar la ID canónica:

```xml
<channel id="SkySportsTennis.uk">
  <display-name>Sky Sports Tennis</display-name>
</channel>
<programme channel="SkySportsTennis.uk" ...>
  ...
</programme>
```

Si no existe una fuente confiable o hay más de una coincidencia, el runner debe
dejar el canal en estado `epg_pending` y reportar el motivo. No debe inventar
una asociación.

## Cómo buscar el logo

El logo se resolverá independientemente de la URL del proveedor:

1. Mapa curado por `catalogKey`.
2. Logo local existente asociado al `catalogKey`.
3. Alias canónico + país, siempre que la coincidencia sea única.
4. Búsqueda editorial controlada usando `name`, `countryKey` y `category`.

La prioridad siempre será la ID estable. No se debe usar el nombre `(FHD)`, el
slug `leaf` ni el nombre del archivo remoto como identidad del logo.

Si no se puede confirmar el logo, se conserva el canal sin reemplazarlo por un
logo de otra región y se informa:

```text
logo_status=pending
logo_reason=no_unique_match
catalogKey=SkySportsTennis.uk
```

## Reconciliación cuando Highfly rota un recurso

El runner debe comparar primero por `catalogKey`:

```text
selección anterior:
  catalogKey=SkySportsTennis.uk
  providerResourceId=leaf:old

selección nueva:
  catalogKey=SkySportsTennis.uk
  providerResourceId=leaf:new
```

Resultado esperado:

- actualizar solo el localizador Highfly;
- conservar el `tvg-id` público;
- conservar la EPG;
- conservar el logo;
- conservar el orden editorial;
- no crear un segundo canal;
- no eliminar el canal por haber cambiado el `leaf`.

## Reglas para bitrate y candidatos

Los candidatos HLS de Highfly pertenecen al mismo `catalogKey`. La calidad no
crea una nueva identidad:

```text
SkySportsTennis.uk
  ├── candidato 8.2 Mbps
  ├── candidato 5.1 Mbps
  └── candidato 3.8 Mbps
```

La aplicación debe ordenar y probar primero el candidato con mayor bitrate
anunciado. Si la validación HLS falla, puede probar el siguiente. Las URLs
resultantes viven solo durante la reproducción y no se publican en este
archivo.

## Validación obligatoria antes de aceptar una ID

El runner debe rechazar o marcar para revisión cualquier fila que tenga:

- `catalogKey` vacío;
- `catalogKey` diferente al ID canónico conocido sin una migración explícita;
- `catalogKey` basado únicamente en un número secuencial;
- `providerResourceId` usado como `tvg-id`;
- `resolverSlug` con una URL, query string o token;
- una URL HLS en la selección;
- dos canales con el mismo `catalogKey` y distinto país sin una regla explícita;
- más de una EPG o logo posible sin una elección editorial;
- un `identityState=provisional` tratado como identidad pública confirmada.

## Resultado esperado del runner

Por cada fila válida, el runner debe producir un reporte similar a:

```text
catalogKey=SkySportsTennis.uk
provider=highfly
tvg_id=SkySportsTennis.uk
resource_updated=true
epg_status=matched
epg_source=uk1/SkySp.Tennis.HD.uk
logo_status=matched
logo_path=logos/sky-sports-tennis.png
publication_scope=channel_only
```

Si solo cambia `providerResourceId` o `resolverSlug`, la publicación debe ser
acotada al canal afectado. No debe regenerar ni reordenar toda la lista por ese
cambio.

## Compatibilidad con TvVoo

Para TvVoo se mantiene el mismo principio, aunque su `catalogKey` tiene el
formato definido por su contrato:

```text
countryKey|canonicalAlias
```

El `catalogKey` TvVoo tampoco debe confundirse con una URL HLS, un token o un
alias temporal. El runner usará esa clave para conservar el `tvg-id`, la EPG y
el logo publicados.

## Checklist para el editor de selección

Antes de publicar una selección, el editor web debe comprobar:

- [ ] `provider` está permitido.
- [ ] `catalogKey` existe y es estable.
- [ ] `catalogKey` no depende de un `leaf` ni de una URL HLS.
- [ ] Highfly incluye `providerResourceId` y `resolverSlug` separados.
- [ ] `providerResourceId` empieza por `leaf:` y no contiene token.
- [ ] `resolverSlug` contiene solo el slug, sin `leaf:` ni URL.
- [ ] `name`, `category` y `order` corresponden a la selección del usuario.
- [ ] una rotación del recurso no cambia `catalogKey`.
- [ ] no se publican URLs HLS, contraseñas, firmas ni respuestas completas del
  proveedor.

La identidad debe ser útil para que Lista M3U encuentre EPG y logos sin tener
que adivinar qué canal quiso seleccionar el usuario.

## Catálogo editorial compartido con el editor web

El orden de reproducción y la visibilidad que el usuario prepara en el editor
se publica en `data/channel-editor-layout.json`, con `schemaVersion: 1`, una
lista `channels` y la lista durable `excludedM3u` para identidades M3U
eliminadas definitivamente de la vista editorial. Cada fila usa `tvgId` como identidad para M3U o `catalogKey`
para Highfly/TvVoo; nunca usa el orden, número, `providerResourceId`,
`resolverSlug` ni una URL como identidad.

Una fila tiene `order` y `number` positivos, y `state` igual a `active`,
`hidden` o `deleted`. Ocultar o enviar a papelera un canal Highfly/TvVoo lo
retira de `data/vibem3u-selection.json`, pero la fila editorial se conserva
para poder restaurarla. Eliminar definitivamente solo borra la fila editorial;
no elimina un registro del catálogo fuente ni los artefactos originales de
Lista M3U. Para una fila M3U purgada, `excludedM3u` conserva el `tvgId` como
tombstone hasta que se vuelva a añadir desde el catálogo disponible. La app
debe excluir esos IDs de su catálogo visible y ocultarlos también en el almacén
local; debe mostrar únicamente filas `active` en el orden indicado, con
respaldo a su catálogo integrado si el archivo aún no está disponible.

La asignación directa a Lista 1 o Lista 2 se conserva en `sourceList` de cada
fila M3U (`1.m3u` o `2.m3u`). El sitio exporta las filas activas a
`presentation-overrides.json` en `orders.m3u.m3u` y
`orders.m3u-externa.m3u`, y las filas M3U ocultas, en papelera o purgadas a
`excluded_m3u`. El runner usa esas decisiones para actualizar la pertenencia
de las dos salidas públicas, valida que ninguna exclusión aparezca en ellas y
falla sin publicar si la Lista 1 quedara vacía. Las exclusiones fuera del
catálogo actual se mantienen como tombstones, sin tratarse como identidades
de reproducción.

El editor descubre Highfly y TvVoo directamente desde sus catálogos públicos;
no requiere importar un archivo generado por la aplicación ni llama a
endpoints de reproducción. Para Highfly, los nombres se contrastan con el
registro canónico de `channel-catalog.m3u`; las identidades nuevas o ambiguas
se mantienen provisionales para que el runner no les asigne EPG o logo por
aproximación. Los IDs de evento que no usan el prefijo persistente `leaf:` no
se ofrecen como canales ordenables.

Para TvVoo, el editor toma los catálogos regionales declarados por el
manifiesto y selecciona un país por vez. Construye `catalogKey` con la misma
normalización `countryKey|canonicalAlias` que `TvVooCatalogChannel` en
VibeM3U; mantiene el alias en `aliases` y usa `catalogKey` como
`providerResourceId`. Los logos remotos y las referencias de reproducción no
se copian. El editor conserva las elecciones existentes y solo refresca
`providerResourceId`/`resolverSlug` cuando Highfly rota una referencia para el
mismo `catalogKey`.

El editor escribe las elecciones de logo local en `presentation-overrides.json`
como un mapa `logos` de identidad estable a ruta existente bajo `logos/`. Para
Highfly/TvVoo la clave es `catalogKey`; el runner solo traslada esa elección al
`tvg-id` canónico después de una coincidencia confirmada. El runner valida la
ruta y aplica la URL pública local al `tvg-logo`. El orden de cada playlist M3U
se conserva en `presentation-overrides.json` bajo `orders`; el orden global
combinado, las asignaciones Lista 1/2, los estados editoriales y los tombstones
viven en `data/channel-editor-layout.json`.
