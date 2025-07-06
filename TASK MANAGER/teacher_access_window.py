import json
import os
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QFrame, QApplication, QMessageBox,
    QLineEdit, QTextEdit, QComboBox, QDateTimeEdit, QPushButton, QSizePolicy,
    QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QFont, QColor

from task_model import Task
from ui_components import CustomMessageBox
from config import USERS_FILE

class TeacherAccessWindow(QWidget):
    def __init__(self, teacher_username):
        super().__init__()
        self.teacher_username = teacher_username
        self.setWindowTitle("Teacher Access - Task Assignment")
        self.setGeometry(150, 150, 650, 380)
        self.current_edited_task = None # Stores the Task object being edited
        self.current_edited_student = None # Stores the student username for the task being edited

        self.init_ui()
        self.apply_stylesheet()
        self.setup_refresh_timer()
        
        self.populate_student_dropdowns() # Populates both student dropdowns
        self.load_and_display_upcoming_tasks() # Initial load of tasks

    def init_ui(self):
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # --- Left Panel: Assign Task ---
        self.assign_task_container = QFrame()
        self.assign_task_container.setObjectName("containerFrame")
        assign_layout = QVBoxLayout(self.assign_task_container)
        assign_layout.setContentsMargins(20, 20, 20, 20)
        assign_layout.setSpacing(10)
        main_layout.addWidget(self.assign_task_container, 1)

        assign_layout.addWidget(self.create_label("Assign New Task to Student", "h1"), alignment=Qt.AlignCenter)

        assign_layout.addWidget(self.create_label("Select Student:"))
        self.assign_student_dropdown = QComboBox() # Renamed to differentiate
        assign_layout.addWidget(self.assign_student_dropdown)

        assign_layout.addWidget(self.create_label("Task Name:"))
        self.task_name_input = QLineEdit()
        self.task_name_input.setPlaceholderText("Enter task name")
        assign_layout.addWidget(self.task_name_input)

        assign_layout.addWidget(self.create_label("Due Date & Time:"))
        self.due_date_input = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.due_date_input.setCalendarPopup(True)
        self.due_date_input.setDisplayFormat("yyyy-MM-dd HH:mm")
        assign_layout.addWidget(self.due_date_input)

        assign_layout.addWidget(self.create_label("Description:"))
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter task description (optional)")
        assign_layout.addWidget(self.description_input)

        assign_layout.addWidget(self.create_label("Next Step:"))
        self.next_step_input = QLineEdit()
        self.next_step_input.setPlaceholderText("e.g., Email professor, Start research, etc.")
        assign_layout.addWidget(self.next_step_input)

        assign_layout.addWidget(self.create_label("Priority:"))
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["High", "Medium", "Low"])
        self.priority_combo.setCurrentText("Medium")
        assign_layout.addWidget(self.priority_combo)

        self.assign_button = QPushButton("Assign Task")
        self.assign_button.setObjectName("primaryButton")
        self.assign_button.clicked.connect(self.assign_task)
        assign_layout.addWidget(self.assign_button)
        
        # New: Cancel Edit button
        self.cancel_edit_button = QPushButton("Cancel Edit")
        self.cancel_edit_button.setObjectName("secondaryButton")
        self.cancel_edit_button.setVisible(False) # Hidden by default
        self.cancel_edit_button.clicked.connect(self.cancel_edit_mode)
        assign_layout.addWidget(self.cancel_edit_button)

        assign_layout.addStretch()

        # --- Right Panel: Task View and Management ---
        self.upcoming_tasks_container = QFrame()
        self.upcoming_tasks_container.setObjectName("containerFrame")
        upcoming_layout = QVBoxLayout(self.upcoming_tasks_container)
        upcoming_layout.setContentsMargins(20, 20, 20, 20)
        upcoming_layout.setSpacing(10)
        main_layout.addWidget(self.upcoming_tasks_container, 2)

        # Top Bar: Title and Logout
        top_bar_layout = QHBoxLayout()
        top_bar_layout.addWidget(self.create_label("Student Tasks Overview", "h1"), alignment=Qt.AlignCenter)
        top_bar_layout.addStretch()
        self.logout_button = QPushButton("Logout")
        self.logout_button.setObjectName("logoutButton")
        self.logout_button.clicked.connect(self.logout)
        top_bar_layout.addWidget(self.logout_button)
        upcoming_layout.addLayout(top_bar_layout)

        # New: Student Selection for viewing tasks
        view_options_layout = QVBoxLayout()
        view_options_layout.addWidget(self.create_label("View Tasks For:"))
        student_select_layout = QHBoxLayout()
        self.view_student_tasks_dropdown = QComboBox()
        self.view_student_tasks_dropdown.addItem("All Students") # Option to view tasks for all students
        self.view_student_tasks_dropdown.currentIndexChanged.connect(self.load_and_display_upcoming_tasks)
        student_select_layout.addWidget(self.view_student_tasks_dropdown)

        self.refresh_students_button = QPushButton("Refresh Student List")
        self.refresh_students_button.setObjectName("secondaryButton")
        self.refresh_students_button.clicked.connect(self.populate_student_dropdowns)
        student_select_layout.addWidget(self.refresh_students_button)
        view_options_layout.addLayout(student_select_layout)

        # New: Task Filter
        view_options_layout.addWidget(self.create_label("Filter Tasks By:"))
        self.task_filter_dropdown = QComboBox()
        self.task_filter_dropdown.addItems(["Upcoming/Overdue", "All Tasks", "Completed Tasks", "Incomplete Tasks"])
        self.task_filter_dropdown.currentIndexChanged.connect(self.load_and_display_upcoming_tasks)
        view_options_layout.addWidget(self.task_filter_dropdown)
        upcoming_layout.addLayout(view_options_layout)

        self.task_list_widget = QListWidget()
        self.task_list_widget.setObjectName("taskList")
        self.task_list_widget.itemSelectionChanged.connect(self.on_task_selection_changed)
        upcoming_layout.addWidget(self.task_list_widget)

        self.status_label = QLabel("Loading tasks...")
        self.status_label.setObjectName("statusLabel")
        upcoming_layout.addWidget(self.status_label, alignment=Qt.AlignCenter)

        # New: Task Action Buttons
        task_actions_layout = QHBoxLayout()
        self.mark_complete_button = QPushButton("Mark Complete")
        self.mark_complete_button.setObjectName("secondaryButton")
        self.mark_complete_button.clicked.connect(self.mark_task_completed)
        self.mark_complete_button.setEnabled(False) # Disabled until a task is selected
        task_actions_layout.addWidget(self.mark_complete_button)

        self.edit_task_button = QPushButton("Edit Task")
        self.edit_task_button.setObjectName("secondaryButton")
        self.edit_task_button.clicked.connect(self.edit_selected_task)
        self.edit_task_button.setEnabled(False) # Disabled until a task is selected
        task_actions_layout.addWidget(self.edit_task_button)

        self.delete_task_button = QPushButton("Delete Task")
        self.delete_task_button.setObjectName("logoutButton") # Using logoutButton style for delete
        self.delete_task_button.clicked.connect(self.delete_selected_task)
        self.delete_task_button.setEnabled(False) # Disabled until a task is selected
        task_actions_layout.addWidget(self.delete_task_button)
        
        upcoming_layout.addLayout(task_actions_layout)

        upcoming_layout.addStretch()

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
            QFrame#containerFrame {
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
            QPushButton#secondaryButton {
                background-color: #6c757d; /* Grey */
                color: #ffffff;
            }
            QPushButton#secondaryButton:hover {
                background-color: #5a6268;
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
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 5px;
                outline: 0; /* Remove focus outline */
            }
            QListWidget::item {
                padding: 10px;
                margin-bottom: 5px;
                border-radius: 5px;
                background-color: #f7f9fc;
                color: #333333;
                border: 1px solid #f0f0f0;
            }
            QListWidget::item:hover {
                background-color: #e6f0ff;
            }
            QLabel#statusLabel {
                font-style: italic;
                color: #6c757d;
                margin-top: 10px;
            }
        """)

    def show_message_box(self, title, message, icon=QMessageBox.Information, buttons=QMessageBox.Ok):
        msg = CustomMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(icon)
        msg.setStandardButtons(buttons)
        return msg.exec_()

    def setup_refresh_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(60 * 1000) # Refresh every 1 minute
        self.refresh_timer.timeout.connect(self.load_and_display_upcoming_tasks)
        self.refresh_timer.start()

    def populate_student_dropdowns(self):
        self.assign_student_dropdown.clear()
        self.view_student_tasks_dropdown.clear()
        self.view_student_tasks_dropdown.addItem("All Students") # Add "All Students" option first

        users_data = self._load_all_users_data()
        student_usernames = sorted([user for user, data in users_data.items() if data.get("role") == "student"])

        if student_usernames:
            self.assign_student_dropdown.addItems(student_usernames)
            self.view_student_tasks_dropdown.addItems(student_usernames)
            self.assign_button.setEnabled(True)
        else:
            self.assign_student_dropdown.addItem("No students registered")
            self.assign_button.setEnabled(False)
        
        # Trigger task list refresh after dropdowns are populated
        self.load_and_display_upcoming_tasks()

    def assign_task(self):
        # Determine if we are editing an existing task or assigning a new one
        if self.current_edited_task:
            selected_student = self.current_edited_student
            task_name_old = self.current_edited_task.name
            editing_mode = True
        else:
            selected_student = self.assign_student_dropdown.currentText()
            editing_mode = False

        task_name = self.task_name_input.text().strip()
        due_date_str = self.due_date_input.dateTime().toString("yyyy-MM-dd HH:mm")
        description = self.description_input.toPlainText().strip()
        next_step = self.next_step_input.text().strip()
        priority = self.priority_combo.currentText()

        if selected_student == "No students registered":
            self.show_message_box("Assignment Error", "No student selected. Please register students first.", QMessageBox.Warning)
            return
        if not task_name:
            self.show_message_box("Input Error", "Task name cannot be empty.", QMessageBox.Warning)
            return

        student_tasks_file = f"{selected_student}_tasks.json"
        student_tasks = []
        if os.path.exists(student_tasks_file):
            try:
                with open(student_tasks_file, "r") as f:
                    tasks_data = json.load(f)
                    student_tasks = [Task.from_dict(d) for d in tasks_data]
            except json.JSONDecodeError:
                self.show_message_box("Error", f"Could not read tasks for {selected_student}. File might be corrupted.", QMessageBox.Critical)
                return

        if editing_mode:
            # Find the task to update
            found = False
            for i, task in enumerate(student_tasks):
                # We identify the task by its original name and due_date for robustness,
                # assuming task names might not be unique if edited
                # A better approach would be a unique ID for each task
                if task.name == task_name_old and task.due_date == self.current_edited_task.due_date: # Using due_date as an additional identifier
                    student_tasks[i].name = task_name
                    student_tasks[i].due_date = due_date_str
                    student_tasks[i].description = description
                    student_tasks[i].next_step = next_step
                    student_tasks[i].priority = priority
                    found = True
                    break
            if not found:
                self.show_message_box("Error", "Could not find the task to update. It might have been deleted.", QMessageBox.Warning)
                return
            success_message = f"Task '{task_name_old}' for {selected_student} updated to '{task_name}'!"
        else:
            # Check for duplicate task name for the specific student only when adding new task
            if any(task.name == task_name for task in student_tasks):
                self.show_message_box("Duplicate Task", f"A task named '{task_name}' already exists for {selected_student}.", QMessageBox.Warning)
                return
            new_task = Task(task_name, due_date_str, description, next_step, priority)
            student_tasks.append(new_task)
            success_message = f"Task '{task_name}' assigned to {selected_student}!"

        # Save updated tasks for the student
        try:
            with open(student_tasks_file, "w") as f:
                json.dump([task.to_dict() for task in student_tasks], f, indent=4)
            self.show_message_box("Success", success_message, QMessageBox.Information)
            self.clear_assign_inputs()
            self.current_edited_task = None
            self.current_edited_student = None
            self.assign_button.setText("Assign Task")
            self.cancel_edit_button.setVisible(False)
            self.load_and_display_upcoming_tasks() # Refresh view
        except Exception as e:
            self.show_message_box("Error", f"Failed to save task for {selected_student}: {e}", QMessageBox.Critical)

    def clear_assign_inputs(self):
        self.task_name_input.clear()
        self.description_input.clear()
        self.next_step_input.clear()
        self.due_date_input.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.priority_combo.setCurrentText("Medium")
        self.assign_button.setText("Assign Task")
        self.cancel_edit_button.setVisible(False)
        self.current_edited_task = None
        self.current_edited_student = None

    def cancel_edit_mode(self):
        self.clear_assign_inputs()
        self.show_message_box("Edit Cancelled", "Task editing cancelled. Input fields cleared.", QMessageBox.Information)

    def load_and_display_upcoming_tasks(self):
        self.task_list_widget.clear()
        self.status_label.setText("Loading tasks...")
        QApplication.processEvents()

        selected_student_filter = self.view_student_tasks_dropdown.currentText()
        task_filter_type = self.task_filter_dropdown.currentText()

        all_users_data = self._load_all_users_data()
        student_usernames = sorted([user for user, data in all_users_data.items() if data.get("role") == "student"])
        
        display_tasks_list = []
        now = datetime.now()
        upcoming_window_end = now + timedelta(hours=24) 

        students_to_load = []
        if selected_student_filter == "All Students":
            students_to_load = student_usernames
        elif selected_student_filter != "No students registered": # Ensure a valid student is selected
            students_to_load = [selected_student_filter]
        
        for student_username in students_to_load:
            student_tasks_file = f"{student_username}_tasks.json"
            if os.path.exists(student_tasks_file):
                try:
                    with open(student_tasks_file, "r") as f:
                        tasks_data = json.load(f)
                        for task_dict in tasks_data:
                            task = Task.from_dict(task_dict)
                            
                            include_task = False
                            if task_filter_type == "All Tasks":
                                include_task = True
                            elif task_filter_type == "Completed Tasks":
                                include_task = task.completed
                            elif task_filter_type == "Incomplete Tasks":
                                include_task = not task.completed
                            elif task_filter_type == "Upcoming/Overdue":
                                if not task.completed: # Only consider incomplete tasks for this filter
                                    try:
                                        due_dt = datetime.strptime(task.due_date, "%Y-%m-%d %H:%M")
                                        if due_dt > now and due_dt <= upcoming_window_end:
                                            include_task = True
                                        elif due_dt <= now:
                                            include_task = True # Include overdue tasks in this category
                                    except ValueError:
                                        # Invalid date, decide if you want to include it or not
                                        pass 

                            if include_task:
                                display_tasks_list.append({
                                    "student": student_username,
                                    "task": task
                                })
                except json.JSONDecodeError:
                    print(f"Error: Could not decode tasks for {student_username}. Skipping.")
            else:
                print(f"No task file found for student: {student_username}")

        # Sort tasks based on filter type
        def sort_key(item):
            task = item["task"]
            try:
                due_dt = datetime.strptime(task.due_date, "%Y-%m-%d %H:%M")
                if task.completed:
                    return (2, due_dt) # Completed tasks last, by completion date (or due date if not stored)
                elif due_dt <= now: # Overdue incomplete
                    return (0, due_dt) # Overdue first, by oldest due date
                else: # Upcoming incomplete
                    return (1, due_dt) # Upcoming by earliest due date
            except ValueError:
                return (3, datetime.max) # Invalid dates at the very end

        display_tasks_list.sort(key=sort_key)

        self.task_list_widget.clear()
        if not display_tasks_list:
            self.status_label.setText(f"No {task_filter_type.lower()} tasks found for the selected student(s).")
        else:
            for item_data in display_tasks_list:
                task = item_data["task"]
                student = item_data["student"]
                
                status_text = "Completed" if task.completed else "Incomplete"
                due_status_text = ""
                item_color = Qt.black # Default color
                
                if not task.completed:
                    try:
                        due_dt = datetime.strptime(task.due_date, "%Y-%m-%d %H:%M")
                        if due_dt < now:
                            due_status_text = " - OVERDUE!"
                            item_color = Qt.red
                        elif due_dt <= upcoming_window_end:
                            due_status_text = " - Upcoming"
                            item_color = Qt.darkGreen # Example color for upcoming
                    except ValueError:
                        due_status_text = " - Invalid Due Date"
                        item_color = Qt.darkYellow # Example color for invalid date
                
                item_text = (f"Student: {student} | Task: {task.name} (Due: {task.due_date}) "
                             f"[Priority: {task.priority}] [Status: {status_text}{due_status_text}]")
                list_item = QListWidgetItem(item_text)
                list_item.setForeground(item_color)
                list_item.setData(Qt.UserRole, (student, task)) # Store student and task object
                self.task_list_widget.addItem(list_item)
            self.status_label.setText(f"Displayed {len(display_tasks_list)} tasks.")
        
        self.on_task_selection_changed() # Update button states

    def on_task_selection_changed(self):
        selected_items = self.task_list_widget.selectedItems()
        if selected_items:
            self.mark_complete_button.setEnabled(True)
            self.edit_task_button.setEnabled(True)
            self.delete_task_button.setEnabled(True)
            
            # Check if the selected task is already completed
            student, task = selected_items[0].data(Qt.UserRole)
            if task.completed:
                self.mark_complete_button.setText("Already Complete")
                self.mark_complete_button.setEnabled(False)
            else:
                self.mark_complete_button.setText("Mark Complete")

        else:
            self.mark_complete_button.setEnabled(False)
            self.edit_task_button.setEnabled(False)
            self.delete_task_button.setEnabled(False)

    def mark_task_completed(self):
        selected_items = self.task_list_widget.selectedItems()
        if not selected_items:
            self.show_message_box("No Task Selected", "Please select a task to mark as complete.", QMessageBox.Warning)
            return

        student_username, task_to_mark = selected_items[0].data(Qt.UserRole)
        
        reply = self.show_message_box(
            "Confirm Completion",
            f"Are you sure you want to mark '{task_to_mark.name}' for {student_username} as completed?",
            QMessageBox.Question, QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        student_tasks_file = f"{student_username}_tasks.json"
        if os.path.exists(student_tasks_file):
            try:
                with open(student_tasks_file, "r") as f:
                    tasks_data = json.load(f)
                
                found = False
                for i, task_dict in enumerate(tasks_data):
                    # Identify the task based on name and due date (assuming unique per student)
                    if task_dict["name"] == task_to_mark.name and task_dict["due_date"] == task_to_mark.due_date:
                        tasks_data[i]["completed"] = True
                        found = True
                        break
                
                if found:
                    with open(student_tasks_file, "w") as f:
                        json.dump(tasks_data, f, indent=4)
                    self.show_message_box("Success", f"Task '{task_to_mark.name}' for {student_username} marked as completed.", QMessageBox.Information)
                    self.load_and_display_upcoming_tasks() # Refresh the list
                else:
                    self.show_message_box("Error", "Could not find the selected task in the file.", QMessageBox.Warning)

            except json.JSONDecodeError:
                self.show_message_box("Error", f"Could not read tasks for {student_username}. File might be corrupted.", QMessageBox.Critical)
            except Exception as e:
                self.show_message_box("Error", f"Failed to mark task complete: {e}", QMessageBox.Critical)
        else:
            self.show_message_box("Error", "Student task file not found.", QMessageBox.Warning)

    def edit_selected_task(self):
        selected_items = self.task_list_widget.selectedItems()
        if not selected_items:
            self.show_message_box("No Task Selected", "Please select a task to edit.", QMessageBox.Warning)
            return

        student_username, task_to_edit = selected_items[0].data(Qt.UserRole)
        
        # Populate the left panel (assign task) with selected task's details
        self.assign_student_dropdown.setCurrentText(student_username)
        self.task_name_input.setText(task_to_edit.name)
        self.due_date_input.setDateTime(QDateTime.fromString(task_to_edit.due_date, "yyyy-MM-dd HH:mm"))
        self.description_input.setPlainText(task_to_edit.description)
        self.next_step_input.setText(task_to_edit.next_step)
        self.priority_combo.setCurrentText(task_to_edit.priority)

        # Set the current edited task for the assign_task method to know it's an edit
        self.current_edited_task = task_to_edit
        self.current_edited_student = student_username
        self.assign_button.setText("Update Task")
        self.cancel_edit_button.setVisible(True)
        self.show_message_box("Editing Task", f"Editing task '{task_to_edit.name}' for {student_username}. Modify fields on the left and click 'Update Task'.", QMessageBox.Information)

    def delete_selected_task(self):
        selected_items = self.task_list_widget.selectedItems()
        if not selected_items:
            self.show_message_box("No Task Selected", "Please select a task to delete.", QMessageBox.Warning)
            return

        student_username, task_to_delete = selected_items[0].data(Qt.UserRole)
        
        reply = self.show_message_box(
            "Confirm Deletion",
            f"Are you sure you want to delete '{task_to_delete.name}' for {student_username}? This cannot be undone.",
            QMessageBox.Warning, QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        student_tasks_file = f"{student_username}_tasks.json"
        if os.path.exists(student_tasks_file):
            try:
                with open(student_tasks_file, "r") as f:
                    tasks_data = json.load(f)
                
                # Filter out the task to delete. Identify by name and due date.
                updated_tasks_data = [
                    task_dict for task_dict in tasks_data
                    if not (task_dict["name"] == task_to_delete.name and task_dict["due_date"] == task_to_delete.due_date)
                ]
                
                if len(updated_tasks_data) < len(tasks_data): # Task was found and removed
                    with open(student_tasks_file, "w") as f:
                        json.dump(updated_tasks_data, f, indent=4)
                    self.show_message_box("Success", f"Task '{task_to_delete.name}' for {student_username} deleted successfully.", QMessageBox.Information)
                    self.load_and_display_upcoming_tasks() # Refresh the list
                    self.clear_assign_inputs() # Clear any editing state if this task was being edited
                else:
                    self.show_message_box("Error", "Could not find the selected task in the file.", QMessageBox.Warning)

            except json.JSONDecodeError:
                self.show_message_box("Error", f"Could not read tasks for {student_username}. File might be corrupted.", QMessageBox.Critical)
            except Exception as e:
                self.show_message_box("Error", f"Failed to delete task: {e}", QMessageBox.Critical)
        else:
            self.show_message_box("Error", "Student task file not found.", QMessageBox.Warning)


    def _load_all_users_data(self):
        """Loads the main users.json file to get all registered usernames and roles.
        If users.json doesn't exist or is empty/malformed, it creates a default one."""
        try:
            if not os.path.exists(USERS_FILE) or os.path.getsize(USERS_FILE) == 0:
                print(f"Debug: {USERS_FILE} does not exist or is empty. Creating default users.json.")
                default_users = {
                    "teacher_user": {
                        "password": "teacher_password", # In a real app, hash passwords!
                        "role": "teacher",
                        "email": "teacher@example.com",
                        "phone_number": "+1234567890"
                    },
                    "student_user": {
                        "password": "student_password", # In a real app, hash passwords!
                        "role": "student",
                        "email": "student@example.com",
                        "phone_number": "+0987654321"
                    }
                }
                with open(USERS_FILE, "w") as f:
                    json.dump(default_users, f, indent=4)
                print(f"Debug: Created default {USERS_FILE}.")
                return default_users
            
            with open(USERS_FILE, "r") as f:
                data = json.load(f)
                print(f"Debug: Successfully loaded {USERS_FILE}. Data: {data}")
                return data
        except FileNotFoundError:
            self.show_message_box("Error", f"Users file '{USERS_FILE}' not found. Cannot load student data.", QMessageBox.Critical)
            print(f"Error: {USERS_FILE} not found in _load_all_users_data.")
            return {}
        except json.JSONDecodeError:
            self.show_message_box("Error", f"Error decoding '{USERS_FILE}'. File might be corrupted. Please check its content.", QMessageBox.Critical)
            print(f"Error: JSONDecodeError for {USERS_FILE} in _load_all_users_data.")
            return {}
        except Exception as e:
            self.show_message_box("Error", f"An unexpected error occurred while loading users: {e}", QMessageBox.Critical)
            print(f"Error: Unexpected exception in _load_all_users_data: {e}")
            return {}

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