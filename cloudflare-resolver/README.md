# Resolutor Cloudflare para VibeM3U

Variante gratuita del resolutor de TVN, Mega y Meganoticias. Mantiene rutas
publicas para las senales:

- `/health`
- `/mega.m3u8`
- `/tvn.m3u8`
- `/meganoticias.m3u8`

El Worker obtiene los tokens temporales de TVN y Meganoticias. Para Mega lee el
master oficial, selecciona la variante 1080p con audio y convierte sus
referencias `http://` a `https://`. Las rutas con token responden con una
redireccion 302; Mega responde con una playlist HLS simplificada y renovada.
No escribe tokens en los logs ni en GitHub.

## Despliegue

El workflow `Deploy Cloudflare resolver` necesita estos secretos del
repositorio:

- `CLOUDFLARE_API_TOKEN`: token de Cloudflare con permiso para desplegar
  Workers Scripts.
- `CLOUDFLARE_ACCOUNT_ID`: identificador de la cuenta de Cloudflare.

El Worker se publica en `workers.dev`, guarda su URL en la variable
`M3U_RESOLVER_BASE_URL` y luego vuelve a generar la M3U. La lista solo se
conecta al Worker despues de que `/health` responde correctamente.

Cloudflare ejecuta Workers en su red global. Eso evita la dependencia de este
PC y de la facturacion de Google Cloud, pero no garantiza que cada peticion al
origen salga con una IP chilena.
