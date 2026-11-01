from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')

def test_final_master_cards_use_native_rounded_printbench_panel():
    assert 'class PrintbenchCardPanel : public wxPanel' in CPP
    assert 'dc.DrawRoundedRectangle(0, 0, size.x - 1, size.y - 1, FromDIP(8));' in CPP
    assert 'wxPen(wxColour(24, 59, 78), 1)' in CPP
    assert 'auto* card = new PrintbenchCardPanel(parent);' in CPP
    assert 'auto* printer_card = new PrintbenchCardPanel(this);' in CPP

def test_final_master_card_divider_is_subtle_not_native_default():
    assert 'line->SetForegroundColour(wxColour(20, 50, 67));' in CPP
