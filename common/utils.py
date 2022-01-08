"""
Другие утилиты
"""

# from common.decos import log
from common.errors import IncorrectDataReceivedError, NonDictInputError
from common.variables import *
import json
import sys
sys.path.append('../')

logger = logging.getLogger('utils')

# @log


def get_message(client):
    """
    Функция принимает сообщения в формате JSON от удалённых компьютеров,
    декодирует полученное сообщение и проверяет что получен словарь.
    """

    encoded_response = client.recv(MAX_PACKAGE_LENGTH)
    if not encoded_response:
        return {}
    if isinstance(encoded_response, bytes):
        json_response = encoded_response.decode(ENCODING)
        response = None
        try:
            response = json.loads(json_response)
        except Exception as err:
            logger.error(f'Не возможно считать json объект:\n{json_response} '
                         f'- {err}')
        if isinstance(response, dict):
            return response
        else:
            raise IncorrectDataReceivedError
    else:
        raise IncorrectDataReceivedError


# @log
def send_message(sock, message):
    """
    Функция отправки словарей через сокет. Кодирует словарь в формат JSON
    и отправляет через сокет.
    """

    if not isinstance(message, dict):
        raise NonDictInputError
    js_message = json.dumps(message)
    encoded_message = js_message.encode(ENCODING)
    sock.send(encoded_message)
