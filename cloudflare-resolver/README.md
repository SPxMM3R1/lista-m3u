# Resolutor Cloudflare para VibeM3U

Variante gratuita del resolutor de TVN y Meganoticias. Mantiene las mismas
rutas publicas que el servicio de Cloud Run:

- `/health`
- `/tvn.m3u8`
- `/meganoticias.m3u8`

El Worker obtiene el token temporal, responde con una redireccion 302 al
master oficial y conserva el resultado durante 45 segundos. No escribe el
token en los logs ni en GitHub.

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
