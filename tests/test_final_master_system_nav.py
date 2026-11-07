from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')
HPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.hpp').read_text(encoding='utf-8')

def test_system_is_real_fourteenth_master_navigation_row():
    assert 'const std::array<wxString, 14> nav_items' in CPP
    assert 'L"Diagnose", L"System"' in CPP
    assert 'const std::array<const char*, 14> nav_icons' in CPP
    assert '"calib_sf", "settings"' in CPP
    assert 'std::array<PrintbenchNavRow*, 14> m_nav_rows' in HPP

def test_system_navigation_routes_to_real_action_card():
    assert 'm_action_card = action_card;' in CPP
    assert 'case 13: show_master_section(index); break;' in CPP
    assert 'wxWindow* m_action_card{nullptr};' in HPP
    assert '\u2699  System' not in CPP
