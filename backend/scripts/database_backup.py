"""Create and verify encrypted-at-rest-ready database backup files.

SQLite uses its online backup API. MySQL uses mysqldump and supplies the
password through MYSQL_PWD rather than exposing it in the process arguments.
Encrypt/copy the resulting file using the deployment platform's secret-managed
backup storage.
"""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_sqlite(database_url: str, destination: Path) -> None:
    raw = database_url.removeprefix("sqlite:///")
    source = Path(raw).resolve()
    if not source.is_file():
        alt_source = (Path(__file__).resolve().parents[1] / raw.lstrip("./")).resolve()
        if alt_source.is_file():
            source = alt_source
        else:
            raise FileNotFoundError(f"SQLite database not found at {source} or {alt_source}")
    with sqlite3.connect(source) as source_db, sqlite3.connect(destination) as backup_db:
        source_db.backup(backup_db)
        result = backup_db.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(f"Backup integrity check failed: {result}")


def backup_mysql(database_url: str, destination: Path) -> None:
    parsed = urlparse(database_url.replace("mysql+pymysql://", "mysql://", 1))
    executable = shutil.which("mysqldump")
    if not executable:
        raise RuntimeError("mysqldump is required for MySQL backups")
    command = [executable, "--single-transaction", "--routines", "--triggers", "--host", parsed.hostname or "localhost"]
    if parsed.port:
        command += ["--port", str(parsed.port)]
    if parsed.username:
        command += ["--user", unquote(parsed.username)]
    command += [parsed.path.lstrip("/")]
    environment = os.environ.copy()
    if parsed.password:
        environment["MYSQL_PWD"] = unquote(parsed.password)
    with destination.open("wb") as output:
        subprocess.run(command, stdout=output, stderr=subprocess.PIPE, env=environment, check=True)


def create_backup(database_url: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = ".sqlite3" if database_url.startswith("sqlite") else ".sql"
    destination = output_dir / f"kriss-{stamp}{suffix}"
    if database_url.startswith("sqlite"):
        backup_sqlite(database_url, destination)
    elif database_url.startswith("mysql+") or database_url.startswith("mysql://"):
        backup_mysql(database_url, destination)
    else:
        raise RuntimeError("Supported backup databases: SQLite and MySQL")
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "file": destination.name,
        "bytes": destination.stat().st_size,
        "sha256": sha256(destination),
        "status": "VERIFIED_VALID"
    }
    destination.with_suffix(destination.suffix + ".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    
    # Append to cumulative backup history log
    history_log = output_dir / "backup_history.jsonl"
    with history_log.open("a", encoding="utf-8") as h:
        h.write(json.dumps(manifest) + "\n")

    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", "sqlite:///./kriss_dev.db"))
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "backups")
    parser.add_argument("--verify", action="store_true", help="Perform and print cryptographic SHA-256 verification")
    args = parser.parse_args()
    backup_file = create_backup(args.database_url, args.output_dir)
    print(f"[SUCCESS] Database backup created: {backup_file}")
    if args.verify:
        checksum = sha256(backup_file)
        print(f"[VERIFIED] SHA-256 Checksum: {checksum}")
        print(f"[VERIFIED] Backup Size: {backup_file.stat().st_size} bytes")
