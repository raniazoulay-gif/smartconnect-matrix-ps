#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-off maintenance: reset the UNICO 'manager' account password.

Runs against whatever DB the app is configured for (Railway Postgres in prod via
DATABASE_URL, or the local SQLite fallback). Uses the app's own bcrypt hashing so
the new hash is fully compatible with login. The new password is passed as an
argument or the NEW_MANAGER_PASSWORD env var — it is never hardcoded here.

Usage:
    python reset_manager_password.py <new_password>
    # or:  NEW_MANAGER_PASSWORD=... python reset_manager_password.py

On Railway (env vars injected automatically):
    railway run python reset_manager_password.py <new_password>
"""
import os
import sys

from database import get_db, hash_password, _is_postgres


def main():
    new_pw = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NEW_MANAGER_PASSWORD", "")).strip()
    if not new_pw:
        sys.exit("usage: python reset_manager_password.py <new_password>  "
                 "(or set NEW_MANAGER_PASSWORD)")

    username = os.environ.get("MANAGER_USERNAME", "manager")
    db = get_db()
    try:
        row = db.execute("SELECT id, username, role FROM users WHERE username=?",
                         (username,)).fetchone()
        if not row:
            sys.exit(f"no user named '{username}' found — nothing changed. "
                     f"(backend={'postgres' if _is_postgres() else 'sqlite'})")

        db.execute("UPDATE users SET password_hash=? WHERE username=?",
                   (hash_password(new_pw), username))
        db.commit()
        print(f"OK - password reset for user '{row['username']}' "
              f"(role={row['role']}, backend={'postgres' if _is_postgres() else 'sqlite'}).")
        print("The manager can now log in with the new password.")
    finally:
        try:
            db.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
