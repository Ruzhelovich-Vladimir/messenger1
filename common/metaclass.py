import dis


class ClientVerifier(type):
    """ Мета-класс для верификации клиентского приложения  """

    def __init__(cls, cls_name, bases, cls_dict):
        methods = []
        attrs = []
        for func in cls_dict:
            # Почему-то падает на дос строке
            if '__doc__' == func:
                continue
            try:
                ret = dis.get_instructions(cls_dict[func])
            except TypeError:
                pass
            else:
                for i in ret:
                    # print(i)
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            methods.append(i.argval)
                    elif i.opname == 'LOAD_ATTR':
                        if i.argval not in attrs:
                            attrs.append(i.argval)
        # print(methods)
        if 'accept' in methods and 'listen' in methods and 'socket' in methods:
            raise TypeError(
                'Использование методов accept, listen, socket не допустимо на '
                'клиенте')
        # TODO перестало работать контроль инициализации сокета, разобраться
        # if not ('SOCK_STREAM' in attrs and 'AF_INET' in attrs):
        #     print("*"*20, attrs, "*"*20)
        #     raise TypeError('Не корректная инициализация сокета.')
        super().__init__(cls_name, bases, cls_dict)


class ServerVerifier(type):
    """ Мета-класс для верификации серверного приложения  """

    def __init__(cls, cls_name, bases, cls_dict):
        methods = []
        attrs = []
        for func in cls_dict:
            # Почему-то падает на дос строке
            if '__doc__' == func:
                continue
            try:
                ret = dis.get_instructions(cls_dict[func])
            except TypeError:
                pass
            else:
                for i in ret:
                    # print(i)
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            methods.append(i.argval)
                    elif i.opname == 'LOAD_ATTR':
                        if i.argval not in attrs:
                            attrs.append(i.argval)
        # print(methods)
        if 'connect' in methods:
            raise TypeError(
                'Использование метода connect не допустимо в серверном классе')
        if not ('SOCK_STREAM' in attrs and 'AF_INET' in attrs):
            raise TypeError('Не корректная инициализация сокета.')
        super().__init__(cls_name, bases, cls_dict)
