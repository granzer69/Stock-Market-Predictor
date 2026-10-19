# Paper book backup and restore

SQLite file: `backend/paper_trading.db` (gitignored).

## Backup

```bash
./backend/scripts/backup_paper_db.sh
```

Creates `backups/paper_trading_YYYYMMDD_HHMMSS.db`.

## Restore

Stop the API, then:

```bash
cp backups/paper_trading_YYYYMMDD_HHMMSS.db backend/paper_trading.db
```

## Docker Compose

Mount a host directory:

```yaml
volumes:
  - ./data/paper:/app/backend/data/paper
```

Set `PAPER_DB_PATH` if implemented; today default path is `backend/paper_trading.db` beside the API process.
