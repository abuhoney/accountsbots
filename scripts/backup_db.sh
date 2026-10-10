#!/usr/bin/env bash
# Backup guidance for backend: postgresql
set -euo pipefail
case "postgresql" in
  postgresql) pg_dump "$DATABASE_URL" | gzip > "backups/db_$(date +%Y%m%d_%H%M%S).sql.gz" ;;
  mysql) mysqldump --single-transaction "$DATABASE_URL" | gzip > "backups/db_$(date +%Y%m%d_%H%M%S).sql.gz" ;;
  mongodb) mongodump --uri="$MONGO_URI" --archive="backups/db_$(date +%Y%m%d_%H%M%S).archive" ;;
  redis) redis-cli --no-raw BGSAVE && echo "RDB snapshot triggered (see Redis dir setting)" ;;
  *) echo "Use your provider's snapshot/export tooling for backend 'postgresql'. Backup the ./data directory as well." ;;
esac
mkdir -p backups
