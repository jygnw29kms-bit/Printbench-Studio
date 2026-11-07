from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DOC=(ROOT/"docs/FINAL_MASTER_MENU_FUNKTIONEN.md").read_text(encoding="utf-8")
SHELL=(ROOT/"app/orcaslicer/src/slic3r/GUI/MainFrame.cpp").read_text(encoding="utf-8")
PANEL=(ROOT/"app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp").read_text(encoding="utf-8")
NAMES=["Übersicht","Live Ansicht","Steuerung","AMS 2 Pro","Material","Druckaufträge","Historie","Dateien","Kamera","Geräte-Setup","Netzwerk","Sicherheit","Diagnose","System"]

def test_every_master_menu_has_documented_function_and_acceptance_status():
    for i,name in enumerate(NAMES):
        assert f"| {i} | {name} |" in DOC
    assert DOC.count("| offen |") >= 5
    assert "FINAL-Status erst, wenn alle 14 Einträge" in DOC

def test_single_menu_is_the_only_global_product_navigation():
    assert 'const std::array<wxString, 14> pb_nav_names' in SHELL
    assert 'const std::array<wxString, 14> nav_items' in PANEL
    assert 'page_buttons->Show(sel != tpMonitor);' not in SHELL
    assert 'page_buttons->Hide();' in SHELL
