import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "vocab.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS handout (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_number INTEGER NOT NULL UNIQUE,
            source_image_path TEXT,
            uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS vocabulary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handout_id INTEGER REFERENCES handout(id) ON DELETE CASCADE,
            word TEXT NOT NULL,
            part_of_speech TEXT,
            definition TEXT NOT NULL,
            example TEXT,
            example_form TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (handout_id, word)
        );

        CREATE TABLE IF NOT EXISTS quiz_attempt (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vocabulary_id INTEGER NOT NULL REFERENCES vocabulary(id) ON DELETE CASCADE,
            user_input TEXT,
            is_correct INTEGER NOT NULL,
            attempted_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )

    # 예전 DB(example_form 컬럼 없음)를 쓰던 경우를 위한 간단 마이그레이션
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(vocabulary)")
    existing_columns = {row[1] for row in cur.fetchall()}
    if "example_form" not in existing_columns:
        cur.execute("ALTER TABLE vocabulary ADD COLUMN example_form TEXT")

    conn.commit()
    conn.close()


def save_handout(day_number, source_image_path, words):
    """words: [{word, pos, definition, example, example_form}, ...].
    반환값: (handout_id, 새로 저장된 수, 중복이라 건너뛴 수, 필수값 누락으로 건너뛴 수)
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM handout WHERE day_number = ?", (day_number,))
    row = cur.fetchone()
    if row:
        handout_id = row[0]
    else:
        cur.execute(
            "INSERT INTO handout (day_number, source_image_path) VALUES (?, ?)",
            (day_number, source_image_path),
        )
        handout_id = cur.lastrowid

    saved_count = 0
    duplicate_count = 0
    skipped_count = 0
    for w in words:
        word = (w.get("word") or "").strip()
        definition = (w.get("definition") or "").strip()
        if not word or not definition:
            skipped_count += 1
            continue

        example = w.get("example")
        example_form = (w.get("example_form") or "").strip() or None

        try:
            cur.execute(
                """INSERT INTO vocabulary
                   (handout_id, word, part_of_speech, definition, example, example_form)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (handout_id, word, w.get("pos"), definition, example, example_form),
            )
            saved_count += 1
        except sqlite3.IntegrityError:
            duplicate_count += 1

    conn.commit()
    conn.close()
    return handout_id, saved_count, duplicate_count, skipped_count


def get_days():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT day_number FROM handout ORDER BY day_number")
    days = [r[0] for r in cur.fetchall()]
    conn.close()
    return days


def get_words(day_number=None):
    """day_number가 None이면 전체, 아니면 해당 Day만.
    반환 행: (id, word, pos, definition, example, example_form)
    """
    conn = get_connection()
    cur = conn.cursor()
    if day_number is None:
        cur.execute(
            """SELECT id, word, part_of_speech, definition, example, example_form
               FROM vocabulary ORDER BY id"""
        )
    else:
        cur.execute(
            """SELECT v.id, v.word, v.part_of_speech, v.definition, v.example, v.example_form
               FROM vocabulary v JOIN handout h ON v.handout_id = h.id
               WHERE h.day_number = ?
               ORDER BY v.id""",
            (day_number,),
        )
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_handout_by_day(day_number):
    """해당 Day의 handout과 그 안의 모든 단어(+퀴즈 기록)를 삭제. 삭제됐으면 1, 없었으면 0."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM handout WHERE day_number = ?", (day_number,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


def update_word(vocabulary_id, word, pos, definition, example, example_form):
    conn = get_connection()
    conn.execute(
        """UPDATE vocabulary
           SET word = ?, part_of_speech = ?, definition = ?, example = ?, example_form = ?
           WHERE id = ?""",
        (word, pos, definition, example, example_form, vocabulary_id),
    )
    conn.commit()
    conn.close()


def record_attempt(vocabulary_id, user_input, is_correct):
    conn = get_connection()
    conn.execute(
        "INSERT INTO quiz_attempt (vocabulary_id, user_input, is_correct) VALUES (?, ?, ?)",
        (vocabulary_id, user_input, int(is_correct)),
    )
    conn.commit()
    conn.close()


def get_stats():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM vocabulary")
    total_words = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*), SUM(is_correct) FROM quiz_attempt")
    total_attempts, total_correct = cur.fetchone()
    conn.close()
    return {
        "total_words": total_words,
        "total_attempts": total_attempts or 0,
        "total_correct": total_correct or 0,
    }
