# Contrato de receta de resolutores para VibeM3U

Estado: `schemaVersion: 1`, catálogo base `2026.09.01.4`, receta
`bounded-payload-v1`.

Este repositorio publica datos. VibeM3U conserva toda la lógica ejecutable.
Los dos proyectos tienen historiales Git independientes y no deben copiar
clases Android ni mezclar commits.

## Archivos públicos

- Lista principal manual: `m3u.m3u` y su alias `1.m3u`.
- Lista externa: `m3u-externa.m3u` y su alias `2.m3u`.
- Inventario completo: `channel-catalog.m3u`.
- Configuración declarativa: `resolver-catalog.json`.
- Identidades descubiertas de TvVoo: `tvvoo-discovered.json`.
- Guía compartida para todo el inventario: `epg.xml`.

La pertenencia manual no cambia con esta receta: los mismos 42 canales siguen
en la principal y el complemento permanece en la externa. En la última siembra
el reparador trabaja sobre 225 canales del catálogo; el descubrimiento diario
puede aumentar ese complemento dentro de su límite seguro.

## Metadatos TvVoo obligatorios

Cada canal presente en `TVVOO_STREAM_RESOLVER_IDS` debe publicar:

```m3u
#EXTINF:-1 tvg-id="Canal.pais@TvVoo" tvg-name="Canal" x-resolver="tvvoo" x-resolver-endpoint="https://tvvoo.hayd.uk/stream/tv" x-resolver-ids="alias-1;alias-2" x-resolver-refresh="on_play" x-resolver-recipe="bounded-payload-v1",Canal
https://respaldo-temporal.example/hls/index.m3u8
```

Reglas:

- `x-resolver-ids` contiene aliases estables y ordenados, nunca URLs de sesión.
- `x-resolver-recipe` es idéntico para todos los canales TvVoo incluidos.
- No se añade la receta a TVN, Meganoticias, Highfly, Pluto o fuentes directas.
- La URL de la línea siguiente sigue siendo respaldo para otros reproductores.
- La EPG continúa asociándose exclusivamente mediante el `tvg-id` estable.

## Autorización en el catálogo

El proveedor `tvvoo` publica esta configuración:

```json
{
  "recipeId": "bounded-payload-v1",
  "validationMode": "media-signature-v1",
  "maxPayloadDepth": 6,
  "maxExtractedStrings": 256
}
```

La M3U solamente solicita la capacidad. La receta se activa cuando el catálogo
validado y la APK autorizan exactamente el mismo ID. Por eso una modificación
de la lista no puede hacer que VibeM3U ejecute una transformación desconocida.

`bounded-payload-v1` permite a la APK reconocer, bajo límites estrictos, URLs
HLS dentro de JSON anidado o serializado, entidades HTML, URL encoding y
Base64. VibeM3U valida luego playlist, variante, segmento y firma multimedia;
también bloquea destinos de red privados y valida cada redirección.

## Generación y validación

`update_m3u.py` es la fuente autoritativa:

- `TVVOO_RECIPE_ID` fija el ID solicitado por la lista.
- `resolver_attributes_for()` lo aplica únicamente a TvVoo.
- `build_resolver_catalog()` autoriza el mismo ID y sus límites.
- `validate_playlist_resolvers()` exige que todos los aliases y recetas
  coincidan exactamente.
- `validate_resolver_catalog()` bloquea motores, hosts, tokens, recetas y modos
  no permitidos.
- `discover_tvvoo_catalog.py` consulta únicamente catálogos públicos, agrupa
  variantes de calidad, deduplica por alias y escribe solo identidades
  estables en `tvvoo-discovered.json`; no modifica la membresía de la lista 1.
- `catalogVersion` avanza automáticamente en el componente de parche cuando
  cambia el mapa estable, sin modificar el código ejecutable del resolutor.

Comandos sin red para el contrato:

```text
python update_m3u.py --sync-resolver-contract
python update_m3u.py --validate-resolvers-only
```

La ejecución de canales vuelve a sincronizar el contrato antes de publicar las
dos listas. Debe comprobar que la principal conserva su secuencia de `tvg-id`,
que la externa es el complemento exacto del catálogo y que las copias cortas
son idénticas a sus archivos canónicos.

## Datos prohibidos

No deben publicarse en `resolver-catalog.json` ni en atributos `x-resolver-*`:

- `serverKey`, firmas o tokens;
- `access_token` o queries de autorización;
- respuestas `streams[].url`;
- URLs `/sunshine/` o direcciones de sesión;
- código JavaScript, DEX, JAR o instrucciones ejecutables.

Los enlaces HLS efímeros pueden aparecer únicamente como la URL de respaldo de
una entrada M3U y se reemplazan en la siguiente reparación. La app no los usa
como identificador persistente.

## Evolución y compatibilidad

Cambiar aliases, límites o un endpoint ya permitido requiere aumentar
`catalogVersion`; el escritor lo hace automáticamente para los descubrimientos
estables. Una transformación nueva requiere un ID nuevo y una APK que
lo incluya explícitamente; no se cambia silenciosamente el significado de
`bounded-payload-v1`.

Una APK antigua ignora `x-resolver-recipe` y conserva el parser previo. Una APK
nueva, pero sin catálogo coincidente, falla de forma cerrada para esa receta y
mantiene los fallbacks conocidos. El documento complementario del lado Android
es `RESOLVER_RECIPE_V1.md` en el repositorio VibeM3U.
