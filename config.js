// ============================================================
//  CONFIGURATION — fill in your URLs before deploying
// ============================================================

const CONFIG = {
  // HR data CSV auto-synced from SharePoint by sync_hr_data.py
  HR_CSV_URL: 'https://raw.githubusercontent.com/druskim/women_training_dashboard/main/hr_data.csv',

  // Individual Performance Plans + roster, read live from the IPP workbook on Google Drive
  // (shared as "Anyone with the link can view"). Each athlete sheet adds them to the roster.
  IPP_XLSX_URL: 'https://docs.google.com/spreadsheets/d/1y_RA5llgTHyxk_ICyMNAp816ew44T-vJ/export?format=xlsx',

  // Google Sheets questionnaire (bilingual form, 2027 season). The sheet must be shared as
  // "Anyone with the link can view"; the /export URL serves it as CSV.
  QUESTIONNAIRE_URL: 'https://docs.google.com/spreadsheets/d/1q8rNVDC8VhzugMs-fhZYVQiH7d5a7hEYGwWa1rw7gxQ/export?format=csv',

  // Auto-refresh interval in minutes (0 = manual only)
  REFRESH_MINUTES: 15,

  // How many past weeks to display in trend charts
  TREND_WEEKS: 12,

  // 2027 season start (ISO format). From the first Monday on or after this date, charts,
  // averages and the date filter only cover the season; before then everything is shown.
  SEASON_START: '2026-11-01',
};
