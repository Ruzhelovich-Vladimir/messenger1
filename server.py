import configparser
import os
import socket
import argparse
import select
import time

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox

import threading
from common.utils import *
from decos import log

from descriptors import Port, Host
from metaclass import ServerVerifier

from server_database import ServerStorage

from server_gui import MainWindow, HistoryWindow, gui_create_main_form_model, create_stat_form_model, ConfigWindow

logger = logging.getLogger('server')

# Флаг что был подключён новый пользователь, нужен чтобы не мучать BD
# постоянными запросами на обновление
new_connection = False
conflag_lock = threading.Lock()


@log
def arg_parser(default_port, default_address='127.0.0.1'):
    """
    Считывание параметров запуска скрипта
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=default_port, type=int, nargs='?')
    parser.add_argument('-a', default=default_address, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    return listen_address, listen_port


def print_help():
    print('Поддерживаемые комманды:')
    print('users - список известных пользователей')
    print('connected - список подключенных пользователей')
    print('loghist - история входов пользователя')
    print('exit - завершение работы сервера.')
    print('help - вывод справки по поддерживаемым командам')


class Server(threading.Thread, metaclass=ServerVerifier):
    """
    Класс сервера
    """
    listen_port = Port()
    listen_address = Host()

    def __init__(self, host_port, database):
        """ Инициализация сервера """

        # Конструктор предка
        super().__init__()

        # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
        self.listen_address, self.listen_port = host_port

        logger.info(
            f'Запущен сервер, порт для подключений: {self.listen_port} , '
            f'адрес с которого принимаются подключения: {self.listen_address}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')

        # Готовим сокет
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                self.transport.bind((self.listen_address, self.listen_port))
            except KeyboardInterrupt:
                break
            except:
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

    def __wait_connect_client(self):
        """ Ждём подключения, если таймаут вышел, ловим исключение. """
        try:
            client, client_address = self.transport.accept()
        except OSError:
            return None
        logger.info(f'Установлено соедение с ПК {client_address}')
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
        """ Принимаем сообщения и если ошибка, исключаем клиента """
        global new_connection

        if self.receive_data_lst:
            for client_with_message in self.receive_data_lst:
                try:
                    message = get_message(client_with_message)
                    self.__process_client_message(message, client_with_message)
                except OSError:
                    logger.info(
                        f'Клиент {client_with_message.getpeername()} отключился от сервера.')
                    # Ищем клиента в словаре клиентов, удаляем его из него из базы подключённых
                    for name in self.names:
                        if self.names[name] == client_with_message:
                            self.database.user_logout(name)
                            del self.names[name]
                            break
                    self.clients.remove(client_with_message)
                    with conflag_lock:
                        new_connection = True

    def __process_messages(self):
        """ Обрабатываем имеющиеся сообщения """
        global new_connection
        for message in self.messages:
            try:
                self.process_message(message, self.send_data_lst)
            except (ConnectionAbortedError, ConnectionError, ConnectionResetError, ConnectionRefusedError):
                logger.info(f'Связь с клиентом с именем {message[DESTINATION]} была потеряна')
                self.clients.remove(self.names[message[DESTINATION]])
                self.database.user_logout(message[DESTINATION])
                del self.names[message[DESTINATION]]
                with conflag_lock:
                    new_connection = True
        self.messages.clear()

    def __process_client_message(self, message, client):
        """ Разбор сообщения клиент """
        logger.debug(f'Разбор сообщения от клиента : {message}')

        # Регистрация пользователя на сервере
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message and USER in message:
            self.registration(message, client)

        # Регистрация выхода
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.client_quit(message, client)

        # Регистрация сообщения в очереди
        elif ACTION in message and message[ACTION] == MESSAGE and DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message and self.names[message[SENDER]] == client:
            self.add_message_to_queue(message, client)

        # Запрос списка контактов
        elif ACTION in message and message[ACTION] == GET_CONTACTS and USER in message and \
                self.names[message[USER]] == client:
            self.get_contacts(message, client)

        # Добавление контакта
        elif ACTION in message and message[ACTION] == ADD_CONTACT and ACCOUNT_NAME in message and USER in message \
                and self.names[message[USER]] == client:
            self.add_contact(message, client)

        # Удаление контакта
        elif ACTION in message and message[ACTION] == REMOVE_CONTACT and ACCOUNT_NAME in message and USER in message \
                and self.names[message[USER]] == client:
            self.del_contact(message, client)

        # Если это запрос известных пользователей
        elif ACTION in message and message[ACTION] == USERS_REQUEST and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.send_unknown_user_request(message, client)

        # Иначе отдаём Bad request
        else:
            self.send_bad_request(message, client)

    def registration(self, message, client):
        """ Регистрация пользователя на сервере """
        global new_connection
        # Если пользователь не зарегистрирован, то регистрируем,
        # иначе отправляем ответ и завершаем соединение.
        if message[USER][ACCOUNT_NAME] not in self.names.keys():
            self.names[message[USER][ACCOUNT_NAME]] = client
            client_ip, client_port = client.getpeername()
            self.database.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
            send_message(client, RESPONSE_200)
            with conflag_lock:
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
        self.database.user_logout(message[ACCOUNT_NAME], client_ip, client_port)
        logger.info(f'Клиент {message[ACCOUNT_NAME]} корректно отключился от сервера.')
        self.clients.remove(self.names[message[ACCOUNT_NAME]])
        self.names[message[ACCOUNT_NAME]].close()
        del self.names[message[ACCOUNT_NAME]]
        with conflag_lock:
            new_connection = True

    def add_message_to_queue(self, message, client):
        """ Добавление сообщения в очередь """
        if message[DESTINATION] in self.names:
            self.messages.append(message)
            self.database.process_message(message[SENDER], message[DESTINATION])
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

    def send_unknown_user_request(self, message, client):
        """ Запрос от неизвестного пользователя"""
        response = RESPONSE_202
        response[LIST_INFO] = [user[0] for user in self.database.users_list()]
        send_message(client, response)

    def send_bad_request(self, message, client):
        """ Отправляем ответ, что запрос не корректный """
        response = RESPONSE_400
        response[ERROR] = 'Запрос некорректен.'
        send_message(client, response)

    def process_message(self, message, listen_socks):
        if message[DESTINATION] in self.names and self.names[message[DESTINATION]] in listen_socks:
            send_message(self.names[message[DESTINATION]], message)
            logger.info(f'Отправлено сообщение пользователю {message[DESTINATION]} от пользователя {message[SENDER]}.')
        elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            logger.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, отправка сообщения невозможна.')


def config_load():
    config = configparser.ConfigParser()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/{'server.ini'}")
    # Если конфиг файл загружен правильно, запускаемся, иначе конфиг по умолчанию.
    if 'SETTINGS' in config:
        return config
    else:
        config.add_section('SETTINGS')
        config.set('SETTINGS', 'Default_port', str(DEFAULT_PORT))
        config.set('SETTINGS', 'Listen_Address', '')
        config.set('SETTINGS', 'Database_path', '')
        config.set('SETTINGS', 'Database_file', 'server_database.db3')
        return config

def main():
    # Загрузка файла конфигурации сервера
    config = config_load()

    # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
    listen_address, listen_port = arg_parser(config['SETTINGS']['Default_port'], config['SETTINGS']['Listen_Address'])

    # Инициализация базы данных
    database = ServerStorage(os.path.join(config['SETTINGS']['Database_path'], config['SETTINGS']['Database_file']))

    # Создание экземпляра класса - сервера и его запуск:
    server = Server((listen_address, listen_port), database)
    server.daemon = True
    server.start()

    # Создаём графическое окуружение для сервера:
    server_app = QApplication(sys.argv)
    main_window = MainWindow()

    # Инициализируем параметры в окна
    main_window.statusBar().showMessage('Server Working')
    main_window.active_clients_table.setModel(gui_create_main_form_model(database))
    main_window.active_clients_table.resizeColumnsToContents()
    main_window.active_clients_table.resizeRowsToContents()

    def list_update():
        """ Функция обновляющяя список подключённых """
        global new_connection
        if new_connection:
            main_window.active_clients_table.setModel(
                gui_create_main_form_model(database))
            main_window.active_clients_table.resizeColumnsToContents()
            main_window.active_clients_table.resizeRowsToContents()
            with conflag_lock:
                new_connection = False

    def show_statistics():
        """ Функция создающяя окно со статистикой клиентов """
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(create_stat_form_model(database))
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()
        stat_window.show()

    def server_config():
        """ Функция создающяя окно с настройками сервера. """
        global config_window
        # Создаём окно и заносим в него текущие параметры
        config_window = ConfigWindow()
        config_window.db_path.insert(config['SETTINGS']['Database_path'])
        config_window.db_file.insert(config['SETTINGS']['Database_file'])
        config_window.port.insert(config['SETTINGS']['Default_port'])
        config_window.ip.insert(config['SETTINGS']['Listen_Address'])
        config_window.save_btn.clicked.connect(save_server_config)

    # Функция сохранения настроек
    def save_server_config():
        global config_window
        message = QMessageBox()
        config['SETTINGS']['Database_path'] = config_window.db_path.text()
        config['SETTINGS']['Database_file'] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
        else:
            config['SETTINGS']['Listen_Address'] = config_window.ip.text()
            if 1023 < port < 65536:
                config['SETTINGS']['Default_port'] = str(port)
                with open('server.ini', 'w') as conf:
                    config.write(conf)
                    message.information(
                        config_window, 'OK', 'Настройки успешно сохранены!')
            else:
                message.warning(
                    config_window,
                    'Ошибка',
                    'Порт должен быть от 1024 до 65536')

    # Таймер, обновляющий список клиентов 1 раз в секунду
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # Связываем кнопки с процедурами
    main_window.refresh_button.triggered.connect(list_update)
    main_window.show_history_button.triggered.connect(show_statistics)
    main_window.config_btn.triggered.connect(server_config)

    # Запускаем GUI
    server_app.exec_()

if __name__ == '__main__':
    main()
