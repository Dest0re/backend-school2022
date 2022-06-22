import os
from pathlib import Path

from alembic.config import CommandLine, Config

from megamarket.utils.pg import DEFAULT_PG_URL, make_alembic_config


def main():
    alembic = CommandLine()
    alembic.parser.add_argument(
        '--pg-url',
        default=os.getenv('MEGAMARKET_PG_URL', DEFAULT_PG_URL),
        help='Database URL [env var: MEGAMARKET_PG_URL]'
    )

    options = alembic.parser.parse_args()

    if 'cmd' not in options:
        alembic.parser.error('Too few arguments')
        exit(128)
    else:
        config = make_alembic_config(options)
        exit(alembic.run_cmd(config, options))


if __name__ == '__main__':
    main()
