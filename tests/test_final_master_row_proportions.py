from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')

def test_middle_row_matches_final_master_proportions():
    assert 'middle->Add(print_card, 31, wxEXPAND | wxRIGHT, FromDIP(8));' in CPP
    assert 'middle->Add(temp_card, 35, wxEXPAND | wxRIGHT, FromDIP(8));' in CPP
    assert 'middle->Add(ams_card, 34, wxEXPAND);' in CPP

def test_bottom_row_uses_compact_master_gutters():
    assert 'bottom->Add(device_card, 1, wxEXPAND | wxRIGHT, FromDIP(8));' in CPP
    assert 'bottom->Add(history_card, 1, wxEXPAND | wxRIGHT, FromDIP(8));' in CPP
    assert 'root->Add(bottom, 5, wxEXPAND | wxLEFT | wxRIGHT | wxBOTTOM, FromDIP(10));' in CPP

def test_history_empty_state_has_clean_german_text():
    assert 'Noch keine lokalen Druckabschlüsse.' in CPP
    assert 'DruckabschlǬsse' not in CPP
