from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime, Boolean, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
Base = declarative_base()

class ClientDatabase:

    def __init__(self, username):

        self.database_engine = create_engine(f'sqlite:///client_{username}.db3', echo=False, pool_recycle=7200,
                                             connect_args={'check_same_thread': False})
        Base.metadata.create_all(self.database_engine)

        session = sessionmaker(bind=self.database_engine)
        self.session = session()


    # Класс - отображение таблицы известных пользователей.
    class KnownUsers(Base):
        __tablename__ = 'known_users'

        id = Column(Integer, primary_key=True)
        username = Column(String(25), nullable=True, unique=True, index=True)
        nick = Column(String(25), nullable=True, unique=False)
        first_name = Column(String(25), nullable=True, unique=False)
        last_name = Column(String(25), nullable=True, unique=False)
        birthday = Column(Date, nullable=True, unique=False)

        def __init__(self, user):
            self.username = user

    # Класс - отображение таблицы истории сообщений
    class MessageHistory(Base):
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

    # Класс - отображение списка контактов
    class Contacts(Base):
        __tablename__ = 'contacts'
        id = Column(Integer, primary_key=True)
        user_id = Column(ForeignKey('known_users.id'), nullable=True)

        def __init__(self, user_id):
            self.user_id = user_id


    # Функция добавления контактов
    def add_contact(self, contact):
        id = self.session.query(self.KnownUsers).filter_by(username=contact).first().id
        if id:
            contact_row = self.Contacts(id)
            self.session.add(contact_row)
            self.session.commit()

    # Функция удаления контакта
    def del_contact(self, contact):
        if contact:
            user_id = self.session.query(self.KnownUsers).filter_by(username=contact).all()[0].id
        self.session.query(self.Contacts).filter_by(user_id=user_id).delete()
        self.session.commit()

    # Функция добавления известных пользователей.
    # Пользователи получаются только с сервера, поэтому таблица очищается.
    def add_users(self, users_list):
        self.session.query(self.KnownUsers).delete()
        for user in users_list:
            user_row = self.KnownUsers(user)
            self.session.add(user_row)
        self.session.commit()

    # Функция сохраняющяя сообщения
    def save_message(self, from_user, to_user, message):

        from_user_id = self.session.query(self.KnownUsers).filter_by(username=from_user).all()[0].id
        to_user_id = self.session.query(self.KnownUsers).filter_by(username=to_user).all()[0].id
        message_row = self.MessageHistory(from_user_id=from_user_id, to_user_id=to_user_id, message=message)
        self.session.add(message_row)
        self.session.commit()

    # Функция возвращающяя контакты
    def get_contacts(self):
        # TODO Проверить соединение INNER JOIN
        query = self.session.query(self.KnownUsers.username).join(self.Contacts)
        query_result = query.all()
        return [contact[0] for contact in query_result]

    # Функция возвращающяя список известных пользователей
    def get_users(self):
        return [user[0] for user in self.session.query(self.KnownUsers.username).all()]

    # Функция проверяющяя наличие пользователя в известных
    def check_user(self, user):
        if self.session.query(self.KnownUsers).filter_by(username=user).count():
            return True
        else:
            return False

    # Функция проверяющяя наличие пользователя контактах
    def check_contact(self, contact):
        if self.session.query(self.Contacts).join(self.KnownUsers).filter(self.KnownUsers.username==contact).count():
            return True
        else:
            return False

    # Функция возвращающая историю переписки
    def get_history(self, from_who=None, to_who=None):

        where_str = ''
        where_str += f"from_user.username = '{from_who}'" if from_who else ''
        where_str += ' or ' if from_who and to_who else ''
        where_str += f"to_user.username = '{to_who}'" if to_who else ''

        sql = text(
        f'''
        SELECT DISTINCT
            from_user.username AS from_user
            ,to_user.username AS to_user
            ,message_history.message AS message
            ,message_history.datetime AS datetime
        FROM
            message_history
            JOIN known_users AS from_user ON message_history.from_user_id = from_user.id 
            JOIN known_users AS to_user ON message_history.to_user_id = to_user.id
        WHERE {where_str}
        ''')
        query_result = self.session.execute(sql)

        return [(history_row.from_user, history_row.to_user, history_row.message,
                 datetime.datetime.strptime(history_row.datetime, '%Y-%m-%d %H:%M:%S.%f').replace(microsecond=0))
                for history_row in query_result]
        # TODO разобраться с ORM, связи с дух таблиц
        # tbl1 = self.KnownUsers.username
        # tbl2 = self.KnownUsers.username
        # query = self.session.query(self.MessageHistory, tbl1, tbl2).\
        #     join(tbl1,
        #          self.MessageHistory.from_user_id == tbl1.id, ). \
        #     join(tbl2,
        #          self.MessageHistory.to_user_id == tbl2.id, aliased='to_user')

        # query_result = query.all()
        # return [(history_row.from_user_id, history_row.to_user_id, history_row.message, history_row.datetime)
        #         for history_row in query_result]


# отладка
if __name__ == '__main__':
    test_db = ClientDatabase('test1')
    test_db.add_users(['test1', 'test2', 'test3', 'test4', 'test5'])
    for i in ['test3', 'test4', 'test5']:
        test_db.add_contact(i)
    test_db.add_contact('test4')
    test_db.save_message('test1', 'test2', f'Привет! я тестовое сообщение от {datetime.datetime.now()}!')
    test_db.save_message('test2', 'test1', f'Привет! я другое тестовое сообщение от {datetime.datetime.now()}!')
    print(test_db.get_contacts())
    print(test_db.get_users())
    print(test_db.check_user('test1'))
    print(test_db.check_user('test10'))
    print(test_db.get_history('test2'))
    print(test_db.get_history(to_who='test2'))
    print(test_db.get_history('test3'))
    test_db.del_contact('test4')
    print(test_db.get_contacts())
