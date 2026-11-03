from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')

def test_ams_slot_cards_match_vertical_final_master_density():
    assert 'SetMinSize(wxSize(FromDIP(86), FromDIP(112)));' in CPP
    assert 'const int cx = size.x / 2;' in CPP
    assert 'const int cy = FromDIP(45);' in CPP
    assert 'FromDIP(72)' in CPP
    assert 'FromDIP(89)' in CPP

def test_ams_slot_material_is_centered_and_clipped_truthfully():
    assert 'dc.GetTextExtent(material).x > size.x - FromDIP(12)' in CPP
    assert 'wxString::FromUTF8("…")' in CPP
    assert 'wxString::Format("%d %% Rest", m_remain)' in CPP
