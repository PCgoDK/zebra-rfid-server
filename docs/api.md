# API

API'et findes under `/api/v1`; OpenAPI findes på `/docs` når tjenesten kører.

Hent token:

```bash
curl -X POST http://server-ip:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"adgangskode"}'
```

Send token som `Authorization: Bearer <token>`. `GET /health` er offentlig.
Reader- og tag-read-endpoints understøtter pagination med `offset` og `limit`.
Tag reads kan filtreres på `epc_hex`, `reader_id`, `antenna` og
modtagelsestidspunkt.

Læsere kan konfigureres med `epc_schemes`, en liste over GS1 EPC-schemes der
må gemmes. En tom liste afviser alle EPC'er; udeladt værdi bevarer ufiltreret
lagring for eksisterende læsere.

## SSCC-opslag

SSCC-løbenummeret er serial reference uden extension-ciffer, GS1 company prefix
og GS1-checkciffer. URL'en kan indeholde hele løbenummeret eller kun de sidste
cifre; eksempelvis finder `000010` også `000000010`.

- `GET /api/v1/sscc/{serial}/latest` returnerer den seneste registrering.
- `GET /api/v1/sscc/{serial}/history?offset=0&limit=100` returnerer registreringshistorik
  i faldende tidsorden.