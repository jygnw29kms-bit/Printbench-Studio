from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/"app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp").read_text(encoding="utf-8")
HPP=(ROOT/"app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.hpp").read_text(encoding="utf-8")

def test_printer_status_uses_compact_master_rows():
    assert "add_status_value(status_card" in CPP
    assert "row_panel->SetBackgroundColour(wxColour(8, 25, 37))" in CPP
    assert "m_printer_status_dots" in HPP

def test_printer_status_dots_follow_live_state():
    assert "printer_status_colours" in CPP
    assert "s.has_ams ? PB_OK : PB_MUTED" in CPP
    assert "active_print ? PB_OK" in CPP
