import argparse
import os
import sys

from Crypto.PublicKey import RSA
from PyQt5.QtWidgets import QApplication

from common.variables import *
from common.errors import ServerError
from common.decos import log
from client.database import ClientDatabase
from client.transport import ClientTransport
from client.main_window import ClientMainWindow
from client.start_dialog import UserNameDialog

logger = logging.getLogger('client')


@log
def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('address', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    parser.add_argument('-p', '--password', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    if not 1023 < namespace.port < 65536:
        logger.critical(
            f'Invalid port {namespace.port}. '
            f'The available value is from 1024 to 65535.')
        exit(1)
    result = (namespace.address, namespace.port, namespace.name,
              namespace.password)
    return result


def get_user_security(username):

    # Get security key
    # Загружаем ключи с файла, если же файла нет, то генерируем новую пару.
    #dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_path = os.getcwd()
    key_file = os.path.join(
        dir_path,
        'client',
        '.secrets',
        f'{username}.key')
    if not os.path.exists(key_file):
        user_keys = RSA.generate(2048, os.urandom)
        with open(key_file, 'wb') as key:
            key.write(user_keys.export_key())
    else:
        with open(key_file, 'rb') as key:
            user_keys = RSA.import_key(key.read())

    logger.debug("Keys successfully loaded.")
    return user_keys


if __name__ == '__main__':

    # TODO Решить баг с дублирование записей в списке контактов
    server_address, server_port, client_name, client_passwd = arg_parser()
    client_app = QApplication(sys.argv)

    if not client_name or not client_passwd:
        start_dialog = UserNameDialog()
        client_app.exec_()

        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            client_passwd = start_dialog.client_passwd.text()
            logger.debug(
                f'Using USERNAME = {client_name}, PASSWD = {client_passwd}.')
            del start_dialog
        else:
            exit(0)

    logger.info(
        f'Client application started with parameters server: '
        f'{server_address}:{server_port}, user name: {client_name}')

    keys = get_user_security(client_name)

    database = ClientDatabase(client_name)
    transport = None

    # Start demon
    try:
        transport = ClientTransport(
            server_port,
            server_address,
            database,
            client_name,
            client_passwd,
            keys)
    except ServerError as error:
        print(error.text)
        exit(1)
    transport.setDaemon(True)
    transport.start()

    # Start main application
    main_window = ClientMainWindow(database, transport)
    main_window.make_connection(transport)
    main_window.setWindowTitle(
        f'Messanger application (alpha release) - {client_name}')
    client_app.exec_()

    transport.transport_shutdown()
    transport.join()
