from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / 'tools' / 'build_printbench_network.ps1').read_text(encoding='utf-8-sig')

def test_network_git_calls_trust_only_the_pinned_cache_repo():
    assert 'git -c "safe.directory=$SourceDir" fetch --quiet origin' in SCRIPT
    assert 'git -c "safe.directory=$SourceDir" checkout --quiet --detach $Commit' in SCRIPT
    assert 'git -c "safe.directory=$SourceDir" rev-parse HEAD' in SCRIPT
    assert 'git config --global --add safe.directory' not in SCRIPT
