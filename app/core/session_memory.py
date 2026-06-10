class SessionMemory:
    def __init__(self, max_turns: int = 10):
        """
        Manages the temporary conversation history.
        max_turns: Maximum number of user-assistant exchanges to keep.
        """
        self.max_turns = max_turns
        self.history = []

    def add_user_message(self, content: str):
        self.history.append({"role": "user", "content": content})
        self._truncate()

    def add_assistant_message(self, content: str):
        self.history.append({"role": "assistant", "content": content})
        self._truncate()

    def get_messages(self) -> list:
        """Returns the conversation history as a list of message dicts."""
        return self.history.copy()

    def clear(self):
        """Clears all conversation history."""
        self.history.clear()

    def _truncate(self):
        """Truncates history to respect the max_turns limit (2 messages per turn)."""
        max_messages = self.max_turns * 2
        if len(self.history) > max_messages:
            trimmed = self.history[-max_messages:]
            if trimmed and trimmed[0].get("role") == "assistant":
                trimmed = trimmed[1:]
            self.history = trimmed
