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
        """)

    def add_episode(self, answers: dict):
        cols = ["day", *FIELDS]
        values = [date.today().isoformat(), *(answers.get(f) for f in FIELDS)]
        with self.con:
            self.con.execute(
                f"INSERT INTO episodes ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", values
            )

    def open_episode(self) -> sqlite3.Row | None:
        return self.con.execute("SELECT * FROM episodes WHERE end IS NULL ORDER BY id DESC LIMIT 1").fetchone()

    def close_episode(self, end: str):
        with self.con:
            self.con.execute("UPDATE episodes SET end = ? WHERE end IS NULL", (end,))

    def add_ping(self, pain: bool):
        with self.con:
            self.con.execute("INSERT INTO pings (ts, pain) VALUES (?, ?)", (datetime.now().isoformat(), pain))

    def episodes_since(self, day: date) -> list[sqlite3.Row]:
        return self.con.execute("SELECT * FROM episodes WHERE day >= ? ORDER BY id", (day.isoformat(),)).fetchall()

    def pings_since(self, day: date) -> tuple[int, int]:
        """Возвращает (всего ответов, ответов «нет»)."""
        row = self.con.execute(
            "SELECT COUNT(*), COALESCE(SUM(pain = 0), 0) FROM pings WHERE ts >= ?", (day.isoformat(),)
        ).fetchone()
        return row[0], row[1]

    def dump(self, table: str) -> tuple[list[str], list[tuple]]:
        """Возвращает (названия колонок, все строки) для выгрузки в CSV."""
        cur = self.con.execute(f"SELECT * FROM {table}")
        return [d[0] for d in cur.description], [tuple(r) for r in cur.fetchall()]
