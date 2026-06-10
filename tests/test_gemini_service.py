from unittest.mock import MagicMock

from app.services.gemini_service import GeminiService


class FakeGenerateContentConfig:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeTypes:
    GenerateContentConfig = FakeGenerateContentConfig


def make_service():
    service = GeminiService.__new__(GeminiService)
    service.api_key = "some-key"
    service.model = "gemini-test"
    service.client = MagicMock()
    service._types = FakeTypes
    return service


def test_gemini_service_converts_openai_messages_to_gemini_contents():
    service = make_service()

    system_instruction, contents = service._convert_messages([
        {"role": "system", "content": "Persona Tenri."},
        {"role": "user", "content": "Halo"},
        {"role": "assistant", "content": "Iye, saya di sini."},
        {"role": "user", "content": "Jelaskan slide ini."},
    ])

    assert system_instruction == "Persona Tenri."
    assert contents == [
        {"role": "user", "parts": [{"text": "Halo"}]},
        {"role": "model", "parts": [{"text": "Iye, saya di sini."}]},
        {"role": "user", "parts": [{"text": "Jelaskan slide ini."}]},
    ]


def test_gemini_service_success():
    service = make_service()
    response = MagicMock()
    response.text = "Halo, saya Tenri."
    service.client.models.generate_content.return_value = response

    result = service.get_response([
        {"role": "system", "content": "Persona Tenri."},
        {"role": "user", "content": "Halo"},
    ])

    assert result == "Halo, saya Tenri."
    service.client.models.generate_content.assert_called_once()
    kwargs = service.client.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "gemini-test"
    assert kwargs["contents"] == [{"role": "user", "parts": [{"text": "Halo"}]}]
    assert kwargs["config"].kwargs["system_instruction"] == "Persona Tenri."


def test_gemini_service_streaming_success():
    service = make_service()
    chunk_a = MagicMock()
    chunk_a.text = "Halo, "
    chunk_b = MagicMock()
    chunk_b.text = "saya Tenri."
    service.client.models.generate_content_stream.return_value = [chunk_a, chunk_b]

    result = service.get_response_streaming([
        {"role": "user", "content": "Halo"},
    ])

    assert result == "Halo, saya Tenri."
    service.client.models.generate_content_stream.assert_called_once()
