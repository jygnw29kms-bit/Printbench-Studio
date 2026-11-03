from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ABOUT=(ROOT/'app/orcaslicer/src/slic3r/GUI/AboutDialog.cpp').read_text(encoding='utf-8')
DOWNLOAD=(ROOT/'app/orcaslicer/src/slic3r/GUI/DownloadProgressDialog.cpp').read_text(encoding='utf-8')
DEVICE=(ROOT/'app/orcaslicer/src/slic3r/GUI/DeviceErrorDialog.cpp').read_text(encoding='utf-8')

def test_about_dialog_uses_printbench_branding_but_keeps_upstream_attribution():
    assert 'printbench_about.png' in ABOUT
    assert '135er-PRINTBENCH integration (C) 2026 JL1976 Software' in ABOUT
    assert 'PRINTBENCH uses OrcaSlicer as its open-source slicing foundation' in ABOUT
    assert 'OrcaSlicer remains the upstream slicing project' in ABOUT
    assert 'includes OrcaSlicer-derived components licensed under' in ABOUT

def test_network_plugin_error_names_printbench_not_orca():
    assert 'Please restart 135er-PRINTBENCH and try again.' in DOWNLOAD
    assert 'Please restart OrcaSlicer and try again.' not in DOWNLOAD

def test_device_error_dialog_inherits_printbench_frame_icon():
    assert 'SetIcon(wxGetApp().mainframe->GetIcon());' in DEVICE
    assert 'OrcaSlicerTitle.ico' not in DEVICE

def test_about_brand_asset_exists():
    assert (ROOT/'app/orcaslicer/resources/images/printbench_about.png').is_file()
