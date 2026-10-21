# Propuesta de categorías y orden para Lista 1

Fecha: 2026-10-20 (America/Santiago)
Estado: **propuesta documentada; no aplicada al catálogo**.

## Alcance y reglas

- La propuesta cubre los **68 canales principales visibles** numerados actualmente del 1 al 68.
- Las 52 filas activas de respaldo que aparecen en el layout con números internos mayores a 68 no son canales visibles independientes y **no se cuentan ni se reordenan aquí**. Se conservan sus relaciones de respaldo.
- La columna «ID estable» es la clave para identificar la fila: `tvgId` en filas M3U y `catalogKey` en filas de proveedor. Los enlaces, nombres de origen, direcciones IP y otros localizadores no son identidad.
- Los nombres de la tabla son etiquetas descriptivas para reconocer los canales; **esta propuesta no solicita renombrarlos**, editar `group-title`, ni cambiar logos, EPG, fuentes, resolutores, estados o listas.
- La numeración propuesta sería consecutiva del 1 al 68, según este orden. No se han modificado `channel-editor-layout.json`, las M3U, `presentation-overrides.json`, el catálogo canónico, `epg.xml` ni `epg-pending.json`.
- RWND queda en **Música y conciertos**, al final del bloque, en la posición propuesta 54. Su guía sigue siendo únicamente continuidad `Live`, sin programación ni descripciones.

## Orden propuesto

| Posición propuesta | Categoría | Canal (etiqueta descriptiva) | Posición actual | ID estable (`tvgId` / `catalogKey`) |
|---:|---|---|---:|---|
| 1 | Nacionales | TVN | 1 | `0104` |
| 2 | Nacionales | Mega | 2 | `0105` |
| 3 | Nacionales | CHV | 3 | `0106` |
| 4 | Nacionales | Canal 13 | 4 | `0107` |
| 5 | Nacionales | La Red | 5 | `0102` |
| 6 | Noticias nacionales | 24 Horas | 6 | `0201` |
| 7 | Noticias nacionales | Meganoticias | 7 | `Meganoticias.cl` |
| 8 | Noticias nacionales | CHV Noticias | 8 | `1153` |
| 9 | Noticias nacionales | T13 | 9 | `0124` |
| 10 | Noticias internacionales | DW Español | 14 | `DW.de` |
| 11 | Noticias internacionales | DW English | 15 | `DWEnglish.de` |
| 12 | Noticias internacionales | NHK World Japan | 16 | `NHKWorldJapan.jp` |
| 13 | Noticias internacionales | Arirang TV | 17 | `ArirangTV.kr` |
| 14 | Noticias internacionales | France 24 Español | 18 | `France24.fr` |
| 15 | Noticias internacionales | France 24 English | 19 | `France24.fr@English` |
| 16 | Noticias internacionales | Al Jazeera English | 20 | `AlJazeera.qa` |
| 17 | Noticias internacionales | BBC News | 21 | `BBCNews.uk` |
| 18 | Internacional | TVE Internacional | 55 | `TVEInternacionalAmerica.es@HD` |
| 19 | Deportes | Sky Sports F1 | 22 | `SkySportsF1.uk` |
| 20 | Deportes | Sky Sports F1 UHD | 23 | `SkySportsF1UHD.uk` |
| 21 | Deportes | Sky Sports Tennis | 24 | `SkySportsTennis.uk` |
| 22 | Deportes | Sky Sports Main Event | 25 | `unitedkingdom\|vavoo_SKY%20SPORTS%20MAIN%20EVENT%7Cgroup%3Auk` |
| 23 | Deportes | Sky Sports Main Event UHD | 26 | `SkySportsMainEventUHD.uk` |
| 24 | Deportes | Sky Sports Premier League | 27 | `SkySportsPremierLeague.uk` |
| 25 | Deportes | DAZN F1 | 28 | `spain\|vavoo_DAZN%20F1%7Cgroup%3Aes` |
| 26 | Deportes | TNT Sport 1 | 29 | `unitedkingdom\|vavoo_TNT%20SPORT%201%7Cgroup%3Auk` |
| 27 | Deportes | TNT Sport 2 | 30 | `unitedkingdom\|vavoo_TNT%20SPORT%202%7Cgroup%3Auk` |
| 28 | Deportes | TNT Sports 3 | 31 | `unitedkingdom\|vavoo_TNT%20SPORTS%203%7Cgroup%3Auk` |
| 29 | Deportes | TNT Sport 4 | 32 | `unitedkingdom\|vavoo_TNT%20SPORT%204%7Cgroup%3Auk` |
| 30 | Deportes | Eurosport 1 | 33 | `spain\|vavoo_EUROSPORT%201%7Cgroup%3Aes` |
| 31 | Deportes | Eurosport 2 | 34 | `spain\|vavoo_EUROSPORT%202%7Cgroup%3Aes` |
| 32 | Deportes | ESPN | 35 | `ESPN.co@Direct181` |
| 33 | Deportes | ESPN 2 | 36 | `PublicDirect.d6cca6d4aa23a69d50439c22` |
| 34 | Deportes | Win Sports | 37 | `WinSports.co@Direct181` |
| 35 | Deportes | ESPN 4 | 38 | `ESPN4.co@Direct181` |
| 36 | Deportes | Win+ Fútbol | 39 | `WinPlusFutbol.co@Direct181` |
| 37 | Deportes | ESPN 7 | 40 | `ESPN7.co@Direct181` |
| 38 | Deportes | ESPN 7 (fila directa adicional) | 41 | `PublicDirect.ac1fca2303c88b6a69359958` |
| 39 | Deportes | Red Bull TV World | 56 | `RedBullWorldEnglish.int` |
| 40 | Deportes | Red Bull TV Español | 57 | `RedBullChileEspanol.cl` |
| 41 | Música y conciertos | XITE Hits | 42 | `XITEHits.nl@Germany` |
| 42 | Música y conciertos | XITE Nuevo Latino | 43 | `XITENuevoLatino.us` |
| 43 | Música y conciertos | XITE Siempre Latino | 44 | `XITESiempreLatino.us` |
| 44 | Música y conciertos | XITE 80s Flashback | 45 | `XITE80sFlashback.us` |
| 45 | Música y conciertos | XITE 90s Throwback | 46 | `XITE90sThrowback.us` |
| 46 | Música y conciertos | XITE Rock x Metal | 47 | `XITERockxMetal.nl` |
| 47 | Música y conciertos | XITE Just Chill | 48 | `XITEJustChill.nl` |
| 48 | Música y conciertos | Telehit (fila Telehit MD2) | 49 | `PublicDirect.12addda8ba8591c579cdebfa` |
| 49 | Música y conciertos | Telehit Música | 50 | `TelehitMusica.mx@SD` |
| 50 | Música y conciertos | M1 | 51 | `M1.ua@SD` |
| 51 | Música y conciertos | M2 | 52 | `M2.ua@SD` |
| 52 | Música y conciertos | Qello Concerts by Stingray | 53 | `QelloConcertsbyStingray.ca` |
| 53 | Música y conciertos | Stingray Classica | 54 | `StingrayClassica.ca` |
| 54 | Música y conciertos | RWND | 13 | `RewindTV.cl@SD` |
| 55 | Cine | Sony Movies (fila Sony Movie MD1) | 65 | `PublicDirect.376c74e4d0452f743fd2c811` |
| 56 | Cine | Studio Universal | 66 | `PublicDirect.8b604de41196cd4fe991d551` |
| 57 | Series y ficción | AXN (fila AXN MD2) | 61 | `PublicDirect.a247897d9a490d19fa633661` |
| 58 | Series y ficción | Sony Channel (fila Sony Channel MD1) | 64 | `PublicDirect.9c28a0d10a09856e98930cdc` |
| 59 | Series y ficción | Universal | 67 | `PublicDirect.bf407e29eec656d628dfa2d7` |
| 60 | Series y ficción | USA | 68 | `PublicDirect.1701b6c4abbcc431fb481536` |
| 61 | Infantil y familiar | NTV | 10 | `45` |
| 62 | Documentales, cultura, historia y naturaleza | 13 Cultura | 12 | `13Cultura.cl@DPS` |
| 63 | Documentales, cultura, historia y naturaleza | Autentic History | 58 | `AutenticHistory.de` |
| 64 | Documentales, cultura, historia y naturaleza | Real Wild | 59 | `RealWild.us` |
| 65 | Documentales, cultura, historia y naturaleza | History Channel 1 (fila History MD1) | 63 | `PublicDirect.8da65ba545fa9fd2512f9901` |
| 66 | Documentales, cultura, historia y naturaleza | History Channel 2 | 62 | `PublicDirect.39057ce89326a34e33998e2e` |
| 67 | Entretenimiento, reality y humor | TVN3 | 11 | `1437` |
| 68 | Anime y cultura gamer | ETC TV | 60 | `PublicDirect.3ba5922c6040fadb816835b1` |

## Lectura de la propuesta

- **Noticias internacionales (10–17)** y **internacional (18)** son subbloques consecutivos para mantener juntas las señales del exterior sin clasificar TVE Internacional como canal de noticias.
- **Deportes (19–40)** conserva el orden interno actual de los veinte canales deportivos; agrega Red Bull World y Red Bull Español al final del bloque, por su orientación a deportes y eventos.
- **Música y conciertos (41–54)** conserva el orden interno de los trece canales musicales actuales y coloca RWND en el cierre del bloque, conforme a la corrección del usuario.
- Se conservan los doce encabezados acordados. **Estilo de vida, cocina y hogar** queda vacío porque no hay una señal visible de Lista 1 que encaje claramente; no se fuerza una asignación.
- Los casos potencialmente mixtos (TVE Internacional, TVN3, AXN, Sony Channel, Universal y USA) quedan como propuesta editorial por formato predominante, no como afirmación de exclusividad temática.

## Para aplicar en una tarea posterior

Antes de cambiar el catálogo, volver a leer `AGENTS.md`, `ESTADO.md` y `REGLAS.md`; comprobar que cada ID siga activo y que las relaciones de respaldo no cambien; revisar el orden visible actual desde el layout remoto más reciente; y aplicar el cambio desde el editor o con las validaciones del repositorio. Si cambia cualquier fila o posición desde ahora, actualizar esta propuesta y documentar la aplicación real en `ESTADO.md`. Cualquier publicación debe seguir las pruebas, revisión del diff y verificación del SHA remoto.
