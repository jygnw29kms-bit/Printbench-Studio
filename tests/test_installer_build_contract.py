from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=(ROOT/'tools/build_printbench_installer.ps1').read_text(encoding='utf-8-sig')

def test_installer_build_uses_short_staging_to_avoid_nsis_path_limits():
    assert 'Join-Path $env:LOCALAPPDATA "PB\\pkg"' in SCRIPT
    assert '& $CPack -G NSIS -C Release -B $StageDir' in SCRIPT

def test_installer_build_requires_modern_cpack_and_nsis():
    assert 'CPack 4.x+' in SCRIPT
    assert 'C:\\Program Files (x86)\\NSIS' in SCRIPT
    assert 'makensis.exe' in SCRIPT

def test_installer_build_publishes_to_project_dist_with_hash():
    assert 'dist\\windows' in SCRIPT
    assert 'Get-FileHash $Final -Algorithm SHA256' in SCRIPT
    assert '135er-PRINTBENCH*.exe' in SCRIPT
