import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
UI=ROOT/'tools/printbench_collector/pi_ui/static'
HTML=(UI/'index.html').read_text(encoding='utf-8')
JS=(UI/'app.js').read_text(encoding='utf-8')
MOBILE=(UI/'mobile-app.js').read_text(encoding='utf-8')
CSS=(UI/'app.css').read_text(encoding='utf-8')

def test_mobile_app_single_final_master_menu():
    expected=['overview','live','control','ams','spools','jobs','prints','files','camera','setup','network','security','diagnostics','system']
    nav=HTML.split('<nav class="side-nav"',1)[1].split('</nav>',1)[0]
    routes=re.findall(r'<button data-view="([^"]+)"',nav)
    assert routes==expected
    for name in expected: assert 'data-view-panel="'+name+'"' in HTML
    assert 'class="top-nav"' not in HTML

def test_mobile_app_installable_identity():
    manifest=json.loads((UI/'manifest.webmanifest').read_text(encoding='utf-8'))
    assert manifest['name']=='135er-PRINTBENCH'
    assert manifest['display']=='standalone'
    assert manifest['start_url']=='/'
    for size in [180,192,512]: assert (UI/f'icons/icon-{size}.png').is_file()
    assert 'rel="apple-touch-icon"' in HTML

def test_mobile_controls_never_send_tokens_over_plain_http():
    assert "location.protocol === 'https:'" in MOBILE
    assert "if(!secureControl)" in MOBILE
    assert "'X-API-Key':mobileControlToken" in JS
    assert "nativeControlAuthorized &&" in JS
    assert "window.confirm" in JS

def test_mobile_service_worker_never_caches_printer_data():
    sw=(UI/'sw.js').read_text(encoding='utf-8')
    assert "url.pathname.startsWith('/api/')" in sw
    assert "url.pathname.startsWith('/camera/')" in sw

def test_single_menu_and_touch_targets():
    assert '.top-nav{display:none!important}' in CSS
    assert '.side-nav button.active{background:#0d70ee' in CSS
    assert 'min-height:44px' in CSS
