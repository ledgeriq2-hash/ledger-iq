#!/usr/bin/env sh
set -euo pipefail

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR=${BACKUP_DIR:-/backups}
mkdir -p "${BACKUP_DIR}"

DB_HOST=${DB_HOST:-postgres}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-${POSTGRES_USER:-postgres}}
DB_NAME=${DB_NAME:-${POSTGRES_DB:-ledgeriq}}
S3_BUCKET=${S3_BACKUP_BUCKET:-}
S3_REGION=${S3_REGION:-us-east-1}
S3_ENDPOINT=${S3_ENDPOINT_URL:-}

FILE_NAME="ledgeriq_${TIMESTAMP}.sql.gz"
FILE_PATH="${BACKUP_DIR}/${FILE_NAME}"

echo "Creating backup ${FILE_NAME}..."
pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" | gzip > "${FILE_PATH}"
echo "Backup created at ${FILE_PATH}"

if [ -n "${S3_BUCKET}" ]; then
  echo "Uploading to s3://${S3_BUCKET}/${FILE_NAME}"
  AWS_ARGS="--region ${S3_REGION}"
  if [ -n "${S3_ENDPOINT}" ]; then
    AWS_ARGS="${AWS_ARGS} --endpoint-url ${S3_ENDPOINT}"
  fi
  aws s3 cp "${FILE_PATH}" "s3://${S3_BUCKET}/${FILE_NAME}" ${AWS_ARGS}
fi

echo "Done."
