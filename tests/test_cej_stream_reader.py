# tests/test_cej_stream_reader.py
import os
import io
import pytest
from pathlib import Path
from typing import List, Tuple

from dantesito.chasky.config.taxonomies import SectionEnum
from dantesito.chasky.ingestion.cej_stream_reader import CEJStreamReader


@pytest.fixture
def valid_cej_json_content() -> str:
    """Retorna una cadena JSON válida representativa de CEJ."""
    return """{
    "encabezado": {
        "numero_expediente": "00123-2023-0-1801-JR-CI-01",
        "juzgado": "1° JUZGADO CIVIL DE LIMA",
        "materia": "OBLIGACION DE DAR SUMA DE DINERO",
        "estado": "EN TRAMITE"
    },
    "partes": [
        {
            "rol": "Demandante",
            "nombre": "BANCO X S.A.A.",
            "tipo_documento": "RUC",
            "numero_documento": "20100000001"
        },
        {
            "rol": "Demandado",
            "nombre": "JUAN PEREZ ALVAREZ",
            "tipo_documento": "DNI",
            "numero_documento": "40506070"
        }
    ],
    "resoluciones": [
        {
            "fecha": "10/01/2023 10:00",
            "tipo": "AUTO ADMISORIO",
            "sumilla": "SE ADMITE A TRAMITE LA DEMANDA EN VIA EXECUTIVA"
        },
        {
            "fecha": "15/02/2023 12:30",
            "tipo": "NOTIFICACION",
            "sumilla": "SE NOTIFICA A LA PARTE DEMANDADA"
        }
    ]
}"""


def test_stream_and_flatten_valid_json(tmp_path: Path, valid_cej_json_content: str) -> None:
    """Verifica que un archivo JSON válido de CEJ sea procesado correctamente

    mediante el generador y mapeado a las secciones esperadas.
    """
    json_file = tmp_path / "expediente_test.json"
    json_file.write_text(valid_cej_json_content, encoding="utf-8")

    reader = CEJStreamReader()
    results: List[Tuple[SectionEnum, str]] = list(reader.stream_and_flatten(json_file))

    assert len(results) == 5

    # 1. Verificar Encabezado
    sec_encabezado, text_encabezado = results[0]
    assert sec_encabezado == SectionEnum.ENCABEZADO
    assert "NUMERO EXPEDIENTE: 00123-2023-0-1801-JR-CI-01" in text_encabezado
    assert "JUZGADO: 1° JUZGADO CIVIL DE LIMA" in text_encabezado
    assert "MATERIA: OBLIGACION DE DAR SUMA DE DINERO" in text_encabezado

    # 2. Verificar Partes
    sec_parte1, text_parte1 = results[1]
    assert sec_parte1 == SectionEnum.PARTES
    assert text_parte1 == "ROL: Demandante | NOMBRE: BANCO X S.A.A. | RUC: 20100000001"

    sec_parte2, text_parte2 = results[2]
    assert sec_parte2 == SectionEnum.PARTES
    assert text_parte2 == "ROL: Demandado | NOMBRE: JUAN PEREZ ALVAREZ | DNI: 40506070"

    # 3. Verificar Resoluciones
    sec_res1, text_res1 = results[3]
    assert sec_res1 == SectionEnum.RESOLUCION
    assert text_res1 == "FECHA: 10/01/2023 10:00 | TIPO: AUTO ADMISORIO | SUMILLA: SE ADMITE A TRAMITE LA DEMANDA EN VIA EXECUTIVA"

    sec_res2, text_res2 = results[4]
    assert sec_res2 == SectionEnum.RESOLUCION
    assert text_res2 == "FECHA: 15/02/2023 12:30 | TIPO: NOTIFICACION | SUMILLA: SE NOTIFICA A LA PARTE DEMANDADA"


def test_stream_and_flatten_file_not_found() -> None:
    """Valida que se lance FileNotFoundError si la ruta dada no existe."""
    reader = CEJStreamReader()
    non_existent_path = "ruta/inexistente/expediente.json"

    with pytest.raises(FileNotFoundError) as exc_info:
        list(reader.stream_and_flatten(non_existent_path))

    # SOLUCIÓN DE RUTAS MULTIPLATAFORMA: Normalizamos ambas cadenas
    assert os.path.normpath(non_existent_path) in os.path.normpath(str(exc_info.value))


def test_stream_and_flatten_corrupted_json(tmp_path: Path) -> None:
    """Valida que se lance ValueError al intentar procesar un archivo JSON malformado."""
    corrupted_json_file = tmp_path / "corrupted.json"
    corrupted_json_file.write_text("{ 'encabezado': { invalid_json ", encoding="utf-8")

    reader = CEJStreamReader()

    with pytest.raises(ValueError) as exc_info:
        list(reader.stream_and_flatten(corrupted_json_file))

    assert "corrupto o es inválido" in str(exc_info.value)