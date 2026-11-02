from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')

def test_final_master_cards_use_compact_shared_insets():
    assert 'outer->Add(heading, 0, wxALL, FromDIP(8));' in CPP
    assert 'outer->Add(line, 0, wxEXPAND | wxLEFT | wxRIGHT, FromDIP(8));' in CPP
    assert 'outer->Add(body, 1, wxEXPAND | wxALL, FromDIP(8));' in CPP
    assert 'card->SetMinSize(wxSize(FromDIP(170), FromDIP(112)));' in CPP
