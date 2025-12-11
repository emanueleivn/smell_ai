import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Union, Optional
import sys

import pandas as pd
import pytest

# Base directory che contiene le cartelle TC_01 .. TC_20
BASE_DIR = Path(__file__).resolve().parent
TestConfig = Dict[str, Union[str, bool, int, List[str]]]


TEST_CASES: Dict[str, TestConfig] = {
    # ================== ERROR CASES (TC_01..TC_05) ==================

    # TC_01
    # NF1, EF0, NP1, SP1, NCS0, TCS0, ME2, EP2, NW0, RES2, OUT1
    # Oracolo: il tool segnala che non ci sono file in input da analizzare
    #          e non esegue alcuna analisi.
    "TC_01": {
        "description": "Assenza di file di input: nessuna analisi, errore segnalato.",
        "expected_error": True,
        "expected_smells": None,
        "parallel": False,   # EP2
        "max_walkers": 5,    # ignorato perché parallel=False
        "resume": False,     # RES2
        "multiple": False,   # NP1
    },

    # TC_02
    # NF2, EF1, NP1, SP3, NCS0, TCS0, ME2, EP2, NW0, RES2, OUT1
    # Oracolo: errore sulla struttura del progetto, sottocartelle inaccessibili.
    "TC_02": {
        "description": "Struttura del progetto con sottocartelle inaccessibili: errore segnalato.",
        "expected_error": True,
        "expected_smells": None,
        "parallel": False,   # EP2
        "max_walkers": 5,
        "resume": False,     # RES2
        "multiple": False,   # NP1
        # Path (relativo a tc_path) che rappresenta la sottocartella da rendere inaccessibile.
        # Adatta questo nome in base alla struttura reale della cartella TC_02.
        "unreadable_paths": ["MockDirectoryNotAccessible"],
    },

    # TC_03
    # NF2, EF1, NP1, SP1, NCS0, TCS0, ME2, EP1, NW1, RES2, OUT1
    # Oracolo: numero di walkers non valido (<=0), nessuna analisi.
    "TC_03": {
        "description": "Numero di walkers non valido (<=0) con parallelismo attivo: errore.",
        "expected_error": True,
        "expected_smells": None,
        "parallel": True,    # EP1
        "max_walkers": 0,    # NW1 (<=0) -> errore
        "resume": False,     # RES2
        "multiple": False,   # NP1
    },

    # TC_04
    # NF2, EF1, NP1, SP1, NCS0, TCS0, ME2, EP2, NW0, RES2, OUT2
    # Oracolo: percorso di output mancante o non accessibile.
    "TC_04": {
        "description": "Percorso di output non accessibile: errore.",
        "expected_error": True,
        "expected_smells": None,
        "parallel": False,   # EP2
        "max_walkers": 5,
        "resume": False,     # RES2
        "multiple": False,   # NP1
        # flag speciale per rendere inaccessibile la cartella di output generata
        "lock_output": True,
    },

    # TC_05
    # NF2, EF2, NP1, SP1, NCS0, TCS0, ME2, EP2, NW0, RES2, OUT1
    # Oracolo: nessun file .py, il tool segnala l’errore e non analizza.
    "TC_05": {
        "description": "Nessun file Python da analizzare: errore e nessuna analisi.",
        "expected_error": True,
        "expected_smells": None,
        "parallel": False,   # EP2
        "max_walkers": 5,
        "resume": False,     # RES2
        "multiple": False,   # NP1
    },

    # ================== SUCCESS CASES – NCS = 0 (TC_06..TC_08) ==================

    # TC_06
    # NF3, EF1, NP1, SP1, NCS1 (0 smells), TCS0, ME2, EP2, NW0, RES2, OUT1
    # Oracolo: singolo progetto, nessun code smell.
    "TC_06": {
        "description": "Analisi singolo progetto, nessun code smell.",
        "expected_error": False,
        "expected_smells": 0,  # NCS1 -> 0 smell
        "parallel": False,     # EP2
        "max_walkers": 5,
        "resume": False,       # RES2
        "multiple": False,     # NP1
    },

    # TC_07
    # NF3, EF1, NP2, SP1, NCS1 (0 smells), TCS0, ME2, EP2, NW0, RES2, OUT1
    # Oracolo: multi progetto, nessun code smell.
    "TC_07": {
        "description": "Analisi multi-progetto, nessun code smell.",
        "expected_error": False,
        "expected_smells": 0,
        "parallel": False,     # EP2
        "max_walkers": 5,
        "resume": False,       # RES2
        "multiple": True,      # NP2
    },

    # TC_08
    # NF3, EF1, NP1, SP2, NCS1 (0 smells), TCS0, ME2, EP2, NW0, RES2, OUT1
    # Oracolo: progetto singolo, struttura annidata, nessun code smell.
    "TC_08": {
        "description": "Analisi singolo progetto annidato, nessun code smell.",
        "expected_error": False,
        "expected_smells": 0,
        "parallel": False,     # EP2
        "max_walkers": 5,
        "resume": False,       # RES2
        "multiple": False,     # NP1
    },

    # ================== SUCCESS CASES – SMELL PRESENTI (TC_09..TC_16) ==================

    # TC_09
    # NF2, EF1, NP1, SP1, NCS2 (1 smell), TCS1 (generico),
    # ME2, EP2, NW0, RES1, OUT1
    "TC_09": {
        "description": "Analisi singolo progetto: 1 code smell generico.",
        "expected_error": False,
        "expected_smells": 1,
        "parallel": False,     # EP2
        "max_walkers": 5,
        "resume": True,        # RES1
        "multiple": False,     # NP1
    },

    # TC_10
    # NF2, EF1, NP1, SP1, NCS2 (1 smell), TCS2 (API-specific),
    # ME2, EP2, NW0, RES1, OUT1
    "TC_10": {
        "description": "Analisi singolo progetto: 1 code smell API-specific.",
        "expected_error": False,
        "expected_smells": 1,
        "parallel": False,     # EP2
        "max_walkers": 5,
        "resume": True,        # RES1
        "multiple": False,     # NP1
    },

    # TC_11
    # NF2, EF1, NP1, SP1, NCS3 (>1), TCS1 (generici),
    # ME2, EP2, NW0, RES1, OUT1
    "TC_11": {
        "description": "Analisi singolo progetto: >1 code smell generico.",
        "expected_error": False,
        "expected_smells": ">=2",  # NCS3 -> >1 smell
        "parallel": False,         # EP2
        "max_walkers": 5,
        "resume": True,            # RES1
        "multiple": False,         # NP1
    },

    # TC_12
    # NF2, EF1, NP1, SP1, NCS3 (>1), TCS2 (API-specific),
    # ME2, EP2, NW0, RES1, OUT1
    "TC_12": {
        "description": "Analisi singolo progetto: >1 code smell API-specific.",
        "expected_error": False,
        "expected_smells": ">=2",
        "parallel": False,         # EP2
        "max_walkers": 5,
        "resume": True,            # RES1
        "multiple": False,         # NP1
    },

    # TC_13
    # NF2, EF1, NP1, SP1, NCS3 (>1), TCS3 (misto),
    # ME2, EP2, NW0, RES1, OUT1
    "TC_13": {
        "description": "Analisi singolo progetto: >1 code smell misto.",
        "expected_error": False,
        "expected_smells": ">=2",
        "parallel": False,         # EP2
        "max_walkers": 5,
        "resume": True,            # RES1
        "multiple": False,         # NP1
    },

    # TC_14
    # NF2, EF1, NP1, SP1, NCS2 (1 smell), TCS1,
    # ME2, EP1, NW2 (<5), RES1, OUT1
    "TC_14": {
        "description": "Analisi parallela: 1 code smell generico, walkers < 5.",
        "expected_error": False,
        "expected_smells": 1,
        "parallel": True,          # EP1
        "max_walkers": 3,          # NW2 -> <5
        "resume": True,            # RES1
        "multiple": False,         # NP1
    },

    # TC_15
    # NF2, EF1, NP1, SP1, NCS2 (1 smell), TCS1,
    # ME2, EP1, NW3 (=5), RES1, OUT1
    "TC_15": {
        "description": "Analisi parallela: 1 code smell generico, walkers = 5.",
        "expected_error": False,
        "expected_smells": 1,
        "parallel": True,          # EP1
        "max_walkers": 5,          # NW3 -> =5
        "resume": True,            # RES1
        "multiple": False,         # NP1
    },

    # TC_16
    # NF2, EF1, NP1, SP1, NCS2 (1 smell), TCS1,
    # ME2, EP1, NW4 (>5), RES1, OUT1
    "TC_16": {
        "description": "Analisi parallela: 1 code smell generico, walkers > 5.",
        "expected_error": False,
        "expected_smells": 1,
        "parallel": True,          # EP1
        "max_walkers": 6,          # NW4 -> >5
        "resume": True,            # RES1
        "multiple": False,         # NP1
    },
}


def make_unreadable(path: Path) -> Optional[int]:
    """
    Rende il path non leggibile/non scrivibile.
    Restituisce il mode originale, così da poterlo ripristinare.
    Se il path non esiste, restituisce None.
    """
    if not path.exists():
        return None
    current_mode = path.stat().st_mode
    path.chmod(0)
    return current_mode


def make_readable(path: Path, mode: Optional[int]) -> None:
    """
    Ripristina i permessi originali se mode è valorizzato.
    """
    if mode is None:
        return
    if path.exists():
        path.chmod(mode)


def list_test_cases() -> List[str]:
    """
    Elenca le directory TC_01..TC_16 in BASE_DIR, ordinate numericamente.
    """
    cases: List[str] = []
    if not BASE_DIR.exists():
        return cases

    for entry in BASE_DIR.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        if not name.startswith("TC_"):
            continue
        try:
            number = int(name.split("_")[-1])
        except ValueError:
            continue
        if 1 <= number <= 16:
            cases.append(name)

    cases.sort(key=lambda x: int(x.split("_")[-1]))
    return cases


@pytest.mark.parametrize("tc_dir", list_test_cases())
def test_system_case(tc_dir: str) -> None:
    """
    Esegue il test di sistema per la cartella tc_dir (es. 'TC_02'),
    configurando parametri e oracolo secondo il documento di system testing.
    """
    tc_path = BASE_DIR / tc_dir
    config = TEST_CASES[tc_dir]

    # 1) Preparazione cartella di output DEDICATA PER TC
    output_dir = BASE_DIR / "output" / tc_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # 2) Gestione permessi non leggibili (OUT2 o SP3)
    locked_paths: List[tuple[Path, Optional[int]]] = []

    # Caso OUT2: output non accessibile
    if config.get("lock_output"):
        original_mode = make_unreadable(output_dir)
        locked_paths.append((output_dir, original_mode))

    # Caso SP3: sottocartelle inaccessibili
    for relative in config.get("unreadable_paths", []):
        target = tc_path / relative
        original_mode = make_unreadable(target)
        locked_paths.append((target, original_mode))

    # 3) Costruzione del comando CLI

    cmd: List[str] = [
        sys.executable,
        "-m",
        "cli.cli_runner",
        "--input",
        str(tc_path),
        "--output",
        str(output_dir),
    ]

    if config.get("parallel"):
        cmd.append("--parallel")
        cmd.extend(["--max_walkers", str(config.get("max_walkers", 5))])

    if config.get("resume"):
        cmd.append("--resume")

    if config.get("multiple"):
        cmd.append("--multiple")

    # Esecuzione dal root del repository (adatta se necessario)
    repo_root = Path(__file__).resolve().parents[2]
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=repo_root,
        env=env,
    )

    # 4) Ripristino permessi
    for path_obj, mode in locked_paths:
        make_readable(path_obj, mode)

    # 5) Verifica oracolo: exit code
    if config["expected_error"]:
        assert completed.returncode != 0, (
            f"{tc_dir} doveva fallire, ma exit code = 0.\n"
            f"Stderr:\n{completed.stderr}"
        )
        # In caso di errore non ci aspettiamo report significativi
        return

    # Caso senza errore
    assert completed.returncode == 0, (
        f"{tc_dir} doveva completarsi con successo, ma exit code = {completed.returncode}.\n"
        f"Stderr:\n{completed.stderr}"
    )

    # 6) Verifica oracolo: numero di smell tramite overview.csv UNICO
    overview = output_dir / "overview.csv"
    expected_smells = config.get("expected_smells")

    # expected_smells = None => nessun report di smell previsto
    if expected_smells is None:
        if overview.exists():
            df = pd.read_csv(overview)
            assert df.empty, (
                f"{tc_dir}: non erano attesi report di smell, ma overview.csv contiene "
                f"{len(df)} righe."
            )
        return

    # expected_smells = 0 => o nessun file o file vuoto
    if not overview.exists():
        # Acceptable only if we ci aspettiamo 0 smell
        assert expected_smells == 0, (
            f"{tc_dir}: attesi {expected_smells} smell, ma overview.csv è assente."
        )
        return

    df = pd.read_csv(overview)
    smell_count = len(df)

    if expected_smells == 0:
        assert smell_count == 0, (
            f"{tc_dir}: attesi 0 smell, trovati {smell_count}."
        )
    elif expected_smells == ">=2":
        assert smell_count >= 2, (
            f"{tc_dir}: attesi almeno 2 smell, trovati {smell_count}."
        )
    else:
        # expected_smells è un intero > 0
        assert smell_count == expected_smells, (
            f"{tc_dir}: attesi {expected_smells} smell, trovati {smell_count}."
        )


# Dipendenze non standard:
# - pytest
# - pandas
