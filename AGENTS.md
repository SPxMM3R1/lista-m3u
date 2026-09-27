# AGENTS.md — Lista M3U

Guía para agentes de IA que trabajen en este repositorio (catálogo público, runner de canales/resolutores, EPG y editor web).

## Qué es este repositorio

- Catálogo público que consume VibeM3U (Android TV): `channel-catalog.m3u` (inventario canónico), `m3u.m3u`/`1.m3u` (Lista 1), `m3u-externa.m3u`/`2.m3u` (Lista 2), `epg.xml`, `epg-pending.json`, `resolver-catalog.json`, `logos/`.
- Runner: `update_m3u.py` (canales y resolutores; incluye `build_epg`/`refresh_epg`), `run_m3u_6h.py`, `run_epg_6h.py`, `publish_epg.py`, `targeted_update.py`, `change_plan.py`, `scripts/build_site_data.py`.
- Editor web: `site/` (JS puro). La lógica pura vive en `site/editor-core.mjs` y `site/provider-catalog.mjs` con tests en `tests/editor-core.test.mjs`. Se sirve con el auxiliar `VibeM3U/local-catalog`.
- Datos editoriales publicados: `data/channel-editor-layout.json` (orden, número, visibilidad y logos que lee la app), `data/vibem3u-selection.json` (declaración de proveedores para el runner) y `presentation-overrides.json` (órdenes y exclusiones).

## Límites

- No modificar el checkout de VibeM3U desde aquí ni mover archivos entre repositorios. Un commit por repositorio.
- La identidad pública es `catalogKey` (Highfly) o `countryKey|alias` (TvVoo). `providerResourceId`, `resolverSlug` y las URL HLS son referencias que pueden rotar; nunca usarlas como identidad.
- Nunca escribir tokens, credenciales, URL firmadas ni secretos en JSON, M3U, EPG, logs o commits.
- No publicar sin: tests en verde, diff revisado y estado remoto verificado.

## Cómo trabajar

- Tests obligatorios antes de commitear:
  - `python -m unittest discover -s tests -p "test_*.py"` (esperado: 174 en verde).
  - `node --test tests/editor-core.test.mjs` (esperado: 24 en verde).
- Validar el editor local sin tocar el repo: `python scripts/build_site_data.py --output <carpeta temp>` (solo acepta salidas dentro de la carpeta temporal).
- Commits en español con prefijo: `feat(editor)`, `fix(resolvers)`, `feat(epg)`, `fix(catalogo)`, `chore(...)`.
- Cambios del editor: primero `site/editor-core.mjs` (o `provider-catalog.mjs`) con test, después `site/editor.js`, `site/index.html` y `site/styles.css`.
- Verificación de publicaciones: el Raw de GitHub cachea minutos; comprobar con `git show origin/main:<archivo>` o raw fijado al SHA del commit.

## Publicación automática

- Push de un commit editorial (layout/selección/presentación) dispara `update-channels.yml` con `M3U_MAINTENANCE_SCOPE=main` (Lista 2 se conserva; el catálogo recibe igual la reconciliación). Al terminar bien, `update-epg.yml` corre por `workflow_run`.
- Canales por cron: `0 4,10,16,22` America/Santiago. EPG por cron: `0 0,6,12,18` America/Santiago, forzada (`EPG_FORCE_REFRESH=true`).
- Puede dispararse a mano: `gh workflow run update-channels.yml -f force_run=true` y `gh workflow run update-epg.yml`.
- `deploy-site.yml` publica el editor en GitHub Pages cuando cambian `site/**` o `scripts/build_site_data.py`.

## Reglas funcionales vigentes

- EPG solo para Lista 1 más canales gestionados con fuente (aislados y opcionales): prioridad oficial → Zapping (frontales `*-apig.zappingtv.com` con `curl --connect-to`) → TecnoCentro; Red Bull con respaldo Pluto. Sin relleno técnico: si no hay fuente, el canal queda pendiente diagnosticado; única excepción acordada: Rwnd = `Live`.
- Procurar al menos 12 h de programación por canal en cada corrida; los pendientes se reintentan por canal dentro de la corrida y en cada ciclo de 6 h.
- El runner no inventa programación, EPG ni coincidencias: ante ambigüedad, dejar pendiente.

## Documentos de referencia

- `VIBEM3U_ID_CONTRACT_EPG_LOGOS.md` (contrato de identidad, EPG y logos).
- `RESOLVER_RECIPE_CONTRACT.md` y `VAVOO_TVVOO_SOLUCIONES_VIBEM3U.md`.
- `LOCAL_CATALOG_EDITOR.md` (editor local y auxiliar).
- `PRODUCT.md` y `README.md` (descripción vigente del producto).
