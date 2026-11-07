from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PANEL=(ROOT/"app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp").read_text(encoding="utf-8")
HEADER=(ROOT/"app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.hpp").read_text(encoding="utf-8")
SHELL=(ROOT/"app/orcaslicer/src/slic3r/GUI/MainFrame.cpp").read_text(encoding="utf-8")

def test_master_sidebar_rows_are_interactive():
    assert 'std::array<PrintbenchNavRow*, 14> m_nav_rows' in HEADER
    assert 'item->Bind(wxEVT_LEFT_UP, [this, i](wxMouseEvent&) { handle_nav(i); });' in PANEL
    assert 'activate_nav(index);' in PANEL

def test_sidebar_routes_to_real_native_sections():
    assert 'show_master_section(index);' in PANEL
    for target in ('m_camera_card', 'm_quick_card', 'm_ams_card', 'm_print_card', 'm_history_card'):
        assert f'm_master_' in PANEL
        assert target in PANEL
    assert 'select_tab(MainFrame::tpMultiDevice)' in PANEL
    assert 'show_log_window()' in PANEL

def test_single_sidebar_routes_across_workspaces_without_duplicate_top_menu():
    assert 'case 11: wxGetApp().open_preferences(); break;' in SHELL
    assert 'case 9: case 10: select_tab(tpMultiDevice); break;' in SHELL
    assert 'case 7: open_printbench_files(); break;' in SHELL
    assert 'const std::array<wxString, 6> top_items' not in PANEL
