from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')
HPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.hpp').read_text(encoding='utf-8')

def test_header_status_matches_master_two_line_device_summary():
    assert 'class PrintbenchHeaderStatus : public wxPanel' in CPP
    assert 'PrintbenchHeaderStatus* m_header_status' in HPP
    assert 'P2S Online' in CPP and 'P2S Offline' in CPP
    assert 'LAN • lokal' in CPP

def test_header_status_uses_real_snapshot_state():
    assert 'm_header_status->SetSnapshot(s.online, wxString::FromUTF8(s.wifi_signal));' in CPP
    assert 'Keine LAN-Verbindung' in CPP
