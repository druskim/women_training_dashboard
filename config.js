// ============================================================
//  CONFIGURATION — fill in your URLs before deploying
// ============================================================

const CONFIG = {
  // Direct URL to your live-updating HR CSV
  // e.g. a Dropbox/OneDrive/Google Drive direct-download link
  HR_CSV_URL: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vQOywZDLt7LYUfzftc0L6fiCCuSlKYCwRf7XBo4oP0C8sDIKsffzqd7TKzNIaxa2W_eWvLTXl8KP2wu/pub?output=csv',

  // Google Sheets questionnaire — publish the sheet as CSV:
  //   File → Share → Publish to web → Sheet1 → CSV → Publish
  //   Paste the resulting URL here
  QUESTIONNAIRE_URL: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRxL2VMLwe0V2xGCUhySASpFFEh2QO7-hqarMv7VVOTn8YwB8T-pprGgsg50wmLGqZSG0cYUHYbjpFs/pub?output=csv',

  // Auto-refresh interval in minutes (0 = manual only)
  REFRESH_MINUTES: 15,

  // How many past weeks to display in trend charts
  TREND_WEEKS: 12,

  // Current season start date (ISO format) — used to limit data range
  SEASON_START: '2025-09-01',
};
