import sys

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QAction, qApp, \
    QTableView

from server.add_user import RegisterUser
from server.config_window import ConfigWindow
from server.remove_user import DelUserDialog
from server.stat_window import StatWindow

global stat_window
global config_window
global reg_window
global rem_window


class MainWindow(QMainWindow):
    """Класса главного окна"""

    def __init__(self, database, server, config):
        super().__init__()

        self.database = database
        self.server_thread = server
        self.config = config

        self._init_windows_from()
        self._init_status_bar_form()
        self._init_toolbar_from()
        self._init_data_form()

        self.refresh_button.triggered.connect(self.view_users_model)
        self.show_history_button.triggered.connect(self.show_statistics)
        self.config_btn.triggered.connect(self.server_config)
        self.register_user_btn.triggered.connect(self.reg_user)
        self.remove_user_btn.triggered.connect(self.rem_user)

        self.show()

    def _init_windows_from(self):
        self.setWindowTitle("Messenger server manager")
        self.setFixedSize(420, 600)

    def _init_toolbar_from(self):
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(qApp.quit)
        self.refresh_button = QAction('Refresh list', self)
        self.config_btn = QAction('Settings', self)
        self.show_history_button = QAction('History', self)
        self.register_user_btn = QAction('Registration user', self)
        self.remove_user_btn = QAction('Remove user', self)

        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(exit_action)
        self.toolbar.addAction(self.refresh_button)
        self.toolbar.addAction(self.show_history_button)
        self.toolbar.addAction(self.config_btn)
        self.toolbar.addAction(self.register_user_btn)
        self.toolbar.addAction(self.remove_user_btn)

    def _init_status_bar_form(self):
        self.statusBar()

    def _init_data_form(self):
        self.label = QLabel('Connections list:', self)
        self.label.setFixedSize(240, 30)
        self.label.move(10, 25)

        # Таймер, обновляющий список клиентов 1 раз в секунду
        self.timer = QTimer()
        self.timer.timeout.connect(self.view_users_model)
        self.timer.start(1000)

        self.active_clients_table = QTableView(self)
        self.active_clients_table.move(10, 55)
        self.active_clients_table.setFixedSize(400, 520)

    def view_users_model(self):
        """Active connections list model"""
        list_users = self.database.active_users_list()
        list_model = QStandardItemModel()
        list_model.setHorizontalHeaderLabels(['User', 'IP', 'Port', 'Time'])
        for row in list_users:
            user, ip, port, time = row
            user = QStandardItem(user)
            user.setEditable(False)
            ip = QStandardItem(ip)
            ip.setEditable(False)
            port = QStandardItem(str(port))
            port.setEditable(False)
            time = QStandardItem(str(time.replace(microsecond=0)))
            time.setEditable(False)
            # pubkey = QStandardItem(str(pubkey))
            # pubkey.setEditable(False)
            list_model.appendRow([user, ip, port, time])
        self.active_clients_table.setModel(list_model)
        self.active_clients_table.resizeColumnsToContents()
        self.active_clients_table.resizeRowsToContents()
        return list_model

    def view_statistic_form_model(self):
        """History connections"""
        # Список записей из базы
        hist_list = self.database.message_history()

        # Объект модели данных:
        lst = QStandardItemModel()
        lst.setHorizontalHeaderLabels(
            ['User', 'Last login', 'Sent by', 'Received'])

        for row in hist_list:

            user, last_seen, sent, receive = row
            user = QStandardItem(user)
            user.setEditable(False)
            last_seen = QStandardItem(str(last_seen.replace(microsecond=0)))
            last_seen.setEditable(False)
            sent = QStandardItem(str(sent))
            sent.setEditable(False)
            receive = QStandardItem(str(receive))
            receive.setEditable(False)
            lst.appendRow([user, last_seen, sent, receive])

        return lst

    def show_statistics(self):
        """ Функция создающая окно со статистикой клиентов """
        global stat_window
        stat_window = StatWindow(self.database)
        stat_window.show()

    @staticmethod
    def server_config():
        """ Функция создающая окно с настройками сервера. """
        global config_window
        # Создаём окно и заносим в него текущие параметры
        config_window = ConfigWindow()

    def reg_user(self):
        """ Метод создающий окно регистрации пользователя. """
        global reg_window
        reg_window = RegisterUser(self.database, self.server_thread)
        reg_window.show()

    def rem_user(self):
        """ Метод создающий окно удаления пользователя. """
        global rem_window
        rem_window = DelUserDialog(self.database, self.server_thread)
        rem_window.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # win = MainWindow()
    # win.show()
    sys.exit(app.exec_())
