from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime, \
    create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
Base = declarative_base()


class ClientDatabase:
    """ Класс структуры данных для клиентского приложения"""

    def __init__(self, username):

        self.database_engine = \
            create_engine(f'sqlite:///client_{username}.db3',
                          echo=False, pool_recycle=7200,
                          connect_args={'check_same_thread': False})
        Base.metadata.create_all(self.database_engine)

        session = sessionmaker(bind=self.database_engine)
        self.session = session()

    class KnownUsers(Base):
        """ Класс - отображение таблицы пользователей системы """
        __tablename__ = 'known_users'

        id = Column(Integer, primary_key=True)
        username = Column(String(25), nullable=True, unique=True, index=True)
        nick = Column(String(25), nullable=True, unique=False)
        first_name = Column(String(25), nullable=True, unique=False)
        last_name = Column(String(25), nullable=True, unique=False)
        birthday = Column(Date, nullable=True, unique=False)

        def __init__(self, user):
            self.username = user

    class MessageHistory(Base):
        """ Класс - отображение таблицы истории сообщений """
        __tablename__ = 'message_history'

        id = Column(Integer, primary_key=True)
        from_user_id = Column(ForeignKey('known_users.id'), nullable=True)
        to_user_id = Column(ForeignKey('known_users.id'), nullable=True)
        message = Column(String(256))
        datetime = Column(DateTime, nullable=False, unique=False)

        def __init__(self, from_user_id, to_user_id, message):
            self.from_user_id = from_user_id
            self.to_user_id = to_user_id
            self.message = message
            self.datetime = datetime.datetime.now()

    class Contacts(Base):
        """ Класс - отображение таблицы контактов """
        __tablename__ = 'contacts'
        id = Column(Integer, primary_key=True)
        user_id = Column(ForeignKey('known_users.id'), nullable=True)

        def __init__(self, user_id):
            self.user_id = user_id

    def add_contact(self, contact):
        """ Функция добавления контактов """
        user_id = self.session.query(self.KnownUsers).\
            filter_by(username=contact).\
            first().id
        if id:
            contact_row = self.Contacts(user_id)
            self.session.add(contact_row)
            self.session.commit()

    def del_contact(self, contact):
        """ Функция удаления контакта """
        if contact:
            user_id = self.session.query(self.KnownUsers).\
                filter_by(username=contact).all()[0].id
            self.session.query(self.Contacts).\
                filter_by(user_id=user_id).delete()
            self.session.commit()

    def add_users(self, users_list):
        """ Функция добавления известных пользователей.
        Пользователи получаются только с сервера, поэтому таблица очищается.
        """
        self.session.query(self.KnownUsers).delete()
        for user in users_list:
            user_row = self.KnownUsers(user)
            self.session.add(user_row)
        self.session.commit()

    def save_message(self, from_user, to_user, message):
        """ Функция сохраняющая сообщения """
        from_user_id = self.session.query(self.KnownUsers).\
            filter_by(username=from_user).all()[0].id
        to_user_id = self.session.query(self.KnownUsers).\
            filter_by(username=to_user).all()[0].id
        message_row = self.MessageHistory(from_user_id=from_user_id,
                                          to_user_id=to_user_id,
                                          message=message)
        self.session.add(message_row)
        self.session.commit()

    def get_contacts(self):
        """ Функция возвращающая контакты """
        # TODO Проверить соединение INNER JOIN
        query = self.session.query(self.KnownUsers.username).\
            join(self.Contacts)
        query_result = query.all()
        return [contact[0] for contact in query_result]

    def get_users(self):
        """ Функция возвращающая список известных пользователей """
        return [user[0]
                for user in self.session.query(self.KnownUsers.username).all()]

    def check_user(self, user):
        """ Функция проверяющая наличие пользователя в известных """
        if self.session.query(self.KnownUsers).\
                filter_by(username=user).count():
            return True
        else:
            return False

    def check_contact(self, username):
        """" Функция проверяющая наличие пользователя в известных """
        if self.session.query(self.Contacts).join(self.KnownUsers).\
                filter(self.KnownUsers.username == username).count():
            return True
        else:
            return False

    def get_history(self, from_who=None, to_who=None):
        """ Функция возвращающая историю переписки """
        where_str = ''
        where_str += f"from_user.username = '{from_who}'" if from_who else ''
        where_str += ' or ' if from_who and to_who else ''
        where_str += f"to_user.username = '{to_who}'" if to_who else ''

        sql = text(f'''
        SELECT DISTINCT
            from_user.username AS from_user
            ,to_user.username AS to_user
            ,message_history.message AS message
            ,message_history.datetime AS datetime
        FROM
            message_history
            JOIN known_users AS from_user ON 
            message_history.from_user_id = from_user.id 
            JOIN known_users AS to_user ON 
            message_history.to_user_id = to_user.id
        WHERE {where_str}
        ''')
        query_result = self.session.execute(sql)

        return [(history_row.from_user,
                 history_row.to_user,
                 history_row.message,
                 datetime.datetime.strptime(history_row.datetime,
                                            '%Y-%m-%d %H:%M:%S.%f').
                 replace(microsecond=0))
                for history_row in query_result]
        # TODO разобраться с ORM, связи с дух таблиц


if __name__ == '__main__':
    test_db = ClientDatabase('test1')
    test_db.add_users(['test1', 'test2', 'test3', 'test4', 'test5'])
    for i in ['test3', 'test4', 'test5']:
        test_db.add_contact(i)
    test_db.add_contact('test4')
    test_db.\
        save_message('test1',
                     'test2',
                     f'Привет! я тестовое сообщение от '
                     f'{datetime.datetime.now()}!')
    test_db.save_message('test2',
                         'test1',
                         f'Привет! я другое тестовое сообщение от '
                         f'{datetime.datetime.now()}!')
    print(test_db.get_contacts())
    print(test_db.get_users())
    print(test_db.check_user('test1'))
    print(test_db.check_user('test10'))
    print(test_db.get_history('test2'))
    print(test_db.get_history(to_who='test2'))
    print(test_db.get_history('test3'))
    test_db.del_contact('test4')
    print(test_db.get_contacts())
