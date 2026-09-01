# Resolver Forge: resultados auditables

Fecha de ejecucion: 2026-09-01.

## Protocolo final congelado

- SHA-256 de `forge_core.py` antes de generar las semillas:
  `5a5aae66f571c31d14c63419e0520139ac0aa7055b364d86d06cb9b1d8bd0017`.
- Cuatro semillas criptograficamente aleatorias generadas despues del hash.
- Dos repeticiones de cada familia por semilla: 208 casos en total.
- El motor solo recibio URL de entrada, alias estable y politica de red.
- El juez conservo familia, respuesta correcta y tokens fuera del motor.
- Criterio solicitado: importa que exista video reproducible; no se compara el
  contenido editorial con el nombre del canal.

## Prueba sintetica ciega

| Resultado | Cantidad |
|---|---:|
| Reparaciones correctas (TP) | 128 |
| Rechazos correctos (TN) | 80 |
| Reparaciones compatibles rechazadas (FN) | 0 |
| Aceptaciones incorrectas (FP) | 0 |
| Fugas de tokens o fallos de presupuesto | 0 |

El maximo observado por fase fue de 6 peticiones y 1777 bytes en documentos de
control y muestras de segmento. Las 128 reparaciones aceptadas funcionaron dos
veces con un token distinto, demostrando que la receta no dependia de una URL
de sesion congelada.

Las fuentes sin identidad, con metadatos distintos o con un identificador HLS
diferente se aceptaron cuando entregaron video. El alias autorizado del catalogo
es la autoridad de enrutamiento; logos, moscas, comerciales y contenido visual
no participan en la decision.

Se agrego un adversarial nuevo: master y playlist validos cuyo supuesto
segmento respondia HTTP 200 con HTML. Las ocho repeticiones fueron rechazadas.
La comprobacion exige una firma multimedia reconocible (MPEG-TS, fMP4 o audio),
no solamente una respuesta no vacia.

## Holdout real TvVoo

TvVoo expuso dos incompatibilidades que los fixtures pequeños no revelaron:

1. El nodo HLS HTTPS tenia el certificado vencido, mientras su ruta HTTP seguia
   operativa. Se agrego un fallback desactivado por defecto y habilitable solo
   por la politica confiable del proveedor; nunca se permite para la API de
   control.
2. Los segmentos reales superaban el limite reservado para JSON/HTML. La
   comprobacion final ahora lee una muestra acotada de 1024 bytes y prueba
   tambien los mas recientes para evitar falsos 404 por rotacion.

Con el nuevo criterio, una tanda de seis canarios TvVoo obtuvo 4/6 resoluciones
renovables en esa ejecucion:

- pasaron: DAZN F1, Sky Sport F1 Germany, Sky Sport F1 Italia y XITE Alemania;
- fallaron cerrados: Sky F1 UK y BBC Earth Polonia, HTTP 404.

Una muestra nueva de diez aliases seleccionados aleatoriamente despues del hash
obtuvo 9/10 resoluciones renovables:

- pasaron: NRJ Hits, BBC Two Reino Unido, DAZN 5 Portugal, Sky F1 UK,
  Sky Sport 24 Italia, Sport TV 1, Eurosport 1 Portugal, DAZN LaLiga 1 y
  TNT Sports 1;
- fallo cerrado: ESPN 2 Espana, HTTP 404.

Sky F1 UK fallo en la tanda de canarios y funciono minutos despues en la muestra
aleatoria. Eso demuestra la volatilidad temporal del proveedor y la necesidad
de resolver y comprobar en cada reproduccion o corrida.

Los informes TvVoo conservan nombre, hash del alias, host final, metricas y
motivo. No guardan URL HLS, query, token ni ruta de sesion.

## Veredicto

El nucleo acotado funciona con el criterio de disponibilidad: generaliza a
envoltorios desconocidos dentro de su DSL, renueva sesiones y rechaza cambios
de host, profundidad, esquema, tamano, segmento roto o contenido que no sea
multimedia.

No se necesita OCR, huella de logo ni comparacion visual. La arquitectura
recomendada para una promocion automatica basada en video es:

1. descubrir una receta declarativa en sandbox;
2. repetirla con una sesion nueva;
3. validar master, variante y muestra multimedia de segmentos;
4. mantener API de control, alias y politica dentro del catalogo autorizado;
5. publicar primero como canario reversible;
6. promover tras multiples ejecuciones y revertir si deja de entregar video.

Las pruebas habilitan la siguiente fase de integracion, pero este laboratorio
todavia no modifica por si mismo el workflow de produccion.
