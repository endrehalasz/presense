# Források és licencek – Gravel Bad Reichenhall

Generálva: 2026-10-03. Minden adatot a `tools/` mappa szkriptjei töltöttek le és dolgoztak fel; kézi adatbevitel nem volt.

## Összefoglaló

- **23 útvonal**, ebből **0 valódi forrás-GPX** és **23 generált nyomvonal**.
- Mindegyik nyomvonal valódi, utakat követő track: egy saját gravel-útvonaltervező (`tools/router.py`) számolta az OpenStreetMap úthálózatán (Overture Maps), a leírásban szereplő fő útpontokon át. Egyenesekkel összekötött pont nincs.
- Mindegyik útvonal és GPX-fájl **„generált nyomvonal”** címkét kapott (a weboldalon, a GPX `<desc>` mezőjében és a KML-ben is).

## Miért nincs valódi forrás-GPX?

A munkakörnyezet hálózati szabályzata (egress proxy) csak néhány hostot engedett. Az alábbiak mind **HTTP 403 / „egress blocked”** választ adtak, így nem lehetett letölteni róluk:

| Forrás | Host | Eredmény |
|---|---|---|
| WOSSA ZIP-ek (Etappe1, gesamt) | thomaskargl.at | tiltva |
| komoot API és guide-oldalak | www.komoot.com | tiltva (WebFetch-csel is) |
| bergfex, outdooractive, gps-tour.info | bergfex.at stb. | tiltva |
| BRouter nyilvános API | brouter.de | tiltva |
| Overpass API (OSM surface/tracktype) | overpass-api.de | tiltva |
| OpenTopoData / Open-Elevation | api.opentopodata.org | tiltva |
| Wikimedia Commons API | commons.wikimedia.org | tiltva (build-időben) |
| Térképcsempék | tile.openstreetmap.org stb. | tiltva (build-időben) |

Elérhető volt viszont az **AWS S3** – így a nyílt adatokat innen szereztem be:

## Felhasznált adatok

| Adat | Forrás | Licenc |
|---|---|---|
| Úthálózat, úttípus, burkolat (`road_surface`), kerékpáros hozzáférés | Overture Maps Foundation, `release/2026-09-23.1`, `theme=transportation/type=segment` (s3://overturemaps-us-west-2) – OpenStreetMap-alapú | ODbL 1.0, © OpenStreetMap-közreműködők |
| Tavak, folyók (offline alaptérkép) | Overture `theme=base/type=water` | ODbL 1.0 |
| Parkolók, kilátópontok | Overture `theme=base/type=infrastructure` | ODbL 1.0 |
| Állomások, kunyhók, POI-k (útpontok ellenőrzése) | Overture `theme=places/type=place` | CDLA-Permissive-2.0 / ODbL (forrásonként) |
| Domborzat (magasság, szint, offline domborzatárnyékolás) | SRTM 1″ (≈30 m) – AWS Terrain Tiles, `elevation-tiles-prod/skadi` | közkincs (NASA/USGS) |
| Térképmegjelenítés | Leaflet 1.9.4 (npm) – `lib/leaflet/` | BSD-2-Clause |
| Fotók | Wikimedia Commons API – **futásidőben**, a böngészőben töltődnek be szerzővel és licenccel | képenként (CC-BY, CC-BY-SA, PD …) |
| Online térképrétegek | OpenStreetMap, OpenTopoMap, CyclOSM, Esri World Imagery | a rétegeken feltüntetett feltételekkel |

A GPX- és KML-fájlok az OSM-adatbázisból származtatott művek: **ODbL 1.0**, forrásmegjelölés: „© OpenStreetMap contributors (via Overture Maps)”.

## Útvonalanként

| Fájl | Útvonal | Táv / szint | Típus | Ihlet / útpont-forrás | Licenc |
|---|---|---|---|---|---|
| `gpx/thumsee-listsee.gpx` | Thumsee–Listsee bemelegítő | 19.6 km / 465 m | generált | saját kreatív útvonal | ODbL (© OSM-közreműködők) |
| `gpx/frillensee-falkensee.gpx` | Frillensee–Falkensee–Listsee | 52.9 km / 1305 m | generált | komoot túra [30929451](https://www.komoot.com/tour/30929451) (40 km) | ODbL (© OSM-közreműködők) |
| `gpx/stoisser-alm.gpx` | Stoißer Alm–Frillensee | 55.1 km / 1435 m | generált | komoot túra [1120085034](https://www.komoot.com/tour/1120085034) (55 km) | ODbL (© OSM-közreműködők) |
| `gpx/untersberg-menten.gpx` | Untersberg mentén Salzburg kapujáig | 40.1 km / 357 m | generált | komoot túra [1109509177](https://www.komoot.com/tour/1109509177) (50 km) | ODbL (© OSM-közreműködők) |
| `gpx/teisendorf.gpx` | Rupertiwinkel – Höglwörth és Teisendorf | 52.4 km / 763 m | generált | komoot túra [1037421873](https://www.komoot.com/tour/1037421873) (59 km) | ODbL (© OSM-közreműködők) |
| `gpx/staufen-kor.gpx` | Hochstaufen-kör | 56.8 km / 1164 m | generált | komoot túra [1053575264](https://www.komoot.com/tour/1053575264) (69 km) | ODbL (© OSM-közreműködők) |
| `gpx/aschauer-klamm-lofer.gpx` | Aschauer Klamm–Lofer | 75.7 km / 1514 m | generált | komoot túra [1175420631](https://www.komoot.com/tour/1175420631) (100 km) | ODbL (© OSM-közreműködők) |
| `gpx/hoegl.gpx` | Högl-dombhát | 30.9 km / 636 m | generált | komoot túra [1120085549](https://www.komoot.com/tour/1120085549) (28 km) | ODbL (© OSM-közreműködők) |
| `gpx/untersberg-kor.gpx` | Untersberg-kör | 54.8 km / 864 m | generált | komoot túra [1035527445](https://www.komoot.com/tour/1035527445) (59 km) + bergfex [2307368](https://www.bergfex.at/sommer/salzburg/touren/mountainbike/2307368/) | ODbL (© OSM-közreműködők) |
| `gpx/hintersee-strubklamm.gpx` | Wiestal–Strubklamm–Hintersee (Flachgau) | 56.7 km / 1481 m | generált | komoot túra [1223393682](https://www.komoot.com/tour/1223393682) (58 km) | ODbL (© OSM-közreműködők) |
| `gpx/haunsberg.gpx` | Haunsberg és a Salzach | 47.2 km / 451 m | generált | komoot túra [1033799113](https://www.komoot.com/tour/1033799113) (39 km) | ODbL (© OSM-közreműködők) |
| `gpx/alte-postalmstrasse.gpx` | Alte Postalmstraße – vonattal Gollingig | 84.7 km / 2404 m | generált | komoot túra [1229213372](https://www.komoot.com/tour/1229213372) (130 km) | ODbL (© OSM-közreműködők) |
| `gpx/hirschbichl-lofer.gpx` | Hirschbichl-hágó–Lofer nagy kör | 84.8 km / 1723 m | generált | komoot túra [1431200842](https://www.komoot.com/tour/1431200842) (134 km) | ODbL (© OSM-közreműködők) |
| `gpx/saalach-mussbach.gpx` | Saalach–Mußbach kör | 36.3 km / 615 m | generált | komoot guide: „Gravelbiken rund um Bad Reichenhall” | ODbL (© OSM-közreműködők) |
| `gpx/mordaualm.gpx` | Schwarzbachwacht–Mordaualm | 54.1 km / 1587 m | generált | komoot guide: „Gravelbiken rund um Bad Reichenhall” | ODbL (© OSM-közreműködők) |
| `gpx/watzmann-koenigssee.gpx` | Watzmann–Königssee kör | 30.6 km / 888 m | generált | komoot guide: „Gravelbiken around Thumsee” | ODbL (© OSM-közreműködők) |
| `gpx/roethelmoos-weitsee.gpx` | Röthelmoos–Weitsee tóvidék | 61.0 km / 1029 m | generált | komoot guide: „Gravelbiken around Thumsee” | ODbL (© OSM-közreműködők) |
| `gpx/rossfeld.gpx` | Rossfeld-panorámaút – vonattal oda, bringával haza | 54.7 km / 1395 m | generált | saját kreatív útvonal | ODbL (© OSM-közreműködők) |
| `gpx/loferer-alm.gpx` | Loferer Alm és a Vorderkaserklamm | 36.4 km / 967 m | generált | komoot guide: „Gravelbiken around Thumsee” | ODbL (© OSM-közreműködők) |
| `gpx/soleleitung-traunstein.gpx` | A sólé útja – 400 éves sóvezeték Traunsteinig | 43.9 km / 874 m | generált | saját kreatív útvonal | ODbL (© OSM-közreműködők) |
| `gpx/salzburg-haza.gpx` | Vonattal Salzburgba, bringával haza (WOSSA 1 ihlette) | 32.2 km / 318 m | generált | WOSSA Etappe 1 (thomaskargl.at) – ihlet | ODbL (© OSM-közreműködők) |
| `gpx/salzach-laufen.gpx` | Salzach-ártér–Abtsdorfer See–Laufen | 46.7 km / 230 m | generált | saját kreatív útvonal | ODbL (© OSM-közreműködők) |
| `gpx/waginger-see.gpx` | Waginger See és Tachinger See | 102.9 km / 736 m | generált | saját kreatív útvonal | ODbL (© OSM-közreműködők) |

## Feldolgozás (tools/)

1. `fetch_overture.py` – Overture parquet-fájlok letöltése a bbox-ra (12,40–13,45 K, 47,45–47,98 É), sorcsoport-statisztika alapú szűréssel.
2. `build_graph.py` – az OSM-szegmensek csomópontoknál feldarabolva, egybeeső végpontok összevonva; gravel-költség: kerékpárral tiltott utak kizárva, murvás erdei út / kerékpárút kedvezményes, főút és ösvény büntetett, emelkedés-büntetés (SRTM).
3. `routes_def.py` – útpontok, leírások, értékelések, indulási módok, októberi figyelmeztetések (Overture-névjegyzékkel ellenőrzött koordináták).
4. `process.py` – útvonaltervezés (Dijkstra), 20 m-es újramintavételezés, SRTM-magasság, 200 m-es simítás, szint 4 m-es küszöbbel, leghosszabb emelkedő (≤15 m visszaeséssel), legmeredekebb 500 m, burkolat-megoszlás, Douglas–Peucker 10 m, GPX/KML/`data.js` export.
5. `basemap.py` – offline domborzatárnyékolás (Web Mercator) + vektorrétegek (`basemap.js`).

Burkolat-kategóriák: *aszfalt* = paved/paving_stones; *kemény murva* = gravel, ill. burkolatlan erdészeti/mező út (`track`/`service`/`unclassified` + unpaved vagy ismeretlen); *laza murva / erdei* = dirt/ground; *ösvény* = path/footway/bridleway burkolat nélkül. Az OSM-ben ismeretlen burkolatú `track` utakat kemény murvának becsültük.

Újragenerálás: a munkakönyvtárban (ahol a parquet-fájlok és a `graph.pkl` vannak) `DEM_DIR=<hgt mappa> GRAPH=graph.pkl python3 tools/process.py <gravel mappa>`.
