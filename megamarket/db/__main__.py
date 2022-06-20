import os
from pathlib import Path

from alembic.config import CommandLine, Config
from asyncpgsa import PG

from megamarket.utils.pg import DEFAULT_PG_URL


PROJECT_PATH = Path(__file__).parent.parent.resolve()


def main():
    alembic = CommandLine()
    alembic.parser.add_argument(
        '--pg-url',
        default=os.getenv('MEGAMARKET_PG_URL', DEFAULT_PG_URL),
        help='Database URL [env var: MEGAMARKET_PG_URL]'
    )

    options = alembic.parser.parse_args()

    if not os.path.isabs(options.config):
        options.config = os.path.join(PROJECT_PATH, options.config)

    config = Config(file_=options.config, ini_section=options.name, cmd_opts=options)

    alembic_location = config.get_main_option('script_location')
    if not os.path.isabs(alembic_location):
        config.set_main_option('script_location', os.path.join(PROJECT_PATH, alembic_location))

    config.set_main_option('sqlalchemy.url', options.pg_url)

    exit(alembic.run_cmd(config, options))


if __name__ == '__main__':
    main()
