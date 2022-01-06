from common.decos import log
from common.errors import IncorrectDataReceivedError, NonDictInputError
from common.variables import *
import json
import sys
sys.path.append('../')


logger = logging.getLogger('utils')

# Утилита приёма и декодирования сообщения
# принимает байты, выдаёт словарь, если принято что-то другое отдаёт ошибку
# значения


@log
def get_message(client):
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


# Утилита кодирования и отправки сообщения
# принимает словарь и отправляет его
@log
def send_message(sock, message):
    if not isinstance(message, dict):
        raise NonDictInputError
    js_message = json.dumps(message)
    encoded_message = js_message.encode(ENCODING)
    sock.send(encoded_message)
