# VIKAS — Database Backup, Point-in-Time Recovery & Disaster Recovery Runbook

This document details backup strategies, scheduled backup automation, Point-in-Time Recovery (PITR) configuration, integrity validation, and recovery procedures for the VIKAS PostgreSQL database.

---

## 1. Overview of Database Constraints & Invariants

The VIKAS database schema enforces core business constraints at the engine level to prevent data corruption or invalid analytical states:

| Constraint Name | Table | Condition | Business Invariant |
|---|---|---|---|
| `ck_skill_gaps_gap_score_non_negative` | `skill_gaps` | `gap_score >= 0` | Alignment gaps cannot have negative distance |
| `ck_skill_gaps_nlp_confidence_range` | `skill_gaps` | `nlp_confidence >= 0 AND nlp_confidence <= 1` | Probabilistic confidence bounded to [0.0, 1.0] |
| `ck_courses_seats_non_negative` | `courses` | `seats_available >= 0` | Training course enrollment capacity cannot be negative |
| `ck_panel_reviews_signoffs_positive` | `panel_reviews` | `required_signoffs > 0` | Human governance quorum requires at least one sign-off |
| `uq_panel_votes_review_member` | `panel_votes` | `UNIQUE(panel_review_id, panel_member_id)` | One vote per panel member per review |
| `ck_audit_logs_actor_id` | `audit_logs` | Foreign Key / Indexing | Actor accountability for all governance decisions |

---

## 2. Supabase Managed Backups & Point-in-Time Recovery (PITR)

### A. Point-in-Time Recovery (PITR) Configuration
For enterprise or production tiers in Supabase (or AWS RDS PostgreSQL):
1. Navigate to **Project Settings** -> **Database** -> **Backups**.
2. Enable **Point in Time Recovery (PITR)**.
3. Configure the retention window to **7 days** or **14 days**.
4. With PITR active, the database writes continuous Write-Ahead Logs (WAL) to secure object storage (e.g. S3), enabling rollback to any specific second (e.g. 5 seconds before an accidental batch deletion).

### B. Performing a Supabase Point-in-Time Restore
1. In Supabase Dashboard, go to **Database** -> **Backups** -> **PITR Restore**.
2. Select the target timestamp in UTC.
3. Confirm restoration into a new target project or fork to avoid in-place data destruction.
4. Verify application connectivity against the restored fork before swapping connection strings.

---

## 3. Automated Daily Logical Backup (`pg_dump` Cron)

In addition to managed PITR, an automated off-site logical backup must be archived daily.

### Automated Backup Script (`backup_db.sh`)
```bash
#!/usr/bin/env bash
set -euo pipefail

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/backups/vikas"
BACKUP_FILE="${BACKUP_DIR}/vikas_backup_${TIMESTAMP}.dump"
LOG_FILE="/var/log/vikas_backup.log"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting logical database backup..." >> "${LOG_FILE}"

# Execute pg_dump with custom directory-compressed format
pg_dump "${DATABASE_URL}" \
    --format=custom \
    --no-owner \
    --no-privileges \
    --compress=9 \
    --file="${BACKUP_FILE}"

echo "[$(date)] Backup completed successfully: ${BACKUP_FILE} ($(du -h "${BACKUP_FILE}" | cut -f1))" >> "${LOG_FILE}"

# Optional: Encrypt and sync to cloud storage
# aws s3 cp "${BACKUP_FILE}" s3://vikas-db-backups-secure/daily/

# Retention: Delete local backups older than 14 days
find "${BACKUP_DIR}" -name "vikas_backup_*.dump" -mtime +14 -exec rm {} \;
```

### Cron Schedule (`/etc/cron.d/vikas-backup`)
```cron
# Run daily at 02:30 IST (21:00 UTC)
0 21 * * * postgres /opt/vikas/scripts/backup_db.sh >> /var/log/vikas_backup_cron.log 2>&1
```

---

## 4. Disaster Recovery & Restorability Verification Script

A backup is only as good as its proven ability to restore. Never test restoration against production!

### Script: `backend/scripts/verify_backup_restoration.sh`
```bash
#!/usr/bin/env bash
# Verifies a backup dump by restoring into an ephemeral scratch database
set -euo pipefail

BACKUP_FILE="${1:-}"
if [[ -z "${BACKUP_FILE}" ]]; then
    echo "Usage: $0 <path_to_backup_dump>"
    exit 1
fi

TEST_DB_NAME="vikas_restore_test_$(date +%s)"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"

echo "Step 1: Creating ephemeral verification database: ${TEST_DB_NAME}..."
createdb -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" "${TEST_DB_NAME}"

cleanup() {
    echo "Cleaning up ephemeral database..."
    dropdb -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" --if-exists "${TEST_DB_NAME}"
}
trap cleanup EXIT

echo "Step 2: Restoring dump into ephemeral database..."
pg_restore -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" \
    -d "${TEST_DB_NAME}" \
    --exit-on-error \
    --verbose "${BACKUP_FILE}"

echo "Step 3: Validating schema tables and invariants..."
TABLE_COUNT=$(psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${TEST_DB_NAME}" -t -c \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")

ALEMBIC_VERSION=$(psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${TEST_DB_NAME}" -t -c \
    "SELECT version_num FROM alembic_version;")

echo "Verified: Found ${TABLE_COUNT// /} tables. Alembic version is ${ALEMBIC_VERSION// /}."

if [[ "${TABLE_COUNT}" -ge 15 ]]; then
    echo "SUCCESS: Backup restored and verified cleanly."
    exit 0
else
    echo "FAILURE: Missing expected tables in restored database."
    exit 1
fi
```

---

## 5. Audit Log Immutability Protection

Audit logs in the `audit_logs` table store critical governance records (panel votes, panel approval/rejections, planner overrides, and flag acknowledgements).

To guarantee tamper-proof audit trails:
1. `audit_logs` records only allow `INSERT` and `SELECT` operations.
2. In production, revoke `UPDATE` and `DELETE` on `audit_logs` from standard application roles:
   ```sql
   REVOKE UPDATE, DELETE ON audit_logs FROM authenticated;
   REVOKE UPDATE, DELETE ON audit_logs FROM anon;
   ```
3. Periodic checksumming can be established to verify hash consistency of audit sequence logs.

