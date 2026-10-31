from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PANEL=(ROOT/"app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.cpp").read_text(encoding="utf-8")
HEADER=(ROOT/"app/orcaslicer/src/slic3r/GUI/PrintbenchNativePanel.hpp").read_text(encoding="utf-8")


def test_history_is_local_and_persistent():
    assert 'printbench-print-history.tsv' in PANEL
    assert 'wxStandardPaths::Get().GetUserLocalDataDir()' in PANEL
    assert 'save_history();' in PANEL
    assert 'load_history();' in PANEL


def test_history_does_not_treat_disconnect_as_finished_print():
    assert 'if (m_history_tracking && was_active && !active && s.online)' in PANEL
    assert 'if (s.online)\n        m_previous_print_state = s.print_state;' in PANEL


def test_history_card_renders_three_recent_rows():
    assert 'class PrintbenchHistoryRow;' in HEADER
    assert 'std::array<PrintbenchHistoryRow*, 3> m_history_rows' in HEADER
    assert 'new PrintbenchHistoryRow(history_card)' in PANEL
    assert 'm_history_rows[i]->set_entry(entry.job_name, entry.finished_at, duration, entry.status);' in PANEL
    assert 'm_history.size() > 20' in PANEL


def test_history_rows_match_final_master_structure_without_fake_jobs():
    assert 'class PrintbenchHistoryRow : public wxPanel' in PANEL
    assert 'set_empty_state(wxString::FromUTF8("Noch keine lokalen Druckabschlüsse."))' in PANEL
    assert 'badge.MakeUpper();' in PANEL
    assert 'const bool finished = m_status.CmpNoCase("Fertig") == 0;' in PANEL
