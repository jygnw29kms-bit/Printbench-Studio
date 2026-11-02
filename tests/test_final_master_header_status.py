from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')

def test_header_status_matches_compact_final_master_density():
    assert 'class PrintbenchHeaderStatus : public wxPanel' in CPP
    assert 'SetMinSize(wxSize(FromDIP(118), FromDIP(36)))' in CPP
    assert 'title_font.SetPointSize(8);' in CPP
    assert 'meta_font.SetPointSize(7);' in CPP
    assert 'dc.DrawCircle(FromDIP(7), FromDIP(11), FromDIP(3));' in CPP

def test_header_status_uses_clean_local_lan_separator():
    assert 'wxString(L"LAN \\u2022 lokal")' in CPP
    assert 'wxString(L"LAN \\u2022 ") + m_wifi' in CPP
