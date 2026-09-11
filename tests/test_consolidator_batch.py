# tests/chasky/test_consolidator_batch.py
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dantesito.chasky.config.taxonomies import SectionEnum, SourceEnum
from dantesito.chasky.consolidation.consolidator import ChaskyConsolidator


def test_build_master_expediente_success(tmp_path: Path) -> None:
    """
    Simula el pipeline completo por lotes (Batching) asegurando que se escriba
    el JSON intermedio en disco temporal con las claves exactas.
    """
    cej_path = tmp_path / "cej_0200.json"
    remaju_path = tmp_path / "remaju_0200.pdf"
    sunarp_path = tmp_path / "sunarp_0200.pdf"
    output_path = tmp_path / "output_0200.json"

    cej_path.touch()
    remaju_path.touch()
    sunarp_path.touch()

    consolidator = ChaskyConsolidator()

    with patch("ijson.items") as mock_ijson_items:
        mock_ijson_items.return_value = [{"expediente": "0200-jp", "materia": "CIVIL"}]
        
        with patch("docling.document_converter.DocumentConverter") as mock_converter_class:
            mock_converter_instance = mock_converter_class.return_value
            mock_doc_result = MagicMock()
            mock_doc_result.document.export_to_markdown.return_value = "Párrafo 1\n\nPárrafo 2"
            mock_converter_instance.convert.return_value = mock_doc_result
            
            consolidator._cascade_factory.process_chunks_batch = MagicMock(
                return_value=[
                    (SourceEnum.REMAJU, SectionEnum.ENCABEZADO),
                    (SourceEnum.SUNARP, SectionEnum.PARTES),
                ]
            )

            consolidator.build_master_expediente(
                global_id="0200-jp",
                cej_json_path=str(cej_path),
                remaju_pdf_path=str(remaju_path),
                sunarp_pdf_path=str(sunarp_path),
                output_json_path=str(output_path),
            )

    assert output_path.exists(), "El archivo maestro temporal no fue generado."
    
    with open(output_path, "r", encoding="utf-8") as f:
        master_data = json.load(f)

    assert master_data["global_id"] == "0200-jp"
    assert "informacion_cej" in master_data
    assert master_data["informacion_cej"]["records"][0]["materia"] == "CIVIL"
    assert "informacion_remaju" in master_data
    assert master_data["informacion_remaju"]["file"] == "remaju_0200.pdf"
    assert len(master_data["informacion_remaju"]["sections"]) == 2
    assert "informacion_sunarp" in master_data
    assert master_data["informacion_sunarp"]["file"] == "sunarp_0200.pdf"
    assert len(master_data["informacion_sunarp"]["sections"]) == 2


def test_ingest_pdf_batch_empty_or_missing(tmp_path: Path) -> None:
    """
    Asegura la resiliencia del sistema ante la ausencia física de archivos
    o extracción nula de texto por parte de Docling.
    """
    consolidator = ChaskyConsolidator()
    
    missing_pdf_path = tmp_path / "pdf_fantasma.pdf"
    result_missing = consolidator._ingest_pdf_batch(missing_pdf_path, SourceEnum.SUNARP)
    assert result_missing == {}, "Debe retornar diccionario vacío si el PDF no existe."

    empty_pdf_path = tmp_path / "pdf_vacio_sin_texto.pdf"
    empty_pdf_path.touch()

    with patch("docling.document_converter.DocumentConverter") as mock_converter_class:
        mock_converter_instance = mock_converter_class.return_value
        mock_doc_result = MagicMock()
        mock_doc_result.document.export_to_markdown.return_value = ""
        mock_converter_instance.convert.return_value = mock_doc_result
        
        result_empty = consolidator._ingest_pdf_batch(empty_pdf_path, SourceEnum.REMAJU)
        
        assert result_empty["file"] == "pdf_vacio_sin_texto.pdf"
        assert result_empty["sections"] == [], "Debe retornar una lista de secciones vacía."


def test_taxonomic_integrity(tmp_path: Path) -> None:
    """
    Verifica que las estructuras resultantes en el archivo inyecten los strings
    correctos mapeados desde los enums y que la lógica de arrastre de contexto funcione.
    """
    consolidator = ChaskyConsolidator()
    pdf_path = tmp_path / "documento_taxonomico.pdf"
    pdf_path.touch()

    with patch("docling.document_converter.DocumentConverter") as mock_converter_class:
        mock_converter_instance = mock_converter_class.return_value
        mock_doc_result = MagicMock()
        mock_doc_result.document.export_to_markdown.return_value = "Bloque 1\n\nBloque 2\n\nBloque 3"
        mock_converter_instance.convert.return_value = mock_doc_result
        
        consolidator._cascade_factory.process_chunks_batch = MagicMock(
            return_value=[
                (SourceEnum.SUNARP, SectionEnum.GRAVAMEN),
                (SourceEnum.REMAJU, SectionEnum.RESOLUCION),
                (None, SectionEnum.GRAVAMEN),
            ]
        )

        resultado = consolidator._ingest_pdf_batch(pdf_path, SourceEnum.SUNARP)

    sections = resultado.get("sections", [])
    assert len(sections) == 3, "Deben haberse procesado exactamente 3 fragmentos."

    assert sections[0]["chunk"] == "Bloque 1"
    assert sections[0]["source"] == "sunarp"
    assert sections[0]["section"] == "gravamen"

    assert sections[1]["chunk"] == "Bloque 2"
    assert sections[1]["source"] == "remaju"
    assert sections[1]["section"] == "resolucion"

    assert sections[2]["chunk"] == "Bloque 3"
    assert sections[2]["section"] == "gravamen"
    assert sections[2]["source"] == "remaju", "El arrastre de contexto taxonómico falló."