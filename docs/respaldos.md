# Respaldos: reglas vigentes

> Movidas desde `AGENTS.md` el 2026-10-31 sin cambiar el texto. **Léelo antes de tocar respaldos** (`backupTvVoo`, `backupCountries`, `backups.json`, variantes TvVoo). Cada bloque conserva la sección de `AGENTS.md` de la que salió.

## Cómo trabajar

- **Sin respaldos directos (2026-10-22, decisión del usuario)**: solo se usan respaldos TvVoo (`backupTvVoo`, `backupCountries`). No volver a crear `backupm3u` ni `preferredM3u` salvo pedido explícito; las señales directas extra van como canales independientes de Lista 2 (con guía en `epg-l2-map.json`). `tests/test_channel_quality_backups.py` lo verifica.
- **Respaldos TvVoo de otros países** (2026-10-06): una fila TvVoo con `backupCountries` (lista de countryKey, hasta 6) suma en `tvvoo-variantes.json` el mismo canal de esos países después de sus hermanas. Solo por pedido explícito (hoy Eurosport 1 y 2); la regla general sigue siendo no cruzar países.
- **Versiones hermanas TvVoo** (`tvvoo_variants.py` → `data/tvvoo-variantes.json`, en el workflow de Highfly): por cada canal TvVoo elegido, las otras entradas del mismo canal y país (HD, FHD, UHD, 4K, SD, HD+, HEVC, H265, (BACKUP n)). La app las prueba si la elegida no entrega video. SPORT y SPORTS no se igualan (en DE/IT «SKY SPORT» es la señal local y «SKY SPORTS» la inglesa); (MATCH TIME), [LIVE DURING EVENTS ONLY], (LOCAL) y RAW no son hermanas; nunca se cruzan países. Una hermana que falta en el catálogo se conserva 3 corridas (TvVoo omite entradas de una consulta a otra). Varias versiones elegidas comparten la ficha del catálogo (guía y logo; nombre/logo personalizado de la primera) y una versión sin ficha usa la de su hermana.
- Vigencia de variantes TvVoo: `generatedAt` se renueva cada 24 h tras consultar con éxito
  los catálogos aunque no cambien los alias (la app descarta el archivo a los 7 días).
  No renovar por fecha solamente si hay errores del proveedor; conservar los respaldos.
- Excepción BT/TNT UK: solo nombres completos verificados por fotograma en
  `TVVOO_UK_EQUIVALENCIAS.md`. BT ESPN corresponde a TNT 4; TNT SPORTS ESPN es ESPN US.
  BT 3 HD queda excluido por contenido distinto; no extender la excepción por sufijos.
  Las exclusiones se aplican también al conservar variantes publicadas antes.

## Publicación automática

- **Señal preferida** (2026-10-04): una fila M3U puede llevar `preferredM3u` (tvg-id de otra fila M3U activa de la misma señal; campo «Señal preferida» en el editor). La app 0.5.65+ abre esa señal primero, usa la propia de respaldo y no muestra la otra fila sola. Solo es del layout; el runner no lo usa.
- **Respaldo TvVoo** (2026-10-04): una fila M3U puede llevar `backupTvVoo` (catalogKey de la misma señal en TvVoo; campo «Respaldo TvVoo» en el editor). Es solo del layout: la app 0.5.64+ abre el directo y pasa a TvVoo si falla. El runner no lo usa.
- Respaldos de un canal M3U en el layout: `backupTvVoo` (catalogKey TvVoo), `preferredM3u` (otra fila M3U que la app abre primero) y `backupm3u` (hasta 16 identidades estables, ordenadas). Admite filas M3U HTTP(S) (las referencias Nauta se retiraron el 2026-10-29, ver «Nauta y M6Foot retirados» en `AGENTS.md`); solo establecer el vínculo con petición editorial explícita. No guardar URLs de proveedor, tokens ni HLS firmados. El runner publica las filas igualmente. **VibeM3U 0.6.23+ (`MAX_DIRECT_BACKUPS = 16`) ya usa hasta 16**; el APK v0.6.23 está publicado.

## Reglas funcionales vigentes

- **Respaldo TvVoo (`backupTvVoo`)**: válido en filas M3U y en filas Highfly (2026-10-17), nunca en filas TvVoo. Formato `paisclave|vavoo_…%7Cgroup%3Axx`; para Sky UK solo `unitedkingdom`/`group:uk` con nombre exacto. Un cambio hecho desde el chat se sella con `approval.source = "chat"` (ver `tests/catalog_approval.py`).
- **Formato de `backups.json` (2026-10-24)**: clave = tvg-id del principal en Lista 1; `fields` explica cada campo. Cada copia lleva `tvg_id`, `display_name`, `url`, `group` (los que lee la app), `source_name`, `from_list` y `from_number` (de dónde venía). `number` es informativo: lo pone al día el workflow «Actualizar números de respaldos» (`backup-numbers.yml`, `scripts/refresh_backup_numbers.py`), que corre al final, cuando terminan los workflows del catálogo; el emparejamiento es siempre por tvg-id. `tests/test_backups_json.py` exige principal activo en Lista 1 y copias fuera de las listas.
- **Respaldos de Lista 2 en `backups.json` (2026-10-24)**: `backups.json` (raíz) guarda por canal de Lista 1 sus copias de Lista 2 con la misma familia y la misma guía exacta (`source_id` igual), confirmadas con captura de ambos lados. Esas copias pasan a papelera (`state=deleted`) y salen de `2.m3u`. No es respaldo activo en la app: la app todavía no lee el archivo. Una copia nueva solo entra con captura y guía exacta; si la guía difiere, no es clon.
- **Respaldos por detector de clones (2026-10-28)**: una copia de Lista 2 pasa a respaldo de un canal de Lista 1 solo si abre al primer intento, graba 60 s seguidos, tiene la misma resolución y fps (comparar `r_frame_rate` y además contar cuadros reales: `avg_frame_rate` de HLS da valores falsos como 23,08 o 56) y su audio correlaciona ≥ 0,6 con la de Lista 1 grabada en paralelo. No lanzar varias familias contra el mismo servidor a la vez: 181.78.12.119 dejó de aceptar conexiones. Si la referencia de Lista 1 no graba 60 s, la familia queda sin comparar.
