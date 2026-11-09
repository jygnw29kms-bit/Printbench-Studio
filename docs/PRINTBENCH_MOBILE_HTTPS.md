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

Im iPhone-Menü Material können eigene Spulen einschließlich Typ, Farbe, Hersteller, Restgewicht, Slicer-Profil und Notiz gespeichert, bearbeitet und entfernt werden. Alle Einträge liegen lokal in LOCALAPPDATA/PRINTBENCH/mobile/workspace.sqlite3; eine automatische Übertragung der Materialdaten zum AMS erfolgt nicht. Nach Auswahl von Material, Farbe, AMS-Slot und Düsentemperaturbereich kann die Zuordnung über einen eigenen, bestätigungspflichtigen Befehl am bereiten P2S gesetzt werden. Während laufender oder pausierter Druckaufträge ist das gesperrt.

Im Menü Dateien lässt sich eine hochgeladene Druckdatei zur lokalen Warteliste hinzufügen. Im Menü Druckaufträge kann man wartende Dateien ansehen und wieder entfernen. Aus Sicherheitsgründen startet die Warteliste keine Drucke automatisch: Slicing, AMS-Abgleich und Freigabe bleiben in der nativen Windows-App. Auf Jens-PC gibt es dafür den Startmenüeintrag **PRINTBENCH Druckwarteliste**. Er zeigt alle vorbereiteten Dateien, kann ihre Reihenfolge ändern und eine ausgewählte STL-/3MF-Datei nach ausdrücklicher Bestätigung im nativen PRINTBENCH-Slicer öffnen. Die Reihenfolge lässt sich auch am iPhone mit Hoch/Runter ändern. G-Code wird aus Sicherheitsgründen nicht automatisch gestartet; übertragene Dateien bleiben auch beim Entfernen aus der Warteliste erhalten.

Die Kamera verwendet die MIT-lizenzierte RTSPS-Implementierung aus strands-cad mit eigenem Digest-RTSP-Handshake (siehe THIRD_PARTY_CAMERA_NOTICES.md). Der Drucker muss tatsächlich eine RTSPS/TLS-Sitzung zulassen.

## Ausbau iPhone V10

Die Steuerungsseite kann P2S-Luftkanal Kühlen (modeId 0) oder Heizen/Filtern (modeId 1) nach Bestätigung schalten. Das Kommando ist an die P2S-MQTT-Richtlinien gebunden und liest den tatsächlich berichteten Modus aus der aktuellen Telemetrie. Die implementierte Referenz ist PandaBeFree (MIT) plus P2S-Dokumentation.

Im AMS 2 Pro gibt es manuelle Filament-Lade-/Entladeaktionen mit Slot- und Temperaturwahl. Diese mechanischen Aktionen sowie AMS-Materialzuweisungen und Trocknungsstart sind während laufenden oder pausierten Druckaufträgen gesperrt. Keine Automatisierung startet einen Druck.

Die Systemanzeige erhält Windows-Datenträgerdaten und einen echten Collector-Telemetriestatus statt Linux-Dienst- und Raspberry-Pi-Temperatur-Platzhaltern.

Diese Funktionen wurden auf ausdrücklichen Wunsch ohne Test-Suite implementiert. Eine tatsächliche Geräteabnahme ist davon zu unterscheiden. Die App heißt erst nach kompletter iPhone- und Druckerabnahme FINAL.

## iPhone V12: größerer Funktionsblock

- Sichtbare P2S-, Kamera- und iPhone-Kopplungszustände auf sämtlichen Seiten.
- Rückmeldungen von Druckerbefehlen als gut lesbare Meldungen auch auf AMS- und Kamera-Seiten, statt nur in der versteckten Steuerungsansicht.
- Kamera: aktuelles Bild, Aktualisieren, iOS-Teilen/Speichern sowie Großansicht.
- Geräte-Setup: P2S-/AMS-Zustand und aktuelle Telemetrie.
- Druckaufträge: optionale lokale Druckende-/Fehlermeldungen. Nur bei geöffneter App und erteilter iOS-Berechtigung; keine Hintergrundüberwachung oder Cloud-Push.
- Diagnose: Status von P2S, Kamera, Windows-Collector und verfügbaren Funktionen als JSON lokal speichern/teilen.
- Sofortige Datenaktualisierung, wenn PRINTBENCH auf dem iPhone wieder sichtbar wird.
- Der laufende Druck wird durch diese Funktionen nicht verändert.

Eine funktionierende iPhone-Benachrichtigung in Hintergrund oder bei geschlossener App ist damit ausdrücklich nicht versprochen. Die sichere Kopplung benötigt ein vom iPhone vertrauenswürdiges lokales Zertifikat.

## V14 sichtbare Versionsanzeige

Auf jeder iPhone-Seite wird PRINTBENCH iPHONE V14 im Kopf angezeigt. Der Verbindungsstreifen unterscheidet HTTP :8080 (nur Überwachung, ohne Schreibzugriff) von HTTPS :8444 (Steuerung erst nach sicherer Kopplung). Die untere Navigation gibt Zugriff auf Übersicht, Kamera, Steuerung, AMS und Aufträge. Rückwärtsnavigation über Safari und automatische Wiederaufnahme der gepaarten HTTPS-Sitzung sind integriert.

HTTP 8080 bleibt für Status/Einrichtung und die Bereitstellung des öffentlichen lokalen CA-Zertifikats aktiv. Es ist bewusst nicht mit dem sicheren Bedienzugang zu verwechseln.

## V16: Stabilere iPhone-Kamera

Die bereits aus einer MIT-lizenzierten Open-Source-Implementierung portierte RTSPS-/Digest-Verbindung bleibt auf Jens-PC in einer einzelnen Kamera-Bridge. Der Kamera-Watchdog startet den Decoder bei einem Ausfall erneut. In der iPhone-Web-App werden JPEG-Bilder nacheinander und erst nach erfolgreichem Laden aktualisiert: Es läuft maximal eine neue Abrufanfrage, fehlgeschlagene Anfragen werden gedrosselt. Dazu kommen wählbare Bildabstände (1/2/5 s), Bildpause und Zoom von 100 bis 300 Prozent. Der laufende P2S-Druck wird nicht verändert.

Für die Protokollfunktionen wurde die offen dokumentierte P2S-Implementierung von panda-be-free als Referenz herangezogen. Swift-UI-Quellcode wird nicht als angeblich native iOS-App ausgegeben. Die freigegebenen Protokollteile und deren Lizenzhinweise sind unter docs/THIRD_PARTY_CAMERA_NOTICES.md sowie in der jeweiligen Codequelle dokumentiert.

## Abnahme noch offen

Nach der CA-Installation auf dem iPhone müssen HTTPS-Zugriff, reale Steuerung, Kamera und restliche Menüs produktiv abgenommen werden. Der Code allein ist keine FINAL-Freigabe.


## V15 Kamera-Wiederherstellung

Ein lokaler Watchdog überwacht den einzelnen P2S-RTSPS-Kameraprozess und startet diesen nach Absturz oder 105 Sekunden ohne aktuelles JPEG selbstständig neu. PRINTBENCH gibt veraltete Kamerasnapshots nicht länger mit HTTP 200 aus, sondern meldet HTTP 503. Die iPhone-App zeigt bei einem vorübergehend nicht vorhandenen Bild einen verständlichen Hinweis statt eines kaputten Bildsymbols. V15 ist im Kopf und auf der Zugangsseite sichtbar.

Die Kamera-Bridge wurde am 09.11.2026 erneut gestartet; danach lag auf Jens-PC ein neuer Snapshot mit fortlaufenden Frames vor. Das ist eine Live-Statusbeobachtung und keine vollständige iOS-Abnahme.
