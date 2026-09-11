# tests/test_cross_filter.py
from typing import Any, Dict
import pytest
from dantesito.chasky.config.taxonomies import SectionEnum, SourceEnum
from dantesito.chasky.query_engine.cross_filter import CrossQueryFilter

@pytest.fixture
def query_filter() -> CrossQueryFilter:
    return CrossQueryFilter()

def test_generate_where_clause_for_parties(query_filter: CrossQueryFilter) -> None:
    """Valida la sintaxis estrictamente binaria de ChromaDB para la intención de PARTES."""
    result: Dict[str, Any] = query_filter.generate_where_clause(
        "¿Quién es el demandante?",
        "DOC-001",
    )

    # Contrato ChromaDB: $and debe contener exactamente 2 elementos
    assert result == {
        "$and": [
            {"id_documento": "DOC-001"},
            {
                "$or": [
                    {
                        "$and": [
                            {"fuente": SourceEnum.CEJ.value},
                            {"tipo_seccion": SectionEnum.PARTES.value}
                        ]
                    },
                    {
                        "$and": [
                            {"fuente": SourceEnum.REMAJU.value},
                            {"tipo_seccion": SectionEnum.PARTES.value}
                        ]
                    }
                ]
            }
        ]
    }


def test_generate_where_clause_for_encumbrances(query_filter: CrossQueryFilter) -> None:
    """Valida la sintaxis estrictamente binaria de ChromaDB para la intención de GRAVÁMENES."""
    result: Dict[str, Any] = query_filter.generate_where_clause(
        "¿Tiene hipotecas vigentes?",
        "DOC-002",
    )

    assert result == {
        "$and": [
            {"id_documento": "DOC-002"},
            {
                "$or": [
                    {
                        "$and": [
                            {"fuente": SourceEnum.SUNARP.value},
                            {"tipo_seccion": SectionEnum.GRAVAMEN.value}
                        ]
                    },
                    {
                        "$and": [
                            {"fuente": SourceEnum.REMAJU.value},
                            {"tipo_seccion": SectionEnum.GRAVAMEN.value}
                        ]
                    }
                ]
            }
        ]
    }


def test_generate_where_clause_for_property_description(query_filter: CrossQueryFilter) -> None:
    """Valida la sintaxis estrictamente binaria de ChromaDB para la intención de LINDEROS."""
    result: Dict[str, Any] = query_filter.generate_where_clause(
        "¿Cuáles son los linderos del predio?",
        "DOC-003",
    )

    assert result == {
        "$and": [
            {"id_documento": "DOC-003"},
            {
                "$and": [
                    {"fuente": SourceEnum.SUNARP.value},
                    {"tipo_seccion": SectionEnum.RESOLUCION.value}
                ]
            }
        ]
    }


def test_generate_where_clause_for_case_header(query_filter: CrossQueryFilter) -> None:
    """Valida la sintaxis estrictamente binaria de ChromaDB para la intención de JUZGADO."""
    result: Dict[str, Any] = query_filter.generate_where_clause(
        "¿Cuál es el juzgado y número de expediente?",
        "DOC-004",
    )

    assert result == {
        "$and": [
            {"id_documento": "DOC-004"},
            {
                "$and": [
                    {"fuente": SourceEnum.CEJ.value},
                    {"tipo_seccion": SectionEnum.ENCABEZADO.value}
                ]
            }
        ]
    }


@pytest.mark.parametrize(
    "query_text",
    [
        "",
        "   ",
        "¿Qué información contiene este documento?",
        "Explícame el contenido del inmueble.",
    ],
)
def test_generate_where_clause_for_generic_or_empty_query(
    query_filter: CrossQueryFilter,
    query_text: str,
) -> None:
    result: Dict[str, Any] = query_filter.generate_where_clause(
        query_text,
        "DOC-005",
    )
    assert result == {"id_documento": "DOC-005"}


def test_generate_where_clause_for_invalid_query(query_filter: CrossQueryFilter) -> None:
    result: Dict[str, Any] = query_filter.generate_where_clause(
        None,  # type: ignore[arg-type]
        "DOC-006",
    )
    assert result == {"id_documento": "DOC-006"}


@pytest.mark.parametrize(
    ("query_text", "expected_section"),
    [
        ("¿Quién es el ejecutante?", SectionEnum.PARTES),
        ("¿Quién es el demandado?", SectionEnum.PARTES),
        ("¿Existen cargas inscritas?", SectionEnum.GRAVAMEN),
        ("¿Hay algún embargo?", SectionEnum.GRAVAMEN),
        ("¿Cuál es el área del inmueble?", SectionEnum.RESOLUCION),
        ("¿Cuál es la materia del expediente?", SectionEnum.ENCABEZADO),
    ],
)
def test_generate_where_clause_selects_expected_section(
    query_filter: CrossQueryFilter,
    query_text: str,
    expected_section: SectionEnum,
) -> None:
    result: Dict[str, Any] = query_filter.generate_where_clause(
        query_text,
        "DOC-007",
    )
    
    # Verificación genérica y robusta de la presencia del token de sección esperado
    # dentro de la estructura anidada generada
    serialized_clause = str(result)
    assert expected_section.value in serialized_clause
