# zebra-rfid-server

Produktionsklar Linux-tjeneste til at modtage RFID-data fra Zebra FX7500- og
FX9600-laesere, gemme dem i PostgreSQL samt eksponere REST API og
administrationsportal.

## Udvikling

Kraever Python 3.11 eller nyere.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest
```

Systemet har Alembic-migrationer, EPC-normalisering, asyncio TCP-modtager,
dubletaggregering, REST API, tokenbaseret adgangskontrol og webportal.

Start TCP-modtageren under udvikling:

```bash
python -m app.main
```

Statussiden findes derefter paa `http://localhost:8080`, og health check er
`http://localhost:8080/api/v1/health`. Brug `API_PORT=8088` i `.env` hvis port
8088 oenskes.

Send fragmenterede testevents fra to simulerede laesere:

```bash
python tools/rfid_reader_simulator.py --readers 2 --events 10 --fragment --duplicates 1 --disconnect-every 5
```

## Reader discovery

Discovery understøtter read-only LLRP-kontroller paa port 5084 og valideret manuel
IPv4-adresse. En fundet LLRP-port markeres `connected_without_data`; model,
firmware og serienummer udfyldes først, naar den verificerede Zebra-protokol er
tilgængelig fra en fysisk laeser.

Yderligere dokumentation findes i `docs/`.

## Konfiguration af RFID-laeser

Serveren lytter paa `TCP_HOST:TCP_PORT` (som standard `0.0.0.0:5084`). Giv
laeseren en fast IPv4-adresse og tillad TCP-trafik fra laeserens netvaerk til
serverens port 5084. Opret derefter laeseren manuelt i portalen med dens
IP-adresse, model og serienummer, eller brug `POST /api/v1/readers`.

Den aktuelle modtager forventer TCP-events som UTF-8, newline-afgraenset JSON:

```json
{"reader_id":1,"epc_hex":"31D55BE6800002156C000000","antenna":1,"rssi":-45.2,"phase":12.5,"channel":1}
```

`reader_id` og `epc_hex` er paakraevet. `antenna`, `rssi`, `phase` og
`channel` er valgfrie. ST5500 kan desuden sende `direction`, `zone` og
`location`; FXR90 kan sende `gps_latitude`, `gps_longitude`, `gps_altitude`,
`gps_accuracy` og ISO 8601 `gps_timestamp`.

FX7500, FX9600, FXR90 og ST5500 skal ikke konfigureres til denne JSON-strøm
direkte. For native LLRP konfigureres readerens LLRP-tjeneste på port 5084 og
readerens IP-adresse registreres i portalen. Sæt derefter den pågældende
database-readers numeriske id i `LLRP_READER_IDS` i
`/etc/zebra-rfid-server/server.env` og genstart tjenesten:

```bash
sudoedit /etc/zebra-rfid-server/server.env
# Eksempel: LLRP_READER_IDS=1,3
sudo systemctl restart zebra-rfid-server
```

For hver angivet reader opretter serveren en udgående LLRP-forbindelse til
`reader.ip_address:LLRP_PORT` (standard 5084), modtager `RO_ACCESS_REPORT`,
besvarer `KEEPALIVE` og genforbinder ved forbindelsestab. Valider altid den
konkrete reader- og firmwarekonfiguration på fysisk hardware. Brug
`tools/rfid_reader_simulator.py` til at verificere JSON TCP-modtageren.

## Konfiguration

Kopier `.env.example` til den fremtidige produktionsplacering
`/etc/zebra-rfid-server/server.env`, og angiv mindst `DB_PASSWORD` og
`JWT_SECRET`. Hemmeligheder maa aldrig committes.

## Linux drift

Installer eller opgrader fra en komplet kildekopi paa Linux:

```bash
sudo env INITIAL_ADMIN_PASSWORD='vaelg-en-lang-adgangskode' bash install.sh
sudo bash update.sh
```

`INITIAL_ADMIN_PASSWORD` skal mindst vaere 12 tegn. Ved en opgradering nulstiller
den kun administratoradgangskoden, naar parameteren angives eksplicit.

Tjenesten kører som `zebra-rfid-server` og administreres med:

```bash
sudo systemctl status zebra-rfid-server
sudo systemctl restart zebra-rfid-server
```

Opret en PostgreSQL-backup og gendan den ved behov. Restore erstatter data i
`zebra_rfid_server` med den valgte backup og stopper tjenesten imens.

```bash
sudo bash backup.sh
sudo bash restore.sh /var/lib/zebra-rfid-server/backups/zebra-rfid-server-YYYYMMDD-HHMMSS.dump
```

Afinstallation fjerner programmet og systemd-enheden, men bevarer bevidst
PostgreSQL-databasen, konfiguration, logs og modtagne data:

```bash
sudo bash uninstall.sh
```
