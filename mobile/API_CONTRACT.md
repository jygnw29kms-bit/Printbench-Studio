# PRINTBENCH Mobile API Contract v1

PRINTBENCH Mobile ist ein Local-First-Client. Die PWA spricht ausschließlich mit dem lokalen PRINTBENCH Gateway. Bambu-Zugangsdaten, MQTT-, FTPS- und RTSP-Zugriffe bleiben im Desktop/Core.

## Basis

Standard-Gateway: `https://<printbench-host>:8765`

Die Mobile-App erwartet CORS für das lokale PWA-Origin und eine lokale Authentisierung, sobald das Gateway nicht ausschließlich auf Loopback/LAN-vertrauenswürdig betrieben wird.

## REST

### GET `/api/v1/printers`

Antwort: Array oder `{ "items": [...] }`.

Druckerobjekt:

```json
{
  "id": "135er-melti",
  "name": "135er-Melti",
  "online": true,
  "job": {
    "name": "part.3mf",
    "progress": 37,
    "remainingMinutes": 84,
    "status": "printing"
  },
  "temperatures": {
    "nozzle": 220,
    "nozzleTarget": 220,
    "bed": 58,
    "bedTarget": 60,
    "chamber": 34
  },
  "speed": { "label": "Standard", "percent": 100 },
  "ams": {
    "label": "AMS 2 Pro",
    "status": "Bereit",
    "slots": [
      { "slot": 1, "material": "PETG", "color": "#242424", "remaining": 73 }
    ]
  }
}
```

### POST `/api/v1/printers/{id}/commands`

Body:

```json
{ "action": "pause" }
```

V1 Aktionen:

- `pause`
- `resume`
- `stop`

Später vorgesehen: `light`, `speed`, `temperature`, `fan`, `home`, `move`, `start-print`.

### GET `/api/v1/printers/{id}/camera/snapshot`

Liefert ein aktuelles JPEG/PNG-Bild. V1 nutzt Snapshot statt direkten RTSP-Zugriff aus Safari. Der Desktop/Core übernimmt RTSP/RTSPs und transkodiert/proxied nur bei Bedarf.

## WebSocket

### `/api/v1/events`

Events:

```json
{
  "type": "printer.snapshot",
  "data": { "...": "vollständiges Druckerobjekt" }
}
```

```json
{
  "type": "printer.update",
  "data": { "...": "vollständiges Druckerobjekt" }
}
```

V1 akzeptiert vollständige Snapshots. Delta-Events können später ergänzt werden.

## Sicherheitsgrenze

Mobile darf niemals direkt folgende Secrets erhalten:

- Bambu LAN Access Code
- MQTT Credentials
- FTPS Credentials
- RTSP Credentials
- Cloud Tokens

Das Gateway führt alle Maschinenaktionen stellvertretend aus. Für optionalen Fernzugriff wird später eine eigene PRINTBENCH-Cloud davor gesetzt. LAN bleibt unabhängig funktionsfähig.
