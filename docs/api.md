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
Tag reads kan filtreres på `epc_hex`, `epc_decimal`, `reader_id`, `antenna` og
modtagelsestidspunkt.