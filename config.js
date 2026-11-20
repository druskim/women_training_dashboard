// ============================================================
//  CONFIGURATION — fill in your URLs before deploying
// ============================================================

const CONFIG = {
  // HR data CSV auto-synced from SharePoint by sync_hr_data.py
  HR_CSV_URL: 'https://raw.githubusercontent.com/druskim/women_training_dashboard/main/hr_data.csv',

  // Individual Performance Plans + roster, read live from the IPP workbook on Google Drive
  // (shared as "Anyone with the link can view"). Each athlete sheet adds them to the roster.
  IPP_XLSX_URL: 'https://docs.google.com/spreadsheets/d/1y_RA5llgTHyxk_ICyMNAp816ew44T-vJ/export?format=xlsx',

  // Past IPP reviews: a snapshot of each athlete's plan, saved by sync_hr_data.py whenever their
  // "Date completed" changes. Served from this repo next to index.html.
  IPP_HISTORY_URL: 'ipp_history.json',

  // 2026–27 Yearly Training Plan (Google Sheet shared as "Anyone with the link can view").
  // Its "Meso YTP" tab gives each week's training phase and planned volume. Weeks without a
  // planned volume follow the YTP's GPP pattern, scaled up: each GPP block starts at
  // TARGET_BASE_HOURS and adds 5% a week, tapers are 5% below the week before (not under the base), and deloads are
  // DELOAD_FACTOR × the last training week (they may fall below the threshold).
  YTP_XLSX_URL: 'https://docs.google.com/spreadsheets/d/1hAswQizlsnej4QbZJCdYr4ate9qlpKfMZlJ9A3WnYGg/export?format=xlsx',
  TARGET_BASE_HOURS: 10,
  DELOAD_FACTOR: 0.8,
  // Weekly hours below this should only happen in a deload; other weeks under it are flagged
  LOAD_THRESHOLD_HOURS: 10,

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
