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


def test_unregister_listener_stops_notifications() -> None:
    manager = StateManager()
    calls = []
    listener = lambda o, n, e: calls.append(n)

    manager.register_listener(listener)
    manager.set_state(AppState.LISTENING)
    manager.unregister_listener(listener)
    manager.set_state(AppState.THINKING)

    assert calls == [AppState.LISTENING]  # only the pre-unregister change


def test_unregister_absent_listener_is_safe() -> None:
    manager = StateManager()
    manager.unregister_listener(lambda o, n, e: None)  # must not raise


def test_register_is_idempotent_and_unregister_clears_single_copy() -> None:
    manager = StateManager()
    calls = []
    listener = lambda o, n, e: calls.append(n)

    manager.register_listener(listener)
    manager.register_listener(listener)  # dedup → still one copy
    manager.unregister_listener(listener)
    manager.set_state(AppState.SPEAKING)

    assert calls == []


def test_error_state_tracks_last_error_even_when_listener_fails() -> None:
    manager = StateManager()

    def failing_listener(old_state, new_state, error_msg):
        raise RuntimeError("listener failed")

    manager.register_listener(failing_listener)
    manager.set_state(AppState.ERROR, "boom")

    assert manager.get_last_error() == "boom"
