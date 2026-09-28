import sqlite3
from datetime import date, datetime

from lexicon.lexicon import QUESTIONS

FIELDS = [key for key, _, _ in QUESTIONS]


class Database:
    def __init__(self, path: str):
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(f"""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY, day TEXT, {", ".join(f"{f} TEXT" for f in FIELDS)}
            );
            CREATE TABLE IF NOT EXISTS pings (id INTEGER PRIMARY KEY, ts TEXT, pain INTEGER);
            CREATE TABLE IF NOT EXISTS pills (id INTEGER PRIMARY KEY, ts TEXT, taken INTEGER);
            CREATE TABLE IF NOT EXISTS pending (id INTEGER PRIMARY KEY, kind TEXT, message_id INTEGER);
        """)

    # ---------- эпизоды ----------

    def add_episode(self, answers: dict, day: date | None = None):
        cols = ["day", *FIELDS]
        values = [(day or date.today()).isoformat(), *(answers.get(f) for f in FIELDS)]
        with self.con:
            self.con.execute(
                f"INSERT INTO episodes ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", values
            )

    def open_episode(self) -> sqlite3.Row | None:
        return self.con.execute("SELECT * FROM episodes WHERE end IS NULL ORDER BY id DESC LIMIT 1").fetchone()

    def close_episode(self, end: str):
        with self.con:
            self.con.execute("UPDATE episodes SET end = ? WHERE end IS NULL", (end,))

    def episode(self, episode_id: int) -> sqlite3.Row | None:
        return self.con.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)).fetchone()

    def last_episodes(self, limit: int = 10) -> list[sqlite3.Row]:
        return self.con.execute("SELECT * FROM episodes ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def update_episode(self, episode_id: int, field: str, value: str):
        if field not in FIELDS:
            raise ValueError(field)
        with self.con:
            self.con.execute(f"UPDATE episodes SET {field} = ? WHERE id = ?", (value, episode_id))

    def delete_episode(self, episode_id: int):
        with self.con:
            self.con.execute("DELETE FROM episodes WHERE id = ?", (episode_id,))

    def episodes_since(self, day: date) -> list[sqlite3.Row]:
        return self.con.execute("SELECT * FROM episodes WHERE day >= ? ORDER BY id", (day.isoformat(),)).fetchall()

    # ---------- опросы и таблетки ----------

    def add_ping(self, pain: bool):
        with self.con:
            self.con.execute("INSERT INTO pings (ts, pain) VALUES (?, ?)", (datetime.now().isoformat(), pain))

    def add_pill(self) -> int:
        with self.con:
            cur = self.con.execute("INSERT INTO pills (ts) VALUES (?)", (datetime.now().isoformat(),))
        return cur.lastrowid

    def set_pill(self, pill_id: int, taken: bool):
        with self.con:
            self.con.execute("UPDATE pills SET taken = ? WHERE id = ?", (taken, pill_id))

    def pending_pill(self) -> int | None:
        """id последнего напоминания о таблетках, на которое ещё не ответили."""
        row = self.con.execute("SELECT id FROM pills WHERE taken IS NULL ORDER BY id DESC LIMIT 1").fetchone()
        return row["id"] if row else None

    # ---------- неотвеченные сообщения ----------

    def add_pending(self, kind: str, message_id: int):
        with self.con:
            self.con.execute("INSERT INTO pending (kind, message_id) VALUES (?, ?)", (kind, message_id))

    def take_pending(self, kind: str) -> list[int]:
        """Возвращает id неотвеченных сообщений этого типа и забывает их."""
        rows = self.con.execute("SELECT message_id FROM pending WHERE kind = ?", (kind,)).fetchall()
        with self.con:
            self.con.execute("DELETE FROM pending WHERE kind = ?", (kind,))
        return [row["message_id"] for row in rows]

    # ---------- статистика и выгрузка ----------

    def pings_since(self, day: date) -> tuple[int, int]:
        """Возвращает (всего ответов, ответов «нет»)."""
        row = self.con.execute(
            "SELECT COUNT(*), COALESCE(SUM(pain = 0), 0) FROM pings WHERE ts >= ?", (day.isoformat(),)
        ).fetchone()
        return row[0], row[1]

    def pills_since(self, day: date) -> tuple[int, int]:
        """Возвращает (всего напоминаний, из них с выпитыми таблетками)."""
        row = self.con.execute(
            "SELECT COUNT(*), COALESCE(SUM(taken = 1), 0) FROM pills WHERE ts >= ?", (day.isoformat(),)
        ).fetchone()
        return row[0], row[1]

    def dump(self, table: str) -> tuple[list[str], list[tuple]]:
        """Возвращает (названия колонок, все строки) для выгрузки в CSV."""
        cur = self.con.execute(f"SELECT * FROM {table}")
        return [d[0] for d in cur.description], [tuple(r) for r in cur.fetchall()]
