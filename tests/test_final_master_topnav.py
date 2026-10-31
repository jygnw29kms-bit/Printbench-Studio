from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')
HPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.hpp').read_text(encoding='utf-8')

def test_top_navigation_uses_native_master_items_with_icons():
    assert 'class PrintbenchTopNavItem : public wxPanel' in CPP
    assert 'std::array<PrintbenchTopNavItem*, 6> m_top_nav' in HPP
    assert 'const std::array<const char*, 6> top_icons' in CPP
    assert 'new PrintbenchTopNavItem(this, top_items[i]' in CPP

def test_top_navigation_tracks_active_section_and_sidebar_routes():
    assert 'void PrintbenchNativePanel::activate_top_nav(size_t index)' in CPP
    assert 'activate_top_nav(i);' in CPP
    assert 'case 3: case 4: activate_top_nav(3); break;' in CPP
    assert 'case 6: activate_top_nav(4); break;' in CPP
    assert 'case 9: case 10: activate_top_nav(2); break;' in CPP

def test_top_navigation_has_master_active_underline_and_hover():
    assert 'm_active ? wxColour(10, 66, 137)' in CPP
    assert 'wxColour(20, 125, 245)' in CPP
    assert 'm_hover = true; Refresh(false)' in CPP
