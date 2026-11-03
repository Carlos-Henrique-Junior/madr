import pytest

from madr.sanitize import sanitizar_nome


@pytest.mark.parametrize(
    ('entrada', 'esperado'),
    [
        ('Machado de Assis', 'machado de assis'),
        (
            'Manuel&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Bandeira',
            'manuel bandeira',
        ),
        (
            'Edgar Alan Poe'
            '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;',
            'edgar alan poe',
        ),
        (
            'Androides Sonham Com Ovelhas Elétricas?',
            'androides sonham com ovelhas elétricas',
        ),
        (
            '&nbsp;&nbsp;breve &nbsp;história &nbsp;do tempo&nbsp;',
            'breve história do tempo',
        ),
        (
            'O mundo assombrado pelos demônios',
            'o mundo assombrado pelos demônios',
        ),
        ('  CAFÉ   com   leite  ', 'café com leite'),
    ],
)
def test_sanitizar_nome(entrada, esperado):
    assert sanitizar_nome(entrada) == esperado
