from app.state import AppState, StateManager


def test_listener_exception_does_not_stop_other_listeners() -> None:
    manager = StateManager()
    calls = []

    def failing_listener(old_state, new_state, error_msg):
        calls.append(("failing", old_state, new_state, error_msg))
        raise RuntimeError("listener failed")

    def healthy_listener(old_state, new_state, error_msg):
        calls.append(("healthy", old_state, new_state, error_msg))

    manager.register_listener(failing_listener)
    manager.register_listener(healthy_listener)

    manager.set_state(AppState.THINKING)

    assert len(calls) == 2
    assert calls[0][0] == "failing"
    assert calls[1][0] == "healthy"
    assert manager.get_state() == AppState.THINKING


def test_error_state_tracks_last_error_even_when_listener_fails() -> None:
    manager = StateManager()

    def failing_listener(old_state, new_state, error_msg):
        raise RuntimeError("listener failed")

    manager.register_listener(failing_listener)
    manager.set_state(AppState.ERROR, "boom")

    assert manager.get_last_error() == "boom"
