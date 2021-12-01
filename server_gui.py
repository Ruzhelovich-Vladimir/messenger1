import os
import sys

from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QAction, qApp, QTableView, QDialog, QLineEdit, \
    QPushButton, QFileDialog


def gui_create_main_form_model(database):
    """Active connections list model"""
    list_users = database.active_users_list()
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
        # Уберём милисекунды из строки времени, т.к. такая точность не требуется.
        time = QStandardItem(str(time.replace(microsecond=0)))
        time.setEditable(False)
        list_model.appendRow([user, ip, port, time])
    return list_model


def create_stat_form_model(database):
    """History connections"""
    # Список записей из базы
    hist_list = database.message_history()

    # Объект модели данных:
    list = QStandardItemModel()
    list.setHorizontalHeaderLabels(
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
        list.appendRow([user, last_seen, sent, receive])
    return list


class MainWindow(QMainWindow):
    """Main window"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_windows_from()
        self._init_status_bar_form()
        self._init_toolbar_from()
        self._init_data_form()
        self.show()

    def _init_windows_from(self):
        self.setWindowTitle("Messenger server manager")
        # self.resize(400, 600)
        self.setFixedSize(420, 600)

    def _init_toolbar_from(self):
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(qApp.quit)
        self.refresh_button = QAction('Refresh list', self)
        self.config_btn = QAction('Settings', self)
        self.show_history_button = QAction('History', self)

        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(exit_action)
        self.toolbar.addAction(self.refresh_button)
        self.toolbar.addAction(self.show_history_button)
        self.toolbar.addAction(self.config_btn)

    def _init_status_bar_form(self):
        self.statusBar()

    def _init_data_form(self):
        self.label = QLabel('Connections list:', self)
        self.label.setFixedSize(240, 30)
        self.label.move(10, 25)

        self.active_clients_table = QTableView(self)
        self.active_clients_table.move(10, 55)
        self.active_clients_table.setFixedSize(400, 520)


class HistoryWindow(QDialog):
    def __init__(self):
        super().__init__()
        self._init_windows_from()
        self._init_status_bar_form()
        self._init_toolbar_from()
        self._init_data_form()
        self.show()

    def _init_windows_from(self):
        """Настройки окна"""
        self.setWindowTitle('User statics')
        self.setFixedSize(420, 600)
        self.setAttribute(Qt.WA_DeleteOnClose) # Qt.WA_DeleteOnClose

    def _init_status_bar_form(self):
        pass

    def _init_toolbar_from(self):
        """Кнапка закрытия окна"""
        # self.close_button = QPushButton('Close', self)
        # self.close_button.move(10, 10)
        # self.close_button.clicked.connect(self.close)
        pass

    def _init_data_form(self):
        """ Лист с собственно историей"""
        self.history_table = QTableView(self)
        self.history_table.move(10, 10)
        self.history_table.setFixedSize(400, 580)


# Класс окна настроек
class ConfigWindow(QDialog):
    def __init__(self):
        super().__init__()
        self._init_windows_from()
        self._init_status_bar_form()
        self._init_toolbar_from()
        self._init_data_form()
        self.show()

    def _init_windows_from(self):
        self.setFixedSize(365, 260)
        self.setWindowTitle('Settings server')

    def _init_toolbar_from(self):
        pass

    def _init_status_bar_form(self):
        pass

    def _init_data_form(self):

        self.db_path_label = QLabel('Database path: ', self)
        self.db_path_label.move(10, 10)
        self.db_path_label.setFixedSize(240, 15)

        #  Data base path field
        self.db_path = QLineEdit(self)
        self.db_path.setFixedSize(250, 20)
        self.db_path.move(10, 30)
        self.db_path.setReadOnly(True)

        # Check botton
        self.db_path_select = QPushButton('Choose..', self)
        self.db_path_select.move(275, 28)


        def open_file_dialog():
            """ Функция обработчик открытия окна выбора папки """
            global dialog
            dialog = QFileDialog(self)
            db_path = dialog.getExistingDirectory()
            # path = path.replace('/', '\\') # У меня UBUNTU
            if os.path.isdir(db_path):
                self.db_path.setText(db_path) #insert(path)

        self.db_path_select.clicked.connect(open_file_dialog)

        # Метка с именем поля файла базы данных
        self.db_file_label = QLabel('Database username: ', self)
        self.db_file_label.move(10, 68)
        self.db_file_label.setFixedSize(180, 15)

        # Поле для ввода имени файла
        self.db_file = QLineEdit(self)
        self.db_file.move(200, 66)
        self.db_file.setFixedSize(150, 20)

        # Метка с номером порта
        self.port_label = QLabel('Connection port:', self)
        self.port_label.move(10, 108)
        self.port_label.setFixedSize(180, 15)

        # Поле для ввода номера порта
        self.port = QLineEdit(self)
        self.port.move(200, 108)
        self.port.setFixedSize(150, 20)

        # Метка с адресом для соединений
        self.ip_label = QLabel('Source IP:', self)
        self.ip_label.move(10, 148)
        self.ip_label.setFixedSize(180, 15)

        # Метка с напоминанием о пустом поле.
        self.ip_label_note = QLabel('empty if accepted from any address', self)
        self.ip_label_note.move(10, 168)
        self.ip_label_note.setFixedSize(500, 30)

        # Поле для ввода ip
        self.ip = QLineEdit(self)
        self.ip.move(200, 148)
        self.ip.setFixedSize(150, 20)

        # Кнопка сохранения настроек
        self.save_btn = QPushButton('Save', self)
        self.save_btn.move(190, 220)

        # Кнапка закрытия окна
        self.close_button = QPushButton('Close', self)
        self.close_button.move(275, 220)
        self.close_button.clicked.connect(self.close)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    #win = MainWindow()
    win = HistoryWindow()
    win.show()
    sys.exit(app.exec_())
