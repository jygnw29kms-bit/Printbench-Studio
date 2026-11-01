from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp').read_text(encoding='utf-8')
HPP=(ROOT/'app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.hpp').read_text(encoding='utf-8')

def test_device_status_uses_native_master_tiles():
    assert 'class PrintbenchDeviceStatusCell : public wxPanel' in CPP
    assert 'std::array<PrintbenchDeviceStatusCell*, 6> m_device_status_cells' in HPP
    assert 'dc.DrawRoundedRectangle(0, 0, size.x - 1, size.y - 1, FromDIP(6));' in CPP
    assert 'm_device_status_cells[i] = new PrintbenchDeviceStatusCell' in CPP

def test_device_status_tiles_are_live_and_truthful():
    assert 'm_device_status_cells[i]->SetState(value, device_ok[i]);' in CPP
    assert 'value.Replace(L"●  ", wxEmptyString);' in CPP
