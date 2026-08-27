"""Teste para o entrypoint do comando de console 'clima'."""

import os
from pathlib import Path
import shutil
import subprocess
import sys


def test_clima_console_script_help():
    # Verifica se o script de console 'clima' está no diretório de binários do venv
    venv_bin = Path(sys.executable).parent
    clima_bin = venv_bin / "clima"
    if not clima_bin.exists():
        clima_bin = shutil.which("clima")

    assert clima_bin is not None and Path(clima_bin).exists(), "O executável 'clima' deve existir no ambiente virtual"

    result = subprocess.run([str(clima_bin), "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Dashboard e CLI de Clima para Capitais Mundiais" in result.stdout
