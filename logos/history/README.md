# Versiones históricas de logos

Esta carpeta contiene versiones de imágenes que estuvieron en `logos/` en la
historia de `main` y ya no están entre los logos vigentes. Los archivos se
conservan con nombre descriptivo y sufijo de blob para que puedan elegirse sin
ambigüedad en el pool del editor.

Para incorporar nuevas versiones antiguas después de actualizar un logo,
ejecuta `python tools/archive_logo_history.py` desde la copia local de Lista
M3U y publica los archivos generados junto con el cambio editorial. El runner
no los selecciona por sí solo: solo los usa si el editor guarda explícitamente
una de estas rutas como logo de un canal.
