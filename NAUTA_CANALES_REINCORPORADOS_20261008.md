# Nauta: reincorporación editorial de deportivos y eventos

**34 entradas** vuelven por instrucción del usuario «Agrega todos»: 32 señales deportivas, el partido 108 y el genérico Evento 2 (295), cuya naturaleza deportiva no se ha confirmado. Todos activos en Lista 1, en prueba, sin EPG, con números/órdenes originales. Los otros 105 eliminados siguen excluidos; las 647 filas existentes no cambian. Total: 428 Nauta y 681 filas editoriales.

Reincorporar no equivale a reparar ni garantizar disponibilidad. La reprueba del 08-10 (21:56:56–22:02:04 UTC), con resolver real v0.5.81, enlaces renovados y decodificación, dio vídeo en alguna ronda solo en 295/306/308/320. 306 falló además una apertura independiente; 295 solo respondió una vez. 308/320 mostraron dos fotogramas distintos de contenido FOX Sports Radio. No se modifica el resolutor ni se quitan sus protecciones. No hay prueba física ni estabilidad prolongada.

| Número original recuperado | Canal exacto | Rondas con vídeo |
| ---: | --- | ---: |
| 108 | Atlético Nacional vs Deportes Tolima | 0/3 |
| 114 | AyM Sports | 0/3 |
| 165 | CDN Sportsmax | 0/3 |
| 204 | Claro Sports | 0/3 |
| 205 | Claro Sports 3 HD | 0/3 |
| 216 | Deportes TVC \| Honduras | 0/3 |
| 271 | ESPN (Ahorro de datos) | 0/3 |
| 277 | ESPN 2 HD | 0/3 |
| 295 | Evento 2 | 1/3 |
| 306 | Fox Sports 1 \| HD Sur | 3/3 |
| 308 | Fox Sports 1 \| Sur | 3/3 |
| 309 | Fox Sports 2 \| Chile | 0/3 |
| 311 | Fox Sports 2 \| HD Sur | 0/3 |
| 315 | Fox Sports 3 \| Mexico | 0/3 |
| 319 | Fox Sports Premium HD | 0/3 |
| 320 | Fox Sports Sur | 3/3 |
| 323 | FS2 USA HD | 0/3 |
| 325 | Futv \| Costa Rica | 0/3 |
| 337 | Gol Peru | 0/3 |
| 394 | Liga de Campeones 2 | 0/3 |
| 424 | Movistar Deportes \| Peru | 0/3 |
| 463 | PAC12 HD | 0/3 |
| 476 | PX TV | 0/3 |
| 545 | Tigo Sports Guatemala | 0/3 |
| 562 | TNT Sports  HD \| Argentina | 0/3 |
| 563 | TNT Sports \| Argentina | 0/3 |
| 564 | TNT Sports \| Chile | 0/3 |
| 573 | TUDN HD | 0/3 |
| 584 | UFC Network | 0/3 |
| 597 | Univisión Deportes | 0/3 |
| 598 | Univisión TDN | 0/3 |
| 607 | VTV Plus HD | 0/3 |
| 608 | VTV Plus \| Uruguay | 0/3 |
| 617 | WWE Network | 0/3 |

Auditoría y reporte de bajas originales conservados sin reescribir sus hechos; registro nuevo `contracts/nauta-restoration-20261008-sports.json`. VibeM3U compatible: `e3d2ee2` / v0.5.81, sin commit hermano ni APK nueva. Publicar solo Lista M3U y verificar que el runner conserve las 34 altas y las 105 exclusiones.

## Publicación verificada

Editorial `cd4d66e`; runner de canales `37852531718`, editor `37852531767` y dirigido `37852531793` correctos. Estado generado `bc448ce`: mantiene 428 Nauta, las 34 altas y las 105 bajas restantes. Siete archivos Raw fijados al SHA comprobados contra blobs Git y layout del editor publicado idéntico. Nueve pruebas Nauta repetidas y lector/proyección real de app: 428 Nauta/489 visibles, cero descartes; las 647 filas existentes y selección siguen intactas. EPG sin Nauta; no nueva APK ni garantía de disponibilidad de las señales.
