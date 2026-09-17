from dataclasses import dataclass

from environs import Env


@dataclass
class Config:
    token: str
    user_id: int  # единственный пользователь бота
    db_path: str


def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path)
    return Config(
        token=env("BOT_TOKEN"),
        user_id=env.int("USER_ID"),
        db_path=env("DB_PATH", "headache.db"),
    )
