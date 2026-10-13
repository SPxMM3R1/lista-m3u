# ESTADO.md — Lista M3U: puesta al día para cualquier agente

> Léelo completo antes de trabajar, junto con `AGENTS.md` (cómo trabajar) y `REGLAS.md`
> (reglas vigentes de ambos proyectos). App hermana: `SPxMM3R1/vibem3u` (su `ESTADO.md`
> cubre la app). **Al terminar cualquier cambio, actualiza este archivo en el mismo commit**:
> la sección «Hoy» si cambió el estado y una línea nueva en «Bitácora».

Última actualización: **2026-10-13** (America/Santiago).

## Hoy, en una mirada

- **Baja definitiva de posiciones de Lista 1 (2026-10-13)**: por pedido del usuario se retiraron las posiciones 185–191, 193, 201–204 y 241: 13 canales directos en prueba, sin EPG ni dependientes de respaldo. Se quitaron del layout, `channel-catalog.m3u`, `m3u.m3u` y `1.m3u`; sus IDs quedaron con exclusión permanente en el layout y la presentación para que no vuelvan. Se preservaron todos los números restantes, la selección y la EPG; no hubo cambios en VibeM3U. `targeted_update.py --mode presentation` pasó (Lista 1=136, Lista 2=0, inventario=1900); 347 Python (19 omitidas), 55 JavaScript y bundle estático del editor (473 canales/381 logos). Contrato: `contracts/channel-number-exclusions-20261013.json`. Publicación/runner automático aún por verificar.

- **Guía por canal (2026-10-12, pedido del usuario)**: la EPG deja de depender de un runner de unión. Cada canal tiene su fragmento `epg/canales/<id>.xml` (63 creados desde el `epg.xml` vigente; la unión reproduce exactamente sus 72 canales con alias y 4.650 programas vigentes) y puede tener correcciones por tramo en `epg/manual/<id>.xml`. `update-epg.yml` pasa a un despachador cada 30 min (`epg_dispatch.py`): cada fuente con su ritmo (Red Bull 2 h, resto 6 h), reintentos con espera creciente y solo los canales afectados se reescriben; la unión es sin red y no corre pruebas. Aislamiento por canal en `build_epg` y en la donación de sinopsis; una falla de EPGShare ya no congela la guía de todos en este modo. Highfly ya no se dispara al terminar la EPG (tiene su cron de 30 min). Cambios dirigidos de EPG escriben también los fragmentos; `change_plan` ignora `epg/`. App sin cambios (mismo `epg.xml`). Edición manual desde el editor web publicada según el mockup aprobado («Aplícalo»): inspector › «Ver y corregir guía» muestra lo que verá la TV (automático/manual, en curso), corrige/edita/quita tramos con aviso de lo que se tapa y publica solo `epg/manual/<canal>.xml`; la unión corre al instante por el push. Índice `epg/indice.json`. Probado en navegador con la guía real (TVN, TvVoo Sky Sports Main Event, canal en prueba sin guía) y la corrección resultante ensamblada por Python igual que en el editor. El modo local requiere el auxiliar de VibeM3U con `/api/publish-epg-manual` (commit hermano en SPxMM3R1/vibem3u). 347 Python (1 omitida) y 55 JS.

- **Búsqueda ampliada desde ESPN3 (2026-10-12)**: A petición del usuario se purgaron del inventario canónico 23 canales colombianos no deportivos/no musicales. Quedaron con tombstone permanente en `layout.excludedM3u` y `presentation-overrides.excluded_m3u`, y no están en `channel-catalog.m3u`, `m3u.m3u` ni `1.m3u`. De las otras 97 entradas, 86 ya estaban en papelera y 11 siguen activas en prueba. Se conservan los números/membresía de los demás, los 62 Total Conexión y selección Highfly/TvVoo. Validación local: 347 Python (19 omitidas), 55 JavaScript, runner dirigido correcto (Lista 1=149, Lista 2=0, inventario=1913), bundle 486/381 y auditoría correcta. Commit `4802771` publicado; el runner de canales `38335797763` publicó salida `51a1700`, Pages `38335797811` success y cambios dirigidos `38335797783` success. La EPG no formó parte de la purga, pero el workflow automático `38335907914` terminó success y publicó `ca8605a`; el Raw final tiene cero IDs retirados entre sus 72 canales. No hubo cambios de app ni APK. Informe: `CANALES_DIRECTOS_ADICIONALES_20261012.md`.

- **62 canales «Total Conexión» [IP 181] en prueba (2026-10-12, pedido del usuario en el chat)**: el servidor `181.78.12.119:16123` (de donde salen ESPN 3 Sur = `ch18` y ESPN 5 Sur = `ch19`, vía iptv-org) entrega `ch01`–`ch90`; 64 respondieron y se identificaron por el nombre de servicio del propio MPEG-TS (SDT, proveedor «TOTAL CONEXION», cableoperador colombiano). Los 62 no usados entran al final de Lista 1 como `trial` (números 164–225), tvg-id `<Canal>.co@Direct181`, nombre «<Canal> [IP 181]», grupos existentes (Deportes 5, Música 6, Noticias internacionales 2, Películas 11, Misceláneos 38). Prueba desde Chile: los 64 en vivo; ESPN 6, Cine Premium y Pasiones bajan solo ×1,2–1,3 del tiempo real; El Gourmet y Pasiones traen audio en stream privado; TLC, Caracol, City TV, Teleislas, Telesur e Institucional son MPEG-2. Los «HD» deportivos son 720p. Layout sellado con origen `chat` (nuevo origen admitido en `tests/catalog_approval.py`). Error existente detectado y esquivado sin tocar el runner: `targeted_update.apply_presentation` toma posiciones de líneas del catálogo antes de reordenarlo; con registros nuevos fuera de `orders.channel-catalog.m3u` los índices quedan desfasados. Al agregar registros al catálogo, sumarlos a ese orden y dejar el archivo ya normalizado (idempotente).

- **France 24 English: marcador (EN) eliminado y EPG verificada**: la guía anterior tenía 130 de 301 programas con `(EN)` en campos visibles. El runner lo elimina de título, subtítulo, descripción y categoría solo para `France24.fr@English`; la francesa y otras señales no cambian. Código `5a80c19`; regeneración completa `38293029014` success, salida EPG `d6d5a20`. GitHub Raw verificado: 291 programas de France 24 English, 0 con `(EN)`, SHA-256 `be53165bcb250cf3186a238e3a58bd7eb3cf34e3265bffe3240a9dece87af558`. 332 Python (19 omitidas) y 54 JavaScript pasan.

- **ESPN/MTV, respaldos Nauta y EPG publicados/verificados**: VibeM3U 0.5.93/202 ya está publicada y verificada (código `682b1b5`, tag `v0.5.93`, APK 2.774.715 bytes, SHA-256 `27f694d5f096967f91dede4e7091e5f5dfab894e6ded08659686751c07315d96`; firma compatible). El editor publicó el layout sellado en `77a025b`; la lista se actualizó desde pedidos dirigidos en `f7eb041`. La corrección `5841348` alineó el guardia Python con la lista exacta de cuatro filas Nauta oficiales verificados que ya permitían editor y tests. Runner completo `38281677079` terminó success y publicó salida `eb29cc8`; EPG `38281825821` terminó success y publicó `f44b295`. ESPN 1 Argentina #33 tiene ESPN 1 Sur y Chile como respaldos; ESPN 1 México #34; ESPN 7 #39; Fox Sports 2 HD, antes en la posición 150, pasa a #40 en prueba/sin EPG; ESPN HD es otra identidad y permanece #151 en prueba. MTV Live queda #52, justo antes de MTV Biggest Pop, definitiva con logo y EPG `us2/MTVLIVE.us2`. El XML Raw `f44b295` tiene 5.062 programas en 72 IDs de canal, SHA-256 `7be7b3234896a7148f99b87c2841df512c54a1d92fc82bfbc11b7eb986af6f34`: ESPN 1 Argentina 66, ESPN 1 México 62, ESPN 7 40 y MTV Live 70 programas; ninguno está pendiente. Verificación M3U: Lista 1 98 IDs, Lista 2 0, intersección de IDs EPG/Lista 2 0. Rwnd conserva solo cuatro bloques `Live`, sin descripción/subtítulo/categoría, todos en horas cerradas y de hasta 6 h. Pruebas locales finales: 330 Python (19 omitidas por el sello válido del catálogo) y 54 JavaScript. No se afirma validación de reproducción en TV de los nuevos vínculos.

- **Sello automático de lo que publica el usuario (2026-10-12)**: el editor web y la papelera de la app escriben en `data/channel-editor-layout.json` un campo `approval` (`source` editor/app y SHA-256 del contenido). Con el sello intacto, las 14 pruebas de foto fija del catálogo se saltan solas: mover, renombrar, agregar o borrar desde el editor ya no exige tocar pruebas ni bases. Si alguien cambia el layout por otra vía, el sello no coincide y vuelven a correr (probado: cambio sellado → OK; mismo cambio sin sello → 2 fallas). Paridad JS/Python fijada con el mismo ejemplo en ambas suites. El layout editorial publicado en `77a025b` lleva `approval.source=editor` y SHA-256 `4f41f23fdb306b56389d67f574e8b97103c1f28e7648dc6cff9dc110e5d2c0e2`; las pruebas reconocen el sello actual. 330 Python (19 omitidas por sello/catálogo vivo) y 54 JS en la validación final.

- **Papelera de app y editor juntas; runners desbloqueados (2026-10-12)**: las bajas desde la TV rompieron 6 pruebas que fijaban el catálogo con hashes y listas a mano; como `update-channels` y el `plan` de `update-epg` corrían toda la suite antes de regenerar, quedaron bloqueados desde las 03:10 UTC (la guía no se renovaba y los canales borrados seguían en las listas). Cambios: (1) las 14 pruebas que leen el catálogo publicado llevan `@live_catalog` y los runners de canales/EPG y el despliegue del editor las saltan con `M3U_RUNNER_TESTS=1` (corren completas en `targeted-changes` en cada push de código); (2) las pruebas comparan contra la base aprobada `contracts/editorial-baseline-20261012.json` (commit `9f70fd3`, verifica los digest 0f3350…/ad6addb…/nonNauta) descontando solo filas que el usuario pasó a «deleted» después (`tests/catalog_baseline.py`), así cualquier baja futura, de app o editor, no rompe nada; (3) `app-requests.yml` regenera las listas sin red (`--sync-resolver-contract` + `targeted_update.py --mode presentation`) en el mismo commit y relanza solo el editor web; ya no encola `update-channels`/`update-highfly`, que siguen a su hora; (4) el editor web, al publicar, relee el layout de `main` y conserva las bajas hechas desde la app mientras estaba abierto (`mergeRemoteDeletions`), salvo que esa sesión haya cambiado esa fila. Listas regeneradas: salen 27 canales en papelera (Fox Deportes [IP 23] y 26 Nauta). (5) una corrida de fuentes sueltas (`fuentes=` en `update-epg`) ya no aborta si la guía publicada quedó corta: la usa de respaldo y renueva solo esas fuentes (antes exigía una guía vigente, justo lo que faltaba tras el bloqueo). 325 Python (1 omitida; 19 en modo runner) y 53 JS.

- **RWND con continuidad en horas cerradas — publicado y verificado**: la guía no asigna programación real y solo muestra `Live`. El XML remoto contiene cuatro bloques contiguos, con inicio/fin a `HH:00:00`, de hasta seis horas, cobertura 2026-10-11 22:00 a 2026-10-12 17:00 hora Chile y sin metadatos de programa adicionales. Commit de código `4782c86`; EPG workflow `38192606087` success, salida `7eab81f`; SHA256 remoto de `epg.xml`: `89e4ac8a32c50a1a0a9898f960fbeba7704bc706cdc5f81a5c36e47ea72b15d4`. Último `main` observado `4be6a1c`. Validación local completa: 324 pruebas Python (1 omitida) y 52 JS.

- **Canal 13 oficial como predeterminado**: la fila `0107` permanece en el número 4 y reproduce su señal propia primero. `Canal13.cl@Direct187` pasa a primer respaldo y `T13EnVivo.cl@DPS` queda segundo. La guía oficial, el nombre, logo, número, membresía y app no cambian; un test editorial protege el orden. Validación: 321 Python (1 omitida) y 48 JS.

- **ESPN 7 después del 36 — publicado**: el Nauta antes número 94 está activo en el 37, mostrado como `ESPN 7`, sin `trial`, con logo local y guía en Lista 1; la referencia de reproducción permanece `nautatv_catalog|ESPN 7 HD`. Commit editorial `f22c009`; runner original `38089626317` success y EPG `38089703472` success. El fallo posterior de test en `38090017826` se reparó en `0f41b99`: el digest de presentación no Nauta quita logos de assets solo cuando pertenecen exclusivamente a filas Nauta, preservando rutas compartidas. Validación: 320 pruebas Python (1 omitida) y 48 JS; Pages `38090653457` success. Runner revalidado `38090677815` success; commits generados `f65584c` y `03ef421`. EPG revalidada `38090766510` success, salida `616ba41`: 35 programas CO1, `parrilla real`, no pendiente, hasta el 12-10 22:00 CL; `epg.xml` SHA256 `69003b8417cad6177a516e33641acdac4e1748b7cc8268b256e158803403f716`. El fotograma Nauta decodificado el 10-10 mostró PSG–Arsenal mientras la guía de ese instante indicaba ESPN KnockOut: la guía publicada no demuestra sincronía exacta con esa muestra. Sin cambios en app ni resolutor. VibeM3U `0.5.88` (`e6dcb3a`) sin cambios; `:app:testDebugUnitTest` pasó.

- **Vista completa Nauta del editor local**: la opción «Todos los canales · catálogo completo» reúne todas las categorías TV del manifiesto, deduplica por identidad estable y conserva la categoría real para resolver cada canal. El endpoint «Portada Nauta» solo devuelve 150; las comprobaciones en vivo del 10-10 encontraron entre 528 y 530 nombres únicos, según el momento de consulta. El editor presenta el inventario completo sin el antiguo corte visual de 250, con avance de carga y error explícito si alguna categoría falla. Canales ya agregados, publicados o retirados históricamente se ven deshabilitados; solo una selección explícita de los demás puede agregar filas en prueba. Este cambio afecta la web de Lista M3U y no añade filas editoriales ni cambia la app.

- **Edición editorial integrada del remoto**: mientras se desarrolló la vista completa, el usuario publicó `15b1e83` desde el editor local. El layout de `main` tiene ahora 270 filas, 17 Nauta elegidos explícitamente y 180 tombstones Nauta; al integrar ese commit, la Lista 1 aún tenía 51 canales y 0 Nauta, pendiente de materialización por el runner. Se conservó íntegro `data/channel-editor-layout.json`. Se corrigió una regresión del editor que había reducido `orders.channel-catalog.m3u` de 1.680 IDs a 270: el orden canónico se restauró desde el estado previo y ya no se reconstruye desde el layout reducido.

- **Historial previo — selección múltiple Nauta**: el commit `ca5545d` permitió añadir varios seleccionados por acción. En ese momento el layout tenía 253 filas sin Nauta, Lista 1 tenía 51 y los 180 tombstones de bajas históricas seguían vigentes. Pages `38067781735` terminó success; 319 pruebas Python (1 omitida), 45 JS y bundle 253/380. El estado editorial cambió después con `15b1e83`, descrito arriba.

- **Historial previo — fuente Nauta y respaldo base→HD (publicado y verificado)**: commit `08cf7e1` publicó la consulta Nauta y retiró 55 `backupm3u`; en ese estado anterior había 606 filas (353 Nauta), independientes y en prueba. Runner `37870337325`, editor `37870337366`, dirigida `37870337472` y Highfly `37870337314` success; salida `88bf85ce`. La pestaña Nauta consultaba el auxiliar local, persistía nombre exacto/categoría/ID derivado y el runner materializaba en Lista 1 sin EPG. EPG `37870440382` success, salida `01103ce`, Lista 1 y cero Nauta en XML/pendientes. VibeM3U 0.5.84/193 publicada. Este estado fue sustituido por la retirada general descrita arriba.

- **Historial, no estado actual — respaldos Nauta base→HD**: en el commit editorial `be35025` se publicaron 55 vínculos. Esta configuración fue retirada en el cambio actual; los resultados del runner/EPG de esa versión quedan conservados aquí solo como historial.

- **Bajas Nauta 24/7 y posiciones publicadas/cerradas**: commit `0e6bb56`; runner de canales `37859215025` success, salida `5752379`; editor `37859215094` y dirigido `37859215059` success. Se retiraron permanentemente 75 filas de Lista 1 (70 nombres con «24/7» y posiciones 271, 306, 308, 309, 311 y 321; 321 coincide). Quedan 353 Nauta activos/606 filas editoriales, con números y órdenes restantes preservados y exclusiones persistentes en runner/editor. Raw fijado al resultado final `fabc464` coincide con siete blobs; todos los IDs objetivo ausentes tras el runner. EPG automática `37859356670` success, salida `fabc464`; alcance 60 IDs/0 Nauta y XML/pending sin Nauta. Selección y alcance EPG no se cambiaron. Parser real de VibeM3U 0.5.81: 353 Nauta/414 visibles/0 incompatibles. 309 Python (1 omitida), 41 JS, guardia válida y editor 606/380. Sin cambio de VibeM3U/APK.

- **Reincorporación Nauta publicada y verificada**: editorial `cd4d66e`, estado generado `bc448ce`; canales `37852531718`, editor `37852531767` y dirigido `37852531793` success. Conservados 34 recuperados/428 Nauta activos/105 bajas excluidas y las 647 filas previas. Raw fijado al SHA coincide con siete blobs y el layout publicado en Pages es idéntico. Nueve pruebas Nauta y contrato correctos después del runner; lector/proyección real de app: 428 Nauta/489 visibles/0 descartes. EPG base Lista 1 46, total con gestionados 60, 0 Nauta; corrida automática `37852688070` disparada con alcance habitual, no requerida para los nuevos en prueba. Sin cambio/app/APK. Este cierre cumple el pendiente de la entrada siguiente; la documentación se publica en el mismo flujo. Reincorporación editorial no demuestra operatividad de las 34 señales.

- **Reincorporación editorial Nauta autorizada**: el usuario pide «Agrega todos» tras listar 32 deportivos y dos eventos (108/295); vuelven esas 34 entradas con números/órdenes originales, activas en Lista 1 y en prueba/sin EPG. Total 428 Nauta/681 filas editoriales; otras 105 bajas y las 647 filas previas intactas. Registro nuevo `contracts/nauta-restoration-20261008-sports.json` e informe `NAUTA_CANALES_REINCORPORADOS_20261008.md`; históricos no reescritos. Solo 295/306/308/320 dieron vídeo en alguna ronda de la reprueba 21:56:56–22:02:04 UTC; 306 falló apertura adicional, 295 intermitente. Reincorporación no implica reparación/disponibilidad ni identificación deportiva de Evento 2. App/resolver sin cambios, contraparte `e3d2ee2` / v0.5.81, sin APK nueva. Validado: 306 Python (una copia omitida por ruta y verificada aparte con SHA256 idéntico), 41 JS, bundle 681 filas/380 logos, referencias 428 válidas, diff y preservación de 647 filas/selección correctos. Proyección real de app: 428 Nauta/489 visibles/0 descartes. EPG completa 60 (base Lista 1 + gestionados), 0 Nauta. Pendiente de cierre: push y comprobación de runner/Raw/proyección posterior.

- **Limpieza Nauta publicada y cerrada**: cambio `4518462`; canales `37845505221`, editor `37845505238` y publicación dirigida `37845505311` verdes. Resultado `472b656` conserva exactamente 394 Nauta y no reintroduce ninguna de las 139 bajas; bloques de canal, números y layout intactos (solo comentarios de agrupación normalizados por el runner). Raw fijado al SHA verificado contra siete blobs y seis pruebas Nauta repetidas; contrato y proyección real vuelven a dar 394 Nauta/455 visibles/0 descartes. Lista completa en `NAUTA_CANALES_ELIMINADOS_20261008.md`. Sin APK nueva ni modificación de VibeM3U; contraparte sigue v0.5.81. EPG automática `37845673257` disparada sin ampliar alcance, no requerida para Nauta en prueba. Esta entrada cierra el pendiente de la siguiente.

- **Limpieza completa Nauta preparada y validada**: 533 revisados con resolver real de APK v0.5.81 y decodificación FFmpeg; tres rondas independientes para fallos, controles ESPN 1 Chile/DSports 2 HD correctos en las tres. 394 conservados, 139 retirados permanentemente (39 HTTP 404, 4 nombres ausentes y 96 placas de actualización, no señal válida). Fox Deportes (304) y HBO Xtreme (361) se recuperaron y se conservaron. Informe completo `NAUTA_CANALES_ELIMINADOS_20261008.md`, evidencia segura `contracts/nauta-validation-20261008.json`; snapshot inicial intacto. Layout/inventario/listas/presentación sincronizados, bajas excluidas contra reaparición, sin ocultar ni renumerar supervivientes. 253 filas anteriores/selección/presentación no Nauta intactas; EPG conserva alcance 46/0 Nauta. 303 Python (copia del contrato omitida por ruta, hashes iguales aparte), 41 JS, contrato 394 Nauta y bundle correctos. Proyección real con catálogo integrado de app: 394 Nauta/455 visibles/0 descartes. Sin cambios de app/APK (contraparte `e3d2ee2` / v0.5.81). Pendiente en esta entrada: push main y comprobar runner/estado remoto. Disponibilidad puntual desde PC, no garantía futura ni prueba de TV física.

- **Nauta publicado y comprobado después del runner**: importación `b33cebf`, runner `37718537821` success, estado generado `a5081dd`; Raw fijado al SHA coincide con listas/layout/presentación. Conservadas las 533 filas en prueba y números 87–619; proyección real de app: 594 visibles, 0 descartes. Pruebas Nauta repetidas después del runner: cuatro correctas; EPG 46/0 Nauta. Editor web `37718537777` success. APK 0.5.81/190 y firma/checksum ya verificados antes del catálogo. EPG automática `37718727029` en curso al comprobar, sin ampliar alcance; no se necesita para Nauta. Cierra los pendientes de las entradas siguientes; disponibilidad de todas las señales y TV física no demostradas.

- **APK Nauta publicada y verificada antes de este catálogo**: VibeM3U `e3d2ee2`, versión/tag `0ef0331` / `v0.5.81` (190); CI `37717793042` y Release `37718148346` success. Release pública no draft/prerelease, APK 2.720.775 bytes, SHA256 `dfb24e1a397aa4b029d41ba082414787beee0076ded5869e7c2c00258c1f2ca5`, descarga/firma compatible verificadas. Nuevas referencias requieren actualizar la TV a 0.5.81+. Publicar este catálogo ahora; comprobar estado remoto y conservación de las filas tras el runner. Sin prueba física local: ADB sin dispositivo y no hay ejecutable emulator en el SDK C: verificado.

- **Validación Nauta**: 301 Python (una prueba de copia omitida por ubicación del clon; hashes idénticos comprobados aparte), 41 JS y bundle temporal correctos. Parser real VibeM3U + catálogo integrado acepta 533 referencias, 0 incompatibles. Alcance EPG conservado en 46 canales (ningún Nauta). Java real + FFmpeg dieron contenido ESPN 1 Chile 360p24 y DSports 2 HD 720p60; TV Pública/South Park devolvieron placa de actualización, no señal válida. El resolver excluye temporalmente ese origen. Catálogo completo no significa todas las señales operativas; sin estabilidad ni TV física demostradas. Contraparte funcional VibeM3U `e3d2ee2`; entregar APK 0.5.81/190 antes de estas filas.

- **Nauta preparado 2026-10-07**: snapshot de 18 categorías/páginas, 536 recursos y 533 nombres exactos distintos (el proveedor varía entre consultas). 533 filas nuevas al final de Lista 1, en prueba/sin EPG, sin renumerar ni cambiar las filas anteriores o selección Highfly/TvVoo. URI internas públicas, sin enlaces/IDs opacos/credenciales. Snapshot `contracts/nauta-trial-channels-20261007.json`, contrato `nauta_reference.py` y tests; APK 0.5.81 debe estar publicada antes del catálogo. No se reintroduce CNCVerse. Publicación y prueba física pendientes en esta entrada.

- **France 24 inglés publicado y verificado**: cambio `1073380`, runner `37539066258` success, estado `c76d52f`; no modificó catálogo/streams ni membresía. Raw/blob iguales para ambas listas/layout/presentación, proyección app antes y después: 18 Español → 19 English, mismos 77 visibles y T13 respaldado. Editor web `37539066224` success. EPG automática `37539349779` disparada con el alcance habitual; inglés conserva prueba/sin EPG. Sin APK. Cierra el pendiente de la entrada siguiente.
- **France 24 inglés reubicado**: la fila existente activa/en prueba `France24.fr@English` pasa del 62 al 19, inmediatamente después de Español (18); Al Jazeera = 20, BBC = 21. `assignChannelPosition` desplaza +1 todos los demás activos con número anterior >=19, también Highfly/TvVoo y respaldo T13 (histórico 217, ahora 218); vínculos por identidad intactos. No duplica, no oficializa ni agrega EPG; estado de prueba, stream y logo conservados. Layout/presentación/Lista 1/alias/inventario sincronizados y selección idéntica. Históricos intactos, registro separado de inserción. 312 Python/41 JS, bundle/contrato y proyección real app 0.5.73 `94dd35b`: mismos 77 visibles, proveedor y respaldo correctos. Sin APK nueva. Pendiente en este punto: publicar y comprobar salida remota/runner.
- **Rwnd ya publicado y verificado**: código `45c217f`; workflow completo `37537954410` success; XML `43d110a`, generación 22:04:37 UTC. Raw fijado al SHA coincide con blob Git: solo 3 bloques Live, 0 descripciones/subtítulos/otros metadatos, 17,98 h futuras al verificar 22:05:31 UTC. El lector XMLTV real de app 0.5.73 muestra Live con sinopsis vacía. Sin APK nueva ni prueba física; caché de TV no observado, revalidación mínima de EpgRepository 5 minutos. Esta entrada cierra el pendiente de la siguiente; no se reparó Meganoticias/007 aquí.
- **Rwnd, continuidad sin EPG**: eliminada asociación errónea `us2 / Rewind.TV.us2`. El runner ya no copia programación fresca ni publicada para `RewindTV.cl@SD`; genera solo bloques `Live` sin sinopsis, subtítulos, categorías ni otros metadatos de programa. La guía reutilizada también se limpia y se excluyen donantes/bloqueos manuales. Cinco regresiones nuevas; 309 Python/41 JS. Sin modificar stream, logo, número, selección ni app; contraparte VibeM3U 0.5.73 `94dd35b`, sin APK ni commit hermano nuevo. Pendiente en este punto: publicar main, regenerar EPG y verificar XML remoto/lector real.
- **ESPN 2 Sur publicada y verificada**: código `58d95b4`; regeneración completa `37535307432` correcta; XML `a2b1a02`. GitHub Raw fijado al SHA y lector XMLTV real de app 0.5.73: 76 programas, más de 55 h futuras, a las 18:20 Chile `ESPN Compact` con descripción final masculina Premier Pádel Rotterdam 17:45–18:45. UTC 20:45–21:45 sin desplazamiento; identidad estable preservada. No APK nueva ni reproducción propia en TV afirmada. Esta verificación cierra el pendiente de publicación de la entrada siguiente.
- **ESPN 2 Sur (32), corrección de guía**: ambos alias TvVoo ES/AR usan `uy1 / [ESP2LS].ESPN.2.uy`. Su descripción de ESPN Compact anuncia final masculina Premier Pádel Rotterdam 17:45–18:45 Chile, consistente con foto del usuario de Tapia/Coello–Stupaczuk/Sanz a las 18:20 y torneo/primer set corroborados por FIP. Se contrastaron 51 registros ESPN en seis guías regionales: Chile anuncia fútbol; ESPN 2 HD UY anuncia tenis. No es prueba de país exclusivo ni cambio horario; sin fotograma nuevo del proveedor en este entorno. Retirado respaldo Bolivia no confirmado, última EPG publicada permanece como fallback. Tres regresiones; 304 Python/41 JS. Solo runner/test/docs; canal, identidad, selección, alias, números, resolutores y app intactos; contraparte VibeM3U 0.5.73 `94dd35b`. Pendiente en este punto: publicar código y regeneración EPG, verificar XML remoto y lector real.
- **EPG ESPN 5 ya publicada y comprobada**: código `00897ab`, XML `8196fd0`, ejecución completa `37403016586` correcta. 67 programas y más de 72 h futuras; actual Rumanía–Suecia 23–01 Chile, no boxeo. Lector EPG real de app 0.5.73 probado con ese XML: conserva identidad y horario absoluto, muestra UEFA Nations League. Intento parcial anterior `37402866106` conservó la EPG porque había huecos/cobertura insuficiente en la base; se recuperó con regeneración completa, sin tocar lógica de renovación ni inventar programación.
- **ESPN 5 (35), EPG corregida**: `WinPlusFutbol.co@Direct181` pasa a `uy1 / ESPN.5.HD.uy`. La anterior `[ESPN5SD].ESPN.5.uy` publicaba boxeo/títulos portugueses y no coincidía con la secuencia observada Francia–Bélgica → Rumanía–Suecia. Guías UY1/CO1 coinciden 21–23 / 23–01 Chile; fotograma ESPN 5 en español con previa de Rumanía. No cambio de stream, identidad, logo, número ni región declarada; no offset horario. Dos tests de mapeo y reemplazo de guía anterior, 301 Python/41 JS. Publicar código y regenerar `epgshare` en GitHub, comprobar salida; app 0.5.73 `94dd35b` no requiere APK nuevo.
- **APK compatible verificado antes del catálogo**: VibeM3U `94dd35b` / tag `v0.5.73`, Android CI `37399927443` y Release `37400308175` verdes; firma compatible comprobada por workflow, Release pública no draft/prerelease, APK 2.717.639 bytes, SHA-256 `10cb0b63f150c1c71cb8fff465d949cdb70bdb143a78d647c78f3d8e265c6f4c`. Instalar 0.5.73 para usar el 217 como respaldo; no se afirma reproducción en TV física. La publicación de catálogo usa commit separado y se verifica después del runner.
- **Qué es**: catálogo público de canales, guía EPG y logos que consume la app VibeM3U
  (Android TV), más el runner que los mantiene y el editor web (`site/`).
- **Publicación**: todo corre en GitHub Actions; ningún proceso usa el PC del usuario.
  - Variantes TvVoo: la fecha se renueva cada 24 h tras una consulta correcta aunque
    los alias no cambien, para que la app no descarte respaldos vigentes a los 7 días.
    BT/TNT UK tienen equivalencias explícitas verificadas por imagen; BT ESPN es TNT 4,
    no TNT 1. Rechazados TNT SPORTS ESPN y BT 3 HD (ver `TVVOO_UK_EQUIVALENCIAS.md`).
  - Canales: `update-channels.yml`, un job por proveedor (`direct`, `tvn`, `meganoticias`,
    `highfly`, `tvvoo`) y un job final que arma listas y publica.
  - EPG: `update-epg.yml`, un job por fuente (17 partes, `--list-epg-parts`) y un job final.
  - Highfly: `update-highfly.yml` cada 30 min publica `data/highfly-live.json` (enlace directo
    vigente, sin token). La app lo abre al tiro y usa su resolutor si falla.
- **EPG**: 47 canales. Cada canal mezcla sus fuentes por prioridad (`epg_source_chain`): la de
  más arriba manda donde tiene programas y las demás solo rellenan huecos. Horizonte típico
  30–190 h.
- **Tests**: 324 Python (`python -m unittest discover -s tests -p "test_*.py"`; 1 omitida) y 52 JS
  (`node --test tests/app-requests.test.mjs tests/editor-core.test.mjs tests/layout-contract.test.mjs`).

## Pendientes y decisiones abiertas

- **EPG pendiente (límite de la fuente, no del runner)**:
  - TVN3 (`1437`): solo existe en Zapping, que desde GitHub entrega ~3 h. Buscado el
    2026-09-30 sin éxito: la página de TVN3 no expone su programación, `estaticos.tvn.cl/epg`
    no tiene ruta para TVN3 y TecnoCentro solo lista «TVN» y «TVN HD».
  - La Red (`0102`) puede figurar como `hueco`: tiene más de 160 h, pero no transmite de
    madrugada. No es falta de guía.
  - MTV Biggest Pop, Flow Latino y Spankin' New: Pluto publica ~13 h y se exigen 24 h.
- **Zapping bloquea a GitHub (403)**: la guía completa (hoy + mañana) no responde ni con
  `X-Forwarded-For` chileno ni por su frontal `cl-apig`. El runner usa el endpoint
  `nowplaying` (anterior, actual y siguientes: ~5 programas). Probado el 2026-09-29.
- **CHV**: su página oficial no publica los noticieros. La oficial solo rellena detrás de
  Zapping y TecnoCentro (`EPG_INCOMPLETE_OFFICIAL_IDS`). Más allá de ~30 h todavía puede
  aparecer un programa estirado sobre el noticiero.
- **Logos**: pendiente de decidir si la coincidencia por nombre exige país (`REGLAS.md` §5).
- Carpeta `experiments/direct_links_lab/` **del usuario, sin commitear**: no tocarla, no
  incluirla en commits y no usar `git stash -u` (se la llevó una vez el 2026-09-29).

## Cómo trabaja el usuario (válido para ambos proyectos)

- Responder siempre en **español de Chile, tuteando**. Nunca en inglés.
- **Diseño**: primero mockup (imagen), y solo con «aplícalo» se toca código, se compila o se
  publica. «Sí» a una pregunta no es «aplícalo».
- **No usar el PC del usuario para automatizar** (nada de tareas programadas ni servicios
  locales): todo en GitHub Actions. Para diagnosticar desde fuera de Chile, usar una rama
  temporal con un workflow `on: push` y borrarla después.
- Antes de afirmar que un canal o fuente «no funciona», comprobarlo más de una vez y decir
  «en este momento».
- Nunca force-push; acciones destructivas solo con confirmación; nunca publicar tokens,
  credenciales ni URL firmadas.
- Versiones de la app: solo sube el último número salvo que el usuario decida otra cosa.

## Entorno de trabajo

- Windows, repos en `D:\Users\SP4MM3R\Documents\Codex\` (`Lista M3U` y `VibeM3U`). Git Bash y
  PowerShell; `gh` CLI autenticado.
- **2026-09-30: el disco D: quedó lleno (0 GB libres)** y git no podía escribir. Si un commit
  falla por espacio, avisar al usuario; no borrar nada suyo para liberar espacio.
- **2026-10-06 UTC**: D: vuelve a estar sin espacio; fetch falló sin poder escribir objetos.
  Baja por números trabajada y validada en clon de Lista M3U en C:
  `C:/Users/SP4MM3R/Documents/Codex/2026-09-20/este-chat-coordina-los-proyectos-lista/work/lista-m3u-bajas-numeros-20261006`.
  El checkout original de D: no está sincronizado con esta publicación; conserva el experimento
  no seguido `experiments/direct_links_lab/`. No tocarlo ni asumir que una copia antigua es autoridad.
- Mockups: HTML renderizado con Edge headless. Lo confiable es PowerShell con
  `Start-Process msedge.exe --headless=new --screenshot=... -Wait` y un `--user-data-dir`
  nuevo por captura.

## Bitácora (más reciente arriba)

- **2026-10-13 / baja definitiva de 13 posiciones de Lista 1**: se retiraron 185–191, 193, 201–204 y 241 del layout, inventario canónico, orden canónico y listas públicas; cada `tvg-id` tiene tombstone permanente. Todos eran canales en prueba/sin EPG y ninguno era respaldo de otra fila. No se desplazó ningún canal superviviente. Normalización canónica comprobada idempotente y sin cambio de identidad, orden ni referencia de stream. `targeted_update.py --mode presentation` valida partición 136/0/1900; 347 Python (19 omitidas), 55 JavaScript y editor 473/381. No se cambió selección, EPG, resolutores ni app. Registro: `contracts/channel-number-exclusions-20261013.json`. Falta verificar publicación y resultado del runner remoto.

- **2026-10-12 / purga definitiva de 23 señales colombianas**: el usuario pidió eliminar la lista de canales colombianos no deportivos/no musicales de la búsqueda directa. Los 23 IDs estaban ya `deleted` en el layout, pero aún sobrevivían en el inventario canónico; se purgaron del layout, `channel-catalog.m3u` y orden canónico, con exclusiones permanentes para no reimportarlos. Las M3U públicas ya los tenían fuera; tras el runner mantienen los mismos 149 IDs y su alias. Quedan otras 97 entradas del hallazgo: 86 en papelera y 11 activas en prueba. Se conservaron exactamente los demás IDs y números. Validación: 347 Python (19 omitidas), 55 JS, `targeted_update.py --mode presentation` correcto, bundle 486/381 y auditoría de datos/IDs correcta. Commit `4802771` publicado en `main`; runner de canales `38335797763` publicó `51a1700`, editor `38335797811` y dirigido `38335797783` success. La EPG no se cambió en este commit; el workflow independiente `38335907914` corrió después, publicó `ca8605a` y el Raw verificado contiene 72 canales guía, ninguno de los 23 IDs purgados. Sin cambios de app/APK.

- **Validación de las 120 altas directas / 2026-10-12**: 332 Python (19 omitidas según condiciones existentes), 54 JS, bundle del editor 509 filas/381 logos y materialización dirigida sin red correctos. Comparación contra `af307b0`: filas previas, números, tombstones, selección y registros M3U previos intactos; 120 altas exactas y sin EPG. Smoke JVM del parser M3U del diagnóstico acepta los 120 nombres/URLs una sola vez; no es build Android actual ni prueba en TV. Detalle y límites en `CANALES_DIRECTOS_ADICIONALES_20261012.md`.

- **2026-10-12 / descubrimiento directo ampliado**: 120 señales directas adicionales en prueba, números 226–345; búsqueda pública ampliada y vídeo/audio decodificados, revisión visual y exclusión de placas/negras/identidad ambigua. Conservados los 62 Total Conexión previos, todas las filas anteriores, sus números y tombstones; Highfly/TvVoo/selección, EPG, resolutores y app no cambian. Registro: contracts/public-direct-discovery-20261012.json. Nombres/regiones de fuentes públicas no equivalen a identidad EPG confirmada; sin logos asignados a ciegas. Sin APK ni commit hermano requerido.

- **2026-10-12 / France 24 English**: publicada la limpieza case-insensitive de `(EN)` para título, subtítulo, descripción y categoría de la identidad inglesa, sin alterar otras señales (`5a80c19`). Regresión `tests/test_france24_english_epg_marker.py`; 332 Python (19 omitidas) y 54 JS, todo lo ejecutable en verde. Corrida completa `38293029014` y publicación EPG `d6d5a20` success. Raw verificado: 291 programas y cero marcadores visibles; SHA-256 `be53165bcb250cf3186a238e3a58bd7eb3cf34e3265bffe3240a9dece87af558`.

- **2026-10-12**: preparado y completado el soporte Nauta dinámico de respaldos (`backupm3u`) y los cambios pedidos para ESPN/MTV, en dos repositorios independientes. VibeM3U 0.5.93/202 (`682b1b5`, tag `v0.5.93`) pasó Android CI `38271441176` y Release `38272387946`; APK pública no draft/prerelease, 2.774.715 bytes, SHA-256 `27f694d5f096967f91dede4e7091e5f5dfab894e6ded08659686751c07315d96`, certificado compatible. El artefacto de CI se instaló en el AVD `VibeTV` (API 36), `MainActivity` abrió sin FATAL/ANR; es smoke test y no validación de reproducción Nauta. En Lista M3U, `site/editor-core.mjs`/`editor.js` admiten respaldos explícitos Nauta estables y `update_m3u.py` añade fuentes EPG AR1/MX1/US2. Catálogo editorial publicado por el editor en `77a025b`; lista materializada por cambios dirigidos en `f7eb041`. ESPN 1 Argentina #33 con respaldos Sur/Chile; ESPN 1 México #34; ESPN 7 #39; la fila original #150 es Fox Sports 2 HD y queda #40 en prueba; ESPN HD es distinta y conserva #151 en prueba; MTV Live queda #52 justo antes de MTV Biggest Pop, definitiva con logo y EPG. La publicación de `5841348` corrigió la allowlist de Nauta; runner `38281677079` success, salida `eb29cc8`; EPG `38281825821` success, XML `f44b295`. El Raw de la EPG contiene 5.062 programas y los cuatro canales esperados tienen 66/62/40/70 programas respectivamente, ninguno pendiente; SHA-256 `7be7b3234896a7148f99b87c2841df512c54a1d92fc82bfbc11b7eb986af6f34`. Raw verificado contra Lista 1 (98 IDs), Lista 2 vacía y cero canales EPG en Lista 2; RWND sigue como cuatro bloques `Live` sin metadatos, a horas cerradas y de hasta 6 h. Pruebas locales finales: 330 Python (19 omitidas por sello/catálogo vivo) y 54 JS. No hay afirmación de reproducción en TV de las nuevas señales.

- **2026-10-11 / pedidos de la app (papelera desde la TV)**: VibeM3U 0.5.90 deja un JSON en `data/app-requests/` (esquema 1, `action` "trash", `rowKey` igual que `rowKey()` de editor-core). Workflow «Pedidos de la app» (`app-requests.yml`) corre `scripts/apply_app_requests.mjs`: aplica `setRowState(…, "deleted")`, rehace `presentation-overrides.json` y `vibem3u-selection.json` con las mismas funciones del editor, valida con `validateLayout`, borra los pedidos (los inválidos se omiten y se borran) y relanza `update-channels` y `update-highfly` (un push con GITHUB_TOKEN no los dispara; desde 2026-10-12 ya no: regenera las listas sin red y solo relanza el editor web). Prueba con copia del catálogo real: solo cambió el estado de la fila pedida; las demás solo su `order` interno por el reagrupamiento activos/ocultos/papelera, sin tocar números. Pruebas: `tests/app-requests.test.mjs` (4) en el sitio y en el workflow; 321 Python (1 omitida) y 52 JS.
- **2026-10-11 / RWND en horas cerradas**: el runner reconstruye sus bloques `Live` a la hora en punto desde la hora actual hasta el buffer redondeado hacia arriba. También corrige una guía reutilizada aunque ya tuviera cobertura; una prueba de publicación impide volver a aceptar límites con minutos/segundos. No incorpora parrilla real, descripciones ni datos de Rewind TV estadounidense. Commit de código publicado `4782c86`. En el `main` integrado se actualizaron expectativas de pruebas antiguas para reflejar bajas autorizadas desde la app: Sky Sports Main Event UHD y cuatro Nauta ESPN con tombstones explícitos (`Nauta.6186c37c4a108ec7eb171697@Nauta`, `Nauta.d3d2698fec772d9095f5ed4d@Nauta`, `Nauta.4ad5525f8e38f0915deaa561@Nauta`, `Nauta.8297a7fa0389cc7cf1d200dd@Nauta`); no se editaron esas decisiones editoriales. Runner EPG manual `38192606087` success; generó `7eab81f`, confirmado en el `main` remoto junto al XML con cuatro bloques contiguos (22:00–04:00, 04:00–10:00, 10:00–16:00, 16:00–17:00 hora Chile), título `Live` y sin metadatos extra. SHA256 de `epg.xml`: `89e4ac8a32c50a1a0a9898f960fbeba7704bc706cdc5f81a5c36e47ea72b15d4`. Suite local: 324 pruebas Python (1 omitida) y 52 JS, todas las ejecutables en verde.
- **2026-10-11 / Canal 13 oficial como predeterminado**: se retiró `preferredM3u=Canal13.cl@Direct187` de `0107`; ahora la señal propia oficial abre primero y conserva los respaldos en orden `Canal13.cl@Direct187` → `T13EnVivo.cl@DPS`. Las tres filas permanecen activas en Lista 1, pero la app agrupa las referencias bajo Canal 13. No se modificaron M3U/EPG/selección, identidad, presentación ni VibeM3U; se agregó una regresión editorial. Suite completa: 321 pruebas Python (1 omitida) y 48 JS, todas las ejecutables en verde.

- **2026-10-10 / reparación de test y republicación ESPN 7**: se corrigió `test_cleanup_preserves_other_presentation_and_contains_no_secrets`; la huella de preservación excluye el asset asociado a filas Nauta solo cuando ninguna identidad no Nauta lo comparte. La corrida previa `38090017826` había fallado en esa prueba, no al resolver/publicar ESPN 7. Commit `0f41b99` publicado; Pages `38090653457` pasó todas las pruebas. El runner relanzado `38090677815` pasó sus cinco proveedores, suite del runner, membresía y publicación; sus salidas `f65584c` y `03ef421` preservan ESPN 7 como #37. EPG automática `38090766510` pasó y generó `616ba41`; ESPN 7 queda con 35 programas CO1, fuente `parrilla real`, no pendiente y EPG con SHA256 `69003b8417cad6177a516e33641acdac4e1748b7cc8268b256e158803403f716`. Suite local tras esos outputs: 320 Python (1 omitida) y 48 JS. La muestra de vídeo antigua PSG–Arsenal aún no basta para asegurar alineación temporal perfecta con la guía.
- **2026-10-10 / ESPN 7**: solicitud cumplida y publicada en el commit `f22c009`: canal 94 → 37, después del 36; nombre `ESPN 7`, definitivo, logo local y guía CO1 solo en Lista 1. Runner de canales `38089626317` success/salida `59be701`; EPG `38089703472` success/salida `4be7110`, 35 programas reales, no pendiente. 320 pruebas Python (1 omitida), 48 JS, validador de listas y guardia de resolutores en verde. VibeM3U 0.5.88 permaneció sin cambios; `:app:testDebugUnitTest` pasó. La discrepancia de un fotograma PSG–Arsenal frente a ESPN KnockOut se mantiene como salvedad: programación publicada no demuestra por sí sola que esa emisión Nauta estuviera alineada en ese instante.

- **2026-10-10 / vista completa Nauta**: la portada remota ofrece 150 nombres; la unión de las 18 categorías TV dio entre 528 y 530 identidades únicas en consultas en vivo. La opción local nueva consulta las categorías en grupos de cuatro, deduplica sin alterar localizadores, ordena los nombres y presenta todo el resultado sin recortarlo. Ante error de una categoría no declara el catálogo completo. El selector deja visibles con estado las bajas históricas y los ya agregados/publicados, sin habilitar altas automáticas. El botón para abrir el selector espera a que cargue el catálogo inicial. Regresiones nuevas comprueban más de 500 filas, duplicados, categoría original, concurrencia, fallo parcial y preservación del orden canónico. Validación: 319 pruebas Python (1 omitida), 47 JS, `node --check`, bundle temporal 270/380, `local-catalog:test` verde y web local real con 530 filas (194 deshabilitadas) frente a 150 en «Portada». Se corrigió además el orden canónico truncado por el commit editorial remoto; sin cambio de contrato de filas ni de VibeM3U.
- **2026-10-10 / selección múltiple Nauta publicada**: commit del editor `ca5545d`, Pages `38067781735` success; `index.html` y `editor.js` públicos responden 200 y contienen los textos de selección múltiple. Se pueden marcar varios candidatos y agregarlos en una acción; cada alta explícita sigue yendo a Lista 1, en prueba y sin EPG. No se importa el catálogo completo ni se reponen solos los canales fuera del layout. 319 pruebas Python (1 omitida), 45 JS, `node --check site/editor.js`, `git diff --check` y bundle temporal (253 canales/380 logos) pasan.
- **2026-10-09 / auditoría ciega del generador**: CO1 dejó de publicar el día en curso de DSports (guía vacía desde 02:00); DSports [IP 15] continúa ahora con UY1 «[SPOARHD].DSports.Argentina.HD.uy» solo después de CO1 (otro feed regional; DSports 2 sin equivalente en CL1/AR1/UY1/PE1/EC1/MX1). La guía arrastraba 562 de 3.527 programas ya terminados (hasta 3 días): `EPG_PAST_RETENTION` = 6 h para todas las fuentes y Red Bull. Highfly: dos disparos `workflow_run` casi simultáneos chocaban en `git pull --rebase` (2 de 28 corridas); ahora se reinicia desde `origin/main` y se regenera. `.gitattributes` deja `contracts/*.json` y el informe Nauta sin conversión de fin de línea (sus SHA-256 fallaban en Windows). Revisado sin cambios: numeración activa sin duplicados, `m3u.m3u` = `1.m3u`, respaldos existentes, token del editor solo en memoria. Las IDs TvVoo duplicadas en la guía son intencionales (inventario usa las antiguas, la app las nuevas). Pendiente de decisión del usuario: respaldo TvVoo de Win Sports [IP 181] es «ESPN 3» con país `arabia`/grupo `ar`. 319 pruebas Python (1 omitida), 44 JS.
- **2026-10-09 / exclusión general Nauta publicada y verificada**: commit `fbcf4f6`; runner `37918633118` success, salida `29c9caa`; editor `37918633278`, dirigido `37918633165`, Highfly `37918633241` y actualización posterior al runner `37918764056` success. Las listas remotas conservan 51 canales en Lista 1/alias y 1.680 en inventario, cero Nauta; lista 2 permanece vacía. Layout 253 filas/0 Nauta. La pestaña local muestra los candidatos Nauta y limita la incorporación a uno por acción; Pages HTTP 200. EPG `37918764113` success, salida `f9f43eb`: 46 de Lista 1 +14 gestionados, 60 total y cero Nauta en XML/pendientes. EPG todavía reportó cobertura insuficiente para algunos canales existentes (1437, DSports y DSports 2, entre otros); no se alteró el alcance de la guía. 317 pruebas Python (1 omitida), 44 JS, editor compilado y bundle 253/380; sin APK/cambios en VibeM3U ni prueba física.
- **2026-10-08 / cierre remoto**: commit `08cf7e1` y publicación del editor; runner `37870337325`, editor `37870337366`, dirigido `37870337472` y Highfly `37870337314` success, salida `88bf85ce`. Se confirman 606 filas/353 Nauta/0 respaldos Nauta, dos respaldos HTTP conservados y pestaña Nauta en Pages. EPG `37870440382` success: `epg-run-state.json` la limita a Lista 1; `epg.xml` y `epg-pending.json` no contienen Nauta; salida `01103ce`. Nauta continúa en prueba y fuera de EPG. VibeM3U 0.5.84/193 publicada/verificada. Sin prueba física de TV.
- **2026-10-08**: retirada la relación Nauta base→HD del layout, de la proyección de VibeM3U y del editor de respaldos. Los canales siguen en Lista 1 en prueba, ahora independientes; se conservan los respaldos HTTP ajenos. La pestaña Nauta del generador local consulta categorías y canales actuales mediante el auxiliar local, guarda solo categoría, nombre exacto e ID estable, y el runner materializa el localizador de prueba en la M3U canónica. 316 pruebas Python (1 omitida), 43 JS, guardia de resolutores, bundle y pruebas del auxiliar local pasan. VibeM3U `v0.5.84`/193 publicado/verificado (CI `37869646187`, Release `37869965389`).
- **2026-10-09 UTC, cierre de respaldos Nauta base→HD**: editor `37864447534`, runner `37864447565` y EPG `37864564605` completaron correctamente. GitHub mantiene 353 Nauta activos/55 pares HD-base; 55 referencias únicas presentes en ambas listas M3U, sin mover orden/número ni cambiar prueba. EPG publicada como `27ff2b1`: alcance solo Lista 1, 69 canales y 6.462 programas; cero IDs Nauta en XML y pendientes. La app 0.5.83/192 (`390732a`, tag `v0.5.83`) ya estaba publicada, verificada y compatible antes del catálogo; `PublishedPlaybackCatalogTest` y `TvVooBackupTest` pasaron. Sin prueba física de TV.

- **2026-10-08, cierre de bajas Nauta 24/7 y seis posiciones**: commit `0e6bb56`, runner `37859215025`/salida `5752379`, editor `37859215094`, dirigido `37859215059` y EPG automática `37859356670` completaron con éxito. Las 75 identidades permanecen ausentes; 353 Nauta y 606 filas, números intactos. Siete Raw al SHA final `fabc464` cotejados contra sus blobs. El runner solo normalizó comentarios/espacios de agrupación en las listas, sin reintroducir ni alterar otros bloques de canal. EPG conserva el alcance (60 IDs, 0 Nauta; sin Nauta en XML/pending), selección intacta. Parser real app 0.5.81: 414 visibles y 0 incompatibles; 309 Python (una omitida), 41 JS y editor 606/380. Sin cambio ni APK de VibeM3U.

- **2026-10-08, cierre reincorporación Nauta**: `cd4d66e` publicado, runner `37852531718` y salida `bc448ce` correctos, editor y dirigido verdes. Repetidas pruebas Nauta/contrato y proyección real de app; 428 Nauta/489 visibles, ningún descarte. Raw/blob de siete archivos y layout de Pages verificados; otras filas, selección y exclusiones restantes intactas. La EPG habitual corre aparte y excluye todas las filas Nauta en prueba. Publicar cierre documental también; no mover versión/tag de VibeM3U ni retirar guardas de origen. Disponibilidad de las 34 no garantizada.

- **2026-10-08, reincorporación deportiva/editorial**: autorización «Agrega todos» acotada a 34 entradas enumeradas, incluidos partido 108 y Evento 2 (295). Filas y bloques originales recuperados, solo sus tombstones retirados; 428 Nauta, 105 excluidos, 681 filas. No modificar otros canales, selección, resolutores o EPG. Tres regresiones nuevas protegen alcance cerrado, historias inmutables, posiciones/URI/prueba y evidencia de fallos separada de decisión editorial; nueve tests Nauta. Primero validar runner y después lector/proyección real de app 0.5.81, publicar solo Lista M3U y verificar que runner preserve altas y bajas restantes. No prometer operatividad de canales con fallos.

- **2026-10-08, cierre remoto de limpieza**: `4518462` y salida de runner `472b656`, procesos de canales/editor/dirigido correctos. Bajas ausentes y con exclusiones persistentes; supervivientes preservados y Raw idéntico a Git. Verificación posterior de app con catálogo integrado: 394 Nauta/455 visibles, sin descartes; seis tests Nauta y contrato correctos. Documentación de cierre se publica también en el mismo flujo. No se promete estabilidad futura ni prueba física.

- **2026-10-08, depuración Nauta autorizada**: auditoría completa 21:01–21:07 UTC, sin guardar URLs/IDs opacos/headers/credenciales. Prueba HLS y vídeo, descartando placas mediante huellas de cuatro imágenes con título visualmente examinado. 394 disponibles / 139 bajas comprobadas tres veces; entradas retiradas, no ocultas, numeración y resto editorial preservados. Evidencia completa y lista pública de bajas versionadas, seis tests Nauta incluidos en 303 Python; 41 JS y parser/proyección real de app correctos. Orden runner → app → publicación y verificación de runner automático; app sin commit nuevo ni release. Un intento diagnóstico de parser con `resolver-catalog.json` remoto excedió el límite de aliases de la app; la app carga exclusivamente `app/src/main/assets/resolver_catalog.json`, que pasó la comprobación. No se afirma fallo de producción por ese diagnóstico ni se modifica fuera de alcance.

- **2026-10-07, cierre remoto Nauta**: catálogo `b33cebf` publicado después del APK, editor `37718537777` y runner completo `37718537821` verdes. `a5081dd` conserva 533 referencias, estado en prueba, números y layout; Raw y proyección de clases reales comprobados otra vez. EPG conserva 46 canales sin Nauta; runner automático de EPG disparado, no forma parte de la validación de nuevos canales en prueba. App contraparte `e3d2ee2`, tag `0ef0331`, documentación `2bfa14b`. Este cierre documental se publica también, sin cambio de app/catálogo/EPG.

- **2026-10-07, compuerta APK cumplida**: Release Nauta `37718148346` success; APK exacta descargada de GitHub y comprobada con apksigner/aapt/SHA256 (0.5.81/190, firma estable). Se habilita publicación de las 533 filas en el commit separado de Lista M3U, manteniendo la EPG previa y todos los nuevos en prueba.

- **2026-10-07, compatibilidad Nauta**: 301 Python/41 JS, copia compartida verificada por hash, contrato de resolutores válido (533 Nauta). Parser y proyección publicados de VibeM3U reconocen 533 Nauta, números únicos 87–619, total 594 visibles; ningún proveedor descartado. App funcional `e3d2ee2`, versión/tag `0ef0331` / 0.5.81/190, Android CI `37717793042` success en compilación y pruebas instrumentadas. Release `37718148346` se comprueba antes de subir este catálogo. No tocar la selección Highfly/TvVoo ni ampliar EPG: 46 en alcance, todos los nuevos en prueba.

- **2026-10-07, Nauta**: importación completa autorizada junto a resolver Android. Nuevas filas mediante `editor-core.addRow` y presentación por `buildPresentationOverrides`; filas previas intactas. Los nombres exactos repetidos son alternativas de resolución. IDs opacos, headers y URLs viven solo en RAM; `notWebReady` no equivale a DRM en Android. Orden de validación runner → app, publicación APK compatible → Lista 1; EPG actual intacta.


- **2026-10-06**: a pedido del usuario, el 68 («ESPN», `ESPN.us@Direct181`) va a la papelera y el
  69 (`ESPN4.br@Direct181`) pasa al 35 como «ESPN 4», oficial y con logo `logos/espn-4.png`
  (tv-logos Brasil recoloreado al rojo de ESPN 3/5). No es Brasil: es ESPN 4 Norte (barra en
  español con horarios MÉX/PAN). Guía `pa1` `Canal.ESPN.4.(Panamá).pa`, comprobada con dos
  cuadros (20:45 NFL, 21:09 Southern Miss vs. Troy); las guías ESPN 4 de UY/CO son del feed Sur.
- **2026-10-06**: pedidos del usuario.
  - Eurosport 1 (63) y 2 (64) de TvVoo España: `backupCountries` = portugal, unitedkingdom,
    france, italy, germany, netherlands. `tvvoo_variants.py` suma, después de las hermanas del
    país, el mismo canal de cada país (uno por país, mejor calidad, nunca BACKUP); la app ya los
    prueba en orden (resuelve por alias, que trae el país). Excepción editorial a «no cruzar países».
  - France 24 English (19) deja de estar en prueba: recibe la guía `France.24.Anglais.fr` ya
    configurada. DSports [IP 15] (118→37) y DSports 2 [IP 187] (120→38) pasan antes de los XITE
    (números libres, nada más se renumera), oficiales y con guía de Colombia (`co1`):
    `DSPORTS.(COL).(DTSC).co` y `DSPORTS.2.HD(DTV2HD).co`, elegidas comparando cuadros de las
    señales (20:34) con la parrilla: son el feed andino. Las pruebas que fijaban el estado
    anterior (France 24 en prueba, DSports 2 en el 120) se actualizaron a este pedido.
- **2026-10-06, cierre France 24**: código editorial `1073380f3c4e22885ec7201e79e49151b0cce305` publicado main, cuatro archivos Raw fijados al SHA iguales a sus blobs Git y lector/proyector 0.5.73 correcto. Runner de canales `37539066258` success: generó `c76d52f` solo para salud/estado; posición/streams/layout/selección sin cambios. Editor web `37539066224` success y EPG habitual `37539349779` disparada, sin oficializar France 24 inglés. Git limpio tras integrar main; documentación de cierre publicada sin force push. No validación física de reproducción ni APK nueva, se reutiliza la fuente existente.
- **2026-10-06, France 24 inglés**: usuario pide incorporarlo después del español; ya existía activo/en prueba en el 62, por lo que se reubica al 19 con editor-core, sin duplicar ni alterar prueba/stream/logo/identidad/membresía. Se informa en el chat antes de aplicar que se conserva prueba; no se interpreta como autorización de oficialización/EPG. Número 18 español conserva posición y activos siguientes suben +1 (incluidos proveedores, respaldo T13 ahora 218), orden editorial y M3U coherentes. Registro `contracts/channel-position-change-20261006-france24.json`; los fixtures históricos de bajas/altas no se reescriben. Tres regresiones nuevas y adaptación de expectativas de números históricos a esta inserción. 312 Python/41 JS, bundle temporal y contrato correctos; lector/proyector real VibeM3U 0.5.73 `94dd35b`: 77 visibles, France24 consecutivos 18/19, sin proveedores descartados y mismo T13/respaldo. Solo Lista M3U, selección y app sin cambios. Publicar en main y verificar runner y archivos remotos; sin APK nueva.
- **2026-10-06, cierre Rwnd**: `45c217f` publicado y todas las fuentes/armado/publicación/verificación Raw de `37537954410` correctos. XML remoto `43d110ad924341d33a9267dfd95fee6bafc0fc53`; hash blob Raw/Git idéntico `6dc7dabb73794ba2c6ea0737f38c3d462990f312`. Tres bloques Live de seis horas, sin sinopsis ni otros metadatos, cobertura futura casi 18 h. Lectura real de EpgParser/EpgProgramme 0.5.73 correcta; no APK, no test en TV física ni renovación de caché observada. Orden validado runner → lector app → publicación/regeneración → XML remoto/lector. Documentación de cierre se publica en el mismo flujo, sin force push ni modificación de los repos originales de D:.
- **2026-10-06, Rwnd**: el usuario pide mantener solo continuidad Live sin EPG/descripciones. Causa: el mapa `us2/Rewind.TV.us2` copiaba una guía ajena y la normalización solo cambiaba el título, conservando sinopsis. Retirado mapa y bloqueadas fuentes/fallback, donantes y bloqueo manual para la identidad; limpieza de metadatos al reutilizar XML. Cinco tests cubren overrides de fuente, guía fresca + publicada, limpieza idempotente sin tocar otros canales, donación y bloqueo manual. Validar primero runner (309 Python/41 JS), después lector XMLTV real de app 0.5.73 `94dd35b`, publicar código y regeneración/verificación EPG. No corrección de reproducción del 007 en este cambio, no APK ni cambios de catálogo.
- **2026-10-06, cierre ESPN 2**: código `58d95b4` publicado main; todas las fuentes y armado/publicación de `37535307432` correctos, XML remoto `a2b1a02`. Raw fijado al SHA y contenido Git coinciden. Parser EpgParser/EpgData/EpgProgramme de VibeM3U 0.5.73 recompilado para verificación JVM: 76 programas de la identidad `spain|vavoo_ESPN%202%7Cgroup%3Aes@TvVoo`, título ESPN Compact, descripción de final masculina de Rotterdam, UTC 20:45–21:45 y 12+ h futuras (aprox. 55 h). No nueva APK, no cambio de reproducción ni prueba de TV física. Orden cumplido: runner/tests reales → lector app → código main → workflow → XML remoto/lector. Documentación de cierre publicada en el mismo flujo, sin force push.
- **2026-10-06, ESPN 2 Sur**: usuario confirma foto contemporánea a las 18:20 Chile y solicita revisar todas las señales Sur. Comparadas guías AR1/CL1/CO1/EC1/PE1/UY1 (51 registros ESPN, 14 variantes ESPN 2, 3 sin programa en la franja; no guía dedicada BO/PY/VE). Coincide `[ESP2LS].ESPN.2.uy`: ESPN Compact, descripción final masculina Rotterdam del 04-10, 17:45–18:45; FIP confirma Tapia/Coello–Stupaczuk/Sanz, primer set 6–3. El chat inicial omitió esa descripción ya disponible: no atribuir hallazgo a una actualización del proveedor. Cambiados solo mapeos heredados ES/AR y retirado respaldo Bolivia no confirmado, sin desplazar hora/renombrar canal/tocar resolutores. Tres tests protegen selección exacta, sustitución de fútbol/tenis viejo, descripción/horas y alias estable de app; 304 Python/41 JS. Contraparte app existente `94dd35b`, sin nueva APK. Publicar main y regenerar todas las fuentes si la base no admite renovación parcial; conservar compuertas y verificar XML publicado/lector Android antes de dar la reparación por cerrada.
- **2026-10-06 UTC, cierre ESPN 5**: publicación del código `00897ab` y regeneración completa correcta `37403016586`, XML remoto `8196fd0`. Guía actual Rumanía–Suecia 23–01 Chile, 67 programas/72+ h; validación primero runner (301 Python/41 JS y armado fresco), después parser XMLTV real de app 0.5.73, sin nueva APK. Se documenta limitación operativa: renovación parcial `37402866106` falló porque la EPG anterior no cubría Lista 1 sin huecos; no publicó nada, por lo que se ejecutaron todas las fuentes existentes. No se desactivaron compuertas ni cambió el mantenimiento o pertenencia de canales. Verificar GitHub Raw fijado al SHA, no caché de main. Documentación de cierre también se publica en el mismo flujo.
- **2026-10-06 UTC**: autorizado «Hazlo» tras diagnóstico de ESPN 5. Corregido solo mapeo de `WinPlusFutbol.co@Direct181` de `[ESPN5SD].ESPN.5.uy` a `ESPN.5.HD.uy`, fuente UY1 ya integrada. Secuencia reportada Francia–Bélgica/Rumanía–Suecia y contraste UY1/CO1, captura 02:01:50 UTC (23:01:50 Santiago) con logo ESPN 5/textos españoles/Rumanía. No inferir país exclusivo por programas compartidos ni nombre SD/HD. Dos regresiones: fuente correcta y guía fresca gana a boxeo publicado sin mover horas o identidad. 301 Python/41 JS; no edición manual XML ni nueva EPG para otras listas, sin app/stream/logo/número/layout/selección. Publicar código separado y regenerar EPG por workflow `fuentes=epgshare`, verificar fuente y programación XML remoto; contraparte app existente `94dd35b`, sin APK.
- **2026-10-05**: a pedido del usuario, el 81 (TVN3 [Mediastream], `TVN3.cl@Mediastream`, en prueba) va
  a la papelera: era el mismo stream de TVN3 (011) sin el sufijo `?PlaylistM3UCL`.
- **2026-10-05**: respaldos directos múltiples (`backupm3u` en el layout, app 0.5.72): lista ordenada
  de tvg-id de otras filas M3U de la misma señal que la app prueba después de la propia (y de la
  preferida, si hay). Editor: `setBackupM3u`, validación (hasta 8, sin repetir, filas M3U
  existentes), sección «Respaldos directos» en el inspector y etiquetas «+ N respaldos» / «Dentro
  de NNN». A pedido del usuario: TVN (01) ← 73 y 74; Canal 13 (004) ← 85 (después del 079 y su
  propia señal). El runner no cambia: las filas siguen publicadas en Lista 1 (en prueba) y la app
  las oculta.
- **2026-10-05**: a pedido del usuario, el 38 (Fox Sports 1, `FoxSports1.us@Direct`, en prueba) va
  a la papelera con `setRowState` del editor; el resto conserva número y orden.
- **2026-10-05**: a pedido del usuario, el 120 (Sky Sports F1 UK de TvVoo, agregado el 04-10 para
  comparar con Highfly; daba lo mismo) va a la papelera con `setRowState` del editor. Los activos
  conservan número y orden; las filas en papelera que estaban intercaladas quedan al final (la
  convención del editor: activos, ocultos y papelera).
- **2026-10-04**: revisión de F1 UHD (22) y Main Event UHD (25): Highfly exige Premium para las
  dos hojas 4K (`now-34343434`, `now-srr343434`); su API gratuita entrega un marcador
  (`url` www.google.com, «🔒 Upgrade to Premium») en vez de HLS. El runner no estaba roto:
  F1 UHD sigue publicando la FHD gratuita (`now-545445`) como respaldo, según lo decidido el
  03-10; Main Event UHD no tiene hoja gratuita y solo funciona con Premium vinculado en la app
  (Main Event de TvVoo está en el 24). Cambio: `fetch_highfly_stream_urls_for_slug` falla con
  «hoja Highfly bloqueada por Premium» (`highfly_payload_premium_locked`) y `highfly_live.py`
  muestra en el log el motivo de cada hoja sin señal. Hosts Premium (`premium*.highfly.to`)
  responden normal (401 con token de prueba).
- **2026-10-04**: Canal 13 (004) con `preferredM3u` = `Canal13.cl@Direct187` (079, misma señal en
  mejor calidad): VibeM3U 0.5.65 abre primero la 079 y, si falla, la propia del 004; la 079 deja de
  verse sola en la app (sigue publicada en Lista 1, en prueba). Sky Sports F1 UK de TvVoo (FHD, con
  sus hermanas como versiones) vuelve al final, 120, «Sky Sports F1 UK (TvVoo)», para comparar
  con el de Highfly, que va ~3 h diferido (confirmado con capturas y la parrilla oficial de Sky).
- **2026-10-04**: 75 (Mega [VTR]) y 77 (Mega [Movistar]) a la papelera; 70 activos, Lista 1 = 56.
- **2026-10-04**: ESPN 5 Sur (035) con `logos/espn-5.png` (tv-logos Brasil, recoloreado al rojo de
  `espn-3.png`).
- **2026-10-04**: ESPN 3 Sur (033) usa `logos/espn-3.png` (`logoOverride`).
- **2026-10-04**: a pedido del usuario, 63 canales a la papelera (34, 37, 39, 63–66, 70–72, 76, 78,
  80, 82–84, 87–116, 120–123, 125, 127–138; el «165» pedido se tomó como 135). Sin renumerar:
  quedan 72 activos, 16 en prueba; Lista 1 = 58.
- **2026-10-04**: ESPN 3 Sur en un solo canal: el directo «Win Sports [IP 181]» (033, «ESPN 3 Sur»)
  lleva `backupTvVoo` = `arabia|vavoo_ESPN%203%7Cgroup%3Aar`; la fila TvVoo suelta va a la papelera
  y el 036 queda libre. Necesita VibeM3U 0.5.64 (antes se ve solo el directo). «Win+ Fútbol [IP 181]»
  es «ESPN 5 Sur». EPG: ESPN 3 Sur = `Canal.ESPN.3.(Chile).cl` (Argentina de relleno); ESPN 5 Sur =
  `[ESPN5SD].ESPN.5.uy` (nueva fuente `uy1`; el otro ESPN 5 de Uruguay coincide con Colombia/México).
  Títulos EPG: siglas cortas con números quedan en mayúsculas («A3D», «4K») y se suman siglas
  deportivas (NFL, NBA, UFC…); tras «: » la letra va en mayúscula. Editor: campo «Respaldo TvVoo».
- **2026-10-04**: canales «en prueba» y Lista 2 vacía, a pedido del usuario. Todo lo directo de
  Lista 2 pasa a Lista 1 con `trial: true` (75 activos + 13C; los 46 que el usuario tenía en la
  papelera siguen ahí). Lista 1 = 118 (42 oficiales + 76 en prueba); `m3u-externa.m3u`/`2.m3u`
  quedan con solo la cabecera (`external_list_disabled`). Los 46 espejos TvVoo/Highfly salen de
  Lista 2 (la app los toma de los proveedores). En prueba = sin EPG, sin validación ni reparación,
  fuera de la compuerta EPG; «Oficializar» en el editor los vuelve normales. Arreglado de paso: el
  guardado de las 17:39 nombró «ESPN 3» a Win Sports [IP 181], que choca con el canal TvVoo «ESPN 3»
  y rompía canales y cambios dirigidos; queda «ESPN 3 [IP 181]».
- **2026-10-04**: los 69 canales nuevos de Lista 2 (iptv-org, tlink y 13C) entran a la grilla del
  editor como filas M3U de Lista 2, activas, del 68 al 136 (tras los 67 que dejó el usuario).
- **2026-10-04**: a pedido del usuario, también a Lista 2 las 20 transmisiones de iptv-org en
  tlink.cl (fallaban desde EE. UU.; probablemente solo responden en Chile): nacionales, Mega 2,
  Mega Ficción, Meganoticias Ahora, Megatiempo, CDO, ETC TV y otras, con tvg-id `…@tlink`. Y 13C
  (`13C.cl@SD`, ya en el catálogo) pasa a Lista 2.
- **2026-10-04**: 48 transmisiones de iptv-org a Lista 2 (`m3u-externa.m3u`/`2.m3u`) y al
  catálogo, para revisarlas en el editor: respaldos de nacionales (TVN, Mega, Canal 13, 24 Horas,
  TVN3), canales chilenos nuevos (13 Realities, 13 Festival, 13T, T13 En Vivo, TV+, Bío Bío, UCV,
  Vía X, Telecanal, TV Chile, Teletrak, Turf Móvil) y deportes (DSports, DSports 2, Claro Sports,
  TyC, Win Sports, Win+ Fútbol, Movistar Deportes PE, L1 Max, Tigo Sports PY/GT, beIN XTRA ES,
  Golf Channel LA, Azteca Deportes). Solo las que entregaron segmento en una prueba desde GitHub
  Actions (EE. UU.); tvg-id `<id iptv-org>@<origen>`. Las de tlink.cl fallaron desde EE. UU. y no
  se agregaron. Cinco ya existían en el catálogo con otro ID y no se duplicaron.
- **2026-10-04**: ESPN 2 Latam (119) perdió su EPG desde la unión ES+AR: la reconciliación veía
  dos fichas (`Vavoo.es.ESPN2` y `Vavoo.ar.ESPN2`) y dejaba la fila «catalog_match_ambiguous».
  Ahora, si una fila TvVoo toca varias fichas, manda la de su alias estable
  (`_matches_stable_alias`). Verificado: la señal es ESPN 2 Sur (Chile/Argentina); a las 14:34
  UTC daba Azerbaiyán vs. Lituania, igual que `Canal.ESPN.2.(Chile).cl`.
- **2026-10-04**: Eurosport 2 España (ex 163) pasa al 117, junto a Eurosport 1 (116), con
  `logos/eurosport-2.png` (tv-logos, mismo estilo que el 1); los 117–128 se corren +1. ESPN 2
  Latam: las filas ES y AR (misma señal) quedan en una sola, la 119, con los dos alias TvVoo
  como versiones (`resolverAliases`) y `logos/espn-2.png` (tv-logos AR); la fila AR va a la
  papelera y el 121 queda libre.
- **2026-10-03**: 118 y 120 son la misma señal, ESPN 2 Latinoamérica (lo confirmó el usuario):
  ambos se llaman «ESPN 2 Latam» y usan la EPG `Canal.ESPN.2.(Chile).cl`, con Bolivia (`ar1`) de
  relleno. `Vavoo.es.ESPN2@TvVoo` sale de `NO_EPG_CHANNEL_IDS`.
- **2026-10-03**: a pedido del usuario, 51 filas TvVoo a la papelera del editor (129–180 salvo
  163 Eurosport 2 España; incluye TNT Sports ESPN y TNT Sports 5). Sin renumerar: quedan 121
  activos, último 163. Eurosport 1 (116) usa `logos/eurosport-1.png` (el logo del ex 179).
- **2026-10-03**: Main Event como F1 (normal y luego UHD): 24 Sky Sports Main Event (TvVoo),
  25 Main Event UHD, 26 Premier League. Nada más cambió de número.
- **2026-10-03**: el editor ordena por `order`, no por `number`: al mover F1 UHD (22) y Main
  Event UHD (24) solo cambié el número y quedaron al final. Ahora `order` sigue al número en
  todos los activos (ocultos y papelera después). Al reubicar canales por script, actualizar
  ambos campos (o usar `assignChannelPosition` del editor).
- **2026-10-03**: orden pedido por el usuario: 21 Sky Sports F1 · 22 F1 UHD · 23 Tennis ·
  24 **Sky Sports Main Event UHD** (Highfly 4K `now-srr343434`, `SkySportsMainEventUHD.uk`,
  logo recuperado del historial, guía de Main Event) · 25 Premier League y el resto corrido +2.
  Main Event solo existe en 4K en Highfly: sin Premium no tiene respaldo gratuito dentro de
  Highfly (la versión TvVoo sigue aparte en el 26).
- **2026-10-03**: Sky Sports F1 y **Sky Sports F1 UHD** son canales distintos. El editor
  agrupaba «(4k) SKY SPORTS F1» con la FHD y dejó F1 en la hoja 4K, que sin Premium solo entrega
  un aviso «🔒 Upgrade to Premium». Ahora la calidad 4K/UHD/8K de Highfly es una identidad
  propia (`isUltraHighflyName`/`ultraHighflyIdentity` en el editor y `is_uhd` en
  `parse_highfly_live_resolver_map`): F1 vuelve a `now-545445` (FHD gratuita) y F1 UHD
  (`SkySportsF1UHD.uk`, número 179, `now-34343434`) recupera el logo borrado el 13-09. Su
  respaldo gratuito sale solo: el runner publica para la fila UHD la primera hoja con señal de
  sus variantes (la FHD), y la app con Premium prueba antes la 4K. Guía: la misma de F1.
- **2026-10-03**: los 38 canales TvVoo que solo llegaban por `2.m3u`/`m3u-externa.m3u`
  (formato antiguo: tvg-id `…@TvVoo` con varios `x-resolver-ids`) pasan al editor como filas
  de proveedor, con la misma `addRow` del generador y la fila del catálogo oficial de TvVoo de
  cada país (números 141–178, en el orden de la M3U). No cambia ningún número existente: el
  script lo verifica fila por fila. Se conserva el nombre y el logo que mostraban; los logos
  externos de tv-logo se copiaron a `logos/tvvoo/` (algunos son genéricos o de otro país, como
  estaban). Otros 6 ya tenían fila en el editor (2 de ellas borradas por el usuario: Sky F1 UK
  y Sky Sports Mix, que no se reactivaron). Sky Sport 9 Alemania y Eurosport 1 Alemania quedaron
  con su versión vigente («HD (BACKUP)» y «HD»). Pendientes de antes, sin fila en el catálogo
  (sin guía): ESPN, ESPN 3 y ESPN 4 Países Bajos, Fox Sports 3 España, Fox Sports Premium y TNT
  Sports Premium Arabia.
- **2026-10-03**: agregado TNT Sports 5 (TvVoo Reino Unido,
  `unitedkingdom|vavoo_TNT%20SPORTS%205%7Cgroup%3Auk`, número 140) con fila de catálogo
  `Vavoo.uk.TNTSPORTS5@TvVoo` (marca managed) y guía de EPGShare UK1 `TNT.Sports.5.HD.uk`.
  Logo `logos/tvvoo/tnt-sports-5-uk.png` (tv-logo). Comprobado que entrega video en este momento.
  Hecho desde una copia en C: porque el disco D: del usuario quedó lleno.
- **2026-10-03**: agregado TNT Sports ESPN (TvVoo Reino Unido,
  `unitedkingdom|vavoo_TNT%20SPORTS%20ESPN%7Cgroup%3Auk`, número 139) como alternativa mientras
  TNT Sports 1 está caído en el origen de Vavoo (502). Reconcilia con `Vavoo.uk.TNTSPORTESPN@TvVoo`.
  Sin guía: EPGShare UK1 no publica un canal TNT Sports ESPN (solo TNT Sports 1–10), así que no se
  le asignó EPG ajena. TNT Sports 5 existe en TvVoo UK pero respondió de forma intermitente; no se agregó.
- **2026-10-02**: aplicado el cambio de color aprobado de Qello Concerts: las letras
  negras pasan a blanco mediante `fill="#FFFFFF"` en el grupo del SVG original;
  la clase cyan `#03A4D9`, los trazados y la transparencia se conservan. Se regenera
  `logos/qello.png` al tamaño original para que la app y el editor lo consuman por
  la misma ruta. Tres regresiones protegen colores, los 24 trazados originales y
  el tamaño RGBA de 1000×424. No cambia identidad, selección, EPG, numeración ni APK.

- **2026-10-02**: equivalencias BT/TNT UK verificadas con fotogramas reales antes de
  incorporarlas a los respaldos de TNT 1–4. Lista cerrada por país y nombre exacto;
  diez regresiones nuevas. BT SPORT ESPN/HD muestran TNT 4. TNT SPORTS ESPN muestra
  ESPN US y BT SPORT 3 HD rugby en vez del snooker de TNT 3: excluidos. Tres variantes
  BT sin fotograma siguen pendientes. TNT SPORT 1 entrega una placa de error que
  decodifica como video: añadir respaldos no demuestra detección automática de esa
  placa en la app. Evidencia y límites en `TVVOO_UK_EQUIVALENCIAS.md`. Sin cambios de
  selección, numeración, EPG, logos ni APK; VibeM3U 0.5.52 consume el mismo esquema.
  Validados: 266 Python + 34 JS + 3 JVM en verde; parser actual de la app acepta
  el JSON real con 2/2/2/3 respaldos para TNT 1/2/3/4. Sin prueba en la TV.

- **2026-10-02**: corregida la caducidad silenciosa de las variantes TvVoo. El runner
  renueva `generatedAt` cada 24 h aunque los alias sean idénticos; una consulta fallida
  no renueva la fecha de un documento sin cambios conservado como respaldo. Ocho tests
  nuevos cubren el caso de 8 días, el límite de 24 h, errores y fechas inválidas.
  No cambia la app, la selección de canales ni la agrupación por país.
- **2026-10-02**: TNT Sports 1, 2 y 4 sin guía. Una corrida de canales (19b0b2d) les borró
  la marca `x-vibem3u-selection="managed"` y la EPG solo incluía canales con esa marca. Ahora
  `epg_scope_extra_channels` usa la selección vigente (reconciliada) además de la marca, así una
  marca perdida no deja canales elegidos sin guía. Pendiente: averiguar qué paso del runner de
  canales borra la marca. TNT Sports 1 además está caído en la fuente en este momento.
- **2026-10-01**: respaldo real entre versiones del mismo canal TvVoo. TvVoo lista varias
  entradas por canal (MIX, MIX HD, MIX FHD, MIX (BACKUP)), cada una con fuente propia en Vavoo,
  pero la app solo probaba la elegida. `tvvoo_variants.py` publica las hermanas de cada canal
  elegido en `data/tvvoo-variantes.json` (VibeM3U 0.5.50 las usa como respaldo). Reglas por país
  acordadas con el usuario: SPORT ≠ SPORTS. Además, el aviso «Esta identidad ya está vinculada»
  desaparece: las versiones comparten la guía; Sky Sports Tennis suma su alias TvVoo en el
  catálogo. Quedan sin guía «SKY SPORTS F1» de los grupos DE e IT (sin hermana en su país).
- **2026-10-01**: sinopsis para la programación que no tenía. Las oficiales chilenas solo
  dejaban un texto técnico (se borra al publicar), así que TVN, Mega, CHV, Canal 13, La Red,
  24 Horas, T13, CHV Noticias, Meganoticias, NTV, DW Español y France 24 Español no tenían
  ninguna descripción. Ahora Zapping guarda la sinopsis real de cada programa y
  `donate_epg_descriptions` la pasa al programa publicado si coinciden hora y título. Prueba
  con la guía del día: 321 programas pasan a tener sinopsis. Se corrigió además que `dwe` de
  Zapping (DW Español) rellenaba la parrilla de DW English. Siguen sin sinopsis: Arirang
  (Zapping no la publica), Autentic History, M1, M2 y Telehit.
  - Misma fecha: la guía de Zapping da 403 desde GitHub, así que en Actions no llegaban
    sinopsis. Se suma Claro Video (`claro-sinopsis`), que sí responde desde Actions
    (verificado con una rama temporal ya borrada). Con Claro sola, en las próximas 24 h:
    TVN 12/17, Mega 14/18, T13 23/27, 24 Horas 24/30, 13 Cultura 21/25, DW Español 42/50,
    France 24 Español 93/108, Canal 13 10/16. Bajos: CHV, Meganoticias, NTV y La Red
    (Claro tiene otra parrilla para La Red).
- **2026-10-01**: TNT Sports 1–4 (TvVoo Reino Unido) agregados como canales 124–127 con
  `editor-core`. TvVoo publica varias variantes por número; se eligió la que hoy entrega
  video (HLS y segmento verificados): `TNT SPORT 1`, `TNT SPORT 2`, `TNT SPORTS 3`,
  `TNT SPORT 4`. Esas variantes se sumaron primero a `x-resolver-ids` de las filas del
  catálogo (`TNTSports1.uk`, `Vavoo.uk.TNTSPORTS2`, `TNTSports3.uk`,
  `Vavoo.uk.TNTSPORTS4`) para que la selección encuentre su fila y su EPG (EPGShare UK).
  TNT 2 respondió con cortes en las pruebas.
- **2026-09-30**: logo de Sky Sports Premier League con las proporciones del logo real en pantalla (foto del usuario, perspectiva corregida): bloque «Premier League» 727×136 centrado y león dentro del marco. Mismo archivo 870×377, mismo estilo blanco con marco que el resto de Sky.
- **2026-09-30 (estabilidad, tras una revisión externa de Sol)**:
  - `epg-pending.json` distingue `sin-guia`, `guia-corta` y `hueco`.
  - Highfly renueva la fecha de `highfly-live.json` cada 3 h (la app lo descartaba con más de
    24 h aunque los enlaces siguieran vigentes) y corre también al terminar canales y EPG,
    porque GitHub ejecutaba el cron de 30 min cada 4-6 h.
  - Búsqueda de una segunda fuente para TVN3, sin resultado.
- **2026-09-30**: `AGENTS.md` y este `ESTADO.md` pasan a ser la puesta al día obligatoria;
  punteros `CLAUDE.md`, `GEMINI.md` y `.github/copilot-instructions.md` para cualquier
  proveedor de IA. Codex y OpenCode leen `AGENTS.md` directo; `opencode.json`
  hace que OpenCode cargue también `ESTADO.md`.
- **2026-09-29**:
  - CHV: la oficial pasa a relleno detrás de Zapping y TecnoCentro (el noticiero aparecía como
    «Plan Perfecto»).
  - Mezcla general de fuentes por prioridad para todos los canales; la guía anterior solo
    rellena (6 h de pasado máximo); TVN y Mega pasan de ~29 h a ~73 h.
  - Respaldos que continúan guías cortas sin huecos ni duplicados: TecnoCentro continúa a
    Zapping en T13, CHV Noticias, NTV y Meganoticias; EPGShare continúa a DW; 13Go se
    redondea al minuto. Pendientes: de 12 a 4.
  - Runners por partes: canales por proveedor y EPG por fuente.
- **2026-09-28**:
  - Highfly: el runner publica el enlace directo vigente de cada canal (`highfly-live.json`).
  - TVN movió su reproductor fuera de `live.tvn.cl` (host nuevo `*.run.app`).
- **2026-09-27**:
  - EPG sin tope de 18 h (se integra toda la guía real, hasta 8 días).
  - Red Bull Chile vía `X-Forwarded-For` chileno (sin PC).
  - Cada fuente EPG en `epg_sources/<fuente>.py`, con fallos aislados.
  - Sky F1 vuelve a Highfly con alias TvVoo aparte.
  - `REGLAS.md` como documento único de reglas; contrato compartido de filas de proveedor.
  - Grupo propio de concurrencia para la EPG.
- **2026-09-26**:
  - Mantenimiento de canales solo sobre Lista 1.
  - EPG oficial → Zapping → TecnoCentro sin relleno técnico.
  - Editor con selección múltiple.
- **2026-09-25 y antes**: editor web local, logos históricos, Highfly y TvVoo gestionados
  desde el editor, listas 1 y 2.
