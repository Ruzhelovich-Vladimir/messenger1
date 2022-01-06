import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QTableView, QApplication


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
        self.setAttribute(Qt.WA_DeleteOnClose)  # Qt.WA_DeleteOnClose

    def _init_status_bar_form(self):
        pass

    def _init_toolbar_from(self):
        """Кнопка закрытия окна"""
        # self.close_button = QPushButton('Close', self)
        # self.close_button.move(10, 10)
        # self.close_button.clicked.connect(self.close)
        pass

    def _init_data_form(self):
        """ Лист с собственно историей"""
        self.history_table = QTableView(self)
        self.history_table.move(10, 10)
        self.history_table.setFixedSize(400, 580)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = HistoryWindow()
    win.show()
    sys.exit(app.exec_())
