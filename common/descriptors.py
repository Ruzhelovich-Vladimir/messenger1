"""
Реализовать дескриптор для класса серверного сокета, а в нем — проверку номера
порта. Это должно быть целое число (>=0). Значение порта по умолчанию равняется
7777. Дескриптор надо создать в отдельном классе. Его экземпляр добавить в
пределах класса серверного сокета. Номер порта передается в экземпляр
дескриптора при запуске сервера.
"""
from common.host_ping import is_available_host


class Port:
    """ Дескриптор контроля порта """

    def __set__(self, instance, value):
        if not 1023 < value < 65536:
            raise ValueError("Допустимы значение порта с 1024 до 65535")
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name


class Host:
    """ Дескриптор контроля хоста """

    def __set__(self, instance, value):
        if not is_available_host(value):
            raise ValueError("Хост не доступен")
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name
