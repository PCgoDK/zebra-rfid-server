# Zebra-konfiguration

Konfigurer læserens event-destination til serverens TCP-adresse og port 5084,
hvis den benyttede Zebra-integration understøtter det. Verificer altid
konfigurationen i Zebra Interface Control Guide og på en fysisk FX7500 eller
FX9600 før produktion.

Den native LLRP-klient forbinder til hver reader angivet i `LLRP_READER_IDS`
på `LLRP_PORT` (standard 5084). Den understøtter `RO_ACCESS_REPORT`,
`TagReportData`, EPCData/EPC-96, antenne, RSSI, UTC-tid og `KEEPALIVE_ACK`.
Discovery foretager kun en read-only forbindelsesprobe på port 5084 og ændrer
aldrig læserens konfiguration.

Den eksisterende TCP-adapter forventer stadig newline-afgraenset JSON fra
simulatoren. Bekræft altid LLRP-eventdata fra den konkrete reader og firmware
før produktionsbrug.

FXR90-events kan angive `gps_latitude`, `gps_longitude`, `gps_altitude`,
`gps_accuracy` og `gps_timestamp` som ISO 8601-tid. GPS-felterne er valgfrie;
de gemmes som `NULL` for læsere, der ikke leverer position.