# Database

PostgreSQL-databasen hedder `zebra_rfid_server`, og loginrollen har samme navn.
Skemaet administreres med Alembic; `install.sh` og `update.sh` kører
`alembic upgrade head` uden at slette databasen.

Tabeller: `readers`, `tag_reads`, `api_users`, `application_settings` og
`audit_log`. `tag_reads` har indekser for `epc_hex` og `reader_id, received_at`.

Backup oprettes med `sudo bash backup.sh`. Gendannelse med `sudo bash
restore.sh <fil>` erstatter databaseindholdet og må kun udføres med en
verificeret backup.