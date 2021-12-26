from PyQt5.QtWidgets import QDialog, QPushButton, QLineEdit, QApplication, QLabel , qApp


class UserNameDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.ok_pressed = False
        self.setWindowTitle('Messanger client (Beta)')
        self.setFixedSize(350, 160)

        self.label = QLabel('Enter username:', self)
        self.label.setFixedSize(330, 20)
        self.label.move(10, 10)

        self.client_name = QLineEdit(self)
        self.client_name.setFixedSize(330, 20)
        self.client_name.move(10, 35)

        self.label_passwd = QLabel('Enter password:', self)
        self.client_name.setFixedSize(330, 20)
        self.label_passwd.move(10, 60)

        self.client_passwd = QLineEdit(self)
        self.client_passwd.setFixedSize(330, 20)
        self.client_passwd.move(10, 85)
        self.client_passwd.setEchoMode(QLineEdit.Password)

        self.btn_ok = QPushButton('Continue..', self)
        self.btn_ok.move(170, 120)
        self.btn_ok.clicked.connect(self.click)

        self.btn_cancel = QPushButton('Exit', self)
        self.btn_cancel.move(260, 120)
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
