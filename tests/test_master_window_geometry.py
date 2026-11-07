from pathlib import Path
CPP=(Path(__file__).resolve().parents[1]/'app/orcaslicer/src/slic3r/GUI/MainFrame.cpp').read_text(encoding='utf-8')


def test_single_menu_layout_preserves_usable_windows_frame():
    assert 'SetMinSize(printbench_min_window);' in CPP
    assert 'const wxSize printbench_min_window(FromDIP(1100), FromDIP(720));' in CPP
    assert 'SetSize(wxSize(FromDIP(1440), FromDIP(900)));' in CPP
    assert 'page_buttons->Show(sel != tpMonitor);' not in CPP
