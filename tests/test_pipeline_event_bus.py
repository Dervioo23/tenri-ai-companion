import logging

from app.pipeline.event_bus import PipelineEventBus
from app.pipeline.events import PipelineEvent, PipelineEventType


def test_event_bus_preserves_order_and_supports_wildcard_subscriber() -> None:
    bus = PipelineEventBus()
    typed: list[str] = []
    all_events: list[str] = []
    bus.subscribe(
        PipelineEventType.CAPTURE_STARTED,
        lambda event: typed.append(event.turn_id),
    )
    bus.subscribe(None, lambda event: all_events.append(event.type.value))
    bus.start()

    assert bus.publish(PipelineEvent(PipelineEventType.CAPTURE_STARTED, "turn-1"))
    assert bus.publish(PipelineEvent(PipelineEventType.UTTERANCE_CAPTURED, "turn-1"))
    assert bus.flush(timeout=1.0)
    bus.stop()

    assert typed == ["turn-1"]
    assert all_events == [
        PipelineEventType.CAPTURE_STARTED.value,
        PipelineEventType.UTTERANCE_CAPTURED.value,
    ]


def test_event_bus_isolates_subscriber_error(caplog) -> None:
    bus = PipelineEventBus()
    delivered: list[str] = []

    def broken(_event) -> None:
        raise RuntimeError("subscriber boom")

    bus.subscribe(PipelineEventType.RUNTIME_STARTED, broken)
    bus.subscribe(PipelineEventType.RUNTIME_STARTED, lambda event: delivered.append(event.turn_id))
    bus.start()
    with caplog.at_level(logging.WARNING, logger="AICompanion.PipelineEventBus"):
        bus.publish(PipelineEvent(PipelineEventType.RUNTIME_STARTED, "runtime"))
        assert bus.flush(timeout=1.0)
    bus.stop()

    assert delivered == ["runtime"]
    assert "subscriber boom" in caplog.text


def test_event_bus_rejects_publish_before_start() -> None:
    bus = PipelineEventBus()
    assert not bus.publish(PipelineEvent(PipelineEventType.RUNTIME_STARTED))
