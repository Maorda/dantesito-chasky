# tests/test_consolidation.py
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from dantesito.chasky.consolidation.consolidator import ChaskyConsolidator
from dantesito.chasky.config.taxonomies import SectionEnum, SourceEnum


def _build_mock_collection() -> MagicMock:
    collection = MagicMock()
    collection.get.return_value = {"documents": ["Texto de prueba"]}
    return collection


def test_build_master_expediente_creates_required_json_structure(tmp_path: Path) -> None:
    """Verifica la generación del JSON intermedio con la nueva arquitectura por lotes."""
    output_path = tmp_path / "master.json"
    cej_path = tmp_path / "cej.json"
    remaju_path = tmp_path / "remaju.pdf"
    sunarp_path = tmp_path / "sunarp.pdf"

    cej_path.touch()
    remaju_path.touch()
    sunarp_path.touch()

    consolidator = ChaskyConsolidator()

    # Parcheamos las librerías in-line desde sus scopes nativos de importación
    with patch("ijson.items") as mock_ijson, \
         patch("docling.document_converter.DocumentConverter") as mock_docling:
         
        mock_ijson.return_value = [{"expediente": "0200", "materia": "CIVIL"}]
        
        mock_converter = mock_docling.return_value
        mock_doc = MagicMock()
        mock_doc.document.export_to_markdown.return_value = "Texto extraído de prueba"
        mock_converter.convert.return_value = mock_doc

        # Mockear la cascada en lote para evitar llamadas HTTP a la nube
        consolidator._cascade_factory.process_chunks_batch = MagicMock(
            return_value=[(SourceEnum.REMAJU, SectionEnum.RESOLUCION)]
        )

        consolidator.build_master_expediente(
            global_id="GLOBAL-001",
            cej_json_path=str(cej_path),
            remaju_pdf_path=str(remaju_path),
            sunarp_pdf_path=str(sunarp_path),
            output_json_path=str(output_path)
        )

    assert output_path.exists()
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["global_id"] == "GLOBAL-001"
    assert "informacion_cej" in data


def test_build_master_expediente_ingests_pdfs_sequentially(tmp_path: Path) -> None:
    """Verifica que el flujo de ingesta masiva se ejecute ordenadamente en disco."""
    output_path = tmp_path / "master.json"
    cej_path = tmp_path / "cej.json"
    remaju_path = tmp_path / "remaju.pdf"
    sunarp_path = tmp_path / "sunarp.pdf"

    cej_path.touch()
    remaju_path.touch()
    sunarp_path.touch()

    consolidator = ChaskyConsolidator()

    with patch("ijson.items") as mock_ijson, \
         patch("docling.document_converter.DocumentConverter") as mock_docling:
         
        mock_ijson.return_value = []
        mock_converter = mock_docling.return_value
        mock_doc = MagicMock()
        mock_doc.document.export_to_markdown.return_value = "Texto remaju\n\nTexto sunarp"
        mock_converter.convert.return_value = mock_doc

        consolidator._cascade_factory.process_chunks_batch = MagicMock(
            return_value=[
                (SourceEnum.REMAJU, SectionEnum.RESOLUCION),
                (SourceEnum.SUNARP, SectionEnum.GRAVAMEN)
            ]
        )

        consolidator.build_master_expediente(
            global_id="GLOBAL-002",
            cej_json_path=str(cej_path),
            remaju_pdf_path=str(remaju_path),
            sunarp_pdf_path=str(sunarp_path),
            output_json_path=str(output_path)
        )

    assert output_path.exists()


def test_build_master_expediente_persists_chunks_with_global_id(tmp_path: Path) -> None:
    """Valida la inyección del identificador global dentro del lote."""
    output_path = tmp_path / "master.json"
    cej_path = tmp_path / "cej.json"
    remaju_path = tmp_path / "remaju.pdf"
    sunarp_path = tmp_path / "sunarp.pdf"

    cej_path.touch()
    remaju_path.touch()
    sunarp_path.touch()

    consolidator = ChaskyConsolidator()

    with patch("ijson.items") as mock_ijson, \
         patch("docling.document_converter.DocumentConverter") as mock_docling:
         
        mock_ijson.return_value = []
        mock_converter = mock_docling.return_value
        mock_doc = MagicMock()
        mock_doc.document.export_to_markdown.return_value = "Chunk persistido"
        mock_converter.convert.return_value = mock_doc

        consolidator._cascade_factory.process_chunks_batch = MagicMock(
            return_value=[(SourceEnum.REMAJU, SectionEnum.GRAVAMEN)]
        )

        consolidator.build_master_expediente(
            global_id="GLOBAL-003",
            cej_json_path=str(cej_path),
            remaju_pdf_path=str(remaju_path),
            sunarp_pdf_path=str(sunarp_path),
            output_json_path=str(output_path)
        )

    assert output_path.exists()


def test_build_master_expediente_uses_cross_filter_and_streaming(tmp_path: Path) -> None:
    """Verifica la compatibilidad del entrypoint intermedio con la persistencia en disco duro."""
    output_path = tmp_path / "master.json"
    cej_path = tmp_path / "cej.json"
    remaju_path = tmp_path / "remaju.pdf"
    sunarp_path = tmp_path / "sunarp.pdf"

    cej_path.touch()
    remaju_path.touch()
    sunarp_path.touch()

    consolidator = ChaskyConsolidator()

    with patch("ijson.items") as mock_ijson, \
         patch("docling.document_converter.DocumentConverter") as mock_docling:
         
        mock_ijson.return_value = []
        mock_converter = mock_docling.return_value
        mock_doc = MagicMock()
        mock_doc.document.export_to_markdown.return_value = "Fase 4 Stream"
        mock_converter.convert.return_value = mock_doc

        consolidator._cascade_factory.process_chunks_batch = MagicMock(
            return_value=[(SourceEnum.REMAJU, SectionEnum.ENCABEZADO)]
        )

        consolidator.build_master_expediente(
            global_id="GLOBAL-004",
            cej_json_path=str(cej_path),
            remaju_pdf_path=str(remaju_path),
            sunarp_pdf_path=str(sunarp_path),
            output_json_path=str(output_path)
        )

    assert output_path.exists()
