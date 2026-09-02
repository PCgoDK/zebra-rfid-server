# Sikkerhed

Hemmeligheder ligger kun i `/etc/zebra-rfid-server/server.env` med ejer
`root:zebra-rfid-server` og tilstand `0640`; de må aldrig committes.

Adgangskoder hashes med Argon2id. Login begrænses pr. klient-IP og bruger en
dummy hash for ukendte brugere, så svartid ikke afslører brugernavne. JWT-
hemmeligheden skal være mindst 32 bytes.

Systemd-servicen kører som `zebra-rfid-server` med `NoNewPrivileges`,
`PrivateTmp`, `ProtectHome`, `ProtectSystem=strict` og eksplicitte
`ReadWritePaths` for data og logs.