from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')
HPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.hpp').read_text(encoding='utf-8')

def test_sidebar_uses_native_rounded_rows_and_live_device_cards():
    assert 'class PrintbenchNavRow : public wxPanel' in CPP
    assert 'dc.DrawRoundedRectangle(0, 0, size.x - 1, size.y - 1, FromDIP(7));' in CPP
    assert 'class PrintbenchSidebarDevice : public wxPanel' in CPP
    assert 'std::array<PrintbenchSidebarDevice*, 2> m_sidebar_devices' in HPP

def test_sidebar_device_cards_follow_real_snapshot_state():
    assert 'm_sidebar_devices[0]->SetState(s.online' in CPP
    assert 'm_sidebar_devices[1]->SetState(s.has_ams' in CPP
    assert 's.has_ams ? "Verbunden" : "Nicht verbunden"' in CPP

def test_sidebar_branding_keeps_jl1976_and_compact_two_line_master_layout():
    assert 'printbench_app_icon_32' in CPP
    assert 'JL1976 Software' in CPP
    assert 'brand_text->Add(brand_sub' in CPP
