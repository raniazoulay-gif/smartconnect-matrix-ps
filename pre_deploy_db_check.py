# -*- coding: utf-8 -*-
"""
בדיקה+ניקוי חיבורי DB תקועים — להריץ רגע לפני deploy ל-UNICO.
מציג חיבורים פתוחים, ומנתק idle-in-transaction / חיבורים תקועים
כדי שה-ALTER TABLE ב-startup של הקונטיינר החדש לא ייתקע על locks.
(זה מה שהפיל את הפריסה ב-2026-07-13.)

בטוח להריץ לפני deploy: מנתק רק חיבורים שאינם החיבור הנוכחי.
הרצה:  python pre_deploy_db_check.py
"""
import re, psycopg2

txt = open(r"C:\Users\Ran Azoulay\backup_unico.py", encoding="utf-8").read()
DB_URL = re.search(r"DB_URL\s*=\s*['\"](postgresql://[^'\"]+)['\"]", txt).group(1)

conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()

print("=== חיבורים פעילים (pid | state | גיל טרנזקציה | query) ===")
cur.execute("""
    SELECT pid, state, COALESCE((now()-xact_start)::text,'-'), left(query,60)
    FROM pg_stat_activity
    WHERE datname = current_database() AND pid <> pg_backend_pid()
    ORDER BY xact_start NULLS LAST
""")
rows = cur.fetchall()
for r in rows:
    print(r)
print(f"סה\"כ חיבורים אחרים: {len(rows)}")

# מנתק חיבורי zombie: idle-in-transaction (הרוצחים מהאירוע) + כל חיבור אחר שאינו שלנו
cur.execute("""
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = current_database() AND pid <> pg_backend_pid()
      AND (state = 'idle in transaction'
           OR (now() - COALESCE(xact_start, query_start)) > interval '2 minutes')
""")
killed = cur.fetchall()
print(f"\nנותקו {len(killed)} חיבורים תקועים.")
conn.close()
print("[OK] ה-DB מוכן ל-deploy.")
