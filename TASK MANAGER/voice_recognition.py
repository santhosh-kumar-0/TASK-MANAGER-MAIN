# voice_recognition.py

import speech_recognition as sr
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget

class VoiceRecognitionThread(QWidget):
    """
    A QWidget-based class to handle speech recognition in a separate thread.
    Emits a signal with the recognized text.
    """
    recognized_text = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False

    def listen(self):
        """
        Starts listening for audio input and attempts to recognize speech.
        Emits `recognized_text` signal with the result or an error message.
        """
        self.is_listening = True
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
                audio = self.recognizer.listen(source, timeout=5) # Listen for up to 5 seconds
            
            try:
                text = self.recognizer.recognize_google(audio)
                self.recognized_text.emit(text)
            except sr.UnknownValueError:
                self.recognized_text.emit("Could not understand audio")
            except sr.RequestError as e:
                self.recognized_text.emit(f"Could not request results from Google Speech Recognition service; {e}")
        except Exception as e:
            self.recognized_text.emit(f"Error during voice recognition: {str(e)}")
        finally:
            self.is_listening = False
    def stop_listening(self):
        """
        Stops the listening process if it is currently active.
        """
        if self.is_listening:
            self.is_listening = False
            # Note: Stopping the microphone listening is handled by the recognizer's context manager
            # when exiting the `with` block in the listen method.   
    def is_listening_active(self):
        """
        Returns True if the voice recognition is currently listening for input.
        """
        return self.is_listening