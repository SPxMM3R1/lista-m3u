# Respaldos BT/TNT UK verificados con fotogramas

Comprobación: **2026-10-02, 12:26–12:29 UTC**. Petición del usuario: agregar
respaldos equivalentes, pero comprobarlos con un fotograma real antes de publicar.
No cambia selección, identidad pública, número, logo, EPG ni código de VibeM3U.

## Regla implementada

Solo `unitedkingdom` / `group:uk`, mediante nombres completos exactos. No basta quitar
«HD» o «BACKUP», ni sustituir SPORT por SPORTS en general. El nombre del catálogo y
el nombre decodificado del alias deben coincidir. Las entradas rechazadas no vuelven
por la retención de tres corridas, ni siquiera si falla el catálogo.

| Identidad elegida | Respaldos admitidos | Evidencia visual |
|---|---|---|
| TNT SPORT 1 | BT SPORT 1; BT SPORT 1 (BACKUP) | Marca TNT SPORTS 1 LIVE; snooker Wu Yize / Shaun Murphy |
| TNT SPORT 2 | BT SPORT 2; BT SPORT 2 HD | Marca TNT SPORTS 2 LIVE; WRC, misma emisión de rally |
| TNT SPORTS 3 | TNT SPORTS 3 HD; BT SPORT 3 | Marca TNT SPORTS 3; mismo partido de snooker |
| TNT SPORT 4 | TNT SPORTS 4 HD; BT SPORT ESPN; BT SPORT ESPN HD | TNT SPORTS 4; béisbol Braves (juego / entrevista posterior, desfase entre fuentes) |

### Rechazadas o pendientes

- **TNT SPORTS ESPN**: ESPN estadounidense (fútbol americano), no TNT Sports 4.
- **BT SPORT 3 HD**: marca TNT SPORTS 3, pero rugby Leicester/Saracens mientras
  TNT SPORTS 3 y BT SPORT 3 muestran snooker. Posible señal desfasada; no se presume
  equivalencia solo por el logo. Requiere nueva comprobación antes de admitirla.
- **BT SPORT 1 HD**, **BT SPORT 2 (BACKUP)** y **BT SPORT 3 (BACKUP)**: sin fotograma
  de programación después de dos rondas; no se incorporan como respaldo verificado.
- **TNT SPORT 1** (primaria elegida): entregó una placa `STREAM UNAVAILABLE`, aunque
  el HLS y el segmento decodificaron correctamente. Se conserva la identidad elegida
  por el usuario y se añaden BT 1 comprobados. Esto **no** demuestra recuperación
  automática de esa placa: un reproductor puede considerarla video válido. No se
  implementó detección visual de placas ni se modificó la app en este cambio.
- TNT 1 y TNT 3 emitían el mismo snooker: **no** son la misma identidad ni se cruzan
  respaldos entre sus números.

## Método y límites

Catálogo UK en vivo → resolutor TvVoo (NoFreeze / Clean) → HLS `#EXTM3U` → primera
parte de media accesible → decodificación FFmpeg → inspección manual del fotograma.
Video H.264 y pista AAC detectados; no se hizo escucha de audio ni prueba en la TV.
Decodificar un frame no equivale a verificar contenido: la placa TNT 1 se rechazó
como prueba de programación. No se conservaron URL firmadas, enlaces HLS ni tokens.
La captura confirma la señal en ese momento, **no estabilidad futura**.

Capturas originales y `results.json` están en el chat coordinador, dentro de
`outputs/tvvoo-frames-20261002/` y `outputs/tvvoo-frames-20261002-retry/`.
La lámina `outputs/tvvoo-uk-verificacion.png` contiene seis fotogramas reales, sin
imágenes generadas. `accepted` en los informes significa «frame decodificado»;
la aceptación editorial definitiva es la tabla anterior, no ese campo técnico.

### SHA-256 de las capturas (sin datos de resolución privados)

| Carpeta | Archivo | SHA-256 |
|---|---|---|
| primera | bt-sport-1-backup.png | 0eb7986428022a0ff4493f6be6b026fbf4bdf543dc9b33c1da826eca50513daf |
| primera | bt-sport-2-hd.png | 69f3ca57efb0f1e785e93dfd7190a16dd22f5b63a63dff62735471f5bdae4a2f |
| primera | bt-sport-espn.png | e32d0bfecc22c892c098d94ea906a1d63f7ceb544db5a9542376d4396822c851 |
| primera | tnt-sport-2.png | 6fe04ae2709adcebeae85752955087306885b6ed39bd0dbd7fd69191b5f6d451 |
| primera | tnt-sport-4.png | 7ac44957b56504e43f80f489239fa0bc017e96da377dad8364723ff1bbdd05ee |
| primera | tnt-sports-3-hd.png | bb032b8ae08faef042e82a231ffec2a420bee5fc17af8cb1d29a8298378d7de5 |
| primera | tnt-sports-3.png | 848a3a9d6e291ccdd23917290cc54493af66fd7616b42f57933e2d6f0e9d7f6b |
| primera | tnt-sports-4-hd.png | 850b8a8bca61da42134e6face2eb27413b90dbed117ef8fda0a241a441b71c9b |
| primera | tnt-sports-espn.png | 74bacbfd48b5e9a9d95cf9bdca06c3c9bdaec718b1cd61ab71347b075e9e029f |
| segunda | bt-sport-1.png | caafa33481fd847dbde849baa12e459074a49cbff5b166629f23748aa753490a |
| segunda | bt-sport-2.png | 9572154fe879a5817c4aea84d3f6b92b1f091d44353d210f2114260177f7ca3c |
| segunda | bt-sport-3.png | 3c6b2cd034cb655d714988f0de4cb4cf95613b4950f804e99ec5d910c715c261 |
| segunda | bt-sport-3-hd.png | 923e76288327ff4b58ac883d65a3603ab0cba1ccb07a3dc2b6ea93322a4a19c3 |
| segunda | bt-sport-espn-hd.png | 93145ae02be88555d83b464adf8a6a997a0c4e85eb6a49ceea5598dd7a02cfb0 |
| segunda | tnt-sport-1.png | c3ad27079c65d251f234badd26471cd5f1ae6c70a4d11aa9c0c6e27aa8886a29 |

## Validación y coordinación

Diez regresiones adicionales cubren los cuatro números, exclusiones, país, nombre
del alias, entrada seleccionada ausente, retención y paso por `build_variants`.
Validación ejecutada: **266 tests Python, 34 JS y 3 tests JVM** de
`TvVooVariantFallbackTest` en verde. Además, el parser actual de la app compilado
desde su código (`PublishedTvVooVariants`) aceptó el JSON real con 2/2/2/3 respaldos
para TNT 1/2/3/4, sin las dos fuentes rechazadas. No sustituye una prueba en Android TV.
Esquema JSON 1 sin cambios;
VibeM3U 0.5.52 ya consume estas variantes. No requiere commit ni APK nuevo en la app.
Publicación: commit en `main`, verificar SHA remoto, ejecutar `update-highfly.yml`
y comprobar los alias de los cuatro canales en `data/tvvoo-variantes.json` remoto.
