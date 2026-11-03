"""Sanitização de nomes antes de gravar no banco.

Regras (aulas 15): decodificar entidades HTML, remover pontuação,
colapsar espaços, aparar as pontas e caixa baixa — preservando acentos.
"""

import html
import re


def sanitizar_nome(valor: str) -> str:
    texto = html.unescape(valor)
    texto = texto.replace('\xa0', ' ')
    texto = re.sub(r'[^\w\s-]', ' ', texto, flags=re.UNICODE)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto.lower()
