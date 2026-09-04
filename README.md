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

## Registreringer

Efter login viser knappen `Registreringer` de seneste 100 tag-registreringer
med alle tilgængelige datafelter. Søgning på SSCC-løbenummer finder både hele
og delvise løbenumre. Kolonnerne starter med bredde efter indholdet; ved behov
kan tabellen scrolles vandret. Kolonnebredden kan justeres ved at trække i
højre kant af kolonneoverskriften og gemmes lokalt i browseren.

## Intern HTTPS

Installationen konfigurerer automatisk Caddy som HTTPS-proxy på serverens
primære LAN-IP. Brug derfor eksempelvis `https://192.168.1.151/lookup` uden
portnummer. Caddys interne CA-rodcertifikat er gyldigt i cirka 10 år og kopieres
til `/var/lib/zebra-rfid-server/caddy-root.crt`. Installer dette certifikat som
betroet CA-certifikat på Android-enheder, før kamera-scanning bruges. Caddy
fornyer automatisk de korterevarende servercertifikater; rodcertifikatet skal
derfor normalt kun installeres én gang på hver enhed.

## Offentlig læservisning

Hver oprettet læser har en offentlig passagetællerside på
`http://server-ip:8080/{læsernavn}`. Eksempelvis åbnes læseren `Port1` på
`http://server-ip:8080/Port1`. Siden kræver ikke login og viser kun læsernavn,
antal unikke tags og SSCC-løbenumre. Data opdateres automatisk hvert 30.
sekund. Læsernavne med mellemrum skal URL-enkodes, eksempelvis `Port%201`.

## Offentligt SSCC-opslag

`http://server-ip:8080/lookup` er en loginfri, mobilvenlig side til opslag på
SSCC-løbenummer. Den viser læsernavn og tidspunktet for seneste registrering.
På understøttede mobilbrowsere kan kameraet åbnes for scanning af stregkoder;
manuelt indtastet løbenummer, delvist løbenummer og fuld SSCC accepteres.

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

### Zebra FX9600

1. Giv FX9600 en fast IPv4-adresse på samme netværk som serveren, og åbn
	readerens webinterface på `http://<reader-ip>`.

2. I readerens RFID-/LLRP-konfiguration aktiveres LLRP, inventory/ROSpec og
	`RO_ACCESS_REPORT` på TCP-port 5084. Vælg de antenneporte og RFID-region,
	der passer til installationen. Gem og anvend konfigurationen. De præcise
	menunavne afhænger af firmwareversionen.

3. Opret readeren i Zebra RFID Server-portalen med model `FX9600`, dens
	IP-adresse og de kendte identifikationsoplysninger. Noter readerens
	numeriske id fra `GET /api/v1/readers` eller Swagger.

4. Tilføj id'et til `/etc/zebra-rfid-server/server.env` og genstart:

	```bash
	sudoedit /etc/zebra-rfid-server/server.env
	# Eksempel: LLRP_READER_IDS=1
	sudo systemctl restart zebra-rfid-server
	```

5. Bekræft forbindelse og tag-reads med:

	```bash
	sudo journalctl -u zebra-rfid-server -f
	```

Hvis FX9600 ikke sender reads, kontroller LLRP-port, netværksadgang mellem
server og reader, valgt RFID-region, aktive antenner og inventory/ROSpec i
readerens webinterface.

## Konfiguration

Kopier `.env.example` til den fremtidige produktionsplacering
`/etc/zebra-rfid-server/server.env`, og angiv mindst `DB_PASSWORD` og
`JWT_SECRET`. Hemmeligheder maa aldrig committes.

## Linux drift

### Hurtig installation

1. Log ind på en Ubuntu/Debian-server med internetadgang og en bruger med
	`sudo`-rettigheder.

2. Hent den aktuelle `main`-kilde fra GitHub:

	```bash
	source_dir=$(mktemp -d)
	curl -fsSL https://github.com/PCgoDK/zebra-rfid-server/archive/refs/heads/main.tar.gz | tar -xz -C "$source_dir" --strip-components=1
	```

3. Start installationen. Indtast sudo-adgangskoden og vælg derefter en ny
	administratoradgangskode på mindst 12 tegn, når du bliver spurgt:

	```bash
	sudo bash "$source_dir/install.sh"
	rm -rf "$source_dir"
	```

4. Kontroller at tjenesten og API'et kører:

	```bash
	sudo systemctl status zebra-rfid-server
	curl http://127.0.0.1:8080/api/v1/health
	```

5. Åbn `http://server-ip:8080` i browseren, log ind som `admin`, og fjern
	derefter den midlertidige klartekst-adgangskode som beskrevet under
	[Administratoradgangskode](#administratoradgangskode).

Installer direkte fra GitHub til `/opt/zebra-rfid-server`:

```bash
source_dir=$(mktemp -d)
curl -fsSL https://github.com/PCgoDK/zebra-rfid-server/archive/refs/heads/main.tar.gz | tar -xz -C "$source_dir" --strip-components=1
sudo bash "$source_dir/install.sh"
rm -rf "$source_dir"
```

Kommandoerne henter den aktuelle `main`-kilde som et offentligt GitHub-arkiv,
pakker den ud midlertidigt og installerer programmet i
`/opt/zebra-rfid-server`. Metoden kræver ikke Git-kloning eller GitHub-login.
Installationen opretter UFW-regler for `8080/tcp` (web/API) og `5084/tcp`
(RFID-input). Scriptet aktiverer ikke UFW automatisk. Hvis UFW allerede er
aktiv, gælder reglerne straks; ellers aktiveres den bevidst af driftsansvarlig
efter SSH-adgang er verificeret. En ny interaktiv installation spørger efter
administratoradgangskoden og kræver mindst 12 tegn. For en ikke-interaktiv
installation angives den som `INITIAL_ADMIN_PASSWORD`.

### Administratoradgangskode

Ved første installation gemmes den indtastede administratoradgangskode
midlertidigt som klartekst i
`/etc/zebra-rfid-server/server.env` under `INITIAL_ADMIN_PASSWORD`. Efter
første vellykkede login skal klartekstværdien fjernes:

```bash
sudo sed -i '/^INITIAL_ADMIN_PASSWORD=/d' /etc/zebra-rfid-server/server.env
```

Administratorens adgangskode er allerede gemt som en Argon2-hash i
PostgreSQL-tabellen `api_users`; fjernelse af klartekstværdien påvirker ikke
login. Angiv kun `INITIAL_ADMIN_PASSWORD` igen, hvis administratoradgangskoden
bevidst skal nulstilles under en opgradering.

Installer eller opgrader fra en komplet lokal kildekopi:

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

## Total nulstilling

Følgende fjerner permanent program, konfiguration, RFID-data, backups,
PostgreSQL-database, databasebruger og Linux-servicebruger. Tag først en backup
med `sudo bash backup.sh`, hvis data skal kunne gendannes.

```bash
sudo bash uninstall.sh
sudo rm -rf /etc/zebra-rfid-server /var/lib/zebra-rfid-server /var/log/zebra-rfid-server
sudo -u postgres dropdb --if-exists zebra_rfid_server
sudo -u postgres dropuser --if-exists zebra_rfid_server
sudo userdel zebra-rfid-server 2>/dev/null || true
sudo groupdel zebra-rfid-server 2>/dev/null || true
```

Fjern kun følgende UFW-regler, hvis portene ikke anvendes af andre tjenester:

```bash
sudo ufw delete allow 8080/tcp
sudo ufw delete allow 5084/tcp
```

Installer derefter fra GitHub igen. Da `server.env` er væk, spørger
installationen efter en ny administratoradgangskode.
