from datetime import date, timedelta

from database.database import Database
from lexicon.lexicon import STILL_HURTS

PERIODS = {"week": 7, "month": 30, "all": 10_000}


def fmt_day(day: str) -> str:
    return f"{day[8:10]}.{day[5:7]}"


def fmt_episode(e) -> str:
    def val(key: str) -> str:
        return e[key].lower() if e[key] else "—"

    line = (f"• {fmt_day(e['day'])} {e['start'] or '—'}–{e['end'] or STILL_HURTS.lower()}: "
            f"{val('intensity')}, {val('kind')}, {val('side')}")
    if e["meds"] and e["meds"] != "Нет":
        line += f"\n   препараты: {e['meds']}"
    if e["cause"] and e["cause"] != "Нет":
        line += f"\n   причина: {e['cause']}"
    return line


def build_stats(db: Database, period: str) -> str:
    days = PERIODS.get(period, 7)
    since = date.today() - timedelta(days=days - 1)
    episodes = db.episodes_since(since)
    pings, no_pain = db.pings_since(since)
    pills, taken = db.pills_since(since)

    title = "за всё время" if period == "all" else f"за {days} дней (с {fmt_day(since.isoformat())})"
    lines = [
        f"<b>Статистика {title}</b>",
        f"Дней с головной болью: {len({e['day'] for e in episodes})}",
        f"Эпизодов: {len(episodes)}",
        f"Ответов на опрос: {pings}, из них «не болит»: {no_pain}",
        f"Напоминаний про таблетки: {pills}, выпито: {taken}",
    ]
    if episodes:
        lines += ["", *map(fmt_episode, episodes)]
    return "\n".join(lines)
