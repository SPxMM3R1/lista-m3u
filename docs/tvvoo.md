# TvVoo tras el retiro de la instancia pública — 2026-11-06

`tvvoo.hayd.uk` redirige a la guía de ElfHosted con la marca `retired`; en CI,
la API responde 429. No se debe conservar `/live/` como fuente permanente.

Lista 1 conserva sus seis identidades TvVoo, nombres, logos, números y EPG.
Sus URL y las de esas seis filas canónicas pasan a referencias
`tvvoo://channel/<catalogKey codificado>`. `pin_resolver_metadata` migra una
URL del host retirado únicamente si declara `x-resolver="tvvoo"` y una
`x-resolver-stable-id` válida. No infiere identidades desde nombres.
Se declara también `x-resolver-country`, derivado de la identidad. Una tabla cerrada
`TVVOO_LEGACY_REFERENCE_KEYS` conserva los seis tvg-id históricos sin permitir
que apunten a otro alias. El runner las informa como `identity_only`; eso no acredita reproducción.

VibeM3U 0.6.59 conserva `TvVooStreamResolver` y su selector, pero obtiene los enlaces
mediante `VavooSessionClient` en RAM. El engine
publicado sigue llamándose `tvvoo`; no cambia el contrato ni la identidad. Con
MediaFlow, se descubre el destino original en el catálogo Vavoo y se entrega
al extractor configurado por el usuario, sin consultar la instancia retirada.

Las variantes se obtienen del inventario del código oficial
https://github.com/qwertyuiop8899/tvvoo/blob/main/src/channels/lists.json
sin resolver enlaces ni tokens. Un país ausente (Italia no está en ese archivo)
se considera fallo y conserva sus variantes anteriores. Nunca interpretar una
lista vacía como desaparición de todas las señales de un país.

Pruebas de la ruta nativa en VibeTV, 2026-11-07 02:21–02:22 UTC:
Sky Sports Main Event, TNT Sports 3, TNT Sports 4 y Eurosport 1 superaron playlist y segmento.
TNT 3 y 4 además mostraron video real (rugby y cricket) en la app. DAZN F1 y
Eurosport 2 mantienen fallos de origen 502/403. Son fallos
de esas fuentes, no una recuperación completa de las seis señales. En la
instancia local de referencia, Main Event mostró Sky Sports News: no cambiar
su EPG o nombre automáticamente a partir de ese alias mal rotulado.

La instancia Node local fue una prueba aislada, se apagó antes del test nativo
y no es necesaria para la TV. No se publican firmas ni URL de sesión.

La presentación guardada nunca debe quitar alias/country de una referencia.
`apply_presentation_overrides` conserva los metadatos de enrutamiento actuales
al aplicar nombres, grupos y logos antiguos. Validación real de sincronización:
13 selecciones reconciliadas, 0 pendientes y contrato con 1.494 identidades TvVoo.
