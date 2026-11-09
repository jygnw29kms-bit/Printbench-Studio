from pathlib import Path
GUI=Path(__file__).resolve().parents[1]/"app/orcaslicer/src/slic3r/GUI"
FRAME=(GUI/"MainFrame.cpp").read_text(encoding="utf-8")
PANEL=(GUI/"PrintbenchNativePanel.cpp").read_text(encoding="utf-8")
HPP=(GUI/"MainFrame.hpp").read_text(encoding="utf-8")

def test_files_menu_opens_real_native_project_file_chooser_in_all_workspaces():
    assert 'case 7: open_printbench_files(); break;' in FRAME
    assert 'case 7: if (wxGetApp().mainframe) wxGetApp().mainframe->open_printbench_files(); break;' in PANEL
    assert 'void        open_printbench_files();' in HPP
    start=FRAME.index('void MainFrame::open_printbench_files()')
    body=FRAME[start:FRAME.index('void MainFrame::select_tab(wxPanel* panel)',start)]
    assert 'can_open_project()' in body
    assert 'select_tab(tp3DEditor);' in body
    assert '*.stl;*.3mf' in body
    assert 'dialog.ShowModal() != wxID_OK' in body
    assert 'm_plater->load_files(files);' in body
