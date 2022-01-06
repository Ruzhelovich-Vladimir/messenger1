from common.errors import ServerError
from common.utils import *
import binascii
import hashlib
import hmac
import socket
import sys
import time
import threading
from PyQt5.QtCore import pyqtSignal, QObject

sys.path.append('../')

logger = logging.getLogger('client')
socket_lock = threading.Lock()


class ClientTransport(threading.Thread, QObject):
    """ Class of interaction between client app and server app """

    # Signal of new client message
    new_message = pyqtSignal(str)
    # Signal of lost client connection
    connection_lost = pyqtSignal()
    # Signal of 205 Reset Content
    message_205 = pyqtSignal()

    def __init__(self, port, address, database, username, passwd, keys):

        threading.Thread.__init__(self)
        QObject.__init__(self)

        self.server_address = address
        self.server_port = port
        self.database = database
        self.username = username
        self.password = passwd
        self.transport = None
        self.keys = keys

        # Запускаем процедуру авторизации
        # Получаем хэш пароля
        self.passwd_bytes = self.password.encode('utf-8')
        salt = self.username.lower().encode('utf-8')
        self.passwd_hash = hashlib.pbkdf2_hmac(
            'sha512', self.passwd_bytes, salt, 10000)
        self.passwd_hash_string = binascii.hexlify(self.passwd_hash)

        logger.debug(f'Passwd hash ready: {self.passwd_hash_string}')

        # Получаем публичный ключ и декодируем его из байтов
        self.pubkey = self.keys.publickey().export_key().decode('ascii')

        self.__connection_init()
        self.update_users_and_contact_list()
        self.running = True

    def __connection_init(self):
        """ Initialize the socket (transport)
        and notify the server about it """
        if not self.__init_transport():
            self.__critical_error('Failed to connect to server')
        logger.debug('The connection to the server is established.')
        try:
            with socket_lock:
                send_message(self.transport,
                             self.__create_presence())  # Send msg presence
                ans = get_message(self.transport)
                logger.debug(f'Server response = {ans}.')

                if RESPONSE in ans:
                    if ans[RESPONSE] == 400:
                        raise ServerError(ans[ERROR])
                    elif ans[RESPONSE] == 511:
                        # If 511 Network Authentication Required then
                        ans_data = ans[DATA]
                        digest = hmac.new(
                            self.passwd_hash_string,
                            ans_data.encode('utf-8'),
                            'MD5').digest()
                        my_ans = RESPONSE_511
                        my_ans[DATA] = binascii.b2a_base64(
                            digest).decode('ascii')
                        send_message(self.transport, my_ans)
                        ans = get_message(self.transport)
                        self.process_server_ans(ans)
        except (OSError, json.JSONDecodeError):
            self.__critical_error('Lost connection to server')
        logger.info('The connection to the server is established')

    def __init_transport(self):
        """ Initialize the socket (transport)"""
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.transport.settimeout(5)
        # return flag
        connected = False
        for i in range(5):
            logger.info(f'Attempt #{i + 1} to connect to server')
            try:
                self.transport.connect((self.server_address, self.server_port))
            except (OSError, ConnectionRefusedError):
                time.sleep(1)
                continue
            connected = True
            break

        # Если соединится не удалось - исключение
        if not connected:
            logger.critical('Не удалось установить соединение с сервером')
            raise ServerError('Не удалось установить соединение с сервером')

        logger.debug('Starting auth dialog.')

        return connected

    def __create_presence(self):
        """ Запрос о присутствии клиента """
        out = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.username,
                PUBLIC_KEY: self.pubkey
            }
        }
        logger.debug(
            f'{self.username}: Generated {PRESENCE} '
            f'message for user {self.username}')
        return out

    def process_server_ans(self, message):
        """ Функция обрабатывающая сообщения от сервера.
        Ничего не возвращает. Генерирует исключение при ошибке. """

        logger.debug(f'Parse messages from the server: {message}')

        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return
            elif message[RESPONSE] == 400:
                raise ServerError(f'{message[ERROR]}')
            elif message[RESPONSE] == 205:
                self.user_list_update()
                self.contacts_list_update()
                self.message_205.emit()
            else:
                logger.debug(
                    f'Unknown confirmation code accepted: {message[RESPONSE]}')
        # Если это сообщение от пользователя, то добавляем в базу, даём сигнал
        # о новом сообщении
        elif ACTION in message and message[ACTION] == MESSAGE \
                and SENDER in message and DESTINATION in message \
                and MESSAGE_TEXT in message \
                and message[DESTINATION] == self.username:
            logger.debug(
                f'Received message from user: {message[SENDER]}, '
                f'"{message[MESSAGE_TEXT]}"')
            self.database.save_message(
                message[SENDER],
                self.username,
                message[MESSAGE_TEXT])
            self.new_message.emit(message[SENDER])

    def update_users_and_contact_list(self):
        """ Updating user and contact lists """
        try:
            self.user_list_update()
            self.contacts_list_update()
        except OSError as err:
            if err.errno:
                self.__critical_error('Lost connection to server')
            logger.error('Timeout when updating user and contact lists')
        except json.JSONDecodeError:
            self.__critical_error('Lost connection to server')

    def contacts_list_update(self):
        """ Updating contact lists """
        logger.debug(f'The request of contact list of user: {self.username}')
        req = {
            ACTION: GET_CONTACTS,
            TIME: time.time(),
            USER: self.username
        }
        logger.debug(f'Request generated: {req}')
        with socket_lock:
            send_message(self.transport, req)
            ans = get_message(self.transport)
        logger.debug(f'Received a response: {ans}')
        if RESPONSE in ans and ans[RESPONSE] == 202:
            for contact in ans[LIST_INFO]:
                self.database.add_contact(contact)
        else:
            logger.error(f'Failed to update contact list ({self.username})')

    def user_list_update(self):
        """ Updating the table of known users """
        logger.debug(f'The request of known users list ({self.username})')
        req = {
            ACTION: USERS_REQUEST,
            TIME: time.time(),
            ACCOUNT_NAME: self.username
        }
        with socket_lock:
            send_message(self.transport, req)
            ans = get_message(self.transport)
        if RESPONSE in ans and ans[RESPONSE] == 202:
            self.database.add_users(ans[LIST_INFO])
        else:
            logger.error(
                f'Failed to update known users list ({self.username})')

    def key_request(self, user):
        """ Метод запрашивающий с сервера публичный ключ пользователя. """
        logger.debug(f'Запрос публичного ключа для {user}')
        req = {
            ACTION: PUBLIC_KEY_REQUEST,
            TIME: time.time(),
            ACCOUNT_NAME: user
        }
        with socket_lock:
            send_message(self.transport, req)
            ans = get_message(self.transport)
        if RESPONSE in ans and ans[RESPONSE] == 511:
            return ans[DATA]
        else:
            logger.error(f'Не удалось получить ключ собеседника{user}.')

    def add_contact(self, contact):
        """ Добавление нового контакта """
        req = {
            ACTION: ADD_CONTACT,
            TIME: time.time(),
            USER: self.username,
            ACCOUNT_NAME: contact
        }
        logger.debug(f'Create contact {contact} ({self.username})')
        with socket_lock:
            send_message(self.transport, req)
            self.process_server_ans(get_message(self.transport))

    def remove_contact(self, contact):
        """ Удаление контакта """
        logger.debug(f'Delete contact {contact} ({self.username})')
        req = {
            ACTION: REMOVE_CONTACT,
            TIME: time.time(),
            USER: self.username,
            ACCOUNT_NAME: contact
        }
        with socket_lock:
            send_message(self.transport, req)
            self.process_server_ans(get_message(self.transport))

    def transport_shutdown(self):
        """ Отправка сообщения на сервер
        об закрытия соединения и выходе клиента"""
        self.running = False
        message = {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.username
        }
        with socket_lock:
            try:
                send_message(self.transport, message)
            except OSError:
                pass
        logger.debug('The transport shutdown')
        time.sleep(0.5)

    def send_message(self, to, message):
        """ Sending a message to the server """
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.username,
            DESTINATION: to,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        with socket_lock:
            send_message(self.transport, message_dict)
            self.process_server_ans(get_message(self.transport))
            logger.info(f'Message sent to user {to}')

    def run(self):
        logger.debug(
            'The process of receiving messages from the server has started...')
        while self.running:
            # Отдыхаем секунду и снова пробуем захватить сокет.
            # Если не сделать тут задержку, то отправка может достаточно долго
            # ждать освобождения сокета.
            time.sleep(1)
            with socket_lock:
                try:
                    self.transport.settimeout(0.5)
                    message = get_message(self.transport)
                except OSError as err:
                    if err.errno:
                        logger.critical(f'Lost connection to server.')
                        self.running = False
                        self.connection_lost.emit()
                except (ConnectionError, ConnectionAbortedError,
                        ConnectionResetError, json.JSONDecodeError, TypeError):
                    logger.critical(f'Lost connection to server.')
                    self.running = False
                    self.connection_lost.emit()
                else:
                    logger.debug(
                        f'Received a message from the server: {message}')
                    self.process_server_ans(message)
                finally:
                    self.transport.settimeout(5)

    @staticmethod
    def __critical_error(msg):
        """ Handling critical errors """
        logger.critical(msg)
        raise ServerError(msg)
