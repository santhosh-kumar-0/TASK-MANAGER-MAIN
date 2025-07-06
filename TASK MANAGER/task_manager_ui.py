# Updated task_manager_ui.py with notification features added
import json
import os
import threading
from datetime import datetime, timedelta
import requests # For making API calls
import shutil # For copying files
import subprocess # For opening files on Linux/macOS
import sys # For platform detection
from plyer import notification  # Added for desktop notifications

# PyQt5 imports
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTextEdit, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QDateTimeEdit, QMessageBox,
    QStackedWidget, QComboBox, QFrame, QApplication, QSizePolicy, QFileDialog
)
from PyQt5.QtCore import Qt, QDateTime, QTimer, QSize, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor # Import QColor

# Local module imports
from task_model import Task
from ui_components import CustomMessageBox
from voice_recognition import VoiceRecognitionThread
import config # Import the entire config module

# Imports for email notification (standard Python libraries)
import smtplib
import ssl
from email.mime.text import MIMEText

# Imports for SMS notification (Twilio)
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    print("Twilio library not found. SMS notifications will be disabled.")
    TWILIO_AVAILABLE = False


class MainTaskManagerUI(QWidget):
    # Define directory for task attachments
    ATTACHMENTS_DIR = "attachments"

    def __init__(self, main_app_stacked_widget=None):
        super().__init__()
        self.main_app_stacked_widget = main_app_stacked_widget
        self.current_username = None
        self.tasks = []
        self.user_points = 0
        self.user_streak_data = {"current_streak": 0, "last_completed_date": None}
        self.reminders_sent = {} # {task_name: True} to prevent duplicate reminders
        self.ai_chatbot_window = None # Initialize to None

        self.setWindowTitle("Student Task Manager")
        self.setGeometry(100, 100, 750, 450)#Increased width for new panels

        self.init_ui()
        self.apply_stylesheet()
        self.setup_refresh_timer()
        self.setup_reminder_timer() # Timer for checking reminders

    def set_current_user(self, username):
        self.current_username = username
        self.username_label.setText(f"Welcome, {self.current_username}!") # Update label
        self.setWindowTitle(f"Student Task Manager - {self.current_username}")
        self.load_tasks()
        self.load_gamification_data()
        self.load_profile_photo()
        self.update_gamification_display()
        self.display_tasks()
        self.reminders_sent.clear() # Clear reminders on user change

        # Initialize or update AI Chatbot window with current task manager context
        # Import AIChatbotWindow here to avoid potential circular import issues
        from ai_chatbot_window import AIChatbotWindow
        if self.ai_chatbot_window is None: # Only create if it doesn't exist
            self.ai_chatbot_window = AIChatbotWindow(self) # Pass self for context
            self.ai_chat_button.clicked.connect(self.ai_chatbot_window.show) # Connect button here
        else:
            self.ai_chatbot_window.parent_task_manager = self # Ensure context is passed


    def init_ui(self):
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # --- Left Panel: Task Input ---
        self.input_frame = QFrame()
        self.input_frame.setObjectName("inputContainer")
        input_layout = QVBoxLayout(self.input_frame)
        input_layout.setContentsMargins(20, 20, 20, 20)
        input_layout.setSpacing(10)
        main_layout.addWidget(self.input_frame, 1) # Proportional width

        input_layout.addWidget(self.create_label("Add New Task", "h1"), alignment=Qt.AlignCenter)

        input_layout.addWidget(self.create_label("Task Name:"))
        self.task_name_input = QLineEdit()
        self.task_name_input.setPlaceholderText("e.g., Finish Math Homework")
        input_layout.addWidget(self.task_name_input)

        input_layout.addWidget(self.create_label("Due Date & Time:"))
        self.due_date_input = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600)) # Default to 1 hour from now
        self.due_date_input.setCalendarPopup(True)
        self.due_date_input.setDisplayFormat("yyyy-MM-dd HH:mm")
        input_layout.addWidget(self.due_date_input)

        input_layout.addWidget(self.create_label("Description:"))
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Detailed description of the task (optional)")
        input_layout.addWidget(self.description_input)

        input_layout.addWidget(self.create_label("Next Step:"))
        self.next_step_input = QLineEdit()
        self.next_step_input.setPlaceholderText("e.g., Open textbook to page 50")
        input_layout.addWidget(self.next_step_input)

        input_layout.addWidget(self.create_label("Priority:"))
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["High", "Medium", "Low"])
        self.priority_combo.setCurrentText("Medium")
        input_layout.addWidget(self.priority_combo)

        self.add_task_button = QPushButton("Add Task")
        self.add_task_button.setObjectName("primaryButton")
        self.add_task_button.clicked.connect(self.add_task)
        input_layout.addWidget(self.add_task_button)

        input_layout.addStretch()

        # --- Middle Panel: Task List & Controls ---
        self.task_list_frame = QFrame()
        self.task_list_frame.setObjectName("listContainer")
        task_list_layout = QVBoxLayout(self.task_list_frame)
        task_list_layout.setContentsMargins(20, 20, 20, 20)
        task_list_layout.setSpacing(10)
        main_layout.addWidget(self.task_list_frame, 2) # Proportional width

        # Top section: Profile, User Info, Logout, Chatbot
        top_bar_layout = QHBoxLayout()
        
        # Profile Photo and Name
        profile_info_layout = QHBoxLayout()
        self.profile_photo_label = QLabel()
        self.profile_photo_label.setFixedSize(60, 60)
        self.profile_photo_label.setScaledContents(True)
        self.profile_photo_label.setObjectName("profilePhotoLabel")
        profile_info_layout.addWidget(self.profile_photo_label)

        name_layout = QVBoxLayout()
        self.username_label = QLabel("")
        self.username_label.setObjectName("usernameLabel")
        name_layout.addWidget(self.username_label)
        self.role_label = QLabel("Student") # Assuming student for this UI
        self.role_label.setObjectName("roleLabel")
        name_layout.addWidget(self.role_label)
        profile_info_layout.addLayout(name_layout)
        profile_info_layout.addStretch() # Pushes other elements to the right

        top_bar_layout.addLayout(profile_info_layout)
        top_bar_layout.addStretch() # Pushes buttons to the right

        # Logout and AI Chatbot buttons
        button_group_layout = QHBoxLayout()
        # self.ai_chatbot_window is now initialized in set_current_user
        self.ai_chat_button = QPushButton("AI Chatbot")
        self.ai_chat_button.setObjectName("aiChatButton")
        # The connection for this button is now made in set_current_user
        button_group_layout.addWidget(self.ai_chat_button)

        self.logout_button = QPushButton("Logout")
        self.logout_button.setObjectName("logoutButton")
        self.logout_button.clicked.connect(self.logout)
        button_group_layout.addWidget(self.logout_button)

        top_bar_layout.addLayout(button_group_layout)
        task_list_layout.addLayout(top_bar_layout)


        task_list_layout.addWidget(self.create_label("My Tasks", "h1"), alignment=Qt.AlignCenter)
        self.task_list_widget = QListWidget()
        self.task_list_widget.setObjectName("taskList")
        self.task_list_widget.itemClicked.connect(self.show_task_details)
        task_list_layout.addWidget(self.task_list_widget)

        # Task actions
        action_layout = QHBoxLayout()
        self.mark_complete_button = QPushButton("Mark Complete")
        self.mark_complete_button.setObjectName("successButton")
        self.mark_complete_button.clicked.connect(self.mark_task_complete)
        action_layout.addWidget(self.mark_complete_button)

        self.edit_button = QPushButton("Edit Task")
        self.edit_button.setObjectName("secondaryButton")
        self.edit_button.clicked.connect(self.edit_task)
        action_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete Task")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(self.delete_task)
        action_layout.addWidget(self.delete_button)
        task_list_layout.addLayout(action_layout)
        
        # Gamification Display
        self.gamification_frame = QFrame()
        self.gamification_frame.setObjectName("gamificationFrame")
        self.gamification_layout = QVBoxLayout(self.gamification_frame)
        self.gamification_layout.setContentsMargins(10, 10, 10, 10)
        self.gamification_layout.setSpacing(5)
        
        self.gamification_layout.addWidget(self.create_label("Your Progress", "gamificationTitle"), alignment=Qt.AlignCenter)
        
        points_layout = QHBoxLayout()
        points_layout.addWidget(QLabel("Points:"))
        self.points_label = QLabel("0")
        self.points_label.setObjectName("gamificationStat")
        points_layout.addWidget(self.points_label)
        points_layout.addStretch()
        self.gamification_layout.addLayout(points_layout)

        streak_layout = QHBoxLayout()
        streak_layout.addWidget(QLabel("Current Streak:"))
        self.streak_label = QLabel("0 days")
        self.streak_label.setObjectName("gamificationStat")
        streak_layout.addWidget(self.streak_label)
        streak_layout.addStretch()
        self.gamification_layout.addLayout(streak_layout)

        task_list_layout.addWidget(self.gamification_frame)
        task_list_layout.addStretch() # Pushes everything to the top

        # --- Right Panel: Task Details ---
        self.detail_frame = QFrame()
        self.detail_frame.setObjectName("detailContainer")
        detail_layout = QVBoxLayout(self.detail_frame)
        detail_layout.setContentsMargins(20, 20, 20, 20)
        detail_layout.setSpacing(10)
        main_layout.addWidget(self.detail_frame, 1) # Proportional width

        detail_layout.addWidget(self.create_label("Task Details", "h1"), alignment=Qt.AlignCenter)

        self.detail_task_name = self.create_label("", "detailLabel")
        detail_layout.addWidget(self.detail_task_name)
        self.detail_due_date = self.create_label("", "detailLabel")
        detail_layout.addWidget(self.detail_due_date)
        self.detail_priority = self.create_label("", "detailLabel")
        detail_layout.addWidget(self.detail_priority)
        self.detail_status = self.create_label("", "detailLabel")
        detail_layout.addWidget(self.detail_status)

        detail_layout.addWidget(self.create_label("Description:", "subheading"))
        self.detail_description = QTextEdit()
        self.detail_description.setReadOnly(True)
        self.detail_description.setObjectName("detailTextEdit")
        detail_layout.addWidget(self.detail_description)

        detail_layout.addWidget(self.create_label("Next Step:", "subheading"))
        self.detail_next_step = QLineEdit()
        self.detail_next_step.setReadOnly(True)
        self.detail_next_step.setObjectName("detailLineEdit")
        detail_layout.addWidget(self.detail_next_step)

        # --- File Attachments Section ---
        detail_layout.addWidget(self.create_label("Attachments:", "subheading"))
        self.attached_files_list = QListWidget()
        self.attached_files_list.setObjectName("attachedFilesList")
        self.attached_files_list.itemDoubleClicked.connect(self.open_attached_file)
        detail_layout.addWidget(self.attached_files_list)

        attachment_buttons_layout = QHBoxLayout()
        self.attach_file_button = QPushButton("Attach File")
        self.attach_file_button.setObjectName("secondaryButton")
        self.attach_file_button.clicked.connect(self.attach_file_to_selected_task)
        attachment_buttons_layout.addWidget(self.attach_file_button)

        self.remove_attachment_button = QPushButton("Remove Attachment")
        self.remove_attachment_button.setObjectName("dangerButton")
        self.remove_attachment_button.clicked.connect(self.remove_attached_file)
        attachment_buttons_layout.addWidget(self.remove_attachment_button)
        detail_layout.addLayout(attachment_buttons_layout)
        
        detail_layout.addStretch()

    def create_label(self, text, style_class=""):
        label = QLabel(text)
        if style_class:
            label.setObjectName(style_class)
        return label

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f2f5; /* Light gray background */
                color: #333333;
                font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                font-size: 14px;
            }
            QFrame#inputContainer, QFrame#listContainer, QFrame#detailContainer {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 15px;
            }
            QLabel#h1 {
                font-size: 24px;
                font-weight: bold;
                color: #3a7fe0; /* Primary blue */
                margin-bottom: 15px;
            }
            QLabel#subheading {
                font-size: 16px;
                font-weight: bold;
                color: #555555;
                margin-top: 10px;
                margin-bottom: 5px;
            }
            QLineEdit, QTextEdit, QComboBox, QDateTimeEdit {
                background-color: #f8f8f8;
                border: 1px solid #cccccc;
                border-radius: 8px;
                padding: 10px;
                color: #333333;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateTimeEdit:focus {
                border: 1px solid #3a7fe0;
                background-color: #ffffff;
            }
            QTextEdit {
                min-height: 80px;
            }
            QComboBox::drop-down {
                border: 0px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
            }
            QComboBox::down-arrow {
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                selection-background-color: #3a7fe0;
                color: #333333;
            }

            QListWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 5px;
                outline: 0; /* Remove focus outline */
            }
            QListWidget::item {
                padding: 12px 10px;
                margin-bottom: 7px;
                border-radius: 8px;
                background-color: #f7f9fc; /* Slightly off-white for items */
                color: #333333;
                border: 1px solid #f0f0f0;
            }
            QListWidget::item:hover {
                background-color: #e6f0ff; /* Light blue on hover */
            }
            QListWidget::item:selected {
                background-color: #3a7fe0; /* Primary blue on select */
                color: #ffffff;
                border: 1px solid #3a7fe0;
            }
            /* Completed task styling */
            QListWidget::item[data-completed="true"] {
                color: #777777; /* Grey out completed tasks */
                text-decoration: line-through; /* Strikethrough */
                background-color: #e9ecef; /* Lighter background */
            }
            QListWidget::item[data-completed="true"]:selected {
                background-color: #6c757d; /* Darker grey on select for completed */
                color: #ffffff;
            }
            QListWidget#attachedFilesList {
                min-height: 50px;
                max-height: 150px;
            }
            QListWidget#attachedFilesList::item {
                padding: 5px 8px;
                margin-bottom: 3px;
                font-size: 12px;
                background-color: #f0f8ff; /* Lighter background for attachments */
                border: 1px solid #cceeff;
            }
            QListWidget#attachedFilesList::item:selected {
                background-color: #a0d9ff;
                color: #333333;
            }

            QPushButton {
                border: none;
                border-radius: 8px;
                padding: 12px 18px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton#primaryButton {
                background-color: #3a7fe0;
                color: #ffffff;
            }
            QPushButton#primaryButton:hover {
                background-color: #4a8ff0;
            }
            QPushButton#primaryButton:pressed {
                background-color: #2b6ecd;
            }
            QPushButton#successButton {
                background-color: #28a745; /* Green */
                color: #ffffff;
            }
            QPushButton#successButton:hover {
                background-color: #218838;
            }
            QPushButton#secondaryButton {
                background-color: #6c757d; /* Grey */
                color: #ffffff;
            }
            QPushButton#secondaryButton:hover {
                background-color: #5a6268;
            }
            QPushButton#dangerButton {
                background-color: #dc3545; /* Red */
                color: #ffffff;
            }
            QPushButton#dangerButton:hover {
                background-color: #c82333;
            }
            
            QLabel#profilePhotoLabel {
                border: 3px solid #3a7fe0;
                border-radius: 30px; /* Makes it circular */
                background-color: #e9ecef;
                padding: 2px;
            }
            QLabel#usernameLabel {
                font-size: 18px;
                font-weight: bold;
                color: #3a7fe0;
            }
            QLabel#roleLabel {
                font-size: 12px;
                color: #6c757d;
            }
            QPushButton#logoutButton {
                background-color: #f44336; /* Red color */
                padding: 8px 12px;
                font-size: 13px;
                border-radius: 5px;
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton#logoutButton:hover {
                background-color: #d32f2f;
            }
            QPushButton#aiChatButton {
                background-color: #6f42c1; /* Violet */
                padding: 8px 12px;
                font-size: 13px;
                border-radius: 5px;
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton#aiChatButton:hover {
                background-color: #5b36a1;
            }
            QLabel#detailLabel {
                font-size: 15px;
                font-weight: bold;
                color: #3a7fe0;
                margin-top: 5px;
                margin-bottom: 5px;
            }
            QTextEdit#detailTextEdit, QLineEdit#detailLineEdit {
                background-color: #f0f2f5;
                border: 1px solid #d0d2d5;
                border-radius: 8px;
                padding: 10px;
            }
            /* Gamification styles */
            QFrame#gamificationFrame {
                background-color: #e6f7ff; /* Light blue background */
                border: 1px solid #a0d9ff;
                padding: 10px;
                border-radius: 8px;
                margin-top: 15px;
            }
            QLabel#gamificationTitle {
                font-size: 18px;
                font-weight: bold;
                color: #0056b3;
                margin-bottom: 8px;
            }
            QLabel#gamificationStat {
                font-size: 15px;
                font-weight: bold;
                color: #007bff;
            }
        """)

    def show_message_box(self, title, message, icon=QMessageBox.Information, buttons=QMessageBox.Ok):
        msg = CustomMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(icon)
        msg.setStandardButtons(buttons)
        return msg.exec_()

    def load_profile_photo(self):
        # First, try to load the user's specific profile photo
        user_photo_filename = f"{self.current_username}.png" # Assuming .png for simplicity
        user_photo_path = os.path.join(config.PROFILE_PHOTOS_DIR, user_photo_filename) # Use config.PROFILE_PHOTOS_DIR
        
        pixmap = QPixmap(user_photo_path)

        # If user-specific photo not found or invalid, try default_profile.png
        if pixmap.isNull():
            print(f"Warning: Could not load user photo from {user_photo_path}. Trying default.")
            default_photo_path = os.path.join(config.PROFILE_PHOTOS_DIR, config.DEFAULT_PROFILE_PHOTO) # Use config.PROFILE_PHOTOS_DIR and config.DEFAULT_PROFILE_PHOTO
            pixmap = QPixmap(default_photo_path)
            
            # If default photo is also missing/invalid, display "No Photo" text
            if pixmap.isNull():
                print(f"Warning: Could not load default profile photo from {default_photo_path}. Displaying 'No Photo'.")
                self.profile_photo_label.setText("No Photo")
                self.profile_photo_label.setAlignment(Qt.AlignCenter)
                self.profile_photo_label.setStyleSheet("QLabel#profilePhotoLabel { background-color: #e9ecef; color: #6c757d; font-size: 10px; }")
                return # Exit early as no image can be loaded

        self.profile_photo_label.setPixmap(pixmap.scaled(
            self.profile_photo_label.size(), 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        ))
        self.username_label.setText(self.current_username)


    def setup_refresh_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(60 * 1000) # Every 1 minute
        self.refresh_timer.timeout.connect(self.display_tasks)
        self.refresh_timer.start()

    def setup_reminder_timer(self):
        self.reminder_timer = QTimer(self)
        self.reminder_timer.setInterval(30 * 1000) # Check every 30 seconds
        self.reminder_timer.timeout.connect(self.check_for_reminders)
        self.reminder_timer.start()

    def load_tasks(self):
        filename = f"{self.current_username}_tasks.json"
        self.tasks = []
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    tasks_data = json.load(f)
                    for task_dict in tasks_data:
                        self.tasks.append(Task.from_dict(task_dict))
            except json.JSONDecodeError:
                self.show_message_box("Error", "Could not load tasks. File might be corrupted.", QMessageBox.Critical)
                self.tasks = []
        self.display_tasks()

    def save_tasks(self):
        filename = f"{self.current_username}_tasks.json"
        with open(filename, "w") as f:
            json.dump([task.to_dict() for task in self.tasks], f, indent=4)
    
    def load_gamification_data(self):
        filename = f"{self.current_username}_gamification.json"
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    data = json.load(f)
                    self.user_points = data.get("points", 0)
                    self.user_streak_data = data.get("streak", {"current_streak": 0, "last_completed_date": None})
            except json.JSONDecodeError:
                print("Error loading gamification data. Resetting.")
                self.user_points = 0
                self.user_streak_data = {"current_streak": 0, "last_completed_date": None}
        self.update_gamification_display()

    def save_gamification_data(self):
        filename = f"{self.current_username}_gamification.json"
        data = {
            "points": self.user_points,
            "streak": self.user_streak_data
        }
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        self.update_gamification_display()

    def update_gamification_display(self):
        self.points_label.setText(str(self.user_points))
        self.streak_label.setText(f"{self.user_streak_data['current_streak']} days")

    def add_task(self):
        task_name = self.task_name_input.text().strip()
        due_date_str = self.due_date_input.dateTime().toString("yyyy-MM-dd HH:mm")
        description = self.description_input.toPlainText().strip()
        next_step = self.next_step_input.text().strip()
        priority = self.priority_combo.currentText()

        if not task_name:
            self.show_message_box("Input Error", "Task name cannot be empty.", QMessageBox.Warning)
            return

        new_task = Task(task_name, due_date_str, description, next_step, priority)
        self.tasks.append(new_task)
        self.save_tasks()
        self.display_tasks()
        self.clear_task_inputs()
        self.show_message_box("Success", f"Task '{task_name}' added!", QMessageBox.Information)


    def display_tasks(self):
        self.task_list_widget.clear()
        
        # Sort tasks: incomplete high priority first, then by due date, then other incomplete, then completed
        now = datetime.now()
        
        def sort_key(task):
            try:
                due_dt = datetime.strptime(task.due_date, "%Y-%m-%d %H:%M")
            except ValueError:
                # Handle invalid date format by pushing it to the end
                return (2, 0, task.name) 

            is_overdue = not task.completed and due_dt < now
            
            priority_map = {"High": 0, "Medium": 1, "Low": 2}
            priority_value = priority_map.get(task.priority, 1) # Default to Medium

            if task.completed:
                return (3, 0, task.name) # Completed tasks go last
            elif is_overdue:
                return (0, due_dt, task.name) # Overdue tasks first, sorted by oldest first
            else:
                return (1, priority_value, due_dt, task.name) # Incomplete, then priority, then due date
        
        self.tasks.sort(key=sort_key)

        if not self.tasks:
            self.task_list_widget.addItem("No tasks to display. Add a new task!")
            self.clear_task_details()
            return

        for task in self.tasks:
            status = "✓" if task.completed else " "
            
            try:
                due_dt = datetime.strptime(task.due_date, "%Y-%m-%d %H:%M")
                time_diff = due_dt - now
                if not task.completed and time_diff < timedelta(0):
                    time_status = "OVERDUE!"
                    item_text = f"[{status}] {task.name} | Due: {task.due_date} ({time_status}) | Priority: {task.priority}"
                elif not task.completed and time_diff < timedelta(hours=24):
                    hours, remainder = divmod(time_diff.total_seconds(), 3600)
                    minutes, _ = divmod(remainder, 60)
                    time_status = f"{int(hours)}h {int(minutes)}m left"
                    item_text = f"[{status}] {task.name} | Due: {task.due_date} ({time_status}) | Priority: {task.priority}"
                else:
                    item_text = f"[{status}] {task.name} | Due: {task.due_date} | Priority: {task.priority}"
            except ValueError:
                item_text = f"[{status}] {task.name} | Due: Invalid Date | Priority: {task.priority}"
            
            item = QListWidgetItem(item_text)
            
            # Use QListWidgetItem's setData for custom properties for styling
            item.setData(Qt.UserRole, task.name) # Store original task name for easy lookup
            item.setData(Qt.UserRole + 1, task.completed) # Store completion status
            if task.completed:
                item.setData(Qt.DecorationRole, QIcon("icons/check_mark.png")) # Optional: Add a checkmark icon
                item.setData(Qt.UserRole + 2, "true") # For QSS styling
            else:
                item.setData(Qt.UserRole + 2, "false") # For QSS styling

            # Apply colors based on priority and status
            if not task.completed:
                if task.priority == "High":
                    item.setForeground(Qt.red)
                elif task.priority == "Medium":
                    item.setForeground(QColor("darkorange")) # Corrected: Use QColor for darkorange
                # No specific color for Low, uses default text color
            
            self.task_list_widget.addItem(item)
            
            # If a task was selected, re-select it after refresh if it still exists
            selected_items = self.task_list_widget.selectedItems()
            if selected_items:
                selected_task_name = selected_items[0].data(Qt.UserRole)
                for i in range(self.task_list_widget.count()):
                    item_to_check = self.task_list_widget.item(i)
                    if item_to_check.data(Qt.UserRole) == selected_task_name:
                        self.task_list_widget.setItemSelected(item_to_check, True)
                        self.show_task_details(item_to_check)
                        break

    def clear_task_inputs(self):
        self.task_name_input.clear()
        self.description_input.clear()
        self.next_step_input.clear()
        self.due_date_input.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.priority_combo.setCurrentText("Medium")
        self.clear_task_details()

    def clear_task_details(self):
        self.detail_task_name.setText("Select a task to view details.")
        self.detail_due_date.setText("")
        self.detail_priority.setText("")
        self.detail_status.setText("")
        self.detail_description.clear()
        self.detail_next_step.clear()
        self.attached_files_list.clear() # Clear attachments display
        self.attached_files_list.addItem("No files attached.") # Default message
        # Ensure attachment buttons are visible (they are part of the detail layout)
        self.attach_file_button.setVisible(True)
        self.remove_attachment_button.setVisible(True)


    def show_task_details(self, item):
        task_name_to_find = item.data(Qt.UserRole)
        selected_task = next((t for t in self.tasks if t.name == task_name_to_find), None)

        if selected_task:
            self.detail_task_name.setText(f"Task: {selected_task.name}")
            self.detail_due_date.setText(f"Due: {selected_task.due_date}")
            self.detail_priority.setText(f"Priority: {selected_task.priority}")
            status = "Completed" if selected_task.completed else "Pending"
            self.detail_status.setText(f"Status: {status}")
            self.detail_description.setText(selected_task.description)
            self.detail_next_step.setText(selected_task.next_step)

            # Display attachments
            self.attached_files_list.clear()
            if selected_task.attachments:
                for attachment_path in selected_task.attachments:
                    file_name = os.path.basename(attachment_path)
                    attachment_item = QListWidgetItem(file_name)
                    attachment_item.setData(Qt.UserRole, attachment_path) # Store full path
                    self.attached_files_list.addItem(attachment_item)
            else:
                self.attached_files_list.addItem("No files attached.")
        else:
            self.clear_task_details()

    def mark_task_complete(self):
        selected_item = self.task_list_widget.currentItem()
        if not selected_item:
            self.show_message_box("Selection Error", "Please select a task to mark as complete.", QMessageBox.Warning)
            return

        task_name_to_find = selected_item.data(Qt.UserRole)
        task_found = False
        for task in self.tasks:
            if task.name == task_name_to_find:
                if task.completed:
                    self.show_message_box("Info", f"Task '{task.name}' is already marked complete.", QMessageBox.Information)
                    return
                task.completed = True
                self.gain_points(10) # Points for completion
                self.update_streak() # Update streak for completion
                
                # Show desktop notification
                notification.notify(
                    title=f"Task Completed: {task.name}",
                    message="Great job! You've completed this task.",
                    timeout=10
                )
                
                # Send SMS if phone number exists
                user_info = self.get_user_contact_info(self.current_username)
                phone_number = user_info.get("phone_number", "")
                if phone_number and TWILIO_AVAILABLE:
                    self.send_reminder(task, "Task Completed", "sms")
                
                self.show_message_box("Task Completed!", f"Congratulations! Task '{task.name}' marked complete. You gained 10 points!", QMessageBox.Information)
                task_found = True
                break
        
        if task_found:
            self.save_tasks()
            self.save_gamification_data()
            self.display_tasks() # Refresh display to show completed status

    def gain_points(self, amount):
        self.user_points += amount
        self.update_gamification_display()

    def update_streak(self):
        today = datetime.now().date()
        last_date_str = self.user_streak_data["last_completed_date"]
        
        if last_date_str:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
            if today == last_date:
                # Task completed on the same day, streak remains
                pass 
            elif today == last_date + timedelta(days=1):
                # Consecutive day, increase streak
                self.user_streak_data["current_streak"] += 1
            else:
                # Gap, reset streak
                self.user_streak_data["current_streak"] = 1
        else:
            # First task completed, start streak
            self.user_streak_data["current_streak"] = 1
        
        self.user_streak_data["last_completed_date"] = today.strftime("%Y-%m-%d")
        self.update_gamification_display()


    def edit_task(self):
        selected_item = self.task_list_widget.currentItem()
        if not selected_item:
            self.show_message_box("Selection Error", "Please select a task to edit.", QMessageBox.Warning)
            return

        task_name_to_edit = selected_item.data(Qt.UserRole)
        selected_task = next((t for t in self.tasks if t.name == task_name_to_edit), None)

        if selected_task:
            # Populate inputs with selected task's data
            self.task_name_input.setText(selected_task.name)
            self.due_date_input.setDateTime(QDateTime.fromString(selected_task.due_date, "yyyy-MM-dd HH:mm"))
            self.description_input.setText(selected_task.description)
            self.next_step_input.setText(selected_task.next_step)
            self.priority_combo.setCurrentText(selected_task.priority)

            # Change add button to save/update button
            self.add_task_button.setText("Update Task")
            self.add_task_button.clicked.disconnect()
            self.add_task_button.clicked.connect(lambda: self.update_task(selected_task))
        else:
            self.show_message_box("Error", "Selected task not found.", QMessageBox.Critical)

    def update_task(self, original_task):
        new_task_name = self.task_name_input.text().strip()
        new_due_date_str = self.due_date_input.dateTime().toString("yyyy-MM-dd HH:mm")
        new_description = self.description_input.toPlainText().strip()
        new_next_step = self.next_step_input.text().strip()
        new_priority = self.priority_combo.currentText()

        if not new_task_name:
            self.show_message_box("Input Error", "Task name cannot be empty.", QMessageBox.Warning)
            return
        
        # Check if the new name is a duplicate, unless it's the original task itself
        if new_task_name != original_task.name and any(t.name == new_task_name for t in self.tasks):
            self.show_message_box("Input Error", "Task with this name already exists.", QMessageBox.Warning)
            return

        original_task.name = new_task_name
        original_task.due_date = new_due_date_str
        original_task.description = new_description
        original_task.next_step = new_next_step
        original_task.priority = new_priority
        
        self.save_tasks()
        self.display_tasks()
        self.clear_task_inputs()
        self.show_message_box("Success", f"Task '{new_task_name}' updated!", QMessageBox.Information)

        # Revert button back to "Add Task"
        self.add_task_button.setText("Add Task")
        self.add_task_button.clicked.disconnect()
        self.add_task_button.clicked.connect(self.add_task)


    def delete_task(self):
        selected_item = self.task_list_widget.currentItem()
        if not selected_item:
            self.show_message_box("Selection Error", "Please select a task to delete.", QMessageBox.Warning)
            return

        task_name_to_delete = selected_item.data(Qt.UserRole)
        
        reply = CustomMessageBox(self).question(
            self, "Confirm Delete",
            f"Are you sure you want to delete the task '{task_name_to_delete}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # Find the task object to get its attachments
            task_to_delete = next((t for t in self.tasks if t.name == task_name_to_delete), None)
            if task_to_delete:
                self.delete_task_attachments(task_to_delete) # Delete associated files

            self.tasks = [task for task in self.tasks if task.name != task_name_to_delete]
            self.save_tasks()
            self.display_tasks()
            self.clear_task_details()
            self.show_message_box("Success", f"Task '{task_name_to_delete}' deleted.", QMessageBox.Information)

    def delete_task_attachments(self, task):
        """Deletes the directory and all files associated with a task."""
        task_attachments_dir = os.path.join(self.ATTACHMENTS_DIR, self.current_username, task.name.replace(" ", "_"))
        if os.path.exists(task_attachments_dir):
            try:
                shutil.rmtree(task_attachments_dir)
                print(f"Deleted attachment directory for task: {task.name}")
            except Exception as e:
                print(f"Error deleting attachment directory for task '{task.name}': {e}")


    def attach_file_to_selected_task(self):
        selected_item = self.task_list_widget.currentItem()
        if not selected_item:
            self.show_message_box("Selection Error", "Please select a task to attach a file to.", QMessageBox.Warning)
            return

        task_name_to_find = selected_item.data(Qt.UserRole)
        selected_task = next((t for t in self.tasks if t.name == task_name_to_find), None)

        if not selected_task:
            self.show_message_box("Error", "Selected task not found.", QMessageBox.Critical)
            return

        options = QFileDialog.Options()
        # Filter for common image and PDF types
        file_filter = "Image Files (*.png *.jpg *.jpeg *.gif);;PDF Files (*.pdf);;All Files (*)"
        file_names, _ = QFileDialog.getOpenFileNames(
            self, "Select File(s) to Attach", "",
            file_filter, options=options
        )

        if file_names:
            # Create a task-specific directory for attachments
            # Replace spaces in task name for directory safety
            task_safe_name = selected_task.name.replace(" ", "_").replace("/", "_").replace("\\", "_")
            attachments_task_dir = os.path.join(self.ATTACHMENTS_DIR, self.current_username, task_safe_name)
            os.makedirs(attachments_task_dir, exist_ok=True)
            
            for file_path in file_names:
                file_name = os.path.basename(file_path)
                destination_path = os.path.join(attachments_task_dir, file_name)
                
                # Check if file with same name already exists in attachments
                if os.path.exists(destination_path):
                    reply = CustomMessageBox(self).question(
                        self, "File Exists",
                        f"A file named '{file_name}' already exists for this task. Overwrite?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        continue # Skip this file

                try:
                    shutil.copy(file_path, destination_path)
                    # Store relative path to the attachment for portability
                    relative_path_to_store = os.path.relpath(destination_path, os.getcwd())
                    
                    if relative_path_to_store not in selected_task.attachments:
                        selected_task.attachments.append(relative_path_to_store)
                    
                    self.show_message_box("Success", f"File '{file_name}' attached!", QMessageBox.Information)
                except Exception as e:
                    self.show_message_box("Error", f"Failed to attach file '{file_name}': {e}", QMessageBox.Critical)
            
            self.save_tasks()
            self.show_task_details(selected_item) # Refresh details to show new attachment

    def open_attached_file(self, item):
        file_path = item.data(Qt.UserRole) # Retrieve the full path stored in UserRole
        
        if not file_path or not os.path.exists(file_path):
            self.show_message_box("Error", "File not found or path is invalid.", QMessageBox.Warning)
            return
        
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin": # macOS
                subprocess.call(['open', file_path])
            else: # linux
                subprocess.call(['xdg-open', file_path])
        except Exception as e:
            self.show_message_box("Error", f"Could not open file: {e}\nEnsure you have an application to open this file type.", QMessageBox.Critical)

    def remove_attached_file(self):
        selected_attachment_item = self.attached_files_list.currentItem()
        if not selected_attachment_item:
            self.show_message_box("Selection Error", "Please select an attachment to remove.", QMessageBox.Warning)
            return

        selected_task_item = self.task_list_widget.currentItem()
        if not selected_task_item:
            self.show_message_box("Error", "No task selected in the main list.", QMessageBox.Warning)
            return
        
        task_name_of_attachment = selected_task_item.data(Qt.UserRole)
        current_task = next((t for t in self.tasks if t.name == task_name_of_attachment), None)

        if not current_task:
            self.show_message_box("Error", "Associated task not found.", QMessageBox.Critical)
            return

        file_path_to_remove = selected_attachment_item.data(Qt.UserRole)
        file_name = os.path.basename(file_path_to_remove)

        reply = CustomMessageBox(self).question(
            self, "Confirm Removal",
            f"Are you sure you want to remove '{file_name}' from this task?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(file_path_to_remove):
                    os.remove(file_path_to_remove)
                    print(f"Deleted file from disk: {file_path_to_remove}")
                
                if file_path_to_remove in current_task.attachments:
                    current_task.attachments.remove(file_path_to_remove)
                
                self.save_tasks()
                self.show_task_details(selected_task_item) # Refresh display
                self.show_message_box("Success", f"Attachment '{file_name}' removed.", QMessageBox.Information)
            except Exception as e:
                self.show_message_box("Error", f"Failed to remove attachment: {e}", QMessageBox.Critical)


    def check_for_reminders(self):
        now = datetime.now()
        for task in self.tasks:
            if not task.completed: # Only check for incomplete tasks
                try:
                    due_dt = datetime.strptime(task.due_date, "%Y-%m-%d %H:%M")
                    time_until_due = due_dt - now

                    # Get user phone number for SMS
                    user_info = self.get_user_contact_info(self.current_username)
                    phone_number = user_info.get("phone_number", "")

                    # Reminder 1: 1 hour before due
                    if timedelta(0) < time_until_due <= timedelta(hours=1) and not self.reminders_sent.get(task.name + "_1hr"):
                        # Desktop notification
                        notification.notify(
                            title=f"1 Hour Reminder: {task.name}",
                            message=f"Task due at {task.due_date}. Priority: {task.priority}",
                            timeout=10
                        )
                        
                        # SMS if phone number exists
                        if phone_number and TWILIO_AVAILABLE:
                            self.send_reminder(task, "1 Hour Reminder", "sms")
                        
                        self.reminders_sent[task.name + "_1hr"] = True
                        print(f"Sent 1-hour reminder for task: {task.name}")

                    # Reminder 2: 10 minutes before due (new)
                    elif timedelta(0) < time_until_due <= timedelta(minutes=10) and not self.reminders_sent.get(task.name + "_10min"):
                        # Desktop notification
                        notification.notify(
                            title=f"10 Minute Reminder: {task.name}",
                            message=f"Task due soon at {task.due_date}",
                            timeout=10
                        )
                        
                        # SMS if phone number exists
                        if phone_number and TWILIO_AVAILABLE:
                            self.send_reminder(task, "10 Minute Reminder", "sms")
                        
                        self.reminders_sent[task.name + "_10min"] = True
                        print(f"Sent 10-minute reminder for task: {task.name}")

                    # Overdue reminder
                    elif time_until_due < timedelta(0) and not self.reminders_sent.get(task.name + "_overdue"):
                        # Desktop notification
                        notification.notify(
                            title=f"Task Overdue: {task.name}",
                            message=f"This task is overdue! Please complete it ASAP",
                            timeout=10
                        )
                        
                        # SMS if phone number exists
                        if phone_number and TWILIO_AVAILABLE:
                            self.send_reminder(task, "Task Overdue!", "sms")
                        
                        self.reminders_sent[task.name + "_overdue"] = True
                        print(f"Sent overdue reminder for task: {task.name}")

                except ValueError:
                    print(f"Invalid date format for task '{task.name}': {task.due_date}")

    def get_user_contact_info(self, username):
        """Retrieves email and phone number for the given username from users.json."""
        try:
            with open(config.USERS_FILE, "r") as f: # Use config.USERS_FILE
                users_data = json.load(f)
                return users_data.get(username, {})
        except FileNotFoundError:
            print(f"Error: {config.USERS_FILE} not found.") # Use config.USERS_FILE
            return {}
        except json.JSONDecodeError:
            print(f"Error: Could not decode {config.USERS_FILE}. File might be corrupted.") # Use config.USERS_FILE
            return {}
        except Exception as e:
            print(f"Error: An unexpected error occurred while loading user contact info: {e}")
            return {}

    def send_reminder(self, task, reminder_type, method):
        user_info = self.get_user_contact_info(self.current_username)
        recipient_email = user_info.get("email")
        recipient_phone = user_info.get("phone_number") # Get phone number from user info

        if method == "email" and config.SENDER_EMAIL != "your_email@gmail.com" and recipient_email: # Use config.SENDER_EMAIL
            subject = f"Task Reminder: {reminder_type} - {task.name}"
            body = (f"Hi {self.current_username},\n\n"
                    f"Just a friendly reminder about your task:\n\n"
                    f"Task: {task.name}\n"
                    f"Due Date: {task.due_date}\n"
                    f"Description: {task.description}\n"
                    f"Next Step: {task.next_step}\n"
                    f"Priority: {task.priority}\n\n"
                    f"Don't forget to complete it!\n\n"
                    f"Best,\nYour Task Manager")
            threading.Thread(target=self._send_email, args=(recipient_email, subject, body)).start()
        
        elif method == "sms" and TWILIO_AVAILABLE and config.TWILIO_ACCOUNT_SID != "YOUR_TWILIO_ACCOUNT_SID" and recipient_phone: # Use config.TWILIO_ACCOUNT_SID and check recipient_phone
            # Check if the 'To' and 'From' numbers are the same
            if recipient_phone == config.TWILIO_PHONE_NUMBER:
                print(f"Skipping SMS: 'To' and 'From' numbers cannot be the same ({recipient_phone}).")
                return

            message_body = (f"Task Reminder ({reminder_type}): {task.name} "
                            f"is due {task.due_date}. Priority: {task.priority}. "
                            f"Next: {task.next_step[:50]}...") # Truncate for SMS
            threading.Thread(target=self._send_sms, args=(recipient_phone, message_body)).start()


    def _send_email(self, recipient_email, subject, body):
        if not config.SENDER_EMAIL or config.SENDER_EMAIL == "your_email@gmail.com" or not config.SENDER_EMAIL_PASSWORD or config.SENDER_EMAIL_PASSWORD == "your_app_password": # Use config.SENDER_EMAIL and config.SENDER_EMAIL_PASSWORD
            print("Email sender not configured. Skipping email.")
            return

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = config.SENDER_EMAIL # Use config.SENDER_EMAIL
        msg["To"] = recipient_email

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(config.SENDER_EMAIL, config.SENDER_EMAIL_PASSWORD) # Use config.SENDER_EMAIL and config.SENDER_EMAIL_PASSWORD
                server.sendmail(config.SENDER_EMAIL, recipient_email, msg.as_string()) # Use config.SENDER_EMAIL
            print(f"Email reminder sent to {recipient_email} for task.")
        except Exception as e:
            print(f"Failed to send email to {recipient_email}: {e}")

    def _send_sms(self, recipient_phone_number, message_body):
        if not TWILIO_AVAILABLE or not config.TWILIO_ACCOUNT_SID or config.TWILIO_ACCOUNT_SID == "YOUR_TWILIO_ACCOUNT_SID" \
           or not config.TWILIO_AUTH_TOKEN or config.TWILIO_AUTH_TOKEN == "YOUR_TWILIO_AUTH_TOKEN" \
           or not config.TWILIO_PHONE_NUMBER or config.TWILIO_PHONE_NUMBER == "YOUR_TWILIO_PHONE_NUMBER": # Use config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN, config.TWILIO_PHONE_NUMBER
            print("Twilio SMS not configured. Skipping SMS.")
            return

        try:
            client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN) # Use config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN
            message = client.messages.create(
                to=recipient_phone_number,
                from_=config.TWILIO_PHONE_NUMBER, # Use config.TWILIO_PHONE_NUMBER
                body=message_body
            )
            print(f"SMS reminder sent to {recipient_phone_number} for task. SID: {message.sid}")
        except Exception as e:
            print(f"Failed to send SMS to {recipient_phone_number}: {e}")
            # Optionally show a message box, but keep it quiet for background operations


    def logout(self):
        reply = CustomMessageBox(self).question(
            self, "Logout",
            "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if hasattr(self, 'main_app_stacked_widget') and self.main_app_stacked_widget:
                self.main_app_stacked_widget.setCurrentWidget(self.main_app_stacked_widget.auth_window)
                self.close()
            else:
                self.close()