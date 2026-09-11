# tests/test_gemini_streamer.py
import os
from unittest.mock import MagicMock, patch, mock_open
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


def test_gemini_streamer_env_file_rescue() -> None:
    """
    Verifica el Nivel de Rescate 2: si el entorno está vacío, el script debe 
    escanear y leer físicamente la credencial desde el archivo .env.
    """
    env_file_content = "GEMINI_API_KEY=AIzaSyEnvFileKey_456\n"
    
    with patch.dict(os.environ, {}, clear=True):
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=env_file_content)):
                with patch(
                    "dantesito.chasky.classification.strategies.gemini_streamer.genai.Client"
                ) as mock_client_cls:

                    streamer = GeminiStreamer()
                    mock_client_cls.assert_called_once_with(api_key="AIzaSyEnvFileKey_456")


def test_gemini_streamer_unknown_label_returns_none() -> None:
    """
    Verifica que si la API de Gemini devuelve una etiqueta desconocida o 'desconocido',
    el clasificador lo maneje con seguridad retornando (None, None).
    """
    mock_response = MagicMock()
    mock_response.text = "desconocido"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    env_dict = {"GEMINI_API_KEY": "AIzaSyMockKey_Gemini_123"}

    with patch.dict(os.environ, env_dict, clear=True):
        with patch(
            "dantesito.chasky.classification.strategies.gemini_streamer.genai.Client",
            return_value=mock_client,
        ):
            streamer = GeminiStreamer()
            source, section = streamer.classify("Texto aleatorio sin sentido legal...")

            assert source is None
            assert section is None


def test_gemini_streamer_missing_api_key_raises_value_error() -> None:
    """
    Verifica que la ausencia de GEMINI_API_KEY en el entorno y en el archivo .env
    provoque un ValueError de forma defensiva para proteger el pipeline.
    """
    with patch.dict(os.environ, {}, clear=True):
        with patch("os.path.exists", return_value=False):
            with pytest.raises(ValueError) as exc_info:
                GeminiStreamer()
            
            assert "🚨 ERROR CRÍTICO DE CONFIGURACIÓN" in str(exc_info.value)