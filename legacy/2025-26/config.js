// ============================================================
//  CONFIGURATION — 2025–26 SEASON ARCHIVE (frozen, do not edit)
//  Dashboard, roster and data as they were on 18 Oct 2026, before
//  the 2027 IPP roster. Git tag: season-2025-26
// ============================================================

const CONFIG = {
  // HR data pinned to the 18 Oct 2026 sync (commit 08a67a1), so later syncs don't change it
  HR_CSV_URL: 'https://raw.githubusercontent.com/druskim/women_training_dashboard/08a67a1451410777cc07123344d6e3a452460ec9/hr_data.csv',

  // Snapshot of the questionnaire Google Sheet (last response 12 Oct 2026)
  QUESTIONNAIRE_URL: 'questionnaire.csv',

  // The dashboard behaves as if today were this date
  AS_OF: '2026-10-18',

  // Archived data never changes
  REFRESH_MINUTES: 0,

  // How many past weeks to display in trend charts
  TREND_WEEKS: 12,

  SEASON_START: '2025-09-01',
};
