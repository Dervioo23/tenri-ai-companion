import logging
from enum import Enum, auto

logger = logging.getLogger("AICompanion.StateManager")

class AppState(Enum):
    IDLE = auto()
    LISTENING = auto()
    THINKING = auto()
    SPEAKING = auto()
    ERROR = auto()

class StateManager:
    def __init__(self):
        self._current_state = AppState.IDLE
        self._listeners = []
        self._last_error = None

    def get_state(self) -> AppState:
        return self._current_state

    def set_state(self, state: AppState, error_msg: str = None):
        if self._current_state != state:
            old_state = self._current_state
            self._current_state = state
            if state == AppState.ERROR:
                self._last_error = error_msg
            else:
                self._last_error = None
            
            # Notify listeners
            for listener in self._listeners:
                try:
                    listener(old_state, state, error_msg)
                except Exception as e:
                    logger.warning(f"State listener error: {e}")

    def register_listener(self, callback):
        """Register a callback that receives (old_state, new_state, error_msg)."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def get_last_error(self) -> str:
        return self._last_error

# Singleton instance
state_manager = StateManager()
