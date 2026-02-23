#!/usr/bin/env python3
"""Hot backup script for SQLite database."""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def backup(src_path: str = "data/clinical.db", backup_dir: str = "backups") -> str:
    """Perform a hot backup using the SQLite Backup API.

    Args:
        src_path: Path to source database
        backup_dir: Directory to store backups

    Returns:
        Path to the created backup file

    Raises:
        FileNotFoundError: If source database doesn't exist
        sqlite3.Error: If backup operation fails
    """
    src = Path(src_path)
    if not src.exists():
        raise FileNotFoundError(f"Source database not found: {src}")

    # Create backup directory if it doesn't exist
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)

    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst_name = backup_path / f"clinical_{timestamp}.db"

    # Perform hot backup using SQLite Backup API
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(dst_name))

    try:
        with dst_conn:
            src_conn.backup(dst_conn)  # Copies pages safely while DB is active
    finally:
        dst_conn.close()
        src_conn.close()

    print(f"Backup created: {dst_name}")
    return str(dst_name)


def main() -> int:
    """Main entry point for CLI usage."""
    try:
        backup()
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except sqlite3.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
