from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')

def test_master_navigation_is_readable_at_desktop_scale():
    assert 'class PrintbenchNavRow : public wxPanel' in CPP
    assert 'font.SetPointSize(10);' in CPP
    assert 'font.SetWeight(m_active ? wxFONTWEIGHT_BOLD : wxFONTWEIGHT_NORMAL);' in CPP
    assert 'class PrintbenchTopNavItem : public wxPanel' in CPP
    assert 'font.SetPointSize(9);' in CPP

def test_master_card_typography_has_clear_hierarchy():
    assert 'style_label(heading, 12, true, PB_ACCENT);' in CPP
    assert 'name_font.SetPointSize(14);' in CPP
    assert 'class PrintbenchJobHeader : public wxPanel' in CPP
    assert 'style_label(value, 13, true, PB_TEXT);' in CPP
    assert 'style_label(m_device_status_values[i], 11, true' in CPP
