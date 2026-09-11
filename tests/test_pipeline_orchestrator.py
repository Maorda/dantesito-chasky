# tests/test_pipeline_orchestrator.py
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from dantesito.quipu.workflows.pipeline_orchestrator import PipelineOrchestrator
from dantesito.quipu.config.settings import QuipuSettings


@pytest.mark.anyio
@patch("dantesito.quipu.workflows.pipeline_orchestrator.ChaskyConsolidator")
@patch("dantesito.quipu.workflows.pipeline_orchestrator.MasterBuilder")
@patch("dantesito.quipu.workflows.pipeline_orchestrator.GoogleDrivePublisher")
@patch("dantesito.quipu.workflows.pipeline_orchestrator.NestJSClient")
async def test_run_full_cycle_success_with_async_status(
    mock_nestjs_cls,
    mock_drive_cls,
    mock_master_cls,
    mock_chasky_cls,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verifica que el pipeline complete su ciclo con éxito, ejecute la higiene de la Fase 7
    y escriba el estado "completado" de forma no bloqueante sin congelar el Event Loop.
    """
    # 1. Configurar variables de entorno obligatorias (DATA_DIR aísla automáticamente QuipuSettings)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NESTJS_API_URL", "http://localhost:3000/api")
    monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "mock_folder_id_123")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyMockKey_123456789")
    
    # Inicialización limpia respetando las propiedades inmutables de solo lectura
    settings = QuipuSettings()
    
    # Forzar la creación física de los subdirectorios autocalculados en la sandbox del test
    settings.output_json_dir.mkdir(parents=True, exist_ok=True)
    settings.staged_dir.mkdir(parents=True, exist_ok=True)

    global_id = "EXP-2026-TEST-01"

    # Crear archivos dummy de entrada en la caché volátil del test
    cej_path = str(tmp_path / "cej.json")
    remaju_path = str(tmp_path / "remaju.pdf")
    sunarp_path = str(tmp_path / "sunarp.pdf")
    Path(cej_path).write_text("{}", encoding="utf-8")
    Path(remaju_path).write_text("pdf_content", encoding="utf-8")
    Path(sunarp_path).write_text("pdf_content", encoding="utf-8")

    # Simular archivo temporal físico de Chasky que debe ser purgado en la Fase 7 (Higiene)
    temp_chasky = settings.output_json_dir / f"temp_{global_id}.json"
    chasky_payload = {
        "informacion_cej": {"records": []},
        "informacion_remaju": {"sections": []},
        "informacion_sunarp": {"sections": []}
    }
    temp_chasky.write_text(json.dumps(chasky_payload), encoding="utf-8")

    # Simular archivo Markdown residual en staged_dir
    staged_md = settings.staged_dir / f"doc_{global_id}_page1.md"
    staged_md.write_text("# Markdown residuo", encoding="utf-8")

    # 2. ALINEACIÓN DE MOCKS: Sincronización fiel con las firmas reales
    mock_chasky_instance = mock_chasky_cls.return_value
    mock_chasky_instance.build_master_expediente = MagicMock()

    mock_drive_instance = mock_drive_cls.return_value
    mock_drive_instance.upload_legajo = MagicMock(return_value="https://google.com")

    # Simular que master_builder escribe el JSON físico final y retorna su objeto Path
    fake_master_path = settings.output_json_dir / f"exp_{global_id}.json"
    fake_master_path.write_text('{"id_expediente_global": "EXP-2026-TEST-01"}', encoding="utf-8")
    
    mock_master_instance = mock_master_cls.return_value
    mock_master_instance.assemble_and_save = MagicMock(return_value=fake_master_path)

    # El cliente de NestJS es asincrónico no bloqueante en red
    mock_nestjs_instance = mock_nestjs_cls.return_value
    mock_nestjs_instance.send_expediente = AsyncMock(return_value=True)

    # 3. Instanciar y ejecutar el orquestador real
    orchestrator = PipelineOrchestrator(settings)
    
    # Parchear preventivamente la inicialización del DTO de Pydantic v2 para simplificar la aserción unitaria
    with patch("dantesito.quipu.workflows.pipeline_orchestrator.CreateExpedienteDto") as mock_dto_cls:
        mock_dto_cls.return_value = MagicMock()
        success = await orchestrator.run_full_cycle(global_id, cej_path, remaju_path, sunarp_path)

    assert success is True, "El orquestador debió retornar True ante una sincronización NestJS exitosa."

    # 4. Validaciones de la Fase 7 (Higiene y Estado de Cierre)
    assert not temp_chasky.exists(), "El archivo temporal intermedio de Chasky debió ser purgado asíncronamente."
    assert not staged_md.exists(), "El archivo Markdown residual debió ser eliminado de staged_dir."

    status_file = settings.output_json_dir / f"status_{global_id}.json"
    assert status_file.exists(), "El archivo de estado físico final debe existir en el disco duro."

    status_data = json.loads(status_file.read_text(encoding="utf-8"))
    assert status_data["status"] == "completado"
    assert "Fase 7" in status_data["fase_actual"]


@pytest.mark.anyio
@patch("dantesito.quipu.workflows.pipeline_orchestrator.ChaskyConsolidator")
@patch("dantesito.quipu.workflows.pipeline_orchestrator.MasterBuilder")
@patch("dantesito.quipu.workflows.pipeline_orchestrator.GoogleDrivePublisher")
@patch("dantesito.quipu.workflows.pipeline_orchestrator.NestJSClient")
async def test_run_full_cycle_critical_failure_status(
    mock_nestjs_cls,
    mock_drive_cls,
    mock_master_cls,
    mock_chasky_cls,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verifica que ante una excepción crítica en el pipeline, se capture el error,
    se escriba el estado "error" en disco y se ejecute la limpieza en el bloque finally.
    """
    # 1. Configurar entorno y settings obligatorios (Propiedades autocalculadas inmutables)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NESTJS_API_URL", "http://localhost:3000/api")
    monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "mock_folder_id_123")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyMockKey_123456789")
    
    settings = QuipuSettings()
    settings.output_json_dir.mkdir(parents=True, exist_ok=True)

    global_id = "EXP-2026-FAIL-02"

    cej_path = str(tmp_path / "cej.json")
    remaju_path = str(tmp_path / "remaju.pdf")
    sunarp_path = str(tmp_path / "sunarp.pdf")

    # 2. BLINDAJE DE SEGURIDAD: Parchear el resto de componentes para evitar llamadas a la nube real
    mock_drive_instance = mock_drive_cls.return_value
    mock_drive_instance.upload_legajo = MagicMock(return_value="https://google.com")
    
    mock_master_instance = mock_master_cls.return_value
    mock_master_instance.assemble_and_save = MagicMock()

    # Forzar excepción física síncrona controlada en Chasky Core para gatillar la resiliencia
    mock_chasky_instance = mock_chasky_cls.return_value
    mock_chasky_instance.build_master_expediente = MagicMock(side_effect=RuntimeError("Fallo crítico de extracción"))

    # 3. Ejecutar el orquestador
    orchestrator = PipelineOrchestrator(settings)
    success = await orchestrator.run_full_cycle(global_id, cej_path, remaju_path, sunarp_path)

    assert success is False, "El orquestador debe capturar el error de forma segura y retornar False."

    # 4. Validar que el archivo de estado perimetral registre el error crítico para el celular
    status_file = settings.output_json_dir / f"status_{global_id}.json"
    assert status_file.exists(), "El archivo de estado de error debe persistir en disco."

    status_data = json.loads(status_file.read_text(encoding="utf-8"))
    assert status_data["status"] == "error"
    assert "Fallo crítico de extracción" in status_data["fase_actual"]
