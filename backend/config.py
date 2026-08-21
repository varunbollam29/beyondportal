import os
from dataclasses import dataclass

from dotenv import load_dotenv

# override=True: .env must always win over stray shell environment
# variables (e.g. a stale $env:SQL_CONNECTION_STRING left over from
# earlier troubleshooting in a long-running terminal session) — otherwise
# editing .env silently has no effect for as long as that shell lives.
load_dotenv(override=True)


@dataclass(frozen=True)
class Settings:
    storage_articles_container: str
    storage_videos_container: str
    sql_connection_string: str
    sql_admin_username: str
    sql_admin_password: str
    storage_connection_string: str
    foundry_endpoint: str
    foundry_api_key: str
    foundry_deployment_name: str
    # Optional — only needed for the Video Transcript & Summary agent
    # (Section 6 #9). This is a SEPARATE Azure resource from
    # foundry_endpoint/foundry_api_key above — confirmed with Varun
    # 2026-08-20, not the same beyondportal-foundry resource. Not
    # required at startup so the rest of the app isn't blocked on this.
    foundry_transcribe_endpoint: str | None
    foundry_transcribe_api_key: str | None
    foundry_transcribe_deployment_name: str | None
    foundry_legacy_api_version: str | None


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required config value: {name}")
    return value


def _load_settings() -> Settings:
    return Settings(
        storage_articles_container=_require_env("STORAGE_ARTICLES_CONTAINER"),
        storage_videos_container=_require_env("STORAGE_VIDEOS_CONTAINER"),
        sql_connection_string=_require_env("SQL_CONNECTION_STRING"),
        sql_admin_username=_require_env("SQL_ADMIN_USERNAME"),
        sql_admin_password=_require_env("SQL_ADMIN_PASSWORD"),
        storage_connection_string=_require_env("STORAGE_CONNECTION_STRING"),
        foundry_endpoint=_require_env("FOUNDRY_ENDPOINT"),
        foundry_api_key=_require_env("FOUNDRY_API_KEY"),
        foundry_deployment_name=_require_env("FOUNDRY_DEPLOYMENT_NAME"),
        foundry_transcribe_endpoint=os.environ.get("FOUNDRY_TRANSCRIBE_ENDPOINT") or None,
        foundry_transcribe_api_key=os.environ.get("FOUNDRY_TRANSCRIBE_API_KEY") or None,
        foundry_transcribe_deployment_name=os.environ.get("FOUNDRY_TRANSCRIBE_DEPLOYMENT_NAME") or None,
        foundry_legacy_api_version=os.environ.get("FOUNDRY_LEGACY_API_VERSION") or None,
    )


settings = _load_settings()
