# tests/quipu/test_api_server.py
import json
import os
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from dantesito.quipu.entrypoint.api_server import app


@pytest.fixture
def api_client(tmp_path: Path):
    """Configura un entorno aislado mediante DATA_DIR y retorna un TestClient de FastAPI."""
    os.environ["DATA_DIR"] = str(tmp_path)
    os.environ["QUIPU_API_AUTH_TOKEN"] = "Messenger2"
    
    client = TestClient(app)
    return client


def test_get_web_interface(api_client: TestClient) -> None:
    """Verifica que la ruta raíz responda con éxito y renderice la UI mobile-first."""
    response = api_client.get("/")
    assert response.status_code == 200
    assert "Quipu Control" in response.text
    assert "N° Expediente" in response.text


@patch("dantesito.quipu.entrypoint.api_server.run_pipeline_entrypoint")
def test_handle_web_form_success(mock_run_pipeline, api_client: TestClient, tmp_path: Path) -> None:
    """Valida el envío exitoso del formulario web con token correcto, la creación del estado y el encolado."""
    expediente_id = "0200-2026-JP"
    
    response = api_client.post(
        "/",
        data={
            "numero_expediente": expediente_id,
            "token_seguridad": "Messenger2",
        },
        follow_redirects=False,
    )
    
    assert response.status_code == 200
    assert "¡Pipeline Gatillado Exitosamente!" in response.text
    
    # Verificar creación del archivo de estado físico en disco (aislado en tmp_path)
    clean_id = expediente_id.replace("/", "_").replace("\\", "_")
    status_file = tmp_path / "04_output" / f"status_{clean_id}.json"
    assert status_file.exists(), "El archivo JSON de estado físico no fue creado."
    
    with open(status_file, "r", encoding="utf-8") as f:
        status_data = json.load(f)
    assert status_data["status"] == "procesando"
    
    # Verificar que se haya encolado la tarea de fondo (mocked)
    mock_run_pipeline.assert_called_once()


def test_get_pipeline_status_unauthorized(api_client: TestClient) -> None:
    """Verifica que la consulta de estado rechace peticiones sin token o con token inválido (401)."""
    expediente_id = "0200-2026-JP"
    
    # Petición sin header X-Auth-Token
    response_no_token = api_client.get(f"/api/v1/status/{expediente_id}")
    assert response_no_token.status_code == 401
    
    # Petición con header X-Auth-Token incorrecto
    response_bad_token = api_client.get(
        f"/api/v1/status/{expediente_id}",
        headers={"X-Auth-Token": "TokenIncorrecto"}
    )
    assert response_bad_token.status_code == 401


def test_get_pipeline_status_success(api_client: TestClient, tmp_path: Path) -> None:
    """Simula la existencia de un archivo JSON de estado y verifica su consulta exitosa con token válido."""
    expediente_id = "0200-2026-JP"
    clean_id = expediente_id.replace("/", "_").replace("\\", "_")
    
    status_dir = tmp_path / "04_output"
    status_dir.mkdir(parents=True, exist_ok=True)
    status_file = status_dir / f"status_{clean_id}.json"
    
    mock_status_content = {
        "status": "procesando",
        "archivo_actual": "remaju_0200.pdf",
        "fase_actual": "Fase 2: Clasificación Semántica",
        "ultima_actualizacion": "2026-09-10T12:00:00Z"
    }
    
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(mock_status_content, f, ensure_ascii=False)
        
    response = api_client.get(
        f"/api/v1/status/{expediente_id}",
        headers={"X-Auth-Token": "Messenger2"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "procesando"
    assert data["archivo_actual"] == "remaju_0200.pdf"
    assert data["fase_actual"] == "Fase 2: Clasificación Semántica"