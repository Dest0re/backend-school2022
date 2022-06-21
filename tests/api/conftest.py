import pytest
from alembic.command import upgrade
from sqlalchemy import create_engine

from megamarket.api.__main__ import parser
from megamarket.api.app import create_app


@pytest.fixture
def migrated_postgres(alembic_config, postgres):
    upgrade(alembic_config, 'head')

    return postgres


@pytest.fixture
def arguments(aiomisc_unused_port, migrated_postgres):
    return parser.parse_args(
        [
            '--log-level=DEBUG',
            '--api-address=127.0.0.1',
            f'--api-port={aiomisc_unused_port}',
            f'--pg-url={migrated_postgres}',
        ]
    )


@pytest.fixture
async def api_server(arguments, aiohttp_server):
    app = create_app(arguments)
    server = await aiohttp_server(app, port=arguments.api_port)

    try:
        yield server
    finally:
        await server.close()


@pytest.fixture
async def api_client(aiohttp_client, api_server):
    client = await aiohttp_client(api_server)

    try:
        yield client
    finally:
        await client.close()


@pytest.fixture
def migrated_postgres_connection(migrated_postgres):
    engine = create_engine(migrated_postgres)

    connection = engine.connect()

    try:
        yield connection
    finally:
        connection.close()
        engine.dispose()
