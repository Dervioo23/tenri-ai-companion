from scripts.diagnose_microphone import main


def test_diagnostic_entrypoint_is_callable() -> None:
    assert callable(main)
