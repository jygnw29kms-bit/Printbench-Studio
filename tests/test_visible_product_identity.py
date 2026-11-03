from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GUI=ROOT/'app/orcaslicer/src/slic3r/GUI'

def read(name):
    return (GUI/name).read_text(encoding='utf-8')

def test_printbench_splash_has_no_orca_brand():
    for name in ('splash_logo.svg','splash_logo_dark.svg'):
        text=(ROOT/'app/orcaslicer/resources/images'/name).read_text(encoding='utf-8')
        assert 'PRINTBENCH' in text
        assert 'JL1976 SOFTWARE' in text
        assert 'Orca' not in text

def test_windows_runtime_dialogs_name_printbench():
    app=read('GUI_App.cpp')
    for phrase in (
        '135er-PRINTBENCH requires the Microsoft WebView2 Runtime',
        'New version of 135er-PRINTBENCH',
        '135er-PRINTBENCH needs an update',
        'Switching 135er-PRINTBENCH to language',
        'To use 135er-PRINTBENCH with Bambu Lab printers',
    ):
        assert phrase in app
    for stale in (
        'New version of Orca Slicer',
        'OrcaSlicer needs an update',
        'Orca Slicer - Switching language failed',
    ):
        assert stale not in app

def test_preferences_file_associations_name_printbench():
    prefs=read('Preferences.cpp')
    for phrase in (
        'Associate files to 135er-PRINTBENCH',
        'Associate 3MF files to 135er-PRINTBENCH',
        'Associate STL files to 135er-PRINTBENCH',
        'Associate STEP files to 135er-PRINTBENCH',
    ):
        assert phrase in prefs

def test_visible_media_and_printer_errors_name_printbench():
    assert 'slice it with 135er-PRINTBENCH' in read('MediaFilePanel.cpp')
    assert 'same LAN as 135er-PRINTBENCH' in read('SendToPrinter.cpp')
    assert "135er-PRINTBENCH can't connect to %s" in read('Plater.cpp')
    assert 'restart 135er-PRINTBENCH' in read('wxMediaCtrl2.cpp')

def test_visible_update_and_diagnostics_use_printbench_artwork():
    assert 'printbench_about.png' in read('ReleaseNote.cpp')
    assert 'printbench_about.png' in read('UpdateDialogs.cpp')
    trouble=read('TroubleshootDialog.cpp')
    assert 'printbench_about.png' in trouble
    assert 'PRINTBENCH_Logs_' in trouble
    assert 'PRINTBENCH_PackedDebugInfo_' in trouble

def test_upstream_attribution_is_still_preserved():
    about=read('AboutDialog.cpp')
    assert 'OrcaSlicer remains the upstream slicing project' in about
    assert 'includes OrcaSlicer-derived components licensed under' in about
