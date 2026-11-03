from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CMAKE=(ROOT/'app/orcaslicer/CMakeLists.txt').read_text(encoding='utf-8')

def test_windows_installer_uses_short_cpack_staging_root():
    assert '$ENV{LOCALAPPDATA}/PB/pkg' in CMAKE
    assert 'set(CPACK_PACKAGE_DIRECTORY "${PRINTBENCH_CPACK_DIR}")' in CMAKE

def test_windows_installer_is_scoped_to_p2s_bambu_profiles():
    assert 'PATTERN "profiles" EXCLUDE' in CMAKE
    assert 'profiles/BBL" DESTINATION "./resources/profiles"' in CMAKE
    assert 'profiles/BBL.json' in CMAKE
    assert 'profiles/OrcaFilamentLibrary" DESTINATION "./resources/profiles"' in CMAKE
    assert 'profiles/OrcaFilamentLibrary.json' in CMAKE
    assert 'profiles/Anycubic' not in CMAKE
