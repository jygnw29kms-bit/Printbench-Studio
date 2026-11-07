from pathlib import Path
CPP=(Path(__file__).resolve().parents[1]/'app/orcaslicer/src/slic3r/GUI/MainFrame.cpp').read_text(encoding='utf-8')


def test_native_orca_notebook_cannot_reintroduce_second_menu():
    assert 'page_buttons->Show(sel != tpMonitor);' not in CPP
    assert 'page_buttons->Hide();' in CPP
    assert 'm_tabpanel->GetBtnsListCtrl()->Hide();' in CPP
    assert 'pb_workspace->Add(m_printbench_global_nav, 0, wxEXPAND);' in CPP
