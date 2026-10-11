import os
import sys
import traceback
from datetime import datetime
from pathlib import Path


def smoke_test() -> None:
    """Comprueba que las dependencias esenciales están incluidas en el paquete."""
    import sqlite3
    import tkinter
    import customtkinter
    import openpyxl
    import reportlab
    import xlrd

    from open_chess.database import Database
    from open_chess.excel_import import read_student_rows
    from open_chess.reports import standings_pdf
    from open_chess.swiss import generate_pairings

    assert sqlite3.sqlite_version
    assert tkinter.TkVersion
    assert customtkinter.__version__
    assert reportlab.Version
    assert openpyxl.__version__
    assert xlrd.__version__
    assert Database and read_student_rows and standings_pdf and generate_pairings


if "--smoke-test" in sys.argv:
    smoke_test()
    raise SystemExit(0)


from open_chess.app import main


def report_startup_error() -> Path:
    """Guarda los errores de inicio cuando la aplicación no tiene consola visible."""
    if sys.platform == "darwin":
        log_dir = Path.home() / "Library" / "Logs" / "OpenChess"
    elif sys.platform == "win32":
        log_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "OpenChess"
    else:
        log_dir = Path.home() / ".open_chess"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "inicio-error.log"
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n--- {datetime.now().isoformat(timespec='seconds')} ---\n")
        traceback.print_exc(file=log)
    return log_path


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_path = report_startup_error()
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "Open Chess no pudo iniciarse",
                f"Se ha guardado información del error en:\n{log_path}",
            )
        except Exception:
            pass
        raise
