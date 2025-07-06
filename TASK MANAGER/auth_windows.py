# Enhanced auth_windows.py login design with card-style framing and extra options
import os
import shutil
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtGui import QPixmap, QIcon # Import QIcon
from PyQt5.QtWidgets import QMessageBox
import sys
import json
import hashlib
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLineEdit, QPushButton, QLabel, QFrame, QSpacerItem, QSizePolicy, QCheckBox, QGroupBox, QComboBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from config import DEFAULT_PROFILE_PHOTO, PROFILE_PHOTOS_DIR, USERS_FILE
from ui_components import CustomMessageBox # Import CustomMessageBox

class AuthWindow(QWidget):
    def __init__(self, main_app_stacked_widget=None):
        super().__init__()
        self.main_app_stacked_widget = main_app_stacked_widget
        self.setWindowTitle("Login")
        
        # Set window icon
        icon_path = os.path.join("icons", "task_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"Warning: Icon file not found for AuthWindow at {icon_path}.")

        self.setStyleSheet(self.light_stylesheet())
        self.main_app_stacked_widget = main_app_stacked_widget
        self.profile_photo_path = None # To store path of selected profile photo
        self.user_details_dropdown = None
        self.setup_ui()

    def setup_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setAlignment(Qt.AlignCenter)

        self.container = QGroupBox()
        self.container.setTitle("Task Manager")
        self.container.setFixedWidth(400)
        self.container.setFixedHeight(550) # Adjusted height to ensure all fields are visible
        self.container.setObjectName("container")
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setAlignment(Qt.AlignCenter)
        container_layout.setSpacing(15)

        # Title
        title_label = QLabel("Welcome")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(title_label)

        # Stacked widget for login/register
        self.stacked_widget = QStackedWidget()
        container_layout.addWidget(self.stacked_widget)

        self.login_page = self.create_login_page()
        self.register_page = self.create_register_page()

        self.stacked_widget.addWidget(self.login_page)
        self.stacked_widget.addWidget(self.register_page)

        # Toggle buttons
        toggle_layout = QHBoxLayout()
        self.login_toggle_button = QPushButton("Login")
        self.login_toggle_button.setObjectName("toggleButton")
        self.login_toggle_button.clicked.connect(self.show_login_page)
        toggle_layout.addWidget(self.login_toggle_button)

        self.register_toggle_button = QPushButton("Register")
        self.register_toggle_button.setObjectName("toggleButton")
        self.register_toggle_button.clicked.connect(self.show_register_page)
        toggle_layout.addWidget(self.register_toggle_button)
        
        container_layout.addLayout(toggle_layout)
        outer_layout.addWidget(self.container)

        self.show_login_page() # Default to login page

    def create_login_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        self.login_username_input = QLineEdit()
        self.login_username_input.setPlaceholderText("Username")
        self.login_username_input.setObjectName("inputField")
        layout.addWidget(self.login_username_input)

        self.login_password_input = QLineEdit()
        self.login_password_input.setPlaceholderText("Password")
        self.login_password_input.setEchoMode(QLineEdit.Password)
        self.login_password_input.setObjectName("inputField")
        layout.addWidget(self.login_password_input)

        self.show_password_checkbox_login = QCheckBox("Show Password")
        self.show_password_checkbox_login.stateChanged.connect(self.toggle_password_visibility_login)
        layout.addWidget(self.show_password_checkbox_login)

        login_button = QPushButton("Login")
        login_button.setObjectName("actionButton")
        login_button.clicked.connect(self.handle_login)
        layout.addWidget(login_button)
        
        # Forgot password button
        forgot_password_button = QPushButton("Forgot Password?")
        forgot_password_button.setObjectName("linkButton")
        forgot_password_button.clicked.connect(self.show_forgot_password_message)
        layout.addWidget(forgot_password_button)

        return page

    def create_register_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        self.register_username_input = QLineEdit()
        self.register_username_input.setPlaceholderText("Username")
        self.register_username_input.setObjectName("inputField")
        layout.addWidget(self.register_username_input)

        self.register_password_input = QLineEdit()
        self.register_password_input.setPlaceholderText("Password")
        self.register_password_input.setEchoMode(QLineEdit.Password)
        self.register_password_input.setObjectName("inputField")
        layout.addWidget(self.register_password_input)

        self.show_password_checkbox_register = QCheckBox("Show Password")
        self.show_password_checkbox_register.stateChanged.connect(self.toggle_password_visibility_register)
        layout.addWidget(self.show_password_checkbox_register)
        
        # Role selection dropdown
        layout.addWidget(QLabel("Select Role:"))
        self.role_dropdown = QComboBox()
        self.role_dropdown.addItems(["student", "teacher"])
        self.role_dropdown.setObjectName("inputField")
        layout.addWidget(self.role_dropdown)

        # Phone Number Input
        layout.addWidget(QLabel("Phone Number (Optional):")) # Changed label to Phone Number
        self.phone_number_input = QLineEdit() # Renamed email_input to phone_number_input
        self.phone_number_input.setPlaceholderText("e.g., +1234567890") # Changed placeholder text
        self.phone_number_input.setObjectName("inputField")
        layout.addWidget(self.phone_number_input)

        register_button = QPushButton("Register")
        register_button.setObjectName("actionButton")
        register_button.clicked.connect(self.handle_register)
        layout.addWidget(register_button)

        return page

    # Removed set_default_profile_photo and upload_profile_photo methods

    def show_login_page(self):
        self.stacked_widget.setCurrentWidget(self.login_page)
        self.login_toggle_button.setChecked(True)
        self.register_toggle_button.setChecked(False)

    def show_register_page(self):
        self.stacked_widget.setCurrentWidget(self.register_page)
        self.login_toggle_button.setChecked(False)
        self.register_toggle_button.setChecked(True)
        # Removed self.set_default_profile_photo()

    def toggle_password_visibility_login(self, state):
        if state == Qt.Checked:
            self.login_password_input.setEchoMode(QLineEdit.Normal)
        else:
            self.login_password_input.setEchoMode(QLineEdit.Password)

    def toggle_password_visibility_register(self, state):
        # Only affects register_password_input now
        if state == Qt.Checked:
            self.register_password_input.setEchoMode(QLineEdit.Normal)
        else:
            self.register_password_input.setEchoMode(QLineEdit.Password)

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def load_users(self):
        if not os.path.exists(USERS_FILE):
            return {}
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def save_users(self, users):
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)

    def show_message_box(self, title, message, icon=QMessageBox.Information, buttons=QMessageBox.Ok):
        """
        Custom styled QMessageBox for consistent UI across the application.
        """
        msg = CustomMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(icon)
        msg.setStandardButtons(buttons)
        return msg.exec_()

    def handle_login(self):
        username = self.login_username_input.text().strip()
        password = self.login_password_input.text().strip()
        hashed_password = self.hash_password(password)

        users = self.load_users()

        if username in users and users[username]["password"] == hashed_password:
            self.show_message_box("Login Success", f"Welcome, {username}!", QMessageBox.Information)
            role = users[username].get("role", "student") # Default to student if role not set
            
            # Removed profile photo saving logic during login

            if self.main_app_stacked_widget:
                self.main_app_stacked_widget.show_main_window_for_role(username, role)
        else:
            self.show_message_box("Login Failed", "Invalid username or password.", QMessageBox.Warning)

    def handle_register(self):
        username = self.register_username_input.text().strip()
        password = self.register_password_input.text().strip()
        # Removed confirm_password
        role = self.role_dropdown.currentText() # Get selected role
        phone_number = self.phone_number_input.text().strip() # Get phone number (changed from email)

        # Removed password confirmation check
        if not username or not password: # Only check username and password
            self.show_message_box("Registration Error", "Username and Password are required.", QMessageBox.Warning)
            return

        users = self.load_users()
        if username in users:
            self.show_message_box("Registration Error", "Username already exists.", QMessageBox.Warning)
            return

        hashed_password = self.hash_password(password)
        users[username] = {
            "password": hashed_password,
            "role": role, # Save the selected role
            "email": "", # Email is no longer collected, set to empty
            "phone_number": phone_number # Save the phone number
        }
        self.save_users(users)

        # Removed profile photo saving logic during registration

        self.show_message_box("Registration Success", "Account created successfully!", QMessageBox.Information)
        self.show_login_page() # Go back to login page after successful registration
        self.register_username_input.clear()
        self.register_password_input.clear()
        # Removed self.register_confirm_password_input.clear()
        self.phone_number_input.clear() # Clear phone number input (changed from email_input)
        self.profile_photo_path = None # Reset photo path
        # Removed self.set_default_profile_photo()

    def show_forgot_password_message(self):
        self.show_message_box("Forgot Password", "Please contact your administrator to reset your password.", QMessageBox.Information)

    def light_stylesheet(self):
        return """
            QWidget {
                background-color: #e0f2f7; /* Changed background color to a soft blue */
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 14px;
            }
            QGroupBox#container {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 15px;
                padding: 20px;
            }
            QGroupBox::title {
                color: #3a7fe0;
                font-size: 20px;
                font-weight: bold;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
            }
            QLabel#titleLabel {
                font-size: 28px;
                font-weight: bold;
                color: #3a7fe0;
                margin-bottom: 20px;
            }
            QLineEdit#inputField, QComboBox#inputField {
                border: 1px solid #cccccc;
                border-radius: 10px;
                padding: 12px;
                font-size: 15px;
                color: #333333;
                background-color: #f8f8f8;
            }
            QLineEdit#inputField:focus, QComboBox#inputField:focus {
                border: 1px solid #3a7fe0;
                background-color: #ffffff;
            }
            QPushButton#actionButton {
                background-color: #3a7fe0;
                color: white;
                padding: 12px;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton#actionButton:hover {
                background-color: #4a8ff0;
            }
            QPushButton#toggleButton {
                background-color: #e0e0e0;
                color: #555555;
                padding: 10px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                margin: 0 5px;
            }
            QPushButton#toggleButton:checked {
                background-color: #3a7fe0;
                color: white;
            }
            QPushButton#toggleButton:hover:!checked {
                background-color: #d0d0d0;
            }
            QPushButton#linkButton {
                background: none;
                border: none;
                color: #1e70c1;
                text-decoration: underline;
                font-size: 13px;
                padding: 5px;
            }
            QPushButton#linkButton:hover {
                color: #2a80d1;
            }
            QCheckBox {
                font-size: 13px;
                color: #555;
            }
            /* Removed photoButton and photoPreview styles */
        """
