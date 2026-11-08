# PRINTBENCH iPhone LAN App

## Installation

Jens-PC: DESKTOP-BNDD1US, LAN IP 192.168.178.71.

1. iPhone Safari im gleichen WLAN: http://192.168.178.71:8080/
2. Safari Teilen -> Zum Home-Bildschirm.
3. PRINTBENCH erscheint mit dem freigegebenen App-Icon.

Der Windows-PC muss eingeschaltet bleiben. Die App ist eine LAN-Web-App, keine native App-Store-Anwendung.

Windows-LAN-Companion starten:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\start_printbench_mobile.ps1 -StartCollector

Startet HTTP-UI, TLS-zertifikatangepinnten MQTT-Collector und lokale Kamera-Bridge. Windows-Firewall: TCP 8080, privates Netz, LocalSubnet.

Autostart ist auf Jens-PC als Verknüpfung im Startmenü-Autostart installiert. Das reproduzierbare Installationsskript liegt unter tools/install_printbench_mobile_autostart.ps1. Nach einem Windows-Neustart ist der tatsächliche Autostart noch separat zu prüfen.

## Geprüft am 08.11.2026

- UI auf http://192.168.178.71:8080/: HTTP 200.
- API /api/v1/live: aktuelle P2S-MQTT-Telemetrie (RUNNING).
- 390x844 Chrome-Mobilansicht gerendert.
- Alle 14 Menüpunkte haben getrennte Ziele; keine doppelte Topnavigation.
- PRINTBENCH-Icon aus assets/branding/PRINTBENCH_AppIcon_512.png.
- Kamera-Bridge: PyAV installiert, RTSP-Dekodierung meldet noch UnknownError. Keine Kamera-Freigabe.
- Die HTTP-LAN-App ist zurzeit nur lesend. HTTPS plus Autorisierung erforderlich fuer Steuerbefehle.
- Dateiauswahl auf iPhone lokal; Slicing/Datei-Upload noch auf Windows.
- Material, AMS, Historie und System stammen aus dem vorhandenen Collector.

## Sicherheit

Drucker-Zugangscode wird nicht ans iPhone geliefert oder im Repository gespeichert. Zertifikat ist auf Jens-PC unter LOCALAPPDATA/PRINTBENCH/certs/p2s-cert.pem gepinnt.

API-Schluessel werden nie ueber HTTP gesendet. Nach HTTPS-Einrichtung bleibt der eingegebene Control-Schluessel nur im RAM, nicht im LocalStorage. Stop-Befehle verlangen Bestätigung.

Lokale Collector-Umgebung: PRINTBENCH_WEB_PUSH=0, PRINTBENCH_SPOOL_SYNC=0, PRINTBENCH_MEDIA_WORKER=0. Damit sind die alten externen Medien- und Cloud-Push-Funktionen abgeschaltet.

## PandaBeFree

Das MIT-Projekt https://github.com/MiguelSchulz/panda-be-free wurde auf P2S MQTT, AMS und iOS-Funktionen geprueft. Kein Swift-Code wurde direkt eingebettet: die PRINTBENCH-Web-App nutzt die bestehende Python-/Orca-Architektur.

## FINAL verbleibende Punkte

- iPhone-vertrauenswuerdige HTTPS-Verbindung und echte autorisierte Steuerungs-Abnahme.
- Lokales Kamerabild auf dem iPhone (RTSP-Dekodierung).
- Druckwarteschlange, Dateitransfer, Bearbeitung der Material-/AMS-Profile.
- Pixelgenaue optische Abnahme aller 14 Seiten gegen den FINAL MASTER.
- Persistenter Autostart/Watchdog nach Windows-Neustart.
