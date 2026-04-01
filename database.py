import psycopg2
import os
import json

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id SERIAL PRIMARY KEY,
        name TEXT,
        phone TEXT,
        date TEXT,
        time TEXT,
        status TEXT DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        user_id TEXT PRIMARY KEY,
        step TEXT,
        data TEXT
    )
    """)

    conn.commit()
    cur.close()
    conn.close()


def load_session(user_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT step, data FROM sessions WHERE user_id=%s", (user_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if row:
        return {"step": row[0], "data": json.loads(row[1])}

    return {"step": 0, "data": {}}


def save_session(user_id, s):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO sessions (user_id, step, data)
    VALUES (%s, %s, %s)
    ON CONFLICT (user_id)
    DO UPDATE SET step=%s, data=%s
    """, (user_id, s["step"], json.dumps(s["data"]),
          s["step"], json.dumps(s["data"])))

    conn.commit()
    cur.close()
    conn.close()