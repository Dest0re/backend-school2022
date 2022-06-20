import logging
import os
import sys
import socket
import pwd

from aiohttp import web
from configargparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from yarl import URL
from aiomisc.utils import bind_socket
from setproctitle import setproctitle

from megamarket.utils.argparse import positive_int, clear_environ
from megamarket.api.app import create_app
from megamarket.utils.pg import DEFAULT_PG_URL

ENV_VAR_PREFIX = 'MEGAMARKET_'

logging.basicConfig(level=logging.DEBUG)


parser = ArgumentParser(
    auto_env_var_prefix=ENV_VAR_PREFIX,
    formatter_class=ArgumentDefaultsHelpFormatter
)

parser.add_argument('--user', required=False, type=pwd.getpwnam,
                    help='Changes UID')

group = parser.add_argument_group('API Options')
group.add_argument('--api-address', default='0.0.0.0',
                   help='IPv4/IPv6 address API server should listen on')
group.add_argument('--api-port', type=positive_int, default=8081,
                   help='TCP port API server should listen on')

group = parser.add_argument_group('PostgreSQL Options')
group.add_argument('--pg-url', type=URL, default=URL(DEFAULT_PG_URL),
                   help='URL to use to connect to the database')

group = parser.add_argument_group('Logging Options')
group.add_argument('--log-level', default='INFO',
                   choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])


def main():
    args = parser.parse_args()

    # clear_environ(lambda k: k.startswith(ENV_VAR_PREFIX))

    logging.basicConfig(level=args.log_level, format='color')

    sock = bind_socket(address=args.api_address, port=args.api_port,
                       proto_name='http')

    if args.user is not None:
        logging.info('Changing user to %r', args.user.pw_name)
        os.setgid(args.user.pw_gid)
        os.setuid(args.user.pw_uid)

    setproctitle(os.path.basename(sys.argv[0]))

    app = create_app(args)
    web.run_app(app, sock=sock)


if __name__ == '__main__':
    main()
