import pytest
from unittest.mock import patch, MagicMock
from app.services.groq_service import GroqService
from app.config import Config

def test_groq_service_fallback_when_no_client():
    with patch('app.config.Config.GROQ_API_KEY', ''):
        service = GroqService()
        response = service.get_response([{"role": "user", "content": "test"}])
        assert "Offline Mode" in response

def make_stream_chunk(content):
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].delta.content = content
    return chunk

@patch('app.services.groq_service.Groq')
def test_groq_service_success(mock_groq_class):
    # Setup mock client behavior
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = "Halo, saya Tenri."
    mock_client.chat.completions.create.return_value = mock_completion
    
    with patch('app.config.Config.GROQ_API_KEY', 'some-key'):
        service = GroqService()
        response = service.get_response([{"role": "user", "content": "Halo"}])
        
        assert response == "Halo, saya Tenri."
        mock_client.chat.completions.create.assert_called_once()
        kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert kwargs["max_tokens"] == Config.LLM_MAX_TOKENS

@patch('app.services.groq_service.Groq')
def test_groq_service_exception(mock_groq_class):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = Exception("API connection timeout")
    
    with patch('app.config.Config.GROQ_API_KEY', 'some-key'):
        service = GroqService()
        response = service.get_response([{"role": "user", "content": "Halo"}])
        
        assert "Error" in response
        assert "API connection timeout" in response


@patch('app.services.groq_service.Groq')
def test_groq_service_live_model_falls_back_to_base_model(mock_groq_class):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = "Fallback model berhasil."
    mock_client.chat.completions.create.side_effect = [
        Exception("model not found"),
        mock_completion,
    ]

    with (
        patch('app.config.Config.GROQ_API_KEY', 'some-key'),
        patch('app.config.Config.GROQ_MODEL', 'base-model'),
        patch('app.config.Config.GROQ_LIVE_MODEL', 'fast-model'),
    ):
        service = GroqService()
        response = service.get_response([{"role": "user", "content": "Halo"}])

    assert response == "Fallback model berhasil."
    assert mock_client.chat.completions.create.call_count == 2
    assert mock_client.chat.completions.create.call_args_list[0].kwargs["model"] == "fast-model"
    assert mock_client.chat.completions.create.call_args_list[1].kwargs["model"] == "base-model"

@pytest.mark.parametrize("content", [None, "   "])
@patch('app.services.groq_service.Groq')
def test_groq_service_fallback_when_content_is_empty(mock_groq_class, content):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = content
    mock_client.chat.completions.create.return_value = mock_completion

    with patch('app.config.Config.GROQ_API_KEY', 'some-key'):
        service = GroqService()
        response = service.get_response([{"role": "user", "content": "Halo"}])

        assert "Offline Mode" in response

@patch('app.services.groq_service.Groq')
def test_groq_service_streaming_success(mock_groq_class):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    mock_client.chat.completions.create.return_value = [
        make_stream_chunk("Halo, "),
        make_stream_chunk(None),
        make_stream_chunk("saya Tenri."),
    ]

    with patch('app.config.Config.GROQ_API_KEY', 'some-key'):
        service = GroqService()
        response = service.get_response_streaming([{"role": "user", "content": "Halo"}])

        assert response == "Halo, saya Tenri."
        kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert kwargs["stream"] is True
        assert kwargs["max_tokens"] == Config.LLM_MAX_TOKENS

@patch('app.services.groq_service.Groq')
def test_groq_service_streaming_fallback_when_content_is_empty(mock_groq_class):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    mock_client.chat.completions.create.return_value = [make_stream_chunk(None)]

    with patch('app.config.Config.GROQ_API_KEY', 'some-key'):
        service = GroqService()
        response = service.get_response_streaming([{"role": "user", "content": "Halo"}])

        assert "Offline Mode" in response

@patch('app.services.groq_service.Groq')
def test_groq_service_streaming_falls_back_to_standard_call(mock_groq_class):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = Exception("stream unavailable")

    with patch('app.config.Config.GROQ_API_KEY', 'some-key'):
        service = GroqService()
        with patch.object(service, "get_response", return_value="Fallback standar.") as fallback:
            response = service.get_response_streaming([{"role": "user", "content": "Halo"}])

    assert response == "Fallback standar."
    fallback.assert_called_once_with([{"role": "user", "content": "Halo"}])

@patch('app.services.groq_service.Groq')
def test_groq_service_streaming_handles_rate_limit(mock_groq_class):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = Exception("429 rate_limit_exceeded try again in 1m2.0s")

    with patch('app.config.Config.GROQ_API_KEY', 'some-key'):
        service = GroqService()
        response = service.get_response_streaming([{"role": "user", "content": "Halo"}])

    assert "Offline Mode" in response
    assert "1m2.0s" in response


@patch('app.services.groq_service.Groq')
def test_stream_chunks_fall_back_when_live_model_fails_before_first_token(mock_groq_class):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = [
        Exception("live model unavailable"),
        [make_stream_chunk("Jawaban dari base model.")],
    ]

    with (
        patch('app.config.Config.GROQ_API_KEY', 'some-key'),
        patch('app.config.Config.GROQ_MODEL', 'base-model'),
        patch('app.config.Config.GROQ_LIVE_MODEL', 'fast-model'),
    ):
        service = GroqService()
        chunks = list(service.stream_response_chunks([{"role": "user", "content": "Halo"}]))

    assert chunks == ["Jawaban dari base model."]
    assert mock_client.chat.completions.create.call_count == 2
    assert mock_client.chat.completions.create.call_args_list[0].kwargs["model"] == "fast-model"
    assert mock_client.chat.completions.create.call_args_list[1].kwargs["model"] == "base-model"


@patch('app.services.groq_service.Groq')
def test_stream_chunks_do_not_fall_back_after_first_token(mock_groq_class):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client

    def failing_mid_stream():
        yield make_stream_chunk("Sebagian jawaban. ")
        raise RuntimeError("connection lost mid-stream")

    mock_client.chat.completions.create.return_value = failing_mid_stream()

    with (
        patch('app.config.Config.GROQ_API_KEY', 'some-key'),
        patch('app.config.Config.GROQ_MODEL', 'base-model'),
        patch('app.config.Config.GROQ_LIVE_MODEL', 'fast-model'),
    ):
        service = GroqService()
        stream = service.stream_response_chunks([{"role": "user", "content": "Halo"}])

        assert next(stream) == "Sebagian jawaban. "
        with pytest.raises(RuntimeError, match="connection lost mid-stream"):
            next(stream)

    assert mock_client.chat.completions.create.call_count == 1
    assert mock_client.chat.completions.create.call_args.kwargs["model"] == "fast-model"


@patch('app.services.groq_service.Groq')
def test_stream_chunks_close_underlying_groq_stream_when_consumer_stops(mock_groq_class):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    provider_stream = MagicMock()
    provider_stream.__iter__.return_value = iter([
        make_stream_chunk("Kalimat pertama."),
        make_stream_chunk(" Kalimat kedua."),
    ])
    mock_client.chat.completions.create.return_value = provider_stream

    with patch('app.config.Config.GROQ_API_KEY', 'some-key'):
        service = GroqService()
        stream = service.stream_response_chunks([{"role": "user", "content": "Halo"}])
        assert next(stream) == "Kalimat pertama."
        stream.close()

    provider_stream.close.assert_called_once_with()
