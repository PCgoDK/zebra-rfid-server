# Testprocedure

Installer udviklingsafhængigheder og kør hele testen:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest
```

Simuler to læsere med fragmentering, dubletter og forbindelsesafbrydelser:

```bash
python tools/rfid_reader_simulator.py --readers 2 --events 20 --fragment --duplicates 1 --disconnect-every 5
```

PostgreSQL-integrationstests skal bruge en dedikeret testdatabase via
`ZEBRA_RFID_TEST_DATABASE_URL`; brug aldrig produktionsdatabasen til tests.