from datetime import date, timedelta

from database.database import Database
from lexicon.lexicon import STILL_HURTS

PERIODS = {"week": 7, "month": 30, "all": 10_000}


def fmt_day(day: str) -> str:
    return f"{day[8:10]}.{day[5:7]}"


def fmt_episode(e) -> str:
    end = e["end"] or STILL_HURTS.lower()
    line = f"• {fmt_day(e['day'])} {e['start']}–{end}: {e['intensity'].lower()}, {e['kind'].lower()}, {e['side'].lower()}"
    if e["meds"] != "Нет":
        line += f"\n   препараты: {e['meds']}"
    if e["cause"] != "Нет":
        line += f"\n   причина: {e['cause']}"
    return line


def build_stats(db: Database, period: str) -> str:
    days = PERIODS.get(period, 7)
    since = date.today() - timedelta(days=days - 1)
    episodes = db.episodes_since(since)
    pings, no_pain = db.pings_since(since)

    title = "за всё время" if period == "all" else f"за {days} дней (с {fmt_day(since.isoformat())})"
    lines = [
        f"<b>Статистика {title}</b>",
        f"Дней с головной болью: {len({e['day'] for e in episodes})}",
        f"Эпизодов: {len(episodes)}",
        f"Ответов на опрос: {pings}, из них «не болит»: {no_pain}",
    ]
    if episodes:
        lines += ["", *map(fmt_episode, episodes)]
    return "\n".join(lines)
