from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / 'tools/printbench_collector/pi_ui/static'


def test_mobile_navigation_has_single_click_owner():
    core = (UI / 'app.js').read_text(encoding='utf-8')
    mobile = (UI / 'mobile-app.js').read_text(encoding='utf-8')
    assert "document.querySelectorAll('[data-view]').forEach" not in core
    assert "document.querySelectorAll('.side-nav button[data-view]').forEach(b=>b.addEventListener" in mobile
    assert 'stopCameraOnNonCameraView();' in mobile
    assert 'function stopCameraOnNonCameraView()' in core
