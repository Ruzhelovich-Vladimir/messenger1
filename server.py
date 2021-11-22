import socket
# import sys
import argparse
# import json
# import logging
import select
# import time
# import logs.config_server_log
# from common.variables import *
from common.utils import *
from decos import log

from descriptors import Port, Host
from metaclass import ServerVerifier


class Server(metaclass=ServerVerifier):
    """
    Класс сервера
    """
    listen_port = Port()
    listen_address = Host()

    def __init__(self):
        """ Инициализация сервера """
        # Инициализация логирования сервера.
        self.logger = logging.getLogger('server')
        # self.logger.setLevel('INFO')

        # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
        self.listen_address, self.listen_port = self.__arg_parser()

        self.logger.info(
            f'Запущен сервер, порт для подключений: {self.listen_port} , '
            f'адрес с которого принимаются подключения: {self.listen_address}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')

        # Готовим сокет
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.transport.bind((self.listen_address, self.listen_port))
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

        self.__main_process_run()

    @log
    def __del__(self):
        """ Деструктор """
        self.transport.close()

    def __arg_parser(self):
        """
        Считывание параметров запуска скрипта
        """
        parser = argparse.ArgumentParser()
        parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
        parser.add_argument('-a', default=DEFAULT_IP_ADDRESS, nargs='?')
        namespace = parser.parse_args(sys.argv[1:])
        listen_address = namespace.a
        listen_port = namespace.p

        """ Коммментирую чтобы сработал дискриптор """
        # # проверка получения корретного номера порта для работы сервера.
        # if not 1023 < listen_port < 65536:
        #     self.logger.critical(
        #         f'Попытка запуска сервера с указанием неподходящего порта '
        #         f'{listen_port}. Допустимы адреса с 1024 до 65535.')
        #     exit(1)

        return listen_address, listen_port

    @log
    def __main_process_run(self):
        """ Запуск основного процесса """

        self.transport.listen(MAX_CONNECTIONS)
        while True:
            try:  # исслючение по пререванию по клавиатуре
                # Ждём подключения клиента
                self.__wait_connect_client()
                # Обновляем информацию о клиентах on-line
                self.__update_waiting_client_info()
                # Принимаем сообщения
                self.__receive_message()
                # Обрабатываем сообщения
                self.__process_message()
            except KeyboardInterrupt:
                print('Выход')
                break

    def __wait_connect_client(self):
        """ Ждём подключения, если таймаут вышел, ловим исключение. """
        try:
            client, client_address = self.transport.accept()
        except OSError:
            return None
        self.logger.info(f'Установлено соедение с ПК {client_address}')
        self.clients.append(client)
        return client

    def __update_waiting_client_info(self):
        """ Обновляем информацию о ждущих клиентах """

        self.receive_data_lst = self.send_data_lst = self.err_lst = []
        try:
            if self.clients:
                self.receive_data_lst, self.send_data_lst, self.err_lst = select.select(
                    self.clients, self.clients, [], 0)
        except OSError:
            pass

    def __receive_message(self):
        """ принимаем сообщения и если ошибка, исключаем клиента """

        if self.receive_data_lst:
            for client_with_message in self.receive_data_lst:
                try:
                    message = get_message(client_with_message)
                    self.__process_client_message(message, client_with_message)
                except:
                    self.logger.info(
                        f'Клиент {client_with_message.getpeername()} отключился от сервера.')
                    self.clients.remove(client_with_message)

    @log
    def __process_client_message(self, message, client):

        self.logger.debug(f'Разбор сообщения от клиента : {message}')
        # Если это сообщение о присутствии, принимаем и отвечаем
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message and USER in message:
            # Если такой пользователь ещё не зарегистрирован, регистрируем,
            # иначе отправляем ответ и завершаем соединение.
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return
        # Если это сообщение, то добавляем его в очередь сообщений. Ответ не требуется.
        elif ACTION in message and message[ACTION] == MESSAGE and DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message:
            self.messages.append(message)
            return
        # Если клиент выходит
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.clients.remove(self.names[ACCOUNT_NAME])
            self.names[ACCOUNT_NAME].close()
            del self.names[ACCOUNT_NAME]
            return
        # Иначе отдаём Bad request
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return

    def __process_message(self):
        """ Обрабатываем имеющиеся сообщения """
        # Если есть сообщения, обрабатываем каждое.
        for message in self.messages:
            try:
                if message[DESTINATION] in self.names and self.names[message[DESTINATION]] in self.send_data_lst:
                    send_message(self.names[message[DESTINATION]], message)
                    self.logger.info(
                        f'Отправлено сообщение пользователю {message[DESTINATION]} от пользователя {message[SENDER]}.')
                elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] not in self.send_data_lst:
                    raise ConnectionError
                else:
                    self.logger.error(
                        f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, '
                        f'отправка сообщения невозможна.')
            except:
                self.logger.info(
                    f'Связь с клиентом с именем {message[DESTINATION]} была потеряна')
                self.clients.remove(self.names[message[DESTINATION]])
                del self.names[message[DESTINATION]]
        self.messages.clear()


if __name__ == '__main__':

    Server()
