# Resolver Forge: resultados auditables

Fecha de ejecucion: 2026-09-01.

## Protocolo final congelado

- SHA-256 de `forge_core.py` antes de generar las semillas:
  `c7f419c9cfc7db186adf61cf5e0632fbce600c91f55f4e46c4a211149533f36f`.
- Cuatro semillas criptograficamente aleatorias generadas despues del hash.
- Dos repeticiones de cada familia por semilla: 200 casos en total.
- El motor solo recibio URL de entrada, identidad esperada y politica de red.
- El juez conservo familia, respuesta correcta y tokens fuera del motor.

## Prueba sintetica ciega

| Resultado | Cantidad |
|---|---:|
| Reparaciones correctas (TP) | 96 |
| Rechazos correctos (TN) | 96 |
| Reparaciones compatibles rechazadas (FN) | 0 |
| Aceptaciones incorrectas observables | 0 |
| Contenido cruzado sin identidad observable | 8 |
| Fugas de tokens o fallos de presupuesto | 0 |

El maximo observado por fase fue de 6 peticiones y 924 bytes en documentos de
control y muestras de segmento. Las 96 reparaciones aceptadas funcionaron dos
veces con un token distinto, demostrando que la receta no dependia de una URL
de sesion congelada.

Los ocho falsos positivos fueron exclusivamente el caso preparado para exponer
el limite epistemico: el endpoint afirmaba la identidad correcta, pero servia
video de otro canal y el HLS no incluia ninguna identidad comprobable. Master,
playlist y segmentos eran validos. Sin imagen, audio, watermark o una fuente
oficial comparable, ningun parser puede demostrar desde esos datos que el
contenido visual sea el correcto.

## Holdout real TvVoo

TvVoo expuso dos incompatibilidades que los fixtures pequeños no revelaron:

1. El nodo HLS HTTPS tenia el certificado vencido, mientras su ruta HTTP seguia
   operativa. Se agrego un fallback desactivado por defecto y habilitable solo
   por la politica confiable del proveedor; nunca se permite para la API de
   control.
2. Los segmentos reales superaban el limite reservado para JSON/HTML. La
   comprobacion final ahora lee solo 64 bytes del segmento y prueba tambien los
   mas recientes para evitar falsos 404 por rotacion.

Tras volver a congelar el hash y repetir toda la prueba sintetica, una tanda de
seis canarios TvVoo obtuvo 5/6 resoluciones renovables:

- pasaron: DAZN F1, Sky F1 UK, Sky Sport F1 Germany, XITE Alemania y BBC Earth
  Polonia;
- fallo cerrado: Sky Sport F1 Italia, HTTP 404.

Una muestra nueva de diez aliases seleccionados aleatoriamente despues del hash
obtuvo 6/10 resoluciones renovables:

- pasaron: Eleven Sports 3 Portugal, Sky Sports NFL, Sky Sport Calcio Italia,
  DAZN F1, DAZN 1 Italia y BBC Two Reino Unido;
- fallaron cerrados por HTTP 404: Digi Sport 1 Rumania, Eurosport 2 UK,
  Sky Sport F1 Italia y ESPN 1 Paises Bajos.

Los informes TvVoo conservan nombre, hash del alias, host final, metricas y
motivo. No guardan URL HLS, query, token ni ruta de sesion.

## Veredicto

El nucleo acotado funciona como detector y generador de candidatos: generaliza
a envoltorios desconocidos dentro de su DSL, renueva sesiones y rechaza cambios
de host, profundidad, esquema, tamano, identidad observable o segmento roto.

No debe publicar automaticamente una reparacion solo porque el HLS funcione.
La promocion segura necesita una segunda capa independiente de identidad. La
arquitectura recomendable es:

1. descubrir una receta declarativa en sandbox;
2. repetirla con una sesion nueva;
3. validar master, variante y segmentos;
4. comparar una huella visual/audio contra una referencia confiable;
5. publicar primero como canario reversible;
6. promover solo tras multiples ejecuciones y sin degradacion global.

Hasta incorporar ese oraculo, Resolver Forge es util como reparador asistido y
como fuente automatica de propuestas, no como escritor autonomo de produccion.
