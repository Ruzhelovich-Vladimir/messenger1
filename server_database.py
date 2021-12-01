from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime, Boolean, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql.functions import now, func

from common.variables import SERVER_DATABASE

Base = declarative_base()


class ServerStorage:

    class Users(Base):
        """ Таблица пользователей """

        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        username = Column(String(25), nullable=True, unique=True, index=True)
        password = Column(String, nullable=True, unique=False)
        nick = Column(String(25), nullable=True, unique=False)
        email = Column(String, nullable=True, unique=False)
        first_name = Column(String(25), nullable=True, unique=False)
        last_name = Column(String(25), nullable=True, unique=False)
        birthday = Column(Date, nullable=True, unique=False)
        active = Column(Boolean, default=True)

        def __init__(self, **kwargs):
            self.username = kwargs['username'] if 'username' in kwargs else None
            self.password = kwargs['password'] if 'password' in kwargs else None
            self.nick = kwargs['nick'] if 'nick' in kwargs else None
            self.email = kwargs['email'] if 'email' in kwargs else None
            self.first_name = kwargs['first_name'] if 'first_name' in kwargs else None
            self.last_name = kwargs['last_name'] if 'last_name' in kwargs else None
            self.birthday = kwargs['last_name'] if 'last_name' in kwargs else None

    class UsersMessageHistory(Base):
        """Статистика по отправки сообщений пользователем"""

        __tablename__ = 'users_message_history'

        id = Column(Integer, primary_key=True)
        user_id = Column(ForeignKey('users.id'), nullable=True)
        sent = Column(Integer, default=0)
        accepted = Column(Integer, default=0)

        def __init__(self, user_id, sent=0, accepted=0):
            self.user_id = user_id
            self.sent = sent
            self.accepted = accepted


    class UsersEntryHistory(Base):
        """ Таблица истории входа и активных пользователей """

        __tablename__ = 'users_entry_history'

        id = Column('id', Integer, primary_key=True)
        user_id = Column(ForeignKey('users.id'), nullable=True)
        active = Column(Boolean, default=True)
        login_time = Column(DateTime, default=now(), nullable=True)
        logout_time = Column(DateTime, nullable=True)
        ip_address = Column(String, nullable=True)
        port = Column(Integer, nullable=True)

        def __init__(self, **kwargs):
            self.user_id = kwargs['user_id'] if 'user_id' in kwargs else None
            self.ip_address = kwargs['ip_address'] if 'ip_address' in kwargs else None
            self.port = kwargs['port'] if 'port' in kwargs else None

    class UsersRelationship(Base):
        """Таблица связей пользователей"""
        
        __tablename__ = 'users_relationship'

        id = Column('id', Integer, primary_key=True)
        user_id = Column(ForeignKey('users.id'), nullable=True)
        contact_user_id = Column(ForeignKey('users.id'), nullable=True)
        datetime = Column(DateTime, default=now(), nullable=True)
        active = Column(Boolean, default=True)

        def __init__(self, **kwargs):
            self.user = kwargs['user_id'] if 'user_id' in kwargs else None  
            self.contact_user_id = kwargs['contact_user_id'] if 'contact_user_id' in kwargs else None

    def __init__(self):

        self.database_engine = create_engine(SERVER_DATABASE, echo=False, pool_recycle=7200,
                                             connect_args={'check_same_thread': False})

        Base.metadata.create_all(self.database_engine)

        session = sessionmaker(bind=self.database_engine)
        self.session = session()

        self.session.query(self.UsersEntryHistory).filter_by(active=True)\
            .update({"active": False, 'logout_time': now()})
        self.session.commit()

    def user_login(self, username, ip_address, port):
        """Функция выполняющяяся при входе пользователя, записывает в базу факт входа"""
        print('login:', username, ip_address, port)
        rez = self.session.query(self.Users).filter_by(username=username)
        if rez.count():
            user = rez.first()
            user.last_login = now()
        else:
            user = self.Users(username=username, )
            self.session.add(user)
            self.session.commit()
            user_in_history = self.UsersMessageHistory(user.id)
            self.session.add(user_in_history)

        history = self.UsersEntryHistory(user_id=user.id, ip_address=ip_address, port=port)
        self.session.add(history)
        self.session.commit()

    def user_logout(self, username, ip_address, port):
        """Функция фиксирующая отключение пользователя по опредёлённому адресу и порту"""
        print('logout:', username, ip_address, port)
        user = self.session.query(self.Users).filter_by(username=username).first()
        self.session.query(self.UsersEntryHistory).filter_by(user_id=user.id, ip_address=ip_address, port=port).\
            update({'active': False, 'logout_time': now()})
        self.session.commit()

    def process_message(self, sender, recipient):
        """Фиксируем информацию в статистике историии обмена сообщениями"""
        sender = self.session.query(self.Users).filter_by(username=sender).first().id
        recipient = self.session.query(self.Users).filter_by(username=recipient).first().id
        # Запрашиваем строки из истории и увеличиваем счётчики
        sender_row = self.session.query(self.UsersMessageHistory).filter_by(user_id=sender).first()
        recipient_row = self.session.query(self.UsersMessageHistory).filter_by(user_id=recipient).first()

        if sender_row:
            sender_row.sent += 1
        else:
            sender_row = self.UsersMessageHistory(user_id=sender, sent=1)
            self.session.add(sender_row)

        if recipient_row:
            recipient_row.accepted += 1
        else:
            accepted_row = self.UsersMessageHistory(user_id=recipient, accepted=1)
            self.session.add(accepted_row)

        self.session.commit()

    # Функция возвращает список известных пользователей со временем последнего входа.
    def users_list(self):
        query = self.session.query(
            self.Users.username,
            func.max(self.UsersEntryHistory.login_time))\
            .join(self.UsersEntryHistory)\
            .group_by(self.Users.username)\
            .order_by(self.Users.username)
        return query.all()

    def active_users_list(self):
        """ Функция возвращает список активных пользователей"""
        query = self.session.query(
            self.Users.username,
            self.UsersEntryHistory.ip_address,
            self.UsersEntryHistory.port,
            self.UsersEntryHistory.login_time)\
            .join(self.UsersEntryHistory)\
            .filter_by(active=True) \
            .order_by('username')
        # Возвращаем список кортежей
        return query.all()

    def message_history(self):
        """Функция возвращает количество переданных и полученных сообщений"""
        query = self.session.query(
            self.Users.username,
            func.max(self.UsersEntryHistory.login_time),
            func.sum(self.UsersMessageHistory.sent),
            func.sum(self.UsersMessageHistory.accepted)
            ).join(self.UsersEntryHistory, self.UsersMessageHistory)\
            .group_by(self.Users.username)\
            .order_by(self.Users.username)

        # Возвращаем список кортежей
        return query.all()

    def login_history(self, username=None):
        """ Функция возвращающая историю входов по пользователю или всем пользователям """
        query = self.session.query(self.Users.username,
                                   self.UsersEntryHistory.login_time,
                                   self.UsersEntryHistory.logout_time,
                                   self.UsersEntryHistory.ip_address,
                                   self.UsersEntryHistory.port
                                   ).join(self.UsersEntryHistory)\
                                    .order_by('username')
        # Если было указано имя пользователя, то фильтруем по нему
        if username:
            query = query.filter(self.Users.username == username)
        return query.all()


# Отладка
if __name__ == '__main__':
    test_db = ServerStorage()

    print('выполняем подключение пользователя')
    test_db.user_login('client_1', '192.168.1.4', 8888)
    test_db.user_login('client_2', '192.168.1.5', 7777)
    print('выводим список кортежей - активных пользователей:')
    for elem in test_db.active_users_list():
        print(elem)
    print('выполянем отключение пользователя: client_1')
    test_db.user_logout('client_1', '192.168.1.4', 8888)
    print('выводим список активных пользователей:')
    for elem in test_db.active_users_list():
        print(elem)
    print('запрашиваем историю входов по пользователю')
    for elem in test_db.login_history('client_1'):
        print(elem)
    print('выводим список известных пользователей')
    for elem in test_db.users_list():
        print(elem)
