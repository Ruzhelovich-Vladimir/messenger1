
"""
1. Написать функцию host_ping(), в которой с помощью утилиты ping будет
    проверяться доступность сетевых узлов. Аргументом функции является список,
    в котором каждый сетевой узел должен быть представлен именем хоста или
    ip-адресом.

    В функции необходимо перебирать ip-адреса и проверять их доступность с
    выводом соответствующего сообщения («Узел доступен», «Узел недоступен»).
    При этом ip-адрес сетевого узла должен создаваться с помощью функции
    ip_address().

2. Написать функцию host_range_ping() для перебора ip-адресов из заданного
    диапазона. Меняться должен только последний октет каждого адреса. По
    результатам проверки должно выводиться соответствующее сообщение.

3. Написать функцию host_range_ping_tab(), возможности которой основаны на
   функции из примера 2. Но в данном случае результат должен быть итоговым по
   всем ip-адресам, представленным в табличном формате (использовать модуль
   tabulate). Таблица должна состоять из двух колонок и выглядеть примерно так:
    Reachable
    10.0.0.1
    10.0.0.2

    Unreachable
    10.0.0.3
    10.0.0.4
"""
from ipaddress import ip_address
from subprocess import Popen, PIPE, SubprocessError
import json
from tabulate import tabulate


def host_range_ping(start_ip, count):
    """
    2. функция для перебора ip-адресов из заданного диапазона.
    Меняться должен только последний октет каждого адреса. По результатам
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
