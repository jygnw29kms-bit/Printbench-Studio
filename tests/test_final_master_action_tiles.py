from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PANEL=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')

def test_system_actions_use_native_printbench_tiles():
    assert 'class PrintbenchActionTile : public wxPanel' in PANEL
    assert 'std::array<PrintbenchActionTile*, 6> action_buttons' in PANEL
    assert 'new PrintbenchActionTile(' in PANEL
    assert 'new wxButton(action_card' not in PANEL

def test_system_action_capabilities_remain_truthful():
    assert 'select_tab(MainFrame::tp3DEditor)' in PANEL
    assert 'select_tab(MainFrame::tpCalibration)' in PANEL
    assert 'show_log_window()' in PANEL
    assert 'action_buttons[2]->Enable(false);' in PANEL
    assert 'action_buttons[3]->Enable(false);' in PANEL
    assert 'action_buttons[4]->Enable(false);' in PANEL
