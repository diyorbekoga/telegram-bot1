import sqlite3
from config import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS records")
    cur.execute("DROP TABLE IF EXISTS late_counts")
    cur.execute("DROP TABLE IF EXISTS fullname_counts")

    cur.execute("""
        CREATE TABLE records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            postdagi_odam TEXT,
            familiya TEXT,
            ism TEXT,
            fakultet TEXT,
            kurs TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE late_counts (
            user_id INTEGER PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE fullname_counts (
            fullname TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Baza tayyor:", DB_PATH)


def add_record(telegram_id, postdagi_odam, familiya, ism, fakultet, kurs):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO records
        (telegram_id, postdagi_odam, familiya, ism, fakultet, kurs)
        VALUES (?,?,?,?,?,?)
    """, (telegram_id, postdagi_odam, familiya, ism, fakultet, kurs))
    conn.commit()
    conn.close()


def increase_count(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT count FROM late_counts WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row:
        new_count = row[0] + 1
        cur.execute("UPDATE late_counts SET count=? WHERE user_id=?",
                    (new_count, user_id))
    else:
        new_count = 1
        cur.execute("INSERT INTO late_counts (user_id, count) VALUES (?,?)",
                    (user_id, new_count))
    conn.commit()
    conn.close()
    return new_count


def get_count(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT count FROM late_counts WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def increase_fullname_count(fullname):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT count FROM fullname_counts WHERE fullname=?", (fullname,))
    row = cur.fetchone()
    if row:
        new_count = row[0] + 1
        cur.execute("UPDATE fullname_counts SET count=? WHERE fullname=?",
                    (new_count, fullname))
    else:
        new_count = 1
        cur.execute("INSERT INTO fullname_counts (fullname, count) VALUES (?,?)",
                    (fullname, new_count))
    conn.commit()
    conn.close()
    return new_count


def get_fullname_count(fullname):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT count FROM fullname_counts WHERE fullname=?", (fullname,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0