from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/MainFrame.cpp').read_text(encoding='utf-8')
HPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/MainFrame.hpp').read_text(encoding='utf-8')

def test_global_printbench_nav_replaces_hidden_orca_shell_outside_device():
    assert 'm_topbar->Hide();' in CPP
    assert 'm_printbench_global_nav = new wxPanel(this, wxID_ANY);' in CPP
    assert 'PRINTBENCH' in CPP
    assert 'JL1976 SOFTWARE' in CPP
    assert 'std::array<wxPanel*, 14> m_printbench_global_nav_items' in HPP

def test_global_sidebar_has_real_native_routes():
    assert 'case 7: open_printbench_files(); break;' in CPP
    assert 'case 9: select_tab(tpMultiDevice); break;' in CPP
    assert 'case 11:' not in CPP
    assert 'default:' in CPP
    assert 'if (m_monitor) m_monitor->navigate_to_section(i);' in CPP

def test_device_dashboard_does_not_get_duplicate_global_navigation():
    assert 'const bool show_global = tab != tpMonitor;' in CPP
    assert 'm_printbench_global_nav->Show(show_global);' in CPP
    assert 'update_printbench_global_nav(new_selection);' in CPP

def test_global_nav_keeps_final_master_dark_branding():
    assert 'wxColour(2, 11, 22)' in CPP
    assert 'wxColour(5, 46, 103)' in CPP
    assert 'wxColour(0, 188, 230)' in CPP
    assert 'Studio  /  JL1976 Software' in CPP
    assert 'ScalableBitmap(m_printbench_global_nav, "printbench_app_icon_32", 30)' in CPP
