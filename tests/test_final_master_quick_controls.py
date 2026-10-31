from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CPP = (ROOT / "app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp").read_text(encoding="utf-8")
HPP = (ROOT / "app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.hpp").read_text(encoding="utf-8")


def test_quick_controls_are_native_printbench_tiles_not_wxbuttons():
    assert "class PrintbenchQuickTile : public wxPanel" in CPP
    assert "PrintbenchQuickTile::Kind::Print" in CPP
    assert "PrintbenchQuickTile::Kind::Pause" in CPP
    assert "PrintbenchQuickTile::Kind::Stop" in CPP
    assert "PrintbenchQuickTile::Kind::Light" in CPP
    assert "m_print = new wxButton" not in CPP
    assert "m_pause_resume = new wxButton" not in CPP
    assert "m_stop = new wxButton" not in CPP
    assert "m_light = new wxButton" not in CPP
    assert "PrintbenchQuickTile* m_print" in HPP


def test_quick_tiles_keep_live_action_state():
    assert "m_pause_resume->SetCaption" in CPP
    assert "m_light->SetCaption" in CPP
    assert "ProcessWindowEvent(event)" in CPP

def test_speed_modes_are_native_master_pills_with_live_selection():
    assert "class PrintbenchSpeedPill : public wxPanel" in CPP
    assert "PrintbenchSpeedPill*" in HPP
    assert "new PrintbenchSpeedPill(quick_card, speed_names[i])" in CPP
    assert "m_speed_buttons[i]->SetActive(active);" in CPP
    assert "m_speed_buttons[i] = new wxButton" not in CPP