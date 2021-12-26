import dis


class ClientVerifier(type):
    def __init__(self, clsname, bases, clsdict):
        methods = []
        attrs = []
        for func in clsdict:
            # Почему-то падает на дос страке
            if '__doc__' == func:
                continue
            try:
                ret = dis.get_instructions(clsdict[func])
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
            raise TypeError('Использование методов accept, listen, socket не допустимо на клиенте')
        # TODO перестало работать контроль инициализации сокета, разобраться
        # if not ('SOCK_STREAM' in attrs and 'AF_INET' in attrs):
        #     print("*"*20, attrs, "*"*20)
        #     raise TypeError('Не корректная инициализация сокета.')
        super().__init__(clsname, bases, clsdict)

class ServerVerifier(type):

    def __init__(self, clsname, bases, clsdict):
        methods = []
        attrs = []
        for func in clsdict:
            # Почему-то падает на дос страке
            if '__doc__' == func:
                continue
            try:
                ret = dis.get_instructions(clsdict[func])
            except TypeError:
                pass
            else:
                for i in ret:
                    #print(i)
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            methods.append(i.argval)
                    elif i.opname == 'LOAD_ATTR':
                        if i.argval not in attrs:
                            attrs.append(i.argval)
        # print(methods)
        if 'connect' in methods:
            raise TypeError('Использование метода connect не допустимо в серверном классе')
        if not ('SOCK_STREAM' in attrs and 'AF_INET' in attrs):
            raise TypeError('Не корректная инициализация сокета.')
        super().__init__(clsname, bases, clsdict)
