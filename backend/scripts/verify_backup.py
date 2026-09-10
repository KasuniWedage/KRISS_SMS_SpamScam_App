import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path) -> dict:
    manifest_path = path.with_suffix(path.suffix + ".json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if checksum(path) != manifest["sha256"]:
        return {"valid": False, "reason": "checksum mismatch"}
    if path.suffix == ".sqlite3":
        with sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True) as db:
            integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                return {"valid": False, "reason": integrity}
            tables = db.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        return {"valid": True, "type": "sqlite", "tables": tables, "sha256": manifest["sha256"]}
    if path.suffix == ".sql":
        if path.stat().st_size == 0:
            return {"valid": False, "reason": "empty SQL dump"}
        return {"valid": True, "type": "mysql-sql-dump", "sha256": manifest["sha256"], "restore_test_required": True}
    return {"valid": False, "reason": "unsupported backup type"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.backup), indent=2))
