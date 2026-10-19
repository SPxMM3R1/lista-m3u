# Sondeo de Lista 2 ? canales con error (2026-10-19)

M?todo: se probaron las **1.364 filas con URL http(s)** de `m3u-externa.m3u` con ffmpeg (decodificaci?n real de 1 frame de video, `-rw_timeout 15s`), desde GitHub Actions (EE. UU.) con **12 hilos ? 4 shards**, dos pasadas (25 s y 40 s de margen). Los que fallaban se **reintentaron** y adem?s se **confirmaron desde Chile**. Las 36 filas tokenless (Nauta/M6Foot) no son probables con ffmpeg: las resuelve la app en RAM.

Resultado: **1.281 se ven** a la primera ? **4 intermitentes** ? **76 no responden** (58 directos + 18 TvVoo) ? 3 fallan solo desde EE. UU. (desde Chile se ven).

## A) Canales directos que no se ven (fallan desde EE. UU. y desde Chile) ? 58

| # | Canal | tvg-id | Error |
|---|-------|--------|-------|
| 1 | A&E | `PublicDirect.c7d2821fd611bc19eb658d46` | timeout |
| 2 | AMC | `PublicDirect.caeeccc4016b022a977f2d3a` | timeout |
| 3 | AXN | `PublicDirect.454f9076602a3e160d0b9fca` | timeout |
| 4 | Cinecanal | `PublicDirect.f0c4c00299f651ac9f9567c8` | conexion rechazada |
| 5 | COMEDY CENTRAL | `PublicDirect.3299f4e8b54dcbf597e993bb` | timeout |
| 6 | D-SPORT 2 | `PublicDirect.898eaca82f9d45a4f27a0d6e` | 404 ruta inexistente |
| 7 | De Pelicula | `PublicDirect.755fa3f4e7cca33ce733d6cd` | conexion rechazada |
| 8 | Discovery Channel | `PublicDirect.29579f7a2b199b4ea7c5d654` | 404 ruta inexistente |
| 9 | Discovery ID | `PublicDirect.15d0614508ab09e277078868` | 404 ruta inexistente |
| 10 | DISCOVERY SCIENCE | `PublicDirect.2c3fb032b0c9fcac367709f2` | 404 ruta inexistente |
| 11 | Discovery World | `PublicDirect.e075e6bb892667f2a50ed1cd` | 404 ruta inexistente |
| 12 | Distrito Comedia | `PublicDirect.8e6a260099dca431a0b2d3b0` | timeout |
| 13 | Distrito Comedia | `PublicDirect.3d088f9826f5ae90ba65bf61` | conexion rechazada |
| 14 | Dreamworks | `PublicDirect.60d69f519b633bd3b7bf77de` | timeout |
| 15 | Dreamworks | `PublicDirect.74f485ecd00e788ab77f85aa` | 404 ruta inexistente |
| 16 | DW | `PublicDirect.05376c52d75436afff56a4e2` | timeout |
| 17 | E! | `PublicDirect.e063df5b792e02956b83b942` | timeout |
| 18 | ESPN | `PublicDirect.3ad687bd5ded851f66f2535e` | 404 ruta inexistente |
| 19 | ESPN | `PublicDirect.cdcec77a8a160a7079f8f773` | 404 ruta inexistente |
| 20 | ESPN 1 | `PublicDirect.3203195c3727b87c5c19dec8` | 404 ruta inexistente |
| 21 | ESPN 2 | `PublicDirect.0582fb453d77a1c7253c2c25` | 404 ruta inexistente |
| 22 | ESPN 2 | `PublicDirect.b7393faf6d1e51e911220ee8` | 404 ruta inexistente |
| 23 | ESPN 3 | `PublicDirect.708b81d3f7ef86fb303af52f` | 404 ruta inexistente |
| 24 | ESPN 4 | `PublicDirect.54a0e2628bd72606025da8fe` | 404 ruta inexistente |
| 25 | ESPN 5 | `PublicDirect.8375c1a7b00975bcb735e988` | 404 ruta inexistente |
| 26 | ESPN 6 | `PublicDirect.9aa0b9d0d8c630b2d55fc4e2` | 404 ruta inexistente |
| 27 | ESTUDIO UNIVERSAL | `PublicDirect.2c807843dbf37dd0d6eed3ea` | timeout |
| 28 | Europa Europa | `PublicDirect.137593c9fc72e788f73cb940` | timeout |
| 29 | Film & Arts | `PublicDirect.b5c36c621e4b3a3593056b55` | timeout |
| 30 | FOX | `PublicDirect.e1ae633c570d77e93daccb64` | timeout |
| 31 | Fox Deportes | `FoxDeportes.us@Direct23` | timeout |
| 32 | FOX SPORTS 3 | `PublicDirect.e6f02bee7b06467fcc30fc1b` | 404 ruta inexistente |
| 33 | FX | `PublicDirect.dc70423e7d1e03b88b44278c` | conexion rechazada |
| 34 | GOLDEN | `PublicDirect.ecc53f0d42941a2a9266a7e9` | timeout |
| 35 | Golden Edge | `PublicDirect.6bd78da2d3dbc61fbd3aa141` | timeout |
| 36 | Gourment | `PublicDirect.9008460b771a974734c0155b` | timeout |
| 37 | HISTORY CHANNEL | `PublicDirect.da98ca63747a3429dd17f069` | timeout |
| 38 | HISTORY CHANNEL 2 | `PublicDirect.be91f456ee096725d0c0e241` | timeout |
| 39 | LIFETIME | `PublicDirect.2825c7ecdabfa5cbd36dc05a` | timeout |
| 40 | MAS CHIC | `PublicDirect.a3df1ae3bfee1c0ad93dddc9` | timeout |
| 41 | Mega Tv | `PublicDirect.78344a6a388ee1f6e17a83a1` | 404 ruta inexistente |
| 42 | Nat Geo | `PublicDirect.9291a66c6b4f5dc010a88543` | 404 ruta inexistente |
| 43 | National Geographic | `PublicDirect.4529dd3aca5070916ed30ec3` | conexion rechazada |
| 44 | NICK JR | `PublicDirect.593cedf7a658e33492c56b93` | timeout |
| 45 | Nickelodeon | `PublicDirect.1960408a1873ea5cee7549de` | timeout |
| 46 | Paramount | `PublicDirect.3fc51082881edcad7472f055` | timeout |
| 47 | Playboy | `PublicDirect.e26d9ddedaf9994cd7da29f8` | 404 ruta inexistente |
| 48 | RT | `PublicDirect.dc4520bd02f620e9d4ec6909` | timeout |
| 49 | Sky Sports Racing | `SkySportsRacing.uk` | timeout |
| 50 | SONY | `PublicDirect.1153654c0b0f286690796798` | timeout |
| 51 | SONY MOVIE | `PublicDirect.40e68f3f2bb0280997fb5901` | timeout |
| 52 | TCM | `PublicDirect.795a4ee2bf10284e7a01d5e1` | timeout |
| 53 | TNT Series | `PublicDirect.53f0e57d7bc8b944961dba87` | 404 ruta inexistente |
| 54 | UNIVERSAL CHANNEL | `PublicDirect.97e9bf9a9a03fa708f4c84b1` | timeout |
| 55 | UNIVERSAL CINEMA ESTE | `PublicDirect.0d61b9ae2ef5f374bedaee27` | 404 ruta inexistente |
| 56 | Universal TV | `PublicDirect.2b44cbf7778db3510498c23b` | conexion rechazada |
| 57 | USA | `PublicDirect.a33ea304d22106989425a338` | error 5xx |
| 58 | VH1 | `PublicDirect.7a10c43d2f3fbfa44e9d1ac9` | timeout |

## B) Filas de proveedor TvVoo (el enlace publicado no respondi?; la app las resuelve con su resolutor propio) ? 18

| # | Canal | tvg-id | Error en el enlace publicado |
|---|-------|--------|------------------------------|
| 1 | Eurosport 1 | `Eurosport1.fr@TvVoo` | timeout |
| 2 | Eurosport 1 Italia | `Vavoo.it.EUROSPORT1@TvVoo` | timeout |
| 3 | Eurosport 2 Italia | `Eurosport2.it@TvVoo` | timeout |
| 4 | Eurosport 4 Polonia | `Vavoo.pl.EUROSPORT4@TvVoo` | timeout |
| 5 | Eurosport 4 TIMVISION Italia | `Vavoo.it.EUROSPORT4TIMVISION@TvVoo` | timeout |
| 6 | Fox Sports 1 Países Bajos | `Vavoo.nl.FOXSPORTS1@TvVoo` | servidor respondio error |
| 7 | FOX Sports 4 Países Bajos | `Vavoo.nl.FOXSPORT4@TvVoo` | servidor respondio error |
| 8 | Sky Sport F1 Italia | `Vavoo.it.SKYSPORTF1@TvVoo` | timeout |
| 9 | Sky Sport Golf Reino Unido | `Vavoo.uk.SKYSPORTGOLF@TvVoo` | timeout |
| 10 | Sky Sport Max Italia | `SkySportMax.it@TvVoo` | timeout |
| 11 | Sky Sport NBA Italia | `SkySportNBA.it@TvVoo` | timeout |
| 12 | Sky Sport Premier League Germany | `SkySportPremierLeague.de@TvVoo` | servidor respondio error |
| 13 | Sky Sport Uno Italia | `SkySportUno.it@TvVoo` | timeout |
| 14 | Sky Sports Arena | `SkySportsArena.uk@TvVoo` | servidor respondio error |
| 15 | Sky Sports Mix | `SkySportsMix.uk@TvVoo` | timeout |
| 16 | Sky Super Tennis Italia | `Vavoo.it.SKYSUPERTENNIS@TvVoo` | timeout |
| 17 | TNT Sports 5 Reino Unido | `Vavoo.uk.TNTSPORTS5@TvVoo` | servidor respondio error |
| 18 | TNT Sports ESPN Reino Unido | `Vavoo.uk.TNTSPORTESPN@TvVoo` | timeout |

## C) Fallan solo desde EE. UU. (se ven desde Chile) ? 3

| Canal | tvg-id | Error desde EE. UU. |
|-------|--------|---------------------|
| History Latin America | `PublicDirect.d46d5979ce0d7046bf22a514` | 403 prohibido |
| Sky Sport 5 Alemania | `Vavoo.de.SKYSPORT5@TvVoo` | timeout |
| Sky Sport 2 Alemania | `Vavoo.de.SKYSPORT2@TvVoo` | timeout |

## D) Intermitentes (fallan a la primera, pasan el reintento) ? 4

- GOLDEN PREMIER
- Universal
- Sky Sport Golf Italia
- Eurosport 2 UK

## E) Filas tokenless (no probables con ffmpeg; resoluci?n de la app) ? 144

DirecTV Sports (`M6Foot.94@M6Foot`), DirecTV Sports (`M6Foot.94@M6Foot`), DirecTV Sports (`M6Foot.94@M6Foot`), DirecTV Sports (`M6Foot.94@M6Foot`), DirecTV Sports 2 (`M6Foot.95@M6Foot`), DirecTV Sports 2 (`M6Foot.95@M6Foot`), DirecTV Sports 2 (`M6Foot.95@M6Foot`), DirecTV Sports 2 (`M6Foot.95@M6Foot`), DirecTV Sports Plus (`M6Foot.96@M6Foot`), DirecTV Sports Plus (`M6Foot.96@M6Foot`), DirecTV Sports Plus (`M6Foot.96@M6Foot`), DirecTV Sports Plus (`M6Foot.96@M6Foot`), Discovery World (`Nauta.9716fec189bb7b466e1bd9af@Nauta`), Discovery World (`Nauta.9716fec189bb7b466e1bd9af@Nauta`), Discovery World (`Nauta.9716fec189bb7b466e1bd9af@Nauta`), Discovery World (`Nauta.9716fec189bb7b466e1bd9af@Nauta`), ESPN (`Nauta.7437112a4b992980a550d16a@Nauta`), ESPN (`Nauta.7437112a4b992980a550d16a@Nauta`), ESPN (`Nauta.7437112a4b992980a550d16a@Nauta`), ESPN (`Nauta.7437112a4b992980a550d16a@Nauta`), ESPN 1 | Chile (`Nauta.81dc69c20557da0672921475@Nauta`), ESPN 1 | Chile (`Nauta.81dc69c20557da0672921475@Nauta`), ESPN 1 | Chile (`Nauta.81dc69c20557da0672921475@Nauta`), ESPN 1 | Chile (`Nauta.81dc69c20557da0672921475@Nauta`), ESPN 1 | Sur (`Nauta.dac26a78f5bdf111bc9b9ffc@Nauta`), ESPN 1 | Sur (`Nauta.dac26a78f5bdf111bc9b9ffc@Nauta`), ESPN 1 | Sur (`Nauta.dac26a78f5bdf111bc9b9ffc@Nauta`), ESPN 1 | Sur (`Nauta.dac26a78f5bdf111bc9b9ffc@Nauta`), ESPN 2 ARG (`M6Foot.88@M6Foot`), ESPN 2 ARG (`M6Foot.88@M6Foot`), ESPN 2 ARG (`M6Foot.88@M6Foot`), ESPN 2 ARG (`M6Foot.88@M6Foot`), ESPN 3 (`M6Foot.89@M6Foot`), ESPN 3 (`Nauta.ed0ed0370e182f10a4e96f3d@Nauta`), ESPN 3 (`M6Foot.89@M6Foot`), ESPN 3 (`Nauta.ed0ed0370e182f10a4e96f3d@Nauta`), ESPN 3 (`M6Foot.89@M6Foot`), ESPN 3 (`Nauta.ed0ed0370e182f10a4e96f3d@Nauta`), ESPN 3 (`M6Foot.89@M6Foot`), ESPN 3 (`Nauta.ed0ed0370e182f10a4e96f3d@Nauta`), ESPN 4 (`M6Foot.90@M6Foot`), ESPN 4 (`M6Foot.90@M6Foot`), ESPN 4 (`M6Foot.90@M6Foot`), ESPN 4 (`M6Foot.90@M6Foot`), ESPN 4 | Sur (`Nauta.c89a873414ec166795c59f26@Nauta`), ESPN 4 | Sur (`Nauta.c89a873414ec166795c59f26@Nauta`), ESPN 4 | Sur (`Nauta.c89a873414ec166795c59f26@Nauta`), ESPN 4 | Sur (`Nauta.c89a873414ec166795c59f26@Nauta`), ESPN 5 (`M6Foot.91@M6Foot`), ESPN 5 (`M6Foot.91@M6Foot`), ESPN 5 (`M6Foot.91@M6Foot`), ESPN 5 (`M6Foot.91@M6Foot`), ESPN 7 (`Nauta.52bb87a2e2911ed34f7ae3bc@Nauta`), ESPN 7 (`Nauta.52bb87a2e2911ed34f7ae3bc@Nauta`), ESPN 7 (`Nauta.52bb87a2e2911ed34f7ae3bc@Nauta`), ESPN 7 (`Nauta.52bb87a2e2911ed34f7ae3bc@Nauta`), ESPN Plus (`Nauta.53db56d7f89e01787fcc2212@Nauta`), ESPN Plus (`Nauta.53db56d7f89e01787fcc2212@Nauta`), ESPN Plus (`Nauta.53db56d7f89e01787fcc2212@Nauta`), ESPN Plus (`Nauta.53db56d7f89e01787fcc2212@Nauta`), ESPN Premium (`M6Foot.76@M6Foot`), ESPN Premium (`M6Foot.76@M6Foot`), ESPN Premium (`M6Foot.76@M6Foot`), ESPN Premium (`M6Foot.76@M6Foot`), Fox Sport 2 ARG (`M6Foot.79@M6Foot`), Fox Sport 2 ARG (`M6Foot.79@M6Foot`), Fox Sport 2 ARG (`M6Foot.79@M6Foot`), Fox Sport 2 ARG (`M6Foot.79@M6Foot`), Fox Sports (`Nauta.57d13b9b10bcbdc51d4dab10@Nauta`), Fox Sports (`Nauta.57d13b9b10bcbdc51d4dab10@Nauta`), Fox Sports (`Nauta.57d13b9b10bcbdc51d4dab10@Nauta`), Fox Sports (`Nauta.57d13b9b10bcbdc51d4dab10@Nauta`), Fox Sports 3 ARG (`M6Foot.80@M6Foot`), Fox Sports 3 ARG (`M6Foot.80@M6Foot`), Fox Sports 3 ARG (`M6Foot.80@M6Foot`), Fox Sports 3 ARG (`M6Foot.80@M6Foot`), Fox Sports ARG (`M6Foot.78@M6Foot`), Fox Sports ARG (`M6Foot.78@M6Foot`), Fox Sports ARG (`M6Foot.78@M6Foot`), Fox Sports ARG (`M6Foot.78@M6Foot`), HBO (`Nauta.69a2d4671c91e6eb2081468e@Nauta`), HBO (`Nauta.69a2d4671c91e6eb2081468e@Nauta`), HBO (`Nauta.69a2d4671c91e6eb2081468e@Nauta`), HBO (`Nauta.69a2d4671c91e6eb2081468e@Nauta`), HBO 2 (`Nauta.5e0764312e17cd8dbca87fbe@Nauta`), HBO 2 (`Nauta.5e0764312e17cd8dbca87fbe@Nauta`), HBO 2 (`Nauta.5e0764312e17cd8dbca87fbe@Nauta`), HBO 2 (`Nauta.5e0764312e17cd8dbca87fbe@Nauta`), HBO Family (`Nauta.2c79f52754dcec190b01cd93@Nauta`), HBO Family (`Nauta.4cc2aa2f00babf217d641fd6@Nauta`), HBO Family (`Nauta.2c79f52754dcec190b01cd93@Nauta`), HBO Family (`Nauta.4cc2aa2f00babf217d641fd6@Nauta`), HBO Family (`Nauta.2c79f52754dcec190b01cd93@Nauta`), HBO Family (`Nauta.4cc2aa2f00babf217d641fd6@Nauta`), HBO Family (`Nauta.2c79f52754dcec190b01cd93@Nauta`), HBO Family (`Nauta.4cc2aa2f00babf217d641fd6@Nauta`), HBO Mundi (`Nauta.2543531f37454701c960421c@Nauta`), HBO Mundi (`Nauta.2543531f37454701c960421c@Nauta`), HBO Mundi (`Nauta.2543531f37454701c960421c@Nauta`), HBO Mundi (`Nauta.2543531f37454701c960421c@Nauta`), HBO Plus (`Nauta.8c5a91e0b8d25e158a9afa6f@Nauta`), HBO Plus (`Nauta.b5a185bf8235a26035237746@Nauta`), HBO Plus (`Nauta.8c5a91e0b8d25e158a9afa6f@Nauta`), HBO Plus (`Nauta.b5a185bf8235a26035237746@Nauta`), HBO Plus (`Nauta.8c5a91e0b8d25e158a9afa6f@Nauta`), HBO Plus (`Nauta.b5a185bf8235a26035237746@Nauta`), HBO Plus (`Nauta.8c5a91e0b8d25e158a9afa6f@Nauta`), HBO Plus (`Nauta.b5a185bf8235a26035237746@Nauta`), HBO Plus Oeste (`Nauta.b0e158ffa085b177eadaaca6@Nauta`), HBO Plus Oeste (`Nauta.b0e158ffa085b177eadaaca6@Nauta`), HBO Plus Oeste (`Nauta.b0e158ffa085b177eadaaca6@Nauta`), HBO Plus Oeste (`Nauta.b0e158ffa085b177eadaaca6@Nauta`), HBO Pop (`Nauta.14fae38bc645c4c8b6315d89@Nauta`), HBO Pop (`Nauta.14fae38bc645c4c8b6315d89@Nauta`), HBO Pop (`Nauta.14fae38bc645c4c8b6315d89@Nauta`), HBO Pop (`Nauta.14fae38bc645c4c8b6315d89@Nauta`), HBO Xtreme (`Nauta.19ade992e1408ad4cbf1d4d8@Nauta`), HBO Xtreme (`Nauta.5108e1f90fd559d0c4387658@Nauta`), HBO Xtreme (`Nauta.19ade992e1408ad4cbf1d4d8@Nauta`), HBO Xtreme (`Nauta.5108e1f90fd559d0c4387658@Nauta`), HBO Xtreme (`Nauta.19ade992e1408ad4cbf1d4d8@Nauta`), HBO Xtreme (`Nauta.5108e1f90fd559d0c4387658@Nauta`), HBO Xtreme (`Nauta.19ade992e1408ad4cbf1d4d8@Nauta`), HBO Xtreme (`Nauta.5108e1f90fd559d0c4387658@Nauta`), Movistar LaLiga ES (`M6Foot.49@M6Foot`), Movistar LaLiga ES (`M6Foot.49@M6Foot`), Movistar LaLiga ES (`M6Foot.49@M6Foot`), Movistar LaLiga ES (`M6Foot.49@M6Foot`), MTV Live (`Nauta.d6c4cf31e1a88709b605ac8f@Nauta`), MTV Live (`Nauta.d6c4cf31e1a88709b605ac8f@Nauta`), MTV Live (`Nauta.d6c4cf31e1a88709b605ac8f@Nauta`), MTV Live (`Nauta.d6c4cf31e1a88709b605ac8f@Nauta`), Star Channel (`Nauta.a87610ac946968a5f280ec57@Nauta`), Star Channel (`Nauta.a87610ac946968a5f280ec57@Nauta`), Star Channel (`Nauta.a87610ac946968a5f280ec57@Nauta`), Star Channel (`Nauta.a87610ac946968a5f280ec57@Nauta`), Studio Universal (`Nauta.b9df5eea317035bd5bda31cf@Nauta`), Studio Universal (`Nauta.b9df5eea317035bd5bda31cf@Nauta`), Studio Universal (`Nauta.b9df5eea317035bd5bda31cf@Nauta`), Studio Universal (`Nauta.b9df5eea317035bd5bda31cf@Nauta`), TNT Sports Premium (`M6Foot.75@M6Foot`), TNT Sports Premium (`M6Foot.75@M6Foot`), TNT Sports Premium (`M6Foot.75@M6Foot`), TNT Sports Premium (`M6Foot.75@M6Foot`)

Corte: 2026-10-19 ~22:45?23:10 UTC. Evidencia completa en `outputs/lista2-sondeo-20261019/` del chat coordinador (pass1/pass2 por shard, confirmaci?n local).

## Confirmaci?n repetida (2026-10-19 ~23:40 UTC)

Se repiti? el sondeo completo (run 39337752661, mismo m?todo, mismos 1.364 canales). De los 79 ca?dos de la primera corrida, **74 vuelven a fallar** (93,7 % de coincidencia): 57 directos + 17 TvVoo. Volvieron 5 (History Latin America y Sky Sports Racing directos; Eurosport 2 Italia, Sky Sport Max Italia y Sky Sport 5 Alemania de TvVoo) y 4 filas TvVoo nuevas fallaron (Sky Sports Football UK, Sky Sport 6 Alemania, Sky Sport Tennis Italia, Sky Sports Premier League UK). Los directos son los m?s estables: solo 2 de 58 cambiaron de estado.

Evidencia de la repetici?n: `outputs/lista2-sondeo-20261019/repe/` (pass1/pass2 por shard).
