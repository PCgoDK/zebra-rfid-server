# Zebra-konfiguration

Konfigurer læserens event-destination til serverens TCP-adresse og port 5084,
hvis den benyttede Zebra-integration understøtter det. Verificer altid
konfigurationen i Zebra Interface Control Guide og på en fysisk FX7500 eller
FX9600 før produktion.

Den nuværende TCP-adapter forventer newline-afgraenset JSON fra simulatoren.
Native LLRP/Zebra-event-parser skal implementeres ud fra fangede, verificerede
pakker fra den valgte firmware. Discovery foretager kun en read-only
forbindelsesprobe på port 5084 og ændrer aldrig læserens konfiguration.

FXR90-events kan angive `gps_latitude`, `gps_longitude`, `gps_altitude`,
`gps_accuracy` og `gps_timestamp` som ISO 8601-tid. GPS-felterne er valgfrie;
de gemmes som `NULL` for læsere, der ikke leverer position.