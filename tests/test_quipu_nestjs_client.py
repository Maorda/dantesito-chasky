import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from dantesito.quipu.config.schemas import CreateExpedienteDto
from dantesito.quipu.config.settings import QuipuSettings
from dantesito.quipu.dispatchers.nestjs_client import NestJSClient



def _build_settings() -> QuipuSettings:
    environment = {
        "NESTJS_API_URL": "http://localhost:3000",
        "GOOGLE_DRIVE_FOLDER_ID": "drive_mock_123",
    }

    with patch.dict(os.environ, environment, clear=False):
        return QuipuSettings()


def _build_dto() -> CreateExpedienteDto:
    return CreateExpedienteDto(
        id_expediente_global="EXP-2026-000123",
        informacion_cej={
            "expediente_numero": "00123-2026",
            "materia": "EJECUCION DE GARANTIA",
        },
        informacion_remaju={
            "numero_convocatoria": 1,
            "porcentaje_a_rematar": 100,
        },
        informacion_sunarp={
            "partida_registral": "12345678",
            "area_terreno": 120.5,
        },
        drive_legajo_url="https://drive.google.com/file/d/mock/view",
    )


@pytest.mark.anyio
async def test_nestjs_client_send_success() -> None:
    settings = _build_settings()
    dto = _build_dto()

    request = httpx.Request(
        "POST",
        f"{settings.NESTJS_API_URL}/api/v1/expedientes",
    )
    response = httpx.Response(
        status_code=201,
        json={"success": True},
        request=request,
    )

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
    ) as mock_post:
        mock_post.return_value = response

        client = NestJSClient(settings)
        result = await client.send_expediente(dto)

    assert result is True
    mock_post.assert_awaited_once_with(
        f"{settings.NESTJS_API_URL}/api/v1/expedientes",
        json=dto.model_dump(),
    )


@pytest.mark.anyio
async def test_nestjs_client_triggers_exponential_backoff_on_failure() -> None:
    settings = _build_settings()
    dto = _build_dto()

    request = httpx.Request(
        "POST",
        f"{settings.NESTJS_API_URL}/api/v1/expedientes",
    )
    connection_error = httpx.ConnectError(
        "Error temporal de conexión",
        request=request,
    )
    success_response = httpx.Response(
        status_code=201,
        json={"success": True},
        request=request,
    )

    with (
        patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
        ) as mock_post,
        patch(
            "asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep,
    ):
        mock_post.side_effect = [
            connection_error,
            connection_error,
            success_response,
        ]

        client = NestJSClient(settings)
        result = await client.send_expediente(dto)

    assert result is True
    assert mock_post.await_count == 3
    assert mock_sleep.await_count == 2