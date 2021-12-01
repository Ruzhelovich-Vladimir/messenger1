import socket
import time
import argparse
import threading
from common.utils import *
from errors import IncorrectDataRecivedError, ReqFieldMissingError, ServerError
from decos import log
from metaclass import ClientVerifier


class Client(metaclass=ClientVerifier):

    __slots__ = ('logger', 'server_address', 'server_port', 'client_name',
                 'transport')

    def __init__(self):

        # Инициализация клиентского логера
        self.logger = logging.getLogger('client')

        # Загружаем параметы коммандной строки
        self.server_address, self.server_port, self.client_name = self.__arg_parser()

        # Если имя пользователя не было задано, необходимо запросить пользователя.
        if not self.client_name:
            self.client_name = input('Введите имя пользователя: ')

        # Сообщаем о запуске
        print(f'{self.client_name}: Консольный месседжер. Клиентский модуль.')

        self.logger.info(
            f'{self.client_name}: Запущен клиент с парамертами: '
            f'адрес сервера: {self.server_address}, порт: {self.server_port}, '
            f'имя пользователя: {self.client_name}')

        if not self.__init_socket():
            exit(1)
        self.__run_process()
        
    # Инициализируем сокет
    @log
    def __init_socket(self):
        # Инициализация сокета и сообщение серверу о нашем появлении
        try:
            self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.transport.connect((self.server_address, self.server_port))
            # Сообщаем, что мы появились
            send_message(self.transport, self.__create_presence())
            # Получаем ответ
            answer = self.__process_response_ans(get_message(self.transport))
            self.logger.info(
                f'{self.client_name}: Установлено соединение с сервером. Ответ сервера: {answer}')
            print(f'Установлено соединение с сервером.')
        except json.JSONDecodeError:
            self.logger.error(
                f'{self.client_name}: Не удалось декодировать полученную Json строку.')
            return False
        except ServerError as error:
            self.logger.error(
                f'{self.client_name}: При установке соединения сервер вернул ошибку: {error.text}')
            return False
        except ReqFieldMissingError as missing_error:
            self.logger.error(
                f'{self.client_name}: В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
            return False
        except (ConnectionRefusedError, ConnectionError):
            self.logger.critical(
                f'{self.client_name}: Не удалось подключиться к серверу {self.server_address}:{self.server_port}, '
                f'конечный компьютер отверг запрос на подключение.')
            return False
        except KeyboardInterrupt:
            self.logger.critical(
                f'{self.client_name}: Отключение от сервера')
            return False
        else:
            return True

    # Запуск процесса клиента
    @log
    def __run_process(self):
        # Если соединение с сервером установлено корректно, запускаем клиенский процесс приёма сообщний
        receiver = threading.Thread(target=self.__message_from_server)
        receiver.daemon = True
        receiver.start()

        # затем запускаем отправку сообщений и взаимодействие с пользователем.
        user_interface = threading.Thread(target=self.__user_interactive)
        user_interface.daemon = True
        user_interface.start()
        self.logger.debug(f'{self.client_name}: Запущены процессы')

        # Watchdog основной цикл, если один из потоков завершён, то значит или потеряно соединение или пользователь
        # ввёл exit. Поскольку все события обработываются в потоках, достаточно просто завершить цикл.
        while True:
            try:
                time.sleep(1)
                if receiver.is_alive() and user_interface.is_alive():
                    continue
                break
            except KeyboardInterrupt:
                self.logger.critical(
                    f'{self.client_name}: Отключение от сервера')
                exit(1)

    # Парсер аргументов коммандной строки
    @log
    def __arg_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
        parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
        parser.add_argument('-n', '--username', default=None, nargs='?')
        namespace = parser.parse_args(sys.argv[1:])
        server_address = namespace.addr
        server_port = namespace.port
        client_name = namespace.name

        # проверим подходящий номер порта
        if not 1023 < server_port < 65536:
            self.logger.critical(
                f'{self.client_name}: Попытка запуска клиента с неподходящим номером порта: {server_port}. '
                f'Допустимы адреса с 1024 до 65535. Клиент завершается.')
            exit(1)

        return server_address, server_port, client_name

    # Функция создаёт словарь с сообщением о выходе.
    @log
    def __create_exit_message(self, account_name):
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: account_name
        }

    # Функция - обработчик сообщений других пользователей, поступающих с сервера.

    @log
    def __message_from_server(self):

        while True:
            try:
                message = get_message(self.transport)
                if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and DESTINATION in message \
                        and MESSAGE_TEXT in message and message[DESTINATION] == self.client_name:
                    print(
                        f'{self.client_name}: \nПолучено сообщение от пользователя {message[SENDER]}:'
                        f'\n{message[MESSAGE_TEXT]}')
                    self.logger.info(
                        f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                else:
                    self.logger.error(
                        f'{self.client_name}: Получено некорректное сообщение с сервера: {message}')
            except IncorrectDataRecivedError:
                self.logger.error(
                    f'{self.client_name}: Не удалось декодировать полученное сообщение.')
            except (OSError, ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                self.logger.critical(
                    f'{self.client_name}: Потеряно соединение с сервером.')
                break

    @log
    # Функция запрашивает кому отправить сообщение и само сообщение, и отправляет полученные данные на сервер.
    def __create_message(self):
        to = input(f'{self.client_name}: Введите получателя сообщения: ')
        message = input(
            f'{self.client_name}: Введите сообщение для отправки: ')
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.client_name,
            DESTINATION: to,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        self.logger.debug(
            f'{self.client_name}: Сформирован словарь сообщения: {message_dict}')
        try:
            send_message(self.transport, message_dict)
            self.logger.info(
                f'{self.client_name}: Отправлено сообщение для пользователя {to}')
        except Exception as arr:
            self.logger.critical(
                f'{self.client_name}: Потеряно соединение с сервером. - {arr}')
            exit(1)

    @log
    # Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения
    def __user_interactive(self):

        self.__print_help()
        while True:
            command = input(f'{self.client_name}: Введите команду: ')
            if command == 'message':
                self.__create_message()
            elif command == 'help':
                self.__print_help()
            elif command == 'exit':
                send_message(self.transport, self.__create_exit_message(self.client_name))
                print(f'{self.client_name}: Завершение соединения.')
                self.logger.info(
                    f'{self.client_name}: Завершение работы по команде пользователя.')
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                time.sleep(0.5)
                break
            else:
                print(
                    f'{self.client_name}: Команда не распознана, попробойте снова. '
                    f'help - вывести поддерживаемые команды.')

    # Функция генерирует запрос о присутствии клиента

    @log
    def __create_presence(self):
        out = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.client_name
            }
        }
        self.logger.debug(
            f'{self.client_name}: Сформировано {PRESENCE} сообщение для пользователя {self.client_name}')
        return out

    # Функция выводящяя справку по использованию.

    def __print_help(self):
        print(f'{self.client_name}: Поддерживаемые команды:')
        print(
            f'{self.client_name}: message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print(f'{self.client_name}: help - вывести подсказки по командам')
        print(f'{self.client_name}: exit - выход из программы')

    # Функция разбирает ответ сервера на сообщение о присутствии,
    # возращает 200 если все ОК или генерирует исключение при\
    # ошибке.

    @log
    def __process_response_ans(self, message):
        self.logger.debug(
            f'{self.client_name}: Разбор приветственного сообщения от сервера: {message}')
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return '200 : OK'
            elif message[RESPONSE] == 400:
                raise ServerError(f'400 : {message[ERROR]}')
        raise ReqFieldMissingError(RESPONSE)


if __name__ == '__main__':
    Client()
