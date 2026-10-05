# infra/onprem/db/Dockerfile
# PostgreSQL 16 plus the tools needed to ship encrypted base backups and WAL to S3.
FROM postgres:16-alpine
RUN apk add --no-cache aws-cli openssl bash
COPY dr_common.sh archive_wal.sh restore_wal.sh backup_base.sh /usr/local/bin/
RUN chmod 0755 /usr/local/bin/archive_wal.sh /usr/local/bin/restore_wal.sh /usr/local/bin/backup_base.sh \
 && chmod 0644 /usr/local/bin/dr_common.sh
