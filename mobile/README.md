# PRINTBENCH Mobile

Lokale iOS/PWA-Begleitoberfläche für PRINTBENCH.

## Ziel

- iPhone/iPad im selben LAN wie PRINTBENCH
- kein Bambu-Cloud-Zwang
- keine direkten Bambu-Secrets auf mobilen Geräten
- PRINTBENCH Desktop/Core bleibt einzige Geräteinstanz
- optionaler Fernzugriff später über eigene PRINTBENCH-Cloud

## V1

- Druckerstatus
- aktiver Druck, Fortschritt, Restzeit
- Düse/Bett/Kammer
- Speed
- AMS 2 Pro Slots
- Kamera-Snapshot
- Pause/Fortsetzen/Abbrechen
- Offline-fähige PWA-Shell

## Start lokal

Die Dateien müssen über HTTP/HTTPS ausgeliefert werden, nicht per `file://`.

Beispiel:

```bash
cd mobile
python -m http.server 8088
```

Danach auf dem iPhone im LAN `http://<host>:8088` öffnen. Für die endgültige Home-Screen-PWA und Service Worker wird HTTPS im LAN-Gateway vorgesehen.

## Gateway

Standardmäßig erwartet der Client PRINTBENCH unter Port `8765`. Der konkrete Vertrag steht in `API_CONTRACT.md`.

Die aktuelle Oberfläche fällt bei fehlendem Gateway auf Mock-Daten zurück. Das ist absichtlich so, damit UI und Core parallel entwickelt werden können.
