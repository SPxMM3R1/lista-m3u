# Editor local de canales

El frontend sigue siendo el editor HTML de `site/`, pero se sirve desde un auxiliar que escucha solo en `127.0.0.1`. El auxiliar de `VibeM3U/local-catalog` compila las clases de resolución directamente desde `app/src/main/java`; no mantiene una copia alternativa de Highfly, TvVoo, TVN ni Meganoticias.

## Inicio en Windows

1. Instala Java 17, Python 3 y GitHub CLI (`gh`).
2. Ten los repositorios locales separados: Lista M3U y VibeM3U.
3. Desde Lista M3U ejecuta `tools/Start-CatalogEditor.ps1`. Si VibeM3U no está en una carpeta hermana conocida, entrega su ruta como parámetro:

   ```powershell
   .\tools\Start-CatalogEditor.ps1 -VibeM3UPath "C:\ruta\a\VibeM3U"
   ```

El script construye una copia temporal de los datos de interfaz, inicia el auxiliar y abre el navegador. Mantén abierta la ventana de PowerShell; `Ctrl+C` detiene el servicio. No se crea un APK adicional y el inicio no modifica ni publica archivos de ninguno de los dos repositorios.

La primera vez, abre **Publicar catálogo → Conectar GitHub CLI** si GitHub aún no está autorizado en ese equipo. Se abre el flujo oficial de GitHub CLI en una ventana local; el token no se pega en la página. También puedes autorizarlo manualmente con `gh auth login --web --hostname github.com`.

## Reproducción y credenciales

La página solicita una resolución usando `catalogKey` como identidad. El auxiliar lee la URL de Lista 1/2 o los datos Highfly/TvVoo del canal y llama a las implementaciones Java originales de TVN, Meganoticias, Highfly y TvVoo desde VibeM3U (sin duplicarlas). Luego entrega al navegador una ruta HLS local opaca. Las URL firmadas, cookies y cabeceras quedan en memoria del auxiliar; la sesión se descarta al cerrar el reproductor o caduca automáticamente. Las cabeceras de autenticación no se reenvían al cambiar de origen, y las listas HLS no pueden direccionar el relé a redes privadas. No se guardan resoluciones en JSON.

GitHub se autoriza por GitHub CLI en una ventana local separada. El token queda en el almacén administrado por `gh`; no se pide ni se escribe en el frontend. Publicar parte siempre del último `main` y aplica encima los tres documentos editoriales; así los cambios de los runners no invalidan una edición abierta. Si `main` avanza durante la publicación, el auxiliar integra el intento sobre el nuevo árbol y reintenta sin force-push. El commit editorial dispara el runner de canales; al terminar correctamente, se ejecuta la EPG. La cuenta debe tener permiso de escritura sobre ese repositorio.

Se requiere internet para consultar proveedores, resolver la señal y publicar. La interfaz, sus fuentes y el reproductor HLS se sirven localmente; no se aloja el auxiliar ni se abre un puerto de red LAN.
