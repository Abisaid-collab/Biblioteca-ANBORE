import shutil
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ))  # Permite "import dominio" desde las pruebas.

from dominio import ServicioBiblioteca  # noqa: E402


@pytest.fixture
def ruta_datos(tmp_path):
    """Copia de datos.json en una carpeta temporal: las pruebas nunca tocan el original."""
    copia = tmp_path / "datos.json"
    shutil.copy(RAIZ / "datos.json", copia)
    return copia


@pytest.fixture
def servicio(ruta_datos):
    return ServicioBiblioteca(ruta_datos)
