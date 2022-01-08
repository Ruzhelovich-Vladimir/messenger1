
# Класс окна настроек
import os
import sys

from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, \
    QFileDialog, QApplication

global dialog


class ConfigWindow(QDialog):
    def __init__(self):
        super().__init__()
    
        self._init_windows_from()
        self._init_status_bar_form()
        self._init_toolbar_from()
        self._init_data_form()
        self.show()

    def _init_windows_from(self):
        """ Инициализация формы """
        self.setFixedSize(365, 260)
        self.setWindowTitle('Settings server')

    def _init_toolbar_from(self):
        pass

    def _init_status_bar_form(self):
        pass

    def _init_data_form(self):
        """ Инициализация данных """
        self.db_path_label = QLabel('Database path: ', self)
        self.db_path_label.move(10, 10)
        self.db_path_label.setFixedSize(240, 15)

        #  Database path field
        self.db_path = QLineEdit(self)
        self.db_path.setFixedSize(250, 20)
        self.db_path.move(10, 30)
        self.db_path.setReadOnly(True)

        # Check bottom
        self.db_path_select = QPushButton('Choose..', self)
        self.db_path_select.move(275, 28)

        def open_file_dialog():
            """ Функция обработчик открытия окна выбора папки """
            global dialog
            dialog = QFileDialog(self)
            db_path = dialog.getExistingDirectory()
            if os.path.isdir(db_path):
                self.db_path.setText(db_path)

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

        # Кнопка закрытия окна
        self.close_button = QPushButton('Close', self)
        self.close_button.move(275, 220)
        self.close_button.clicked.connect(self.close_windows)

    def close_windows(self):
        """ Закрытие окна """
        super().close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ConfigWindow()
    win.show()
    sys.exit(app.exec_())
