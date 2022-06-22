import logging
import os
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

from aiohttp.web import Application
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

CENSORED = '***'
MAX_QUERY_ARGS = 32767
MAX_INTEGER = 2147483647

DEFAULT_PG_URL = 'postgresql://user:strngpsswrd@localhost/megamarket'
PROJECT_PATH = Path(__file__).parent.parent.resolve()


def max_query_len_with(args: int):
    return MAX_QUERY_ARGS // args


log = logging.getLogger(__name__)


async def setup_pg(app: Application, args: Namespace):
    pg_url = args.pg_url.with_scheme(args.pg_url.scheme + '+asyncpg')
    db_info = pg_url.with_password(CENSORED)
    log.info('Connecting to database: %s', db_info)

    # app['pg'] = PG()
    # await app['pg'].init(
    #     str(args.pg_url)
    # )

    app['pg'] = create_async_engine(
        str(pg_url),
        #echo=True
    )

    async with app['pg'].begin() as conn:
        await conn.execute(text('SELECT 1'))

    log.info('Connected to database %s', db_info)

    try:
        yield
    finally:
        log.info('Disconnecting from database: %s', db_info)

        await app['pg'].dispose()

        log.info('Disconnected from database %s', db_info)


def make_alembic_config(cmd_opts: Namespace | SimpleNamespace, project_dir: str = str(PROJECT_PATH)) -> Config:
    if not os.path.isabs(cmd_opts.config):
        cmd_opts.config = os.path.join(project_dir, cmd_opts.config)

    config = Config(file_=cmd_opts.config, ini_section=cmd_opts.name, cmd_opts=cmd_opts)

    alembic_location = config.get_main_option('script_location')
    if not os.path.isabs(alembic_location):
        config.set_main_option('script_location', os.path.join(project_dir, alembic_location))

    config.set_main_option('sqlalchemy.url', str(cmd_opts.pg_url))

    return config
