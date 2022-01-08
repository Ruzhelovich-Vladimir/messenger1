"""
Модуль проверок доступности хоста
"""
from ipaddress import ip_address
from subprocess import Popen, PIPE, SubprocessError
import json
from tabulate import tabulate


def host_range_ping(start_ip, count):
    """
    Функция для перебора ip-адресов из заданного диапазона.
    По результатам
    проверки должно выводиться соответствующее сообщение.
    """
    result = []

    try:
        _ip_address = ip_address(start_ip)
    except ValueError:
        return []

    for num in range(count):
        result.append(str(_ip_address+num))

    return host_ping(result)


def is_available_host(host, timeout=3):
    """
    Проверка доступности хоста
    """
    try:
        process = Popen(('ping', f'{host}', '-c1',
                         f'-W{timeout}'), shell=False, stdout=PIPE)
        process.wait()
    except SubprocessError:
        return False

    return process.returncode == 0


def host_ping(host_list=None, timeout=3):
    """
    Функцию host_ping(), в которой с помощью утилиты ping будет проверяться
    доступность сетевых узлов. Аргументом функции является список, в котором
    каждый сетевой узел должен быть представлен именем хоста или ip-адресом
    """
    if host_list is None:
        host_list = []
    result = {}
    for host in host_list:

        status = "Reachable" if is_available_host(host, timeout) \
            else 'Unreachable'
        if status in result:
            result[status].append(host)
        else:
            result[status] = [host]
    return result


def host_range_ping_tab(start_ip, count):
    """
    Возвращает таблицу доступности адресов
    """
    return tabulate(host_range_ping(start_ip, count), headers='keys')


if __name__ == '__main__':

    res = host_ping(['localhost'], 1)
    print(json.dumps(res, indent=4))
