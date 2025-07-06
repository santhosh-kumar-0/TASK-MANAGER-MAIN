import json
import os
import threading
from datetime import datetime
import requests # For making API calls

# PyQt5 imports
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTextEdit, QPushButton, QLabel, QFrame,
    QScrollArea, QApplication, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon

# Local module imports
from voice_recognition import VoiceRecognitionThread
from ui_components import CustomMessageBox # For consistent message boxes
from config import GEMINI_API_KEY # Import Gemini API key

class AIChatbotWindow(QWidget):
    # Signals for updating UI from non-GUI threads
    update_chat_display_signal = pyqtSignal(str, str) # role, text
    set_ai_thinking_signal = pyqtSignal(bool) # True for thinking, False for not

    def __init__(self, parent_task_manager=None):
        """
        Initializes the AI Chatbot Window.
        :param parent_task_manager: Reference to the MainTaskManagerUI instance
                                    to retrieve current tasks, points, and streak.
        """
        super().__init__()
        self.parent_task_manager = parent_task_manager
        self.setWindowTitle("AI Chatbot Assistant")
        self.setGeometry(200, 200, 560, 480) # Set initial window size and position

        self.chat_history = [] # Stores history for context (for display)
        self.api_chat_history = [] # Stores history in Gemini API format for context in API calls

        self.init_ui()
        self.apply_stylesheet()

        # Connect signals
        self.update_chat_display_signal.connect(self._display_message)
        self.set_ai_thinking_signal.connect(self._set_ai_thinking)

        # Initialize Voice Recognition Thread
        self.voice_rec_thread = None
        try:
            self.voice_rec_thread = VoiceRecognitionThread()
            self.voice_rec_thread.recognized_text.connect(self._handle_voice_input)
            self.voice_button.setEnabled(True) # Enable button if voice recognition is available
        except Exception as e:
            print(f"Voice recognition not available: {e}")
            self.voice_button.setEnabled(False) # Disable voice button if not available
            self.voice_button.setText("Voice (N/A)")
            self.voice_button.setToolTip("Microphone not detected or PyAudio not installed.")


    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Chat display area
        self.chat_display_area = QWidget()
        self.chat_display_layout = QVBoxLayout(self.chat_display_area)
        self.chat_display_layout.setAlignment(Qt.AlignTop)
        self.chat_display_layout.setSpacing(5)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.chat_display_area)
        self.scroll_area.setObjectName("chatScrollArea")
        main_layout.addWidget(self.scroll_area)

        # AI Thinking indicator
        self.ai_thinking_label = QLabel("AI is thinking...")
        self.ai_thinking_label.setObjectName("aiThinkingLabel")
        self.ai_thinking_label.setAlignment(Qt.AlignCenter)
        self.ai_thinking_label.setVisible(False) # Hidden by default
        main_layout.addWidget(self.ai_thinking_label)

        # Input area
        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type your message here...")
        self.chat_input.setObjectName("chatInput")
        self.chat_input.returnPressed.connect(self.send_message) # Send on Enter
        input_layout.addWidget(self.chat_input)

        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("sendButton")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)

        self.voice_button = QPushButton()
        # Ensure 'icons/microphone.png' exists or replace with a default icon/text
        # For demonstration, let's use a text label if icon is missing.
        icon_path = "icons/microphone.png"
        if os.path.exists(icon_path):
            self.voice_button.setIcon(QIcon(icon_path))
            self.voice_button.setIconSize(QSize(24, 24))
        else:
            self.voice_button.setText("Voice") # Fallback to text
            self.voice_button.setMinimumWidth(60) # Ensure it's wide enough for text

        self.voice_button.setObjectName("voiceButton")
        self.voice_button.setToolTip("Speak your message")
        self.voice_button.clicked.connect(self.start_voice_input)
        self.voice_button.setEnabled(False) # Disabled by default, enabled if voice_rec_thread initializes successfully
        input_layout.addWidget(self.voice_button)
        main_layout.addLayout(input_layout)

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                color: #343a40;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
            }
            #chatScrollArea {
                border: 1px solid #e9ecef;
                border-radius: 8px;
                background-color: #ffffff;
            }
            #chatDisplayArea { /* The widget inside the scroll area */
                background-color: #ffffff;
            }
            QLabel.user-message, QLabel.ai-message {
                padding: 8px 12px;
                border-radius: 18px;
                max-width: 75%;
                word-wrap: break-word;
                margin-bottom: 5px;
            }
            QLabel.user-message {
                background-color: #007bff;
                color: white;
                border-bottom-right-radius: 4px;
            }
            QLabel.ai-message {
                background-color: #e2e6ea;
                color: #343a40;
                border-bottom-left-radius: 4px;
            }
            #chatInput {
                border: 1px solid #ced4da;
                border-radius: 20px;
                padding: 10px 15px;
                background-color: #ffffff;
            }
            QPushButton#sendButton, QPushButton#voiceButton {
                background-color: #28a745; /* Green for send */
                color: white;
                border: none;
                border-radius: 20px;
                padding: 10px 15px;
                font-weight: bold;
                min-width: 70px;
            }
            QPushButton#voiceButton {
                background-color: #6c757d; /* Grey for voice */
                min-width: 40px; /* Adjust for icon */
                padding: 10px 10px;
            }
            QPushButton#sendButton:hover {
                background-color: #218838;
            }
            QPushButton#voiceButton:hover {
                background-color: #5a6268;
            }
            #aiThinkingLabel {
                color: #6c757d;
                font-style: italic;
                padding: 5px;
            }
        """)

    def _display_message(self, role, text):
        """Displays a message in the chat area."""
        message_label = QLabel(text)
        message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        message_label.setWordWrap(True)

        if role == "user":
            message_label.setObjectName("user-message")
            message_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        elif role == "ai":
            message_label.setObjectName("ai-message")
            message_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        # Create a container widget to hold the message label and control its alignment
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0) # No margins for the inner layout
        
        if role == "user":
            container_layout.addStretch() # Push message to right
            container_layout.addWidget(message_label)
        else: # ai
            container_layout.addWidget(message_label)
            container_layout.addStretch() # Push message to left

        self.chat_display_layout.addWidget(container)
        
        # Scroll to bottom
        QApplication.processEvents() # Process events to ensure widget is added before scrolling
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def _set_ai_thinking(self, is_thinking):
        """Shows/hides the AI thinking indicator and disables/enables input."""
        self.ai_thinking_label.setVisible(is_thinking)
        self.chat_input.setEnabled(not is_thinking)
        self.send_button.setEnabled(not is_thinking)
        # Only enable voice button if it was initially available
        if self.voice_rec_thread and self.voice_button.isEnabled():
            self.voice_button.setEnabled(not is_thinking)
        QApplication.processEvents() # Update UI immediately

    def send_message(self):
        user_message = self.chat_input.text().strip()
        if not user_message:
            return

        self._display_message("user", user_message)
        self.chat_input.clear()
        
        # Add to chat_history for display purposes
        self.chat_history.append({"role": "user", "text": user_message})
        # Add to api_chat_history for Gemini API context
        self.api_chat_history.append({"role": "user", "parts": [{"text": user_message}]})

        # Start AI response in a separate thread
        threading.Thread(target=self._get_ai_response, args=(user_message,)).start()

    def start_voice_input(self):
        if not self.voice_rec_thread or not self.voice_button.isEnabled():
            self._display_message("ai", "Voice input is not available. Please check your microphone and PyAudio installation.")
            return

        self._display_message("ai", "Listening... Please speak now.")
        self.set_ai_thinking_signal.emit(True) # Indicate listening
        # Start voice recognition in a separate thread
        threading.Thread(target=self.voice_rec_thread.listen).start()

    def _handle_voice_input(self, text):
        """Callback for voice recognition thread."""
        self.set_ai_thinking_signal.emit(False) # Hide thinking indicator

        if text.startswith("Error during voice recognition") or \
           text == "Could not understand audio" or \
           text.startswith("Could not request results"):
            self._display_message("ai", f"Voice input error: {text}")
        else:
            # Display the recognized text as if the user typed it
            self._display_message("user", f"Voice input: {text}")
            # Add to chat_history for display purposes
            self.chat_history.append({"role": "user", "text": text})
            # Add to api_chat_history for Gemini API context
            self.api_chat_history.append({"role": "user", "parts": [{"text": text}]})
            
            # Send the recognized text to the AI
            threading.Thread(target=self._get_ai_response, args=(text,)).start()


    def _get_ai_response(self, user_prompt):
        """Fetches AI response from Gemini API."""
        self.set_ai_thinking_signal.emit(True) # Show AI thinking indicator

        ai_response_text = "Sorry, I couldn't get a response. Please try again later."
        try:
            # CORRECTED: Using gemini-2.0-flash as per initial instructions
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}

            if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
                raise ValueError("Gemini API Key is not configured in config.py. Please set your API key.")

            context_info = self._get_context_from_task_manager()
            
            # System instruction for the AI
            # This is sent with every request to reinforce the AI's role and constraints.
            system_instruction_parts = [
                {"text": "You are a helpful task management AI assistant. "
                         "Provide concise and relevant advice based on the user's tasks and gamification progress. "
                         "Do not generate long essays or irrelevant information. "
                         "Focus on practical task management tips, motivation, and answering questions directly related to their tasks. "
                         "If asked about a completed task, acknowledge it's done. "
                         "If a task is pending, offer strategies. "
                         "Encourage good habits. "
                         "Keep responses under 100 words unless absolutely necessary. "
                         "Your primary goal is to help the user manage their tasks effectively."
                },
                {"text": "\n--- Current User Context ---"},
                {"text": f"Tasks: {context_info['tasks_info']}"},
                {"text": f"Points: {context_info['user_points']}"},
                {"text": f"Current Streak: {context_info['user_streak']} days"}
            ]

            # Create the current user's message including the combined prompt and context
            current_user_message_for_api = {
                "role": "user",
                "parts": system_instruction_parts + [{"text": f"\n--- User Query ---\n{user_prompt}"}]
            }

            # The `contents` array will be `self.api_chat_history` + the new `current_user_message_for_api`.
            # This assumes `self.api_chat_history` is already alternating user/model roles.
            
            contents = self.api_chat_history + [current_user_message_for_api]

            response = requests.post(url, headers=headers, json={"contents": contents})
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            
            result = response.json()

            if result and "candidates" in result and result["candidates"]:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    ai_response_text = "".join(part["text"] for part in candidate["content"]["parts"])
                    # Add AI's response to api_chat_history for future context
                    self.api_chat_history.append({"role": "model", "parts": [{"text": ai_response_text}]})
                else:
                    ai_response_text = "AI returned an empty response or unexpected format."
                    print("Gemini API: No content or parts in candidate.")
            else:
                ai_response_text = "AI did not return any candidates."
                print("Gemini API: No candidates in response.")
                if "promptFeedback" in result and "blockReason" in result["promptFeedback"]:
                    block_reason = result["promptFeedback"]["blockReason"]
                    ai_response_text += f"\nReason: {block_reason}. Your query might have been flagged."
                    print("Prompt Feedback:", result["promptFeedback"])

        except ValueError as ve:
            ai_response_text = f"Configuration Error: {ve}"
            print(f"Configuration Error: {ve}")
        except requests.exceptions.HTTPError as http_err:
            ai_response_text = f"HTTP error occurred: {http_err}. Status: {http_err.response.status_code}. Response: {http_err.response.text}"
            print(f"HTTP Error: {http_err.response.status_code} - {http_err.response.text}")
        except requests.exceptions.ConnectionError as conn_err:
            ai_response_text = f"Connection error: {conn_err}. Please check your internet connection."
            print(f"Connection Error: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            ai_response_text = f"Request timed out: {timeout_err}. The AI server took too long to respond."
            print(f"Timeout Error: {timeout_err}")
        except requests.exceptions.RequestException as e:
            ai_response_text = f"An unknown error occurred during the API request: {e}"
            print(f"Request Error: {e}")
        except json.JSONDecodeError as e:
            ai_response_text = f"Error decoding API response: {e}. The response might be malformed."
            print(f"JSON Decode Error: {e}. Response content: {response.text if 'response' in locals() else 'N/A'}")
        except Exception as e:
            ai_response_text = f"An unexpected error occurred: {e}"
            print(f"Unexpected Error: {e}")
        finally:
            self.update_chat_display_signal.emit("ai", ai_response_text)
            self.set_ai_thinking_signal.emit(False) # Hide AI thinking indicator

    def _get_context_from_task_manager(self):
        """
        Retrieves current tasks, points, and streak from the parent task manager.
        """
        if self.parent_task_manager and hasattr(self.parent_task_manager, 'tasks') and \
           hasattr(self.parent_task_manager, 'user_points') and \
           hasattr(self.parent_task_manager, 'user_streak_data'):
            tasks_info = []
            for i, task in enumerate(self.parent_task_manager.tasks):
                status = "Completed" if task.completed else "Pending"
                # Add a note if overdue
                try:
                    due_dt = datetime.strptime(task.due_date, "%Y-%m-%d %H:%M")
                    overdue_status = " (Overdue!)" if not task.completed and due_dt < datetime.now() else ""
                except ValueError:
                    overdue_status = " (Invalid Due Date)" # Handle malformed dates
                tasks_info.append(f"{i+1}. {task.name} (Due: {task.due_date}, Priority: {task.priority}, Status: {status}{overdue_status})")
            
            return {
                "tasks_info": "\n".join(tasks_info) if tasks_info else "No tasks currently.",
                "user_points": self.parent_task_manager.user_points,
                "user_streak": self.parent_task_manager.user_streak_data["current_streak"]
            }
        return {
            "tasks_info": "No tasks loaded (Task manager context not available).",
            "user_points": 0,
            "user_streak": 0
        }
