from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / 'app/orcaslicer/src/slic3r/GUI/MainFrame.cpp').read_text(encoding='utf-8')
GUI_APP = (ROOT / 'app/orcaslicer/src/slic3r/GUI/GUI_App.cpp').read_text(encoding='utf-8')
RC = (ROOT / 'app/orcaslicer/src/dev-utils/platform/msw/OrcaSlicer.rc.in').read_text(encoding='utf-8')
CMAKE = (ROOT / 'app/orcaslicer/CMakeLists.txt').read_text(encoding='utf-8')


def test_windows_shell_keeps_native_window_controls():
    assert '#define BORDERLESS_FRAME_STYLE wxDEFAULT_FRAME_STYLE' in MAIN
    assert 'WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_THICKFRAME' in MAIN
    assert 'return wxFrame::MSWWindowProc(nMsg, wParam, lParam);\n\n#if 0' in MAIN


def test_windows_exe_uses_printbench_icon_resource():
    assert 'PRINTBENCH_AppIcon.ico' in RC
    assert 'images/OrcaSlicer.ico' not in RC
    assert (ROOT / 'assets/branding/PRINTBENCH_AppIcon.ico').is_file()
    assert (ROOT / 'assets/branding/PRINTBENCH_AppIcon_MASTER_1024.png').is_file()


def test_printbench_update_service_runs_instead_of_orca_update_channel():
    assert '#include "PrintbenchUpdateService.hpp"' in GUI_APP
    assert 'PrintbenchUpdateService::check' in GUI_APP
    assert '// Lightweight modular PRINTBENCH release check.' in GUI_APP
    assert 'this->check_new_version_sf();' in GUI_APP


def test_windows_installer_uses_the_same_printbench_icon():
    assert 'assets/branding/PRINTBENCH_AppIcon.ico' in CMAKE
    assert 'resources/images\\\\OrcaSlicer.ico' not in CMAKE


def test_windows_shell_and_installer_use_printbench_executable_name():
    src_cmake = (ROOT / 'app/orcaslicer/src/CMakeLists.txt').read_text(encoding='utf-8')
    process_cpp = (ROOT / 'app/orcaslicer/src/slic3r/Utils/Process.cpp').read_text(encoding='utf-8')
    plugin_cpp = (ROOT / 'app/orcaslicer/src/slic3r/Utils/BBLNetworkPlugin.cpp').read_text(encoding='utf-8')
    assert 'OUTPUT_NAME "135er-PRINTBENCH"' in src_cmake
    assert '135er-PRINTBENCH.exe' in RC
    assert '135er-PRINTBENCH.exe' in process_cpp
    assert '135er-PRINTBENCH.exe' in plugin_cpp
    assert 'CPACK_NSIS_INSTALLED_ICON_NAME  "$INSTDIR\\\\\\\\135er-PRINTBENCH.exe"' in CMAKE
    assert 'CPACK_CREATE_DESKTOP_LINKS "135er-PRINTBENCH"' in CMAKE


def test_printbench_editor_never_dereferences_missing_orca_menubar():
    assert 'wxGetApp().tabs_as_menu() && m_menubar != nullptr' in MAIN
    assert 'if (m_menubar != nullptr)\n        MenuFactory::sys_color_changed(m_menubar);' in MAIN
    assert 'if (m_menubar != nullptr) {\n        if (int id = m_menubar->FindMenu' in MAIN


def test_printbench_editor_guards_optional_view_menu_item():
    assert 'if (perspective_item != nullptr)' in MAIN
    assert 'perspective_item->GetId()' in MAIN
