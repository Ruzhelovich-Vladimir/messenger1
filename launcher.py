import subprocess
from time import sleep

PROCESS = {}  # Список процессов


def start_process_server():
    """Запуск процесса сервера"""
    if 'server' not in PROCESS:  # Если сервер еще не запущен, запускам его
        PROCESS['server'] = subprocess.Popen(
            f'python3 server.py'.split())
        sleep(1)


def start_process_client(user_name="user", password='pass'):
    """ Запуска процесса клиента    """

    if user_name not in PROCESS:  # Если клиент еще не запущен, запускаем
        PROCESS[user_name] = subprocess.Popen(
            f'python3 client.py -n {user_name} -p {password}'.split())
        sleep(1)


def kill_process():
    """Закрывает все созданные процесс
    """
    for name, proc in PROCESS.items():
        proc.kill()


if __name__ == '__main__':

    print(f'{"*"*10}Демонстрация работы чата{"*"*10}')
    print(f'{"*"*10}для выхода нажмите Ctrl+с{"*"*10}')
    start_process_server()
    start_process_client('user1', '1')
    start_process_client('user2', '1')
    # start_process_client('user3')
    while True:
        try:
            pass
        except KeyboardInterrupt:  # Обработка прерывания выполнения скрипта
            break
    print('Выход')
    kill_process()
