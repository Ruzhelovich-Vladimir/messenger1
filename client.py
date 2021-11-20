import socket
import time
import argparse
import threading
from common.utils import *
from errors import IncorrectDataRecivedError, ReqFieldMissingError, ServerError
from decos import log

# Инициализация клиентского логера
logger = logging.getLogger('client')

# Функция создаёт словарь с сообщением о выходе.


@log
def create_exit_message(account_name):
    return {
        ACTION: EXIT,
        TIME: time.time(),
        ACCOUNT_NAME: account_name
    }


@log
# Функция - обработчик сообщений других пользователей, поступающих с сервера.
def message_from_server(sock, client_name):
    while True:
        try:
            message = get_message(sock)
            if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and DESTINATION in message \
                    and MESSAGE_TEXT in message and message[DESTINATION] == client_name:
                print(
                    f'{client_name}: \nПолучено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                logger.info(
                    f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
            else:
                logger.error(
                    f'{client_name}: Получено некорректное сообщение с сервера: {message}')
        except IncorrectDataRecivedError:
            logger.error(
                f'{client_name}: Не удалось декодировать полученное сообщение.')
        except (OSError, ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
            logger.critical(
                f'{client_name}: Потеряно соединение с сервером.')
            break


@log
# Функция запрашивает кому отправить сообщение и само сообщение, и отправляет полученные данные на сервер.
def create_message(sock, client_name):
    to = input(f'{client_name}: Введите получателя сообщения: ')
    message = input(f'{client_name}: Введите сообщение для отправки: ')
    message_dict = {
        ACTION: MESSAGE,
        SENDER: client_name,
        DESTINATION: to,
        TIME: time.time(),
        MESSAGE_TEXT: message
    }
    logger.debug(
        f'{client_name}: Сформирован словарь сообщения: {message_dict}')
    try:
        send_message(sock, message_dict)
        logger.info(
            f'{client_name}: Отправлено сообщение для пользователя {to}')
    except Exception as arr:
        logger.critical(f'{client_name}: Потеряно соединение с сервером. - {arr}')
        exit(1)


@log
# Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения
def user_interactive(sock, client_name):
    print_help(client_name)
    while True:
        command = input(f'{client_name}: Введите команду: ')
        if command == 'message':
            create_message(sock, client_name)
        elif command == 'help':
            print_help(client_name)
        elif command == 'exit':
            send_message(sock, create_exit_message(client_name))
            print(f'{client_name}: Завершение соединения.')
            logger.info(
                f'{client_name}: Завершение работы по команде пользователя.')
            # Задержка неоходима, чтобы успело уйти сообщение о выходе
            time.sleep(0.5)
            break
        else:
            print(
                f'{client_name}: Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')


# Функция генерирует запрос о присутствии клиента
@log
def create_presence(client_name):
    out = {
        ACTION: PRESENCE,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: client_name
        }
    }
    logger.debug(
        f'{client_name}: Сформировано {PRESENCE} сообщение для пользователя {client_name}')
    return out


# Функция выводящяя справку по использованию.
def print_help(client_name):
    print(f'{client_name}: Поддерживаемые команды:')
    print(f'{client_name}: message - отправить сообщение. Кому и текст будет запрошены отдельно.')
    print(f'{client_name}: help - вывести подсказки по командам')
    print(f'{client_name}: exit - выход из программы')


# Функция разбирает ответ сервера на сообщение о присутствии, возращает 200 если все ОК или генерирует исключение при\
# ошибке.
@log
def process_response_ans(message, client_name):
    logger.debug(
        f'{client_name}: Разбор приветственного сообщения от сервера: {message}')
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200 : OK'
        elif message[RESPONSE] == 400:
            raise ServerError(f'400 : {message[ERROR]}')
    raise ReqFieldMissingError(RESPONSE)


# Парсер аргументов коммандной строки
@log
def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name

    # проверим подходящий номер порта
    if not 1023 < server_port < 65536:
        logger.critical(
            f'{client_name}: Попытка запуска клиента с неподходящим номером порта: {server_port}. '
            f'Допустимы адреса с 1024 до 65535. Клиент завершается.')
        exit(1)

    return server_address, server_port, client_name


def main():
    # Загружаем параметы коммандной строки
    server_address, server_port, client_name = arg_parser()

    # Если имя пользователя не было задано, необходимо запросить пользователя.
    if not client_name:
        client_name = input('Введите имя пользователя: ')

    # Сообщаем о запуске
    print(f'{client_name}: Консольный месседжер. Клиентский модуль.')

    logger.info(
        f'{client_name}: Запущен клиент с парамертами: адрес сервера: {server_address}, порт: {server_port}, '
        f'имя пользователя: {client_name}')

    # Инициализация сокета и сообщение серверу о нашем появлении
    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect((server_address, server_port))
        send_message(transport, create_presence(client_name))
        answer = process_response_ans(get_message(transport), client_name)
        logger.info(
            f'{client_name}: Установлено соединение с сервером. Ответ сервера: {answer}')
        print(f'Установлено соединение с сервером.')
    except json.JSONDecodeError:
        logger.error(
            f'{client_name}: Не удалось декодировать полученную Json строку.')
        exit(1)
    except ServerError as error:
        logger.error(
            f'{client_name}: При установке соединения сервер вернул ошибку: {error.text}')
        exit(1)
    except ReqFieldMissingError as missing_error:
        logger.error(
            f'{client_name}: В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
        exit(1)
    except (ConnectionRefusedError, ConnectionError):
        logger.critical(
            f'{client_name}: Не удалось подключиться к серверу {server_address}:{server_port}, '
            f'конечный компьютер отверг запрос на подключение.')
        exit(1)
    except KeyboardInterrupt:
        logger.critical(
            f'{client_name}: Отключение от сервера')
        exit(1)
    else:
        # Если соединение с сервером установлено корректно, запускаем клиенский процесс приёма сообщний
        receiver = threading.Thread(
            target=message_from_server, args=(transport, client_name))
        receiver.daemon = True
        receiver.start()

        # затем запускаем отправку сообщений и взаимодействие с пользователем.
        user_interface = threading.Thread(
            target=user_interactive, args=(transport, client_name))
        user_interface.daemon = True
        user_interface.start()
        logger.debug(f'{client_name}: Запущены процессы')

        # Watchdog основной цикл, если один из потоков завершён, то значит или потеряно соединение или пользователь
        # ввёл exit. Поскольку все события обработываются в потоках, достаточно просто завершить цикл.
        while True:
            try:
                time.sleep(1)
                if receiver.is_alive() and user_interface.is_alive():
                    continue
                break
            except KeyboardInterrupt:
                logger.critical(
                    f'{client_name}: Отключение от сервера')
                exit(1)


if __name__ == '__main__':
    main()
