from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')

def test_vertical_master_regions_match_dashboard_weighting():
    assert 'root->Add(hero, 10,' in CPP
    assert 'root->Add(middle, 6,' in CPP
    assert 'root->Add(bottom, 5,' in CPP

def test_hero_camera_and_controls_have_sufficient_minimum_height():
    assert 'printer_card->SetMinSize(wxSize(FromDIP(390), FromDIP(400)))' in CPP
    assert 'status_card->SetMinSize(wxSize(FromDIP(230), FromDIP(400)))' in CPP
    assert 'camera_card->SetMinSize(wxSize(FromDIP(330), FromDIP(280)))' in CPP
    assert 'm_media_ctrl->SetMinSize(wxSize(FromDIP(330), FromDIP(155)))' in CPP

def test_middle_row_matches_master_print_temperature_ams_widths():
    assert 'middle->Add(print_card, 31,' in CPP
    assert 'middle->Add(temp_card, 35,' in CPP
    assert 'middle->Add(ams_card, 34,' in CPP
