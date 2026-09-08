from logging.config import fileConfig

from alembic import context
from flask import current_app

from models import db


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = db.metadata


def get_engine():
    return current_app.extensions["migrate"].db.engine


def run_migrations_offline():
    context.configure(
        url=str(get_engine().url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    with get_engine().connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
