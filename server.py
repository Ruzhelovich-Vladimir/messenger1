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

        # Инициализация логирования сервера.
        self.logger = logging.getLogger('server')
        # self.logger.setLevel('INFO')

        # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
        self.listen_address, self.listen_port = host_port

        self.logger.info(
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
                except Exception as err:
                    self.logger.info(
                        f'Клиент {client_with_message.getpeername()} отключился от сервера. Error {err}')
                    self.clients.remove(client_with_message)

    @log
    def __process_client_message(self, message, client):
        global new_connection
        self.logger.debug(f'Разбор сообщения от клиента : {message}')
        # Если это сообщение о присутствии, принимаем и отвечаем
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message and USER in message:
            # Если такой пользователь ещё не зарегистрирован, регистрируем,
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
            return
        # Если это сообщение, то добавляем его в очередь сообщений. Ответ не требуется.
        elif ACTION in message and message[ACTION] == MESSAGE and DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message:
            self.messages.append(message)
            self.database.process_message(
                message[SENDER], message[DESTINATION])
            return
        # Если клиент выходит
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            client_ip, client_port = client.getpeername()
            self.database.user_logout(message[ACCOUNT_NAME],client_ip, client_port)
            self.clients.remove(self.names[ACCOUNT_NAME])
            self.names[ACCOUNT_NAME].close()
            del self.names[ACCOUNT_NAME]
            with conflag_lock:
                new_connection = True
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


def main():
    config = configparser.ConfigParser()
    ini_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'server.ini')
    config.read(ini_path)

    db_path = os.path.join(config['SETTINGS']['Database_path'], config['SETTINGS']['Database_file'])
    database = ServerStorage(db_path)

    listen_address, listen_port = arg_parser(
        config['SETTINGS']['Default_port'], config['SETTINGS']['Listen_Address'])
    server = Server((listen_address, listen_port), database)
    server.daemon = True
    server.start()

    server_app = QApplication(sys.argv)
    main_window = MainWindow()

    main_window.statusBar().showMessage('server working')
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
                print(port)
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
