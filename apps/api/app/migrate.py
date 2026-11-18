from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config

# app/migrate.py → apps/api/alembic.ini, locally and in the image (/var/task/alembic.ini)
ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"

def handler(event: dict[str, Any], context: Any) -> dict[str, str]:
    command.upgrade(Config(str(ALEMBIC_INI)), "head")
    return {"status": "migrated"}