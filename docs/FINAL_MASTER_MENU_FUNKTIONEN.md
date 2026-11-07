# PRINTBENCH FINAL MASTER – verbindliche Menü-/Funktionsabnahme

Grundregel: Genau ein Menü links. Keine zweite Navigation oben. Jeder Menüpunkt führt zu einer eigenen passenden Funktion bzw. fachlich eindeutigem Bildschirm. Orca bleibt technische Engine, nicht sichtbares Gestaltungssystem.

| # | Menüpunkt | Ist-Implementierung (2026-11-07) | Pflicht für FINAL | Abnahme |
|---|---|---|---|---|
| 0 | Übersicht | Dashboard-Anfang | Live-P2S-Übersicht und Status | teilweise |
| 1 | Live Ansicht | Kamera-Karte im Dashboard | Sichtbare und bedienbare LAN-Liveansicht, Fehlerstatus | teilweise |
| 2 | Steuerung | Schnellsteuerungs-Karte | Start, Pause, Stop, Licht, mit Rückmeldung und Absicherung | teilweise |
| 3 | AMS 2 Pro | AMS-Karte | Slots, Zustand, Feuchte, Temperatur, Zuordnung und verfügbare Aktionen | teilweise |
| 4 | Material | Nur AMS-Karte, **keine Materialverwaltung** | Materialprofile, Farben, Typ, Zuordnung, Slicer-Synchronisierung | offen |
| 5 | Druckaufträge | Aktueller Druck | Druckauftragliste, Warteschlange und Druckaktionen | offen |
| 6 | Historie | Lokal beobachtete Abschlüsse | Nachvollziehbare Historie mit Details und Fehlerfällen | teilweise |
| 7 | Dateien | Slicer-Tab | Datei-Import, lokale Druckdateien und Druckerdateien | offen |
| 8 | Kamera | Kamera-Karte | Auflösung, Aufnahme/Timelapse und verlässliche Video-Funktion | teilweise |
| 9 | Geräte-Setup | Multi-Device-Tab | LAN-Erkennung, Pairing/Identität und Geräteverwaltung | offen |
| 10 | Netzwerk | Derselbe Multi-Device-Tab | LAN-Status, Verbindungsdiagnose, Druckeradresse und Fehleranalyse | offen |
| 11 | Sicherheit | Allgemeine Einstellungen | Zugang, lokale Geheimnisse, Zertifikate und Berechtigungen | offen |
| 12 | Diagnose | Logfenster | Log-Viewer, Geräteprüfung, Fehler-/Status-Diagnose | teilweise |
| 13 | System | Systemaktionen-Karte | Einstellungen, Versionsinfo, Updates, Backup und Systemstatus | offen |

## Verbindliche Abnahmebedingungen

1. Jeder Eintrag ist anklickbar und zeigt **nur** den passenden Inhalt. Ein Scrollziel oder pauschaler Sprung in einen fremden Bereich ist nicht automatisch eine vollständige Funktion.
2. Jeder Bildschirm verwendet denselben FINAL-MASTER-Rahmen, dieselbe linke Navigation und JL1976-Branding, keine sichtbare zweite Orca-Tabbar.
3. Fehlende Hardware, fehlende Berechtigungen oder LAN-Probleme erzeugen sichtbare, richtige Fehlermeldungen, keine leeren Attrappen.
4. Geräteverändernde Aktionen werden auf einen tatsächlich verbundenen Drucker geroutet und liefern Rückmeldung; destruktive Aktionen benötigen Bestätigung.
5. Native Windows-EXE: Start, Navigation, Minimieren/Maximieren/Schließen und funktionierende Druckeraktionen müssen real getestet werden.
6. Jede Menüfunktion bekommt mindestens einen automatisierten Routing-Test und einen erfolgreichen manuellen Live-Test. Reine Quelltext-Tests sind keine Funktionsabnahme.
7. FINAL-Status erst, wenn alle 14 Einträge fachlich und optisch abgenommen sind.

Die Ist-Zustände sind ausdrücklich **kein** FINAL-Status. Aktuelle doppelte Zielrouten (3/4, 9/10) und generische Sicherheitseinstellungen (11) müssen durch eigenständige Funktionsseiten ersetzt werden.
