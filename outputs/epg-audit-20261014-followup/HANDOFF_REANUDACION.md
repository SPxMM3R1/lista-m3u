# Handoff: auditoría visual de EPG de pruebas de Lista 1

Documento de continuidad para reanudar la auditoría en otra sesión. Es un corte local, no una publicación.

## Objetivo y límites

- Revisar visualmente, con la app VibeM3U ya instalada en el emulador, las 247 señales directas que pasaron de prueba a definitivas en Lista 1 y asignarles una guía solo cuando la emisión visible coincida con una entrada de XMLTV curada que ofrezca al menos 12 horas futuras continuas.
- Usar hora y programación del emulador; normalizar los horarios XMLTV a UTC. No asignar por nombre, logo, IP, categoría o similitud genérica del canal. Si el fotograma no identifica suficientemente el programa o la fuente XMLTV no permite distinguir candidatas, dejar el canal pendiente y explicar por qué.
- Una guía equivalente no demuestra el país físico de la señal ni estabilidad futura del stream. No inventar títulos ni continuidad `Live`.
- Al terminar la revisión, comparar las guías completas y normalizadas para encontrar pares con programación exactamente idéntica y reportarlos como posibles respaldos 1:1. No crear `backupm3u`, fusionar canales ni cambiar sus posiciones sin otra autorización explícita.
- Trabajar únicamente en Lista M3U. No modificar el repositorio VibeM3U, la APK, el resolutor ni la app.

## Punto de reanudación

- Repositorio aislado: `work/lista-remove-positions-isolated`.
- Rama: `remove-channel-positions-20261013`; `HEAD` observado: `a86ecb6a85a37c68bf92c680f05c03ace6527abb`, igual a `origin/main` en este corte. Los cambios de auditoría están sin commit.
- Total: 247 canales; 93 tienen guía asignada en el contrato (62 ya presentes en GitHub Raw y 31 verificadas localmente, todavía sin publicar); 154 siguen pendientes.
- **Quedan 42 canales por inspeccionar visualmente: #447–#488.** Este número no es igual a los 154 pendientes: varios pendientes ya se vieron, pero no hubo evidencia bastante para elegir una guía.
- El último canal revisado es #446. El siguiente es:

| Posición | Canal | ID | Estado al corte |
| --- | --- | --- | --- |
| 447 | Galavision [IP 138.59.177.78] | `PublicDirect.d13b3c8e60056f9124a6e2dc` | Pendiente; `regional_feed_not_identified`, 0 candidatas en el contrato |
| 448 | DISCOVERY CHANNEL-IXP [IP 138.59.177.78] | `PublicDirect.76f85d8e18ca914171dde970` | Pendiente; región/feed no identificados |
| 449 | DISCOVERY KIDS-IXP [IP 138.59.177.78] | `PublicDirect.e687f4926b0240629f249807` | Pendiente; región/feed no identificados |
| 450 | DISCOVERY WORLD-IXP [IP 138.59.177.78] | `PublicDirect.e7eacb4779e7c1b75e062879` | Ya asignado localmente a `cl / Canal.Discovery.World.Latinoamérica.cl`; no volver a contarlo como pendiente de inspección |

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

**Estado al preparar este handoff:** aún no había commit ni push de esta auditoría. No descartar, resetear ni reescribir los cambios. Las 31 asignaciones nuevas todavía no estaban en GitHub Raw; los 62 mapas preexistentes sí. Después, verificar el commit/Raw más reciente antes de continuar.

## Validación al preparar este handoff

Desde `work/lista-remove-positions-isolated` se ejecutó:

```powershell
python -m unittest discover -s tests -p test_trial_officialization.py -q
git diff --check
```

Resultado: **11 tests OK** y `git diff --check` sin errores. Una primera ejecución accidental desde la carpeta coordinadora falló al importar `nauta_reference`; repetirla desde la raíz correcta del checkout pasó. No fue un fallo del test ni del código.

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
5. No hacer commit/publicación hasta completar la auditoría y sus validaciones; si se crea commit, publicar en el mismo flujo y verificar SHA remoto/artefactos conforme a las instrucciones del repositorio.
