# Lista M3U para Android TV

Repositorio publico de la lista M3U principal para Android TV. La lista y su
EPG se actualizan mediante un coordinador comun que solo ejecuta el flujo
completo cada 48 horas. Ese mismo resultado puede generarse desde Windows o
desde GitHub Actions.

## URLs para el reproductor

Lista M3U:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/m3u.m3u`

Guia de programacion XMLTV:

`https://raw.githubusercontent.com/SPxMM3R1/lista-m3u/main/epg.xml`

## Funcionamiento

Cada ejecucion completa:

- comprueba los streams, los primeros segmentos multimedia y los logos locales;
- conserva los maestros originales de los canales cuya autenticacion corresponde
  al reproductor;
- publica los maestros HLS originales de cada canal, sin wrappers ni variantes
  generadas por este repositorio;
- prioriza enlaces descubiertos desde las paginas oficiales del emisor al
  reparar una senal; los respaldos conocidos solo se prueban despues;
- actualiza la guia EPG con las parrillas disponibles;
- usa las parrillas oficiales disponibles de TVN y Mega, ademas de las de M1 y
  M2; conserva EPGShare como respaldo cuando el emisor no publica XMLTV o una
  parrilla automatizable;
- integra PLEX1 para las señales FAST de BBC, Bloomberg, CBS, Qello, Stingray
  y XITE, y usa las fuentes pequeñas TR1, SG1 y NG1 solo para TRT World, CNA y
  Africanews, respectivamente; no descarga el XML combinado de todos los
  proveedores;
- conserva MTV Biggest Pop desde el feed latinoamericano de Pluto TV; como la
  señal no publica una parrilla XMLTV estable, el actualizador genera continuidad
  de videoclips sin inventar horarios concretos;
- usa la guia publica de Zapping Chile para las senales nacionales donde
  EPGShare/TecnoCentro mostraban desplazamientos o no entregaban una parrilla
  util; sus marcas Unix absolutas se convierten a America/Santiago sin sumar
  horas manualmente;
- publica `channel-status.json` como artefacto de cada ejecucion.

El coordinador `run_m3u_48h.py` conserva `run-state.json` para que el cambio
entre ejecutor local y GitHub sea transparente. Durante la ventana local hasta
el 1 de septiembre de 2026 se puede registrar
`register_local_48h_task.ps1`; desde el 2 de septiembre GitHub Actions retoma
el mismo flujo. La tarea local se repite cada 48 horas; GitHub usa un disparador
cada dos dias de calendario porque Actions no dispone de un temporizador exacto
de 48 horas, y no ejecuta red/EPG/canales cuando el estado aun no vencio. La
compuerta de `run-state.json` conserva el minimo de 48 horas aunque los cambios
de mes hagan que el intervalo del cron no sea exactamente igual.

Durante esta ventana, GitHub Actions queda deshabilitado para no consumir cuota.
El programador local contiene un disparador puntual para reactivarlo el 2 de
septiembre de 2026 a las 03:05 (hora local), y luego se deshabilita a si mismo.

TVN y Meganoticias conservan sus maestros originales. Actions no interviene en
la autenticacion de reproduccion; esa responsabilidad corresponde a la app.
Mega y La Red publican sus maestros oficiales directos. El PC solo necesita
estar disponible durante la ventana local; despues del 2 de septiembre el
ejecutor vuelve a ser GitHub Actions.

La guia conserva datos vigentes si una fuente externa falla temporalmente. La
ejecucion tambien puede iniciarse manualmente desde la pestana **Actions** con
el workflow **Actualizar M3U y EPG**. `force_run` omite la espera de 48 horas y
`force_epg_refresh` fuerza la descarga de las fuentes EPG.

Todos los logos de los canales se conservan dentro de `logos/` y la M3U y el
EPG apuntan a las copias publicadas en este repositorio. Los logos vectoriales
se mantienen como SVG y los demas como PNG para conservar la mejor calidad
disponible sin depender de servidores externos.

## Orden de la lista

1. Nacionales normales
2. Noticias
3. Miscelaneos nacionales
4. Internacionales y canales agregados por region o tema

## Canales

La lista contiene 46 canales: nacionales, noticias, miscelaneos chilenos,
noticias internacionales, documentales, conciertos y una seleccion musical.

TVN y La Red se actualizan desde sus parrillas oficiales. La fuente oficial de
La Red tiene prioridad sobre Zapping y EPGShare; esas fuentes se conservan como
respaldo si la pagina del canal no responde o no entrega 24 horas futuras.
La EPG usa fuentes XMLTV de Chile, Espana, Francia, Alemania, Polonia,
Letonia, Paises Bajos, PLEX1, Turquia, Singapur y Nigeria, junto con la guia
publica de Zapping para senales chilenas seleccionadas. Zapping se selecciona
por canal cuando su parrilla es valida; una fuente oficial siempre tiene
prioridad y un fallo aislado de Zapping no invalida los demas canales. M1 y M2
se actualizan desde sus parrillas oficiales semanales. Se marca como `senal continua`
cualquier canal que no publique una parrilla diaria verificable, en vez de
presentar esa continuidad como una guia real. Simply.TV (con punto) se reviso
como proveedor B2B de EPG y metadata:
su portal de entrega requiere autenticacion y la cuenta de prueba gratuita solo
ofrece un grupo limitado de canales. No se incorpora como dependencia del flujo
publico hasta contar con acceso autorizado y confirmar cobertura para estos
canales; si se habilita, se integrara como fuente opcional con credenciales fuera
del repositorio y Zapping/fuentes oficiales como respaldo.
