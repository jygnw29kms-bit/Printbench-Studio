from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')
HPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.hpp').read_text(encoding='utf-8')

def test_current_print_uses_native_final_master_job_header():
    assert 'class PrintbenchJobHeader : public wxPanel' in CPP
    assert 'PrintbenchJobHeader* m_job_header' in HPP
    assert 'm_job_header = new PrintbenchJobHeader(print_card);' in CPP
    assert 'menu_obj_cube' not in CPP

def test_job_header_tracks_real_print_state_without_fake_job():
    assert 'm_job_header->SetJob(wxString::FromUTF8(s.job_name), wxString::FromUTF8(s.print_state), active_print);' in CPP
    assert 'm_name = active && !name.empty() ? name : "Kein aktiver Druck";' in CPP
    assert 'badge = "DRUCKT";' in CPP
    assert 'badge = "PAUSE";' in CPP
    assert 'badge = "BEREIT";' in CPP
