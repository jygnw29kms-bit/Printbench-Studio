from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')

def test_master_card_headers_use_compact_spacing():
    assert 'style_label(heading, 10, true, PB_ACCENT);' in CPP
    assert 'outer->Add(heading, 0, wxLEFT | wxRIGHT | wxTOP | wxBOTTOM, FromDIP(6));' in CPP
    assert 'outer->Add(line, 0, wxEXPAND | wxLEFT | wxRIGHT, FromDIP(6));' in CPP
    assert 'outer->Add(body, 1, wxEXPAND | wxALL, FromDIP(6));' in CPP
