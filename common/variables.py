""" Содержит разные глобальные переменные проекта. """

import logging

DEFAULT_PORT = 7777
""" Порт по умолчанию для сетевого взаимодействия """

DEFAULT_IP_ADDRESS = '127.0.0.1'
""" IP адрес по умолчанию для подключения клиента """

MAX_CONNECTIONS = 5
""" Максимальная очередь подключений. """

MAX_PACKAGE_LENGTH = 1024
""" Максимальная длинна сообщения в байтах """

ENCODING = 'utf-8'
""" Кодировка проекта """

LOGGING_LEVEL = logging.DEBUG
"""Текущий уровень логирования"""

SERVER_CONFIG = 'server.ini'
"""База данных для хранения данных сервера:"""


ACTION = 'action'
TIME = 'time'
USER = 'user'
ACCOUNT_NAME = 'account_name'
SENDER = 'from'
DESTINATION = 'to'
DATA = 'bin'
PUBLIC_KEY = 'pubkey'

PRESENCE = 'presence'
RESPONSE = 'response'
ERROR = 'error'
MESSAGE = 'message'
MESSAGE_TEXT = 'mess_text'
EXIT = 'exit'
GET_CONTACTS = 'get_contacts'
LIST_INFO = 'data_list'
REMOVE_CONTACT = 'remove'
ADD_CONTACT = 'add'
USERS_REQUEST = 'get_users'
PUBLIC_KEY_REQUEST = 'pubkey_need'

# Словари - ответы:
RESPONSE_200 = {RESPONSE: 200}
"""Ответ 200."""


RESPONSE_202 = {RESPONSE: 202,
                LIST_INFO: None
                }
"""Ответ 202."""

RESPONSE_400 = {
    RESPONSE: 400,
    ERROR: None
}
"""Ответ 400."""

RESPONSE_205 = {
    RESPONSE: 205
}
"""Ответ 205."""

RESPONSE_511 = {
    RESPONSE: 511,
    DATA: None
}
"""Ответ 511."""
