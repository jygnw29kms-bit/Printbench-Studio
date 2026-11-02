from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')

def test_visible_german_labels_use_real_umlauts():
    assert 'GERÄTESTATUS' in CPP
    assert 'AUFLÖSUNG' in CPP
    assert 'benötigt Material-' in CPP
    assert 'GERAETESTATUS' not in CPP
    assert 'AUFLOESUNG' not in CPP
