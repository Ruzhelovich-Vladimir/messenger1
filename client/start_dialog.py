from PyQt5.QtWidgets import QDialog, QPushButton, QLineEdit, QApplication, QLabel , qApp


class UserNameDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.ok_pressed = False
        self.setWindowTitle('Messanger client (Beta)')
        self.setFixedSize(350, 110)

        self.label = QLabel('Enter username:', self)
        self.label.move(10, 10)
        # self.label.setFixedSize(150, 10)

        self.client_name = QLineEdit(self)
        self.client_name.setFixedSize(330, 20)
        self.client_name.move(10, 35)

        self.btn_ok = QPushButton('Start..', self)
        self.btn_ok.move(170, 70)
        self.btn_ok.clicked.connect(self.click)

        self.btn_cancel = QPushButton('Exit', self)
        self.btn_cancel.move(260, 70)
        self.btn_cancel.clicked.connect(qApp.exit)

        self.show()

    def click(self):
        if self.client_name.text():
            self.ok_pressed = True
            qApp.exit()


if __name__ == '__main__':
    app = QApplication([])
    dial = UserNameDialog()
    app.exec_()
