from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILD=(ROOT/'tools/build_printbench_orca.ps1').read_text(encoding='utf-8')
MSIX=(ROOT/'app/orcaslicer/scripts/msix/build_msix.ps1').read_text(encoding='utf-8')
MANIFEST=(ROOT/'app/orcaslicer/scripts/msix/AppxManifest.xml').read_text(encoding='utf-8')
DOC=(ROOT/'docs/WINDOWS-BUILD-TOOLCHAIN.md').read_text(encoding='utf-8')

def test_build_contract_tracks_branded_windows_executable():
    assert "src\\Release\\135er-PRINTBENCH.exe" in BUILD
    assert "src\\Release\\orca-slicer.exe" not in BUILD
    assert '135er-PRINTBENCH.exe' in DOC

def test_msix_visible_surface_uses_printbench_branding():
    assert "'135er-PRINTBENCH.exe'" in MSIX
    assert '135er-PRINTBENCH_Windows_MSIX.msix' in MSIX
    assert 'JL1976 Software' in MSIX
    assert 'orca-msix-staging' not in MSIX
    assert '<DisplayName>135er-PRINTBENCH</DisplayName>' in MANIFEST
    assert 'Executable="135er-PRINTBENCH.exe"' in MANIFEST
    assert 'DisplayName="135er-PRINTBENCH"' in MANIFEST
    assert 'Native Bambu Lab P2S slicer and device control by JL1976 Software' in MANIFEST
