# ui_components.py

from PyQt5.QtWidgets import QMessageBox

class CustomMessageBox(QMessageBox):
    """
    Custom styled QMessageBox for consistent UI across the application.
    Applies a light theme to the message box itself and its buttons.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QMessageBox {
                background-color: #ffffff;
                color: #333333;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 14px;
            }
            QMessageBox QLabel {
                color: #333333;
            }
            QMessageBox QPushButton {
                background-color: #3a7fe0;
                border: none;
                border-radius: 5px;
                padding: 7px 15px;
                color: #ffffff;
                font-weight: bold;
            }
            QMessageBox QPushButton:hover {
                background-color: #4a8ff0;
            }
            QMessageBox QPushButton:pressed {
                background-color: #2b6ecd;
            }
        """)
        self.setWindowTitle("Notification")
        self.setIcon(QMessageBox.Information)   # Default icon can be changed based on context      
        self.setStandardButtons(QMessageBox.Ok) 
        self.setDefaultButton(QMessageBox.Ok)
    def set_message(self, title, text, icon=QMessageBox.Information):
        """        Set the message box title, text, and icon.           
        """
        self.setWindowTitle(title)
        self.setText(text)
        self.setIcon(icon)  
    def show_message(self):
        """        Show the message box.           
        """
        self.exec_()
        