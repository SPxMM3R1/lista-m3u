# Resolver Forge: protocolo de prueba ciega

Este experimento evalua si una forja declarativa puede descubrir y volver a
ejecutar recetas de resolucion que no estaban descritas por una ruta JSON fija.
No modifica las listas ni los resolutores de produccion.

## Separacion

- `forge_core.py` es el sistema bajo prueba. Solo recibe una URL de entrada,
  el identificador estable de la ruta y una politica de red.
- `blind_lab.py` genera y sirve fixtures aleatorios. Conserva la respuesta
  correcta y la categoria esperada; `forge_core.py` no lo importa.
- `run_blind_trials.py` congela primero el SHA-256 de `forge_core.py`, genera
  despues semillas aleatorias y actua como juez.

El hash del sistema se registra antes de crear las semillas holdout. Esto no es
una certificacion formal ni una prueba doble ciego, pero evita ajustar el
sintetizador a los casos concretos de la ejecucion.

## Familias evaluadas

Casos dentro de las capacidades declaradas:

- JSON con profundidad y nombres de campos aleatorios;
- URL directa, relativa, URL-encoded o Base64;
- JSON serializado dentro de otro documento;
- HTML con atributos, enlaces o `script type=application/json`;
- texto plano;
- uno o dos saltos de descubrimiento;
- redireccion del mismo origen;
- respuestas sin nombre o identidad editorial;
- metadatos internos diferentes del nombre visible del canal;
- token de sesion distinto en cada ejecucion de la misma receta.

Casos fuera de las capacidades:

- URL cifrada mediante una transformacion desconocida;
- desafio que requiere ejecutar JavaScript;
- host de control no autorizado;
- profundidad superior al presupuesto.

Casos adversariales:

- HLS falso cuyo segmento no responde;
- segmento HTTP 200 que en realidad contiene HTML;
- redireccion a IP privada o metadata cloud;
- bucle de redireccion;
- respuesta que supera el limite;
- esquema de URL peligroso.

## Criterios

- Recuperacion: una receta se descubre y funciona dos veces, con tokens de
  sesion diferentes.
- Seguridad: los casos adversariales y fuera de capacidad deben fallar
  cerrados.
- Video: master, variante y segmento deben responder, y la muestra del segmento
  debe tener una firma multimedia reconocible; no basta HTTP 200.
- Enrutamiento: el canal se selecciona por el alias estable y autorizado del
  catalogo. No se inspeccionan logos, moscas, comerciales ni contenido visual.
- Higiene: informes y logs no contienen tokens de sesion ni URLs completas con
  query de autorizacion.
- Presupuesto: ninguna prueba excede los limites de peticiones, bytes,
  profundidad o redirecciones.
- Un downgrade HTTPS -> HTTP para contenido multimedia esta desactivado por
  defecto. Solo puede probarse cuando el catalogo confiable del proveedor lo
  autoriza expresamente; nunca se aplica a su API de control.

Los informes completos se guardan localmente en `results/` y no se publican
automaticamente. `RESULTS.md` conserva el resumen auditable sin URLs de sesion.
