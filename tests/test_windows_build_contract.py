from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / 'tools' / 'build_printbench_orca.ps1').read_text(encoding='utf-8')


def test_windows_build_removes_stale_outputs_before_linking():
    assert "Remove stale PRINTBENCH outputs" in SCRIPT
    assert "Remove-Item -LiteralPath $Output -Force" in SCRIPT
    assert "Stale build output still exists after cleanup" in SCRIPT


def test_windows_build_requires_fresh_nonempty_outputs():
    assert "$BuildStartedUtc = [DateTime]::UtcNow" in SCRIPT
    assert "LastWriteTimeUtc -lt $BuildStartedUtc" in SCRIPT
    assert "Build output is stale" in SCRIPT
    assert "Build output is empty" in SCRIPT
    assert "build complete with fresh outputs" in SCRIPT


def test_windows_build_recovers_after_repo_is_moved():
    assert "CMAKE_HOME_DIRECTORY:INTERNAL=*" in SCRIPT
    assert "PRINTBENCH source moved; reset generated CMake cache" in SCRIPT
    assert "Remove-Item -LiteralPath $MainBuild -Recurse -Force" in SCRIPT
    assert "System.StringComparison]::OrdinalIgnoreCase" in SCRIPT


def test_windows_build_relocates_generated_dependency_metadata():
    assert "Where-Object { $_.Extension -in @('.cmake', '.pc') }" in SCRIPT
    assert 'StalePrefixPattern' in SCRIPT
    assert '[regex]::Replace($Text, $StalePrefixPattern, $PrefixForward)' in SCRIPT
    assert 'Relocated $RelocatedMetadata generated dependency metadata file(s)' in SCRIPT
    assert 'Set-Content -LiteralPath $Metadata.FullName' in SCRIPT
