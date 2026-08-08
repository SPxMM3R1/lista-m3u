# Resolutor Chile para VibeM3U

Este servicio se despliega en Google Cloud Run, region
`southamerica-west1` (Santiago). No depende del PC de la casa.

Rutas publicas:

- `/health`
- `/tvn.m3u8`
- `/meganoticias.m3u8`

Cada ruta de canal obtiene el maestro oficial y responde con una redireccion
302. El token no se guarda en GitHub ni se escribe en los logs. Se reutiliza
durante 45 segundos para que la TV no haga varias renovaciones al abrir.

## Una sola configuracion de Google Cloud

El proyecto debe tener habilitados Cloud Run, Cloud Build y Artifact Registry.
La cuenta que despliega necesita permisos para Cloud Run y para publicar una
imagen desde Cloud Build.

La accion de GitHub espera:

- secreto `GCP_WORKLOAD_IDENTITY_PROVIDER`;
- secreto `GCP_SERVICE_ACCOUNT`;
- variable `GCP_PROJECT_ID` (si no existe, usa `rugged-episode-148820`).

Despues de configurar esos valores, ejecuta **Deploy Chile resolver** desde
GitHub Actions. La accion despliega en Santiago, hace publico el servicio,
guarda su URL en `M3U_RESOLVER_BASE_URL` y actualiza la M3U para usarlo.

Para una prueba manual equivalente:

```bash
gcloud run deploy vibem3u-chile-resolver \
  --source cloud-resolver \
  --region southamerica-west1 \
  --allow-unauthenticated \
  --min 0 --max 2 --memory 256Mi --timeout 30
```

El servicio escala a cero cuando no recibe peticiones. Solo mantener una
instancia minima activa si se prefiere eliminar el primer arranque en frio.
