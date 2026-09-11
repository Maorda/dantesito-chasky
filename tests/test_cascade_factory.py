# tests/test_cascade_factory.py
import os
from typing import Generator
from unittest.mock import patch

import pytest

from dantesito.chasky.classification.cascade_factory import CascadeFactory
from dantesito.chasky.config.taxonomies import SectionEnum, SourceEnum


@pytest.fixture
def mock_env_api_key() -> Generator[None, None, None]:
    """
    Fixture de prueba que asegura la presencia de la credencial GEMINI_API_KEY
    para la inicialización limpia de GeminiStreamer dentro de CascadeFactory.
    """
    with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyMockKey_Gemini_123"}, clear=True):
        yield


def test_cascade_factory_fallback_to_gemini(mock_env_api_key: None) -> None:
    """
    Verifica que la fábrica recurra a GeminiStreamer cuando las estrategias previas
    devuelven (None, None) y capture correctamente la tupla (SourceEnum, SectionEnum).
    """
    sample_text = "Embargo en forma de inscripción sobre la finca registral N° 12345678."

    with patch(
        "dantesito.chasky.classification.strategies.cpu_regex_strategy.CPURegexStrategy.classify",
        return_value=(None, None),
    ), patch(
        "dantesito.chasky.classification.strategies.context_overlap_strategy.ContextOverlapStrategy.classify",
        return_value=(None, None),
    ), patch(
        "dantesito.chasky.classification.strategies.gemini_streamer.GeminiStreamer.classify",
        return_value=(None, SectionEnum.GRAVAMEN),
    ) as mock_gemini_classify:

        factory = CascadeFactory()
        source, section = factory.process_chunk(sample_text, current_source=SourceEnum.SUNARP)

        mock_gemini_classify.assert_called_once_with(sample_text, current_source=SourceEnum.SUNARP)
        assert source == SourceEnum.SUNARP
        assert section == SectionEnum.GRAVAMEN


def test_cascade_factory_empty_text_returns_default(mock_env_api_key: None) -> None:
    """
    Verifica que la entrega de textos nulos o vacíos intercepte la ejecución
    retornando la sección RESOLUCION por defecto sin invocar las estrategias.
    """
    factory = CascadeFactory()

    source_empty, section_empty = factory.process_chunk("", current_source=SourceEnum.REMAJU)
    assert source_empty == SourceEnum.REMAJU
    assert section_empty == SectionEnum.RESOLUCION

    source_none, section_none = factory.process_chunk(None, current_source=SourceEnum.SUNARP)
    assert source_none == SourceEnum.SUNARP
    assert section_none == SectionEnum.RESOLUCION


def test_cascade_factory_full_fallback_returns_default(mock_env_api_key: None) -> None:
    """
    Verifica el comportamiento cuando todas las estrategias (incluyendo GeminiStreamer)
    no logran categorizar el texto, retornando el valor seguro RESOLUCION.
    """
    sample_text = "Texto indeterminado de una resolución registral."

    with patch(
        "dantesito.chasky.classification.strategies.cpu_regex_strategy.CPURegexStrategy.classify",
        return_value=(None, None),
    ), patch(
        "dantesito.chasky.classification.strategies.context_overlap_strategy.ContextOverlapStrategy.classify",
        return_value=(None, None),
    ), patch(
        "dantesito.chasky.classification.strategies.gemini_streamer.GeminiStreamer.classify",
        return_value=(None, None),
    ):

        factory = CascadeFactory()
        source, section = factory.process_chunk(sample_text, current_source=SourceEnum.REMAJU)

        assert source == SourceEnum.REMAJU
        assert section == SectionEnum.RESOLUCION


def test_cascade_factory_handles_strategy_exception(mock_env_api_key: None) -> None:
    """
    Verifica la resiliencia de la fábrica cuando GeminiStreamer lanza una excepción,
    garantizando que se retorne la tupla de fallback sin romper el flujo de ejecución.
    """
    sample_text = "Se resuelve declarar procedente la solicitud presentante."

    with patch(
        "dantesito.chasky.classification.strategies.cpu_regex_strategy.CPURegexStrategy.classify",
        return_value=(None, None),
    ), patch(
        "dantesito.chasky.classification.strategies.context_overlap_strategy.ContextOverlapStrategy.classify",
        return_value=(None, None),
    ), patch(
        "dantesito.chasky.classification.strategies.gemini_streamer.GeminiStreamer.classify",
        side_effect=RuntimeError("Fallo de conexión con Google AI Studio"),
    ):

        factory = CascadeFactory()
        source, section = factory.process_chunk(sample_text, current_source=SourceEnum.SUNARP)

        assert source == SourceEnum.SUNARP
        assert section == SectionEnum.RESOLUCION