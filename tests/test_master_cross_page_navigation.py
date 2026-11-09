from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'app/orcaslicer/src/slic3r/GUI'
MAIN=(ROOT/'MainFrame.cpp').read_text(encoding='utf-8')
MONITOR=(ROOT/'Monitor.cpp').read_text(encoding='utf-8')
NATIVE=(ROOT/'PrintbenchNativePanel.cpp').read_text(encoding='utf-8')


def test_single_rail_routes_dashboard_sections_not_just_home():
    assert 'if (m_monitor) m_monitor->navigate_to_section(i);' in MAIN
    assert 'void MonitorPanel::navigate_to_section(size_t index)' in MONITOR
    assert 'm_printbench_panel->navigate_to_section(index);' in MONITOR
    assert 'void PrintbenchNativePanel::navigate_to_section(size_t index)' in NATIVE
    assert 'handle_nav(index);' in NATIVE


def test_slicer_and_device_routes_still_exist():
    assert 'case 7: open_printbench_files(); break;' in MAIN
    assert 'case 9: select_tab(tpMultiDevice); break;' in MAIN
    assert 'const std::array<wxString, 6> top_items' not in NATIVE
