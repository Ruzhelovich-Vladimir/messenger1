import binascii
import hmac
import os
import threading
import select
import socket
import time

from common.descriptors import Port, Host
from common.metaclass import ServerVerifier
from common.variables import *
from common.utils import send_message, get_message
from common.decos import log

logger = logging.getLogger('server')

conf_lag_lock = threading.Lock()

global new_connection


class MessageProcessor(threading.Thread, metaclass=ServerVerifier):
    """
    Класс сервера
    """
    listen_port = Port()
    listen_address = Host()

    def __init__(self, host_port, database):
        """ Инициализация сервера """

        # Конструктор предка
        super().__init__()

        # Загрузка параметров командной строки, если нет параметров, то задаём
        # значения по умолканию.
        self.listen_address, self.listen_port = host_port

        logger.info(
            f'Запущен сервер, порт для подключений: {self.listen_port} , '
            f'адрес с которого принимаются подключения: '
            f'{self.listen_address}.')

        # Готовим сокет
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                self.transport.bind((self.listen_address, self.listen_port))
            except KeyboardInterrupt:
                break
            except socket.error:
                time.sleep(0.5)
            else:
                break
        self.transport.settimeout(0.5)

        # список клиентов
        self.clients = []
        # очередь сообщений
        self.messages = []

        # Словарь, содержащий имена пользователей и соответствующие им сокеты.
        self.names = dict()

        # Список полученных пакетов
        self.receive_data_lst = []
        # Список пакетов для отправки
        self.send_data_lst = []
        # Список ошибок
        self.err_lst = []

        # База данных сервера
        self.database = database

    @log
    def run(self):
        """ Запуск основного процесса """

        self.transport.listen(MAX_CONNECTIONS)
        while True:
            try:
                self.__wait_connect_client()
                self.__update_waiting_client_info()
                self.__receive_message()
                self.__process_messages()
            except KeyboardInterrupt:
                break

    def remove_client(self, client):
        """
        Метод обработчик клиента с которым прервана связь.
        Ищет клиента и удаляет его из списков и базы:
        """
        logger.info(f'Клиент {client.getpeername()} отключился от сервера.')
        for name in self.names:
            if self.names[name] == client:
                self.database.user_logout(name)
                del self.names[name]
                break
        self.clients.remove(client)
        client.close()

    def __wait_connect_client(self):
        """ Ждём подключения, если таймаут вышел, ловим исключение. """

        try:
            client, client_address = self.transport.accept()
        except OSError:
            return None

        logger.info(f'Установлено сведение с ПК {client_address}')
        self.clients.append(client)
        return client

    def __update_waiting_client_info(self):
        """ Обновляем информацию о ждущих клиентах """

        self.receive_data_lst = self.send_data_lst = self.err_lst = []
        try:
            if self.clients:
                self.receive_data_lst, self.send_data_lst, self.err_lst = \
                    select.select(self.clients, self.clients, [], 0)
        except OSError:
            pass

    def __receive_message(self):
        """ Принимаем сообщения и если ошибка, исключаем клиента """
        global new_connection

        if self.receive_data_lst:
            for client_with_message in self.receive_data_lst:
                try:
                    message = get_message(client_with_message)
                    self.__process_client_message(message, client_with_message)
                except OSError:
                    logger.info(
                        f'Клиент {client_with_message.getpeername()} '
                        f'отключился от сервера.')
                    # Ищем клиента в словаре клиентов, удаляем его из него из
                    # базы подключённых
                    for name in self.names:
                        if self.names[name] == client_with_message:
                            self.database.user_logout(name)
                            del self.names[name]
                            break
                    # Удаляем пользователя из списка подключённых
                    self.clients.remove(client_with_message)
                    with conf_lag_lock:
                        new_connection = True

    def __process_messages(self):
        """ Обрабатываем имеющиеся сообщения """
        global new_connection
        for message in self.messages:
            try:
                self.process_message(message, self.send_data_lst)
            except (ConnectionAbortedError, ConnectionError,
                    ConnectionResetError, ConnectionRefusedError):
                logger.info(
                    f'Связь с клиентом с именем {message[DESTINATION]} '
                    f'была потеряна')
                self.clients.remove(self.names[message[DESTINATION]])
                self.database.user_logout(message[DESTINATION])
                del self.names[message[DESTINATION]]
                with conf_lag_lock:
                    new_connection = True
        self.messages.clear()

    def __process_client_message(self, message, client):
        """ Разбор сообщения клиент """
        logger.debug(f'Разбор сообщения от клиента : {message}')

        if ACTION in message and message[ACTION] == PRESENCE and \
                TIME in message and USER in message:
            # Если сообщение о присутствии, то вызываем функцию авторизации.
            self.authorization(message, client)

        # Регистрация выхода
        elif ACTION in message and message[ACTION] == EXIT and \
                ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.client_quit(message, client)

        # Регистрация сообщения в очереди
        elif ACTION in message and message[ACTION] == MESSAGE and \
                DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message \
                and self.names[message[SENDER]] == client:
            self.add_message_to_queue(message, client)

        # Запрос списка контактов
        elif ACTION in message and message[ACTION] == GET_CONTACTS \
                and USER in message and \
                self.names[message[USER]] == client:
            self.get_contacts(message, client)

        # Добавление контакта
        elif ACTION in message and message[ACTION] == ADD_CONTACT \
                and ACCOUNT_NAME in message and USER in message \
                and self.names[message[USER]] == client:
            self.add_contact(message, client)

        # Удаление контакта
        elif ACTION in message and message[ACTION] == REMOVE_CONTACT \
                and ACCOUNT_NAME in message and USER in message \
                and self.names[message[USER]] == client:
            self.del_contact(message, client)

        # Если это запрос известных пользователей
        elif ACTION in message and message[ACTION] == USERS_REQUEST \
                and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.send_unknown_user_request(client)

        # Если это запрос публичного ключа пользователя
        elif ACTION in message and message[ACTION] == PUBLIC_KEY_REQUEST \
                and ACCOUNT_NAME in message:
            self.request_public_key(client, message)

        # Иначе отдаём Bad request
        else:
            self.send_bad_request(client)

    def registration(self, message, client):
        """ Регистрация пользователя на сервере """
        global new_connection
        # Если пользователь не зарегистрирован, то регистрируем,
        # иначе отправляем ответ и завершаем соединение.
        if message[USER][ACCOUNT_NAME] not in self.names.keys():
            self.names[message[USER][ACCOUNT_NAME]] = client
            client_ip, client_port = client.getpeername()
            self.database.user_login(
                message[USER][ACCOUNT_NAME],
                client_ip,
                client_port,
                message[USER][PUBLIC_KEY])
            send_message(client, RESPONSE_200)
            with conf_lag_lock:
                new_connection = True
        else:
            response = RESPONSE_400
            response[ERROR] = 'Имя пользователя уже занято.'
            send_message(client, response)
            self.clients.remove(client)
            client.close()

    def client_quit(self, message, client):
        """ Регистрация выхода пользователя """
        global new_connection

        client_ip, client_port = client.getpeername()
        self.database.user_logout(
            message[ACCOUNT_NAME], client_ip, client_port)
        logger.info(
            f'Клиент {message[ACCOUNT_NAME]} корректно отключился от сервера.')
        self.clients.remove(self.names[message[ACCOUNT_NAME]])
        self.names[message[ACCOUNT_NAME]].close()
        del self.names[message[ACCOUNT_NAME]]
        with conf_lag_lock:
            new_connection = True

    def add_message_to_queue(self, message, client):
        """ Добавление сообщения в очередь """
        if message[DESTINATION] in self.names:
            self.messages.append(message)
            self.database.process_message(
                message[SENDER], message[DESTINATION])
            send_message(client, RESPONSE_200)
        else:
            response = RESPONSE_400
            response[ERROR] = 'Пользователь не зарегистрирован на сервере.'
            send_message(client, response)

    def get_contacts(self, message, client):
        """ Получение контактов """
        response = RESPONSE_202
        response[LIST_INFO] = self.database.get_contacts(message[USER])
        send_message(client, response)

    def add_contact(self, message, client):
        """ Добавление контакта """
        self.database.add_contact(message[USER], message[ACCOUNT_NAME])
        send_message(client, RESPONSE_200)

    def del_contact(self, message, client):
        """ Удаление контакта """
        self.database.remove_contact(message[USER], message[ACCOUNT_NAME])
        send_message(client, RESPONSE_200)

    def send_unknown_user_request(self, client):
        """ Запрос от неизвестного пользователя"""
        response = RESPONSE_202
        response[LIST_INFO] = [user[0] for user in self.database.users_list()]
        send_message(client, response)

    @staticmethod
    def send_bad_request(client):
        """ Отправляем ответ, что запрос не корректный """
        response = RESPONSE_400
        response[ERROR] = 'Запрос некорректен.'
        send_message(client, response)

    def process_message(self, message, listen_socks):
        if message[DESTINATION] in self.names \
                and self.names[message[DESTINATION]] in listen_socks:
            send_message(self.names[message[DESTINATION]], message)
            logger.info(
                f'Отправлено сообщение пользователю {message[DESTINATION]} '
                f'от пользователя {message[SENDER]}.')
        elif message[DESTINATION] in self.names \
                and self.names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            logger.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на '
                f'сервере, отправка сообщения невозможна.')

    def send_response_about_error_to_user(
            self, response, ru_text, en_text, sock):
        """ Отправка сообщения об ошибке пользователю """
        response[ERROR] = ru_text
        try:
            logger.debug(f'{en_text} {response}')
            send_message(sock, response)
        except OSError:
            logger.debug('OS Error')
            pass
        self.clients.remove(sock)
        sock.close()

    def authorization(self, message, sock):
        """ Метод реализующий авторизацию пользователей. """

        logger.debug(f'Start auth process for {message[USER]}')
        if message[USER][ACCOUNT_NAME] in self.names.keys():
            self.send_response_about_error_to_user(
                RESPONSE_400, 'Имя пользователя уже занято.',
                f'Username busy, sending', sock)
        elif not self.database.check_user(message[USER][ACCOUNT_NAME]):
            self.send_response_about_error_to_user(
                RESPONSE_400, 'Пользователь не зарегистрирован.',
                f'Unknown username, sending', sock)
        else:
            logger.debug('Correct username, starting passwd check.')
            # Иначе отвечаем 511 и проводим процедуру авторизации
            # Словарь - заготовка
            message_auth = RESPONSE_511
            # Набор байтов в hex представлении
            random_str = binascii.hexlify(os.urandom(64))
            # В словарь байты нельзя, декодируем (json.dumps -> TypeError)
            message_auth[DATA] = random_str.decode('ascii')
            # Создаём хэш пароля и связки со случайной строкой, сохраняем
            # серверную версию ключа
            server_hash = hmac.new(
                self.database.get_hash(
                    message[USER][ACCOUNT_NAME]),
                random_str,
                'MD5')
            digest = server_hash.digest()
            logger.debug(f'Auth message = {message_auth}')
            try:
                # Обмен с клиентом
                send_message(sock, message_auth)
                ans = get_message(sock)
            except OSError as err:
                logger.debug('Error in auth, data:', exc_info=err)
                sock.close()
                return
            client_digest = binascii.a2b_base64(ans[DATA])
            # Если ответ клиента корректный, то сохраняем его в список
            # пользователей.
            if RESPONSE in ans and ans[RESPONSE] == 511 \
                    and hmac.compare_digest(digest, client_digest):
                self.names[message[USER][ACCOUNT_NAME]] = sock
                client_ip, client_port = sock.getpeername()
                try:
                    send_message(sock, RESPONSE_200)
                except OSError:
                    self.remove_client(message[USER][ACCOUNT_NAME])
                # добавляем пользователя в список активных и если у него
                # изменился открытый ключ, сохраняем новый
                self.database.user_login(
                    message[USER][ACCOUNT_NAME],
                    client_ip,
                    client_port,
                    message[USER][PUBLIC_KEY])
            else:
                response = RESPONSE_400
                response[ERROR] = 'Неверный пароль.'
                try:
                    send_message(sock, response)
                except OSError:
                    pass
                self.clients.remove(sock)
                sock.close()

    def service_update_lists(self):
        """ Метод реализующий отправки сервисного сообщения 205 клиентам. """
        for client in self.names:
            try:
                send_message(self.names[client], RESPONSE_205)
            except OSError:
                self.remove_client(self.names[client])

    def request_public_key(self, client, message):
        """ Запрос публичного ключа """
        response = RESPONSE_511
        response[DATA] = self.database.get_pubkey(message[ACCOUNT_NAME])

        if response[DATA]:
            try:
                send_message(client, response)
            except OSError:
                self.remove_client(client)
        else:
            response = RESPONSE_400
            response[ERROR] = 'Нет публичного ключа для данного пользователя'
            try:
                send_message(client, response)
            except OSError:
                self.remove_client(client)
