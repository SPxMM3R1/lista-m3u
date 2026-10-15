# Handoff: auditoría visual de EPG de pruebas de Lista 1

Documento de continuidad para reanudar la auditoría en otra sesión. Es un corte local, no una publicación.

## Objetivo y límites

- Revisar visualmente, con la app VibeM3U ya instalada en el emulador, las 247 señales directas que pasaron de prueba a definitivas en Lista 1 y asignarles una guía solo cuando la emisión visible coincida con una entrada de XMLTV curada que ofrezca al menos 12 horas futuras continuas.
- Usar hora y programación del emulador; normalizar los horarios XMLTV a UTC. No asignar por nombre, logo, IP, categoría o similitud genérica del canal. Si el fotograma no identifica suficientemente el programa o la fuente XMLTV no permite distinguir candidatas, dejar el canal pendiente y explicar por qué.
- Una guía equivalente no demuestra el país físico de la señal ni estabilidad futura del stream. No inventar títulos ni continuidad `Live`.
- Al terminar la revisión, comparar las guías completas y normalizadas para encontrar pares con programación exactamente idéntica y reportarlos como posibles respaldos 1:1. No crear `backupm3u`, fusionar canales ni cambiar sus posiciones sin otra autorización explícita.
- Trabajar únicamente en Lista M3U. No modificar el repositorio VibeM3U, la APK, el resolutor ni la app.

## Punto de reanudación

- Repositorio aislado: `work/lista-remove-positions-isolated` (solo Lista M3U; no tocar VibeM3U).
- Rama: `remove-channel-positions-20261013`; commit publicado `13f003e1c85f0303f2c7d4b5734d83439d4a2828` en `main`.
- Total del contrato: 247 canales; 93 tienen una fuente asignada y 154 siguen pendientes. De los 31 casos documentados en este tramo, sus valores `source/source_id` ya estaban semánticamente en `epg-overrides.json` del `main` anterior (`8a4ec62`); el commit `13f003e` publica el informe/contrato/evidencia, no 31 valores nuevos del manifiesto.
- **Quedan 42 canales por inspeccionar visualmente: #447–#488.** Este número no es igual a los 154 pendientes: varios pendientes ya se vieron, pero no hubo evidencia bastante para elegir una guía.
- El último canal revisado es #446. El siguiente es:

| Posición | Canal | ID | Estado al corte |
| --- | --- | --- | --- |
| 447 | Galavision [IP 138.59.177.78] | `PublicDirect.d13b3c8e60056f9124a6e2dc` | Pendiente; `regional_feed_not_identified`, 0 candidatas en el contrato |
| 448 | DISCOVERY CHANNEL-IXP [IP 138.59.177.78] | `PublicDirect.76f85d8e18ca914171dde970` | Pendiente; región/feed no identificados |
| 449 | DISCOVERY KIDS-IXP [IP 138.59.177.78] | `PublicDirect.e687f4926b0240629f249807` | Pendiente; región/feed no identificados |
| 450 | DISCOVERY WORLD-IXP [IP 138.59.177.78] | `PublicDirect.e7eacb4779e7c1b75e062879` | Ya asignado localmente a `cl / Canal.Discovery.World.Latinoamérica.cl`; no volver a contarlo como pendiente de inspección |

## Publicación y estado del runner (2026-10-15)

- El commit `13f003e1c85f0303f2c7d4b5734d83439d4a2828` está en GitHub `main`; `git ls-remote` confirmó el mismo SHA. No se cambió VibeM3U.
- El push creó Actions `38664592864` (`Publicar cambios dirigidos`), que pasó sus pruebas offline. El plan informó `full_run_required=true` por los archivos de documentación/contrato y dejó el cambio «diferido a la próxima ventana completa»; no hubo artefactos dirigidos nuevos.
- El `epg.xml` de ese `main` tiene nodos `<channel>` para los 31 IDs `PublicDirect` de la tanda auditada, pero **cero elementos `<programme>`** para ellos al corte 2026-10-15 01:17 UTC. Están en `1.m3u` y `channel-catalog.m3u`; no contarlos como programación cubierta.
- Se intentó el refresh dirigido solo para esos 31 IDs con Actions `38664866636`. Las pruebas offline pasaron; falló `Aplicar cambio dirigido manual` tras 2m07s, después de informar el alcance global de Lista 1. El log termina en `Process completed with exit code 1`, sin traceback ni causa explícita; no se publicó ningún XML nuevo. La causa sigue sin confirmar.
- Código observado: `refresh_epg()` vuelve a fijar su alcance a toda Lista 1 más selección gestionada aun cuando el llamador entregue canales seleccionados; por eso esa ruta puede recolectar más fuentes que las 31 solicitadas y luego `apply_epg()` solo fusiona los IDs objetivo. Esto es contexto para investigar, no causa confirmada del fallo.

## Última tanda documentada

- **#444 Animal Planet-IXP**: asignado localmente a `cl / Canal.Animal.Planet.(Chile).cl`, por coincidencia de horario *El acuario / El trato de la foca*, cobertura 12,75 h. El vídeo estaba degradado; no inferir país físico ni estabilidad. Evidencia principal: captura `389-channel444-later.png`.
- **#445 Baby TV**: sigue pendiente. Capturas 390–394: hubo segmentos negros/validación y reapertura HLS; durante una captura apareció animación real de BabyTV, pero no un título de programa identificable. Razón: no se pudo distinguir la entrada XMLTV exacta.
- **#446 Cinemax-IXP**: asignado localmente a `pa1 / Canal.Cinemax.(Panamá).pa`, cobertura 14,37 h. Es una inferencia claramente etiquetada: escena de comida final compatible con *Master Z: El legado de Ip Man* y bumper visible «A continuación: Ip Man 4»; no se vio rótulo directo del título actual. Evidencia: `395-channel446-start.png`, `396-channel446-retry.png`, `397-channel446-later.png`. Las guías de Chile, Colombia, Panamá, Guatemala y México coincidían en secuencia; PA1 se eligió porque la transición inminente coincidía mejor. Sin afirmación sobre región física o estabilidad.

El informe histórico de todas las tandas y decisiones está en `OFICIALIZACION_PRUEBAS_20261013.md`; el estado estructurado, la evidencia por canal y los contadores están en `contracts/trial-officialization-20261013.json`; los mapas locales están en `epg-overrides.json`.

## Estado de archivos locales

Cambios existentes que deben preservarse:

- `AGENTS.md`
- `ESTADO.md`
- `OFICIALIZACION_PRUEBAS_20261013.md`
- `contracts/trial-officialization-20261013.json`
- `epg-overrides.json`
- `tests/test_trial_officialization.py`
- `outputs/` (capturas y datos de evidencia)

**Estado actual del handoff:** informe, contrato y este documento están publicados en `13f003e`. Las capturas PNG y el material de evidencia de `outputs/` permanecen locales y sin seguimiento Git para no inflar el repositorio; preservarlos en esta máquina. El árbol puede mostrar esos PNG como untracked. No resetear ni borrarlos. Al reanudar, verificar primero el `main` actual, el resultado de Actions `38664866636` y la disponibilidad del emulador.

## Validación al preparar este handoff

Desde `work/lista-remove-positions-isolated` se ejecutó:

```powershell
python -m unittest discover -s tests -p test_trial_officialization.py -q
git diff --check
```

Resultado del corte anterior: **11 tests OK** y `git diff --check` sin errores. Para el commit publicado se volvió a ejecutar la suite Python completa: **363 tests, 19 skips previstos, OK**, y `node --test tests/editor-core.test.mjs`: **42/42 OK**. Las pruebas offline de Actions del push también pasaron. La ejecución EPG manual fallida no alteró el XML publicado.

## Emulador y cómo reanudar

- ADB actual: `C:\Users\SP4MM3R\AppData\Local\Android\Sdk\platform-tools\adb.exe`.
- `adb devices -l` no mostró dispositivos en el último chequeo; por ello no se pudo capturar #447.
- Había un proceso QEMU de `VibeTV` iniciado desde otra sesión de shell y no visible para ADB. **No terminarlo ni abrir otra instancia encima.** Al retomar, comprobar primero `adb devices -l`; si sigue vacío, resolver quién está usando el emulador o esperar a que quede disponible antes de continuar.
- El último prefijo de captura válido es 397. El intento #398 generó un PNG vacío de 0 bytes y se borró; el siguiente prefijo previsto es **399** (comprueba antes que nadie haya creado uno en el intervalo).
- Capturas guardadas en `outputs/epg-audit-20261014-followup/`. Antes de analizar cualquier PNG, comprobar que su tamaño sea mayor que cero. El avance de canal D-pad utilizado en esta sesión fue `adb shell input keyevent 167` (abajo); `166` es arriba.
- Las 193 capturas PNG (aprox. 177 MB) se quedan locales y fuera del commit para no inflarlo. El commit sí incluirá este handoff; las observaciones resumidas y las referencias de captura permanecen en el informe de auditoría.
- Al reanudar, no recompilar ni reinstalar la app. Si el emulador ya está en #446, avanzar una posición al #447, verificar el OSD, dejar que aparezca vídeo real y conservar captura(s) con una hora de referencia. No contar placas de error, negro, loading, solo OSD o publicidad sin título como identificación de programa.

## Al completar la auditoría

1. Mantener alineados `channels[]`, `epg-overrides.json`, conteos, evidencia narrativa, tests, `AGENTS.md` y `ESTADO.md` en cada cambio.
2. Dejar los casos no identificables como `pending`; no relajar la regla de evidencia exacta ni el mínimo de 12 horas.
3. Ejecutar las pruebas específicas y las validaciones de catálogo/runner/EPG aplicables. Revisar `git diff` y estado remoto antes de cualquier publicación.
4. Comparar la guía completa normalizada, no solo el programa actual, para proponer pares exactamente iguales. Entregar la lista sin crear respaldos automáticamente.
5. La publicación parcial `13f003e` fue solicitada por el usuario y no significa que la auditoría esté terminada. Para cambios siguientes, alinear contrato, manifiesto, informe, `AGENTS.md`, `ESTADO.md` y tests; ejecutar las validaciones, revisar diff/estado remoto y, si se crea commit, publicarlo en el mismo flujo y comprobar SHA y artefactos. No marcar como cubierta una guía hasta confirmar `<programme>` real y al menos 12 h futuras continuas.
