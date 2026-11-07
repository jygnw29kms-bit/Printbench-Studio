from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
GUI = ROOT / "app/orcaslicer/src/slic3r/GUI"
PANEL = (GUI/"PrintbenchNativePanel.cpp").read_text(encoding="utf-8")
SHELL = (GUI/"MainFrame.cpp").read_text(encoding="utf-8")
HEADER = (GUI/"MainFrame.hpp").read_text(encoding="utf-8")

def test_master_has_one_sidebar_and_no_duplicate_top_menu():
    assert 'const std::array<wxString, 14> nav_items' in PANEL
    assert 'const std::array<wxString, 14> pb_nav_names' in SHELL
    assert 'const std::array<wxString, 6> top_items' not in PANEL
    assert 'new PrintbenchTopNavItem(this, top_items[i]' not in PANEL
    assert 'header->AddStretchSpacer();' in PANEL

def test_all_pages_have_same_single_left_navigation():
    assert 'std::array<wxPanel*, 14> m_printbench_global_nav_items' in HEADER
    assert 'pb_workspace->Add(m_printbench_global_nav, 0, wxEXPAND);' in SHELL
    assert 'pb_workspace->Add(m_main_sizer, 1, wxEXPAND);' in SHELL
    assert 'const bool show_global = tab != tpMonitor;' in SHELL
    assert 'm_printbench_global_nav->Show(show_global);' in SHELL

def test_master_nav_tracks_selection_without_a_top_tabbar():
    assert 'void MainFrame::update_printbench_global_nav(size_t tab)' in SHELL
    assert 'm_printbench_global_nav_items[i]->SetBackgroundColour' in SHELL
    assert 'activate_nav(index);' in PANEL
