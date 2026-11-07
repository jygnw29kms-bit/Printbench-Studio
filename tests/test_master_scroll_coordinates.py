from pathlib import Path
CPP=(Path(__file__).resolve().parents[1]/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')


def test_dashboard_navigation_uses_content_coordinates_for_nested_cards():
    start=CPP.index('void PrintbenchNativePanel::scroll_to(wxWindow* target)')
    body=CPP[start:CPP.index('void PrintbenchNativePanel::navigate_to_section',start)]
    assert 'GetViewStart(&view_x, &view_y);' in body
    assert 'target->GetScreenPosition().y - GetScreenPosition().y' in body
    assert 'Scroll(-1, std::max(0, target_content_y / step));' in body
    assert 'target->GetPosition().y / step' not in body
