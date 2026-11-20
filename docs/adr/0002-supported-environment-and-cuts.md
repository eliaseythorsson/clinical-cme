# Support the Claude app with the page store; cut other stores

From 4.3 the skill ships as a Claude plugin, the earlier 4.2.1 zip stays as it is, and nobody uses the database store, the Google Drive mirror or a version-3 ledger. So we support the Claude app with the artifact-page store as primary and keep the folder store (needed by the test harness). The database store, the Drive mirror, the v3 migration with `legacy/`, and the "find capabilities, not names" layer for other assistants are removed. Restoring any of them means reviving code from git history.
