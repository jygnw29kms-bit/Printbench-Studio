from pathlib import Path
GUI=Path(__file__).resolve().parents[1]/'app/orcaslicer/src/slic3r/GUI'
CPP=(GUI/'PrintbenchNativePanel.cpp').read_text(encoding='utf-8')
HPP=(GUI/'PrintbenchNativePanel.hpp').read_text(encoding='utf-8')

def test_menu_switches_visible_workspace_instead_of_scrolling_full_dashboard():
    assert 'void PrintbenchNativePanel::show_master_section(size_t index)' in CPP
    for part in ('m_master_hero','m_master_middle','m_master_bottom'):
        assert f'm_master_root->Show({part},' in CPP
    for i in range(7):
        assert 'case 0: case 1: case 2: case 3: case 4: case 5: case 6:' in CPP
    assert 'show_master_section(index); break;' in CPP
    assert 'm_section_title->SetLabel(names[index]);' in CPP
    assert 'm_section_title->Show(!overview);' in CPP

def test_material_and_queue_do_not_claim_unimplemented_features():
    assert 'Profilverwaltung ist noch nicht verfügbar' in CPP
    assert 'Warteschlange ist noch nicht verfügbar' in CPP
    assert 'm_master_hero_right->Show(m_camera_card, overview || camera)' in CPP
    assert 'm_master_hero_right->Show(m_quick_card, overview || controls)' in CPP
    assert 'm_master_middle->Show(m_ams_card, overview || ams)' in CPP
