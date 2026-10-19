// ============================================================
//  CONFIGURATION — fill in your URLs before deploying
// ============================================================

const CONFIG = {
  // HR data CSV auto-synced from SharePoint by sync_hr_data.py
  HR_CSV_URL: 'https://raw.githubusercontent.com/druskim/women_training_dashboard/main/hr_data.csv',

  // Individual Performance Plans + roster, generated from the IPP workbook by sync_hr_data.py
  IPP_JSON_URL: 'https://raw.githubusercontent.com/druskim/women_training_dashboard/main/ipp_data.json',

  // Google Sheets questionnaire — publish the sheet as CSV:
  //   File → Share → Publish to web → Sheet1 → CSV → Publish
  //   Paste the resulting URL here
  QUESTIONNAIRE_URL: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRxL2VMLwe0V2xGCUhySASpFFEh2QO7-hqarMv7VVOTn8YwB8T-pprGgsg50wmLGqZSG0cYUHYbjpFs/pub?output=csv',

  // Auto-refresh interval in minutes (0 = manual only)
  REFRESH_MINUTES: 15,

  // How many past weeks to display in trend charts
  TREND_WEEKS: 12,

  // 2027 season start (ISO format). From the first Monday on or after this date, charts,
  // averages and the date filter only cover the season; before then everything is shown.
  SEASON_START: '2026-11-01',
};
