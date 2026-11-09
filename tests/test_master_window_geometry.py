from pathlib import Path
CPP=(Path(__file__).resolve().parents[1]/'app/orcaslicer/src/slic3r/GUI/MainFrame.cpp').read_text(encoding='utf-8')


def test_single_menu_layout_preserves_usable_windows_frame():
    assert 'SetMinSize(printbench_min_window);' in CPP
    assert 'std::min(FromDIP(1100), work_area.x)' in CPP
    assert 'std::min(FromDIP(1440), work_area.x)' in CPP
    assert 'std::min(FromDIP(900), work_area.y)' in CPP
    assert 'SetSize(wxSize(FromDIP(1200), FromDIP(800)));' not in CPP
    assert 'page_buttons->Show(sel != tpMonitor);' not in CPP
