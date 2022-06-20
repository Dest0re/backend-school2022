import logging
from argparse import Namespace

from aiohttp.web import Application
from asyncpgsa import PG
from sqlalchemy import text
from sqlalchemy.dialects.postgresql.asyncpg import dialect
from sqlalchemy.ext.asyncio import create_async_engine
from yarl import URL


CENSORED = '***'
DEFAULT_PG_URL = 'postgresql://user:strngpsswrd@localhost/megamarket'
MAX_QUERY_ARGS = 32767


def max_query_len_with(args: int):
    return MAX_QUERY_ARGS // args


log = logging.getLogger(__name__)


async def setup_pg(app: Application, args: Namespace) -> PG:
    pg_url = args.pg_url.with_scheme(args.pg_url.scheme + '+asyncpg')
    db_info = pg_url.with_password(CENSORED)
    log.info('Connecting to database: %s', db_info)

    # app['pg'] = PG()
    # await app['pg'].init(
    #     str(args.pg_url)
    # )

    app['pg'] = create_async_engine(
        str(pg_url),
        echo=True
    )

    async with app['pg'].begin() as conn:
        await conn.execute(text('SELECT 1'))

    log.info('Connected to database %s', db_info)

    try:
        yield
    finally:
        log.info('Disconnecting from database: %s', db_info)

        # await app['pg'].close()

        log.info('Disconnected from database %s', db_info)
