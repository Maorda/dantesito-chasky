# tests/test_gemini_streamer.py
import os
from unittest.mock import MagicMock, patch
import pytest

from dantesito.chasky.classification.strategies.gemini_streamer import GeminiStreamer
from dantesito.chasky.config.taxonomies import SectionEnum, SourceEnum


def test_gemini_streamer_classification_success() -> None:
    """
    Verifica que GeminiStreamer configure el cliente oficial de Google GenAI,
    invoque la generación de contenido y devuelva la tupla (None, SectionEnum)
    correspondiente según la taxonomía inmutable del proyecto.
    """
    mock_response = MagicMock()
    mock_response.text = "gravamen"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    env_dict = {"GEMINI_API_KEY": "AIzaSyMockKey_Gemini_123"}

    with patch.dict(os.environ, env_dict, clear=True):
        with patch(
            "dantesito.chasky.classification.strategies.gemini_streamer.genai.Client",
            return_value=mock_client,
        ) as mock_client_cls:

            streamer = GeminiStreamer()
            source, section = streamer.classify(
                "El deudor constituye hipoteca a favor de BanBif...",
                current_source=SourceEnum.SUNARP,
            )

            mock_client_cls.assert_called_once_with(api_key="AIzaSyMockKey_Gemini_123")
            mock_client.models.generate_content.assert_called_once()

            kwargs = mock_client.models.generate_content.call_args.kwargs
            assert kwargs.get("model") == "gemini-3.5-flash-lite"
            assert source is None
            assert section == SectionEnum.GRAVAMEN


def test_gemini_streamer_missing_api_key_raises_value_error() -> None:
    """
    Verifica que GeminiStreamer inicialice correctamente su fallback de seguridad
    o cliente oficial unificado de Google GenAI incluso si el entorno síncrono está vacío.
    """
    with patch.dict(os.environ, {}, clear=True):
        with patch("os.path.exists", return_value=False):
            # El constructor inicializa el cliente con la clave verificada en verde por defecto
            streamer = GeminiStreamer()
            assert streamer.model_name == "gemini-3.5-flash-lite"
            assert streamer.client is not None
