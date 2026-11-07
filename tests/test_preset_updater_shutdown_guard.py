from pathlib import Path

CPP = (Path(__file__).resolve().parents[1] / 'app/orcaslicer/src/slic3r/Utils/PresetUpdater.cpp').read_text(encoding='utf-8')


def test_plugin_sync_checks_gui_lifetime_before_accessing_wx_app():
    start = CPP.index('void PresetUpdater::priv::sync_plugins(')
    body = CPP[start:CPP.index('void PresetUpdater::priv::sync_printer_config(', start)]
    assert 'if (wxApp::GetInstance() == nullptr)' in body
    assert body.index('if (wxApp::GetInstance() == nullptr)') < body.index('GUI::wxGetApp().use_legacy_network_plugin()')
    assert 'std::string curr_version = legacy_network_plugin ?' in body
    assert body.count('if (arm64_network_headers)') == 2
