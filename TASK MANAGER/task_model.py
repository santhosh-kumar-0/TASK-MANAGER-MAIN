# task_model.py

class Task:
    """
    Represents a single task with its properties.
    Includes attributes for name, due date, description, next step, priority,
    completion status, a 'reminded' flag, and a list of attached file paths.
    """
    def __init__(self, name, due_date, description="", next_step="", priority="Medium", completed=False, reminded=False, attachments=None):
        self.name = name
        self.due_date = due_date  # Stored as a string (e.g., "yyyy-MM-dd HH:mm")
        self.description = description
        self.next_step = next_step
        self.priority = priority # "High", "Medium", "Low"
        self.completed = completed
        self.reminded = reminded # True if a time-based reminder has been sent for this task
        self.attachments = attachments if attachments is not None else [] # List of relative file paths

    def to_dict(self):
        """
        Converts the task object to a dictionary for JSON serialization.
        """
        return {
            "name": self.name,
            "due_date": self.due_date,
            "description": self.description,
            "next_step": self.next_step,
            "priority": self.priority,
            "completed": self.completed,
            "reminded": self.reminded,
            "attachments": self.attachments
        }

    @classmethod
    def from_dict(cls, data):
        """
        Creates a Task object from a dictionary (e.g., loaded from JSON).
        Uses .get() for optional fields to handle older data structures gracefully.
        """
        return cls(
            data["name"],
            data["due_date"],
            data.get("description", ""),
            data.get("next_step", ""),
            data.get("priority", "Medium"),
            data.get("completed", False),
            data.get("reminded", False),
            data.get("attachments", []) # Ensure attachments are loaded, default to empty list
        )