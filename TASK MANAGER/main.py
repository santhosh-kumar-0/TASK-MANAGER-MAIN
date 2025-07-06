# main.py
import sys
from PyQt5.QtWidgets import QApplication, QStackedWidget, QMessageBox
from PyQt5.QtGui import QIcon # Import QIcon
from auth_windows import AuthWindow
import os # Import os for path handling

class ApplicationManager(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.auth_window = AuthWindow(self)
        self.main_task_manager_ui = None
        self.teacher_access_window = None # Initialize teacher window to None
        self.addWidget(self.auth_window)
        self.setCurrentWidget(self.auth_window)

    def show_main_window_for_role(self, username, role):
        if role == "student":
            if self.main_task_manager_ui is None:
                from task_manager_ui import MainTaskManagerUI
                self.main_task_manager_ui = MainTaskManagerUI(self)
                self.addWidget(self.main_task_manager_ui)
            self.main_task_manager_ui.set_current_user(username)
            self.setCurrentWidget(self.main_task_manager_ui)
        elif role == "teacher":
            if self.teacher_access_window is None:
                from teacher_access_window import TeacherAccessWindow
                self.teacher_access_window = TeacherAccessWindow(username) # Pass teacher_username
                self.addWidget(self.teacher_access_window)
            # No set_current_user for teacher window needed unless it has specific user data to load
            self.setCurrentWidget(self.teacher_access_window)
        else:
            print(f"Error: Unknown role '{role}' for user '{username}'.")
            # Optionally show an error message box to the user
            self.auth_window.show_message_box("Login Error", f"Unknown user role: {role}. Please contact support.", QMessageBox.Critical)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Set the application icon
    # Ensure you have an 'icons' directory with 'task_icon.png' in your project root
    icon_path = os.path.join("icons", "task_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        print(f"Warning: Icon file not found at {icon_path}. Application icon might not be displayed.")

    manager = ApplicationManager()
    manager.show()
    sys.exit(app.exec_())
