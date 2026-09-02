# Arkitektur

`app.main` starter Uvicorn-webserveren og den asyncio-baserede TCP-modtager i
samme task group. TCP-modtageren accepterer newline-afgraensede JSON-events fra
simulatoren og sender dem gennem `DuplicateAggregator` til
`TagReadRepository`.

Repositoryet normaliserer EPC, opdaterer reader-status og gemmer eller
aggregerer reads i PostgreSQL. Ved databasefejl skriver `EventBuffer` eventet
til `/var/lib/zebra-rfid-server/pending-tag-reads.jsonl`; bufferen afspilles ved
næste opstart.

`app.api` leverer REST API og Jinja2-dashboardet. API'et bruger Argon2id
password-hashes og JWT bearer-tokens. Nye receiver-protokoller implementeres
som adaptere under `app.adapters`.