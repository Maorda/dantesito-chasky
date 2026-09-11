# tests/test_quipu_master_builder.py

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from dantesito.quipu.config.schemas import CreateExpedienteDto
from dantesito.quipu.config.settings import QuipuSettings

try:
    from dantesito.quipu.consolidator.master_builder import MasterBuilder
except ImportError:
    MasterBuilder = None


def _build_settings(data_dir: Path) -> QuipuSettings:
    environment = {
        "NESTJS_API_URL": "http://localhost:3000",
        "GOOGLE_DRIVE_FOLDER_ID": "mock_google_drive_folder_id",
        "DATA_DIR": str(data_dir),
    }

    with patch.dict(os.environ, environment, clear=False):
        return QuipuSettings()


def test_master_builder_assemble_and_save_success(tmp_path: Path) -> None:
    if MasterBuilder is None:
        pytest.fail(
            "TDD: El archivo de producción master_builder.py aún no existe"
        )

    global_id = "01234-2026"

    data_cej = {
        "expediente_numero": "00123-2026",
        "materia": "EJECUCION DE GARANTIA",
        "demandante": "Banco Demandante",
        "demandado": "Demandado de Prueba",
    }

    data_remaju = {
        "numero_convocatoria": 1,
        "porcentaje_a_rematar": 100,
        "tasacion": 250000.00,
    }

    data_sunarp = {
        "partida_registral": "12345678",
        "area_terreno": 120.5,
        "direccion_predio": "Av. Principal 123",
    }

    settings = _build_settings(tmp_path)
    builder = MasterBuilder(settings)

    result = builder.assemble_and_save(
        global_id,
        data_cej,
        data_remaju,
        data_sunarp,
    )

    expected_path = (
        tmp_path
        / "04_output"
        / "json_maestro"
        / f"exp_{global_id}.json"
    )

    assert isinstance(result, Path)
    assert result == expected_path
    assert result.is_file()

    with result.open("r", encoding="utf-8") as json_file:
        master_json = json.load(json_file)

    assert isinstance(master_json, dict)
    assert master_json["id_expediente_global"] == global_id
    assert master_json["informacion_cej"] == data_cej
    assert master_json["informacion_remaju"] == data_remaju
    assert master_json["informacion_sunarp"] == data_sunarp
    assert master_json["drive_legajo_url"] is None
    assert "fecha_consolidacion" in master_json
    assert master_json["fecha_consolidacion"]
    assert isinstance(master_json["fecha_consolidacion"], str)

    dto = CreateExpedienteDto(
        id_expediente_global=master_json["id_expediente_global"],
        informacion_cej=master_json["informacion_cej"],
        informacion_remaju=master_json["informacion_remaju"],
        informacion_sunarp=master_json["informacion_sunarp"],
        drive_legajo_url=master_json["drive_legajo_url"],
    )

    assert dto.id_expediente_global == global_id
    assert dto.informacion_cej == data_cej
    assert dto.informacion_remaju == data_remaju
    assert dto.informacion_sunarp == data_sunarp