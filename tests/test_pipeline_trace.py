import json

from app.pipeline.events import PipelineEvent, PipelineEventType
from app.pipeline.trace import PipelineTraceWriter


def test_pipeline_trace_writes_metadata_and_removes_sensitive_fields(tmp_path) -> None:
    writer = PipelineTraceWriter(enabled=True, logs_dir=tmp_path)
    writer.handle(PipelineEvent(
        PipelineEventType.RESPONSE_COMPLETED,
        turn_id="turn-1",
        payload={
            "cycle_s": 2.4,
            "response_chars": 80,
            "transcript": "rahasia presenter",
            "response": "rahasia jawaban",
        },
    ))
    path = writer.path
    writer.close()

    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["event"] == "response.completed"
    assert record["turn_id"] == "turn-1"
    assert record["payload"] == {"cycle_s": 2.4, "response_chars": 80}
