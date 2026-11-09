from pathlib import Path
GUI=Path(__file__).resolve().parents[1]/'app/orcaslicer/src/slic3r/GUI'
CPP=(GUI/'PrintbenchNativePanel.cpp').read_text(encoding='utf-8')
HPP=(GUI/'PrintbenchNativePanel.hpp').read_text(encoding='utf-8')

def test_menu_switches_visible_workspace_instead_of_scrolling_full_dashboard():
    assert 'void PrintbenchNativePanel::show_master_section(size_t index)' in CPP
    for part in ('m_master_hero','m_master_middle','m_master_bottom'):
        assert f'm_master_root->Show({part},' in CPP
    assert 'm_section_cards[i]->Show(i == index);' in CPP
    assert 'show_master_section(index);' in CPP
    assert 'm_section_title->SetLabel(names[index]);' in CPP
    assert 'm_section_title->Show(!overview);' in CPP

def test_native_sections_reuse_orca_profiles_and_the_local_mobile_queue():
    assert 'EVT_CREATE_FILAMENT' in CPP
    assert 'open_mobile_shortcut(this, "PRINTBENCH Druckwarteliste")' in CPP
    assert 'open_mobile_shortcut(this, "PRINTBENCH iPhone koppeln")' in CPP
    assert 'm_master_hero_right->Show(m_camera_card, overview || camera)' in CPP
    assert 'm_master_hero_right->Show(m_quick_card, overview || controls)' in CPP
    assert 'm_master_middle->Show(m_ams_card, overview || ams)' in CPP
