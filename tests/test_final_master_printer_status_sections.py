from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')

def test_printer_status_matches_final_master_section_hierarchy():
    assert 'add_status_section("AKTUELLE TEMPERATUR")' in CPP
    assert 'add_status_section("GESCHWINDIGKEIT")' in CPP
    assert 'add_status_section("AMS 2 PRO")' in CPP
    assert 'm_speed = add_status_value(status_card, body, "Modus"' in CPP
    assert 'm_ams_summary = add_status_value(status_card, body, "Status"' in CPP

def test_printer_status_section_labels_are_compact_muted_master_text():
    assert 'style_label(label, 8, true, PB_MUTED);' in CPP
