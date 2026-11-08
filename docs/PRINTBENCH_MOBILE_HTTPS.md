# PRINTBENCH iPhone LAN App, sichere Kopplung

## Einmalige Einrichtung auf dem iPhone

1. iPhone und Jens-PC im gleichen WLAN/LAN.
2. In Safari die HTTP-Seite http://192.168.178.71:8080/ öffnen und unter Sicherheit die öffentliche PRINTBENCH-CA-Datei laden.
3. Einstellungen > Allgemein > VPN & Geräteverwaltung: das heruntergeladene Zertifikatsprofil installieren.
4. Einstellungen > Allgemein > Info > Zertifikatsvertrauenseinstellungen: der PRINTBENCH Private LAN CA vertrauen, nachdem der Fingerabdruck am Jens-PC geprüft wurde.
5. Sichere App: https://192.168.178.71:8444/ (Safari > Teilen > Zum Home-Bildschirm).
6. Auf Jens-PC im Startmenü PRINTBENCH iPhone koppeln wählen. Der achtstellige Code ist einmalig und 15 Minuten gültig.
7. In der iPhone-App unter Sicherheit den Code eingeben. Danach gilt die geschützte Kopplungssitzung bis zu 30 Tage.

## Windows-Dienste

Der Windows-Autostart verwendet tools/start_printbench_mobile.ps1. Zugriff nur im lokalen Netz:
- TCP 8080: Lesen und Download des öffentlichen CA-Zertifikats.
- TCP 8444: HTTPS-App, Kopplung und autorisierte Gerätebefehle.

Zertifikate, private Schlüssel, Sitzungsspeicher, Audit und Kopplungscode liegen unter LOCALAPPDATA/PRINTBENCH/mobile außerhalb des Repositories. Niemals private Schlüssel ins Git legen.

Druckerbefehle benötigen autorisierte HTTPS-Sitzung, aktive lokale Richtlinien, Audit und Bestätigung destruktiver Aktionen. Keine Steuerung über HTTP.

## Dateitransfer

Nach der Kopplung können 3MF, STL, GCODE, GCO und BGCODE vom iPhone über den Menüpunkt Dateien an Jens-PC übertragen werden. Pro Datei sind maximal 256 MB zulässig, insgesamt 1 GB Eingangsordner. Gespeichert wird ausschließlich unter LOCALAPPDATA/PRINTBENCH/mobile/uploads. Der Startmenüeintrag PRINTBENCH iPhone Dateien öffnet diesen Ordner. Keine Datei wird automatisch gestartet oder gedruckt.

## P2S- und AMS-Bedienung

Die sichere iPhone-App bietet nach Kopplung Druckpause, Fortsetzen, Stop (mit Bestätigung), Licht, Geschwindigkeit, Lüfter, Temperaturen, Kameraufnahme, Zeitraffer und Auflösung. Das AMS 2 Pro erhält Slot-/RFID-Einlesen und Trocknungsstart/-stopp. Maximal 65 °C, Start nicht während eines laufenden oder pausierten Drucks. Das Startkommando verwendet das P2S-Feld close_power_conflict und verlangt eine zusätzliche Bestätigung. Der Erfolg wird anhand frischer Geräte-Telemetrie bewertet.

## Kamera

Der P2S benötigt den LAN-Liveview-Modus für RTSPS auf Port 322. Wenn kein Bild erscheint, am P2S in den Netzwerk-/LAN-Einstellungen LAN-Liveview aktivieren. Die lokale Bridge meldet ein Bild nur bei einem tatsächlich frischen Snapshot.

## Lokale Materialverwaltung und Warteliste

Im iPhone-Menü Material können eigene Spulen einschließlich Typ, Farbe, Hersteller, Restgewicht, Slicer-Profil und Notiz gespeichert, bearbeitet und entfernt werden. Alle Einträge liegen lokal in LOCALAPPDATA/PRINTBENCH/mobile/workspace.sqlite3; eine automatische Übertragung der Materialdaten zum AMS erfolgt nicht.

Im Menü Dateien lässt sich eine hochgeladene Druckdatei zur lokalen Warteliste hinzufügen. Im Menü Druckaufträge kann man wartende Dateien ansehen und wieder entfernen. Aus Sicherheitsgründen startet die Warteliste keine Drucke automatisch: Slicing, AMS-Abgleich und Freigabe bleiben in der nativen Windows-App.

Die Kamera verwendet die MIT-lizenzierte RTSPS-Implementierung aus strands-cad mit eigenem Digest-RTSP-Handshake (siehe THIRD_PARTY_CAMERA_NOTICES.md). Der Drucker muss tatsächlich eine RTSPS/TLS-Sitzung zulassen.

## Abnahme noch offen

Nach der CA-Installation auf dem iPhone müssen HTTPS-Zugriff, reale Steuerung, Kamera und restliche Menüs produktiv abgenommen werden. Der Code allein ist keine FINAL-Freigabe.
