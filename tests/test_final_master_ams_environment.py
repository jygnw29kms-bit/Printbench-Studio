from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')
HPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.hpp').read_text(encoding='utf-8')

def test_ams_environment_uses_native_master_bar():
    assert 'class PrintbenchAmsEnvironmentBar : public wxPanel' in CPP
    assert 'PrintbenchAmsEnvironmentBar* m_ams_environment' in HPP
    assert 'm_ams_environment = new PrintbenchAmsEnvironmentBar(ams_card);' in CPP
    assert 'AMS ENV' in CPP

def test_ams_environment_uses_real_temp_and_humidity():
    assert 'm_ams_environment->SetEnvironment(s.has_ams, s.ams_temp_c, s.ams_humidity);' in CPP
    assert '%.1f °C     %d %% RH' in CPP
    assert 'NICHT VERBUNDEN' in CPP

def test_camera_tiles_do_not_rely_on_dead_native_background_calls():
    assert 'm_camera_record->SetBackgroundColour' not in CPP
    assert 'm_camera_timelapse->SetBackgroundColour' not in CPP
