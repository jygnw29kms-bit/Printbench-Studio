from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')
HPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.hpp').read_text(encoding='utf-8')
ASSET=ROOT/'app/orcaslicer/resources/images/printbench_hero_p2s_ams.png'

def test_final_master_hero_is_native_live_panel():
    assert 'class PrintbenchHeroPanel : public wxPanel' in CPP
    assert 'PrintbenchHeroPanel* m_hero_panel' in HPP
    assert 'm_hero_panel = new PrintbenchHeroPanel(printer_card, hero_bitmap);' in CPP
    assert 'm_hero_panel->SetSnapshot(s.online, wxString::FromUTF8(s.print_state));' in CPP

def test_hero_keeps_truthful_live_states():
    for label in ('BEREIT','DRUCKT','PAUSE','ONLINE','OFFLINE'):
        assert f'"{label}"' in CPP
    assert 'Bereit zum Drucken' in CPP
    assert 'Nicht verbunden' in CPP

def test_hero_uses_binding_master_asset_without_duplicate_native_title_block():
    assert ASSET.is_file()
    assert 'm_printer_name = new wxStaticText' not in CPP
    assert 'm_ready_banner = new wxStaticText' not in CPP
    assert 'auto* hero_state = new wxBoxSizer' not in CPP
