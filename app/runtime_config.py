from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from pathlib import Path


@dataclass(frozen=True)
class RuntimeConfig:
    app_env: str
    session_secret_key: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_db_url: str

    @property
    def has_supabase_http(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)

    @property
    def has_supabase_db(self) -> bool:
        return bool(self.supabase_db_url)


def load_runtime_config() -> RuntimeConfig:
    env_values = _load_dotenv_values(Path('.env'))
    return RuntimeConfig(
        app_env=_get_env("APP_ENV", "development", env_values),
        session_secret_key=_get_env("SESSION_SECRET_KEY", "ww_gg-dev-session-key", env_values),
        supabase_url=_get_env("SUPABASE_URL", "", env_values),
        supabase_anon_key=_get_env("SUPABASE_ANON_KEY", "", env_values),
        supabase_service_role_key=_get_env("SUPABASE_SERVICE_ROLE_KEY", "", env_values),
        supabase_db_url=_get_env("SUPABASE_DB_URL", "", env_values),
    )


def _get_env(key: str, default: str, env_values: dict[str, str]) -> str:
    return getenv(key, env_values.get(key, default))


def _load_dotenv_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values
