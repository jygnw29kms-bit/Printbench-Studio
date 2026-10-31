from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')

def test_temperature_chart_matches_final_master_grid_density():
    assert 'for (int i = 0; i <= 4; ++i)' in CPP
    assert 'for (int i = 0; i <= 6; ++i)' in CPP
    assert 'const wxString older = "ALT";' in CPP
    assert 'const wxString live = "LIVE";' in CPP

def test_temperature_chart_keeps_three_live_series_and_end_markers():
    assert 'const std::array<wxColour, 3> colours' in CPP
    assert 'dc.DrawCircle(last' in CPP
    assert 'm_samples.size() > 90' in CPP
