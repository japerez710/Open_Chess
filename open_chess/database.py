from __future__ import annotations

import json
import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    school_name TEXT NOT NULL DEFAULT 'CEIP Vista Alegre',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    course TEXT NOT NULL DEFAULT '',
    center TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tournament_id, number)
);

CREATE TABLE IF NOT EXISTS pairings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id INTEGER NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    board INTEGER NOT NULL,
    white_id INTEGER NOT NULL REFERENCES players(id),
    black_id INTEGER REFERENCES players(id),
    result TEXT NOT NULL DEFAULT '' CHECK (result IN ('', '1-0', '0-1', '1/2-1/2', 'BYE')),
    UNIQUE (round_id, board)
);

CREATE INDEX IF NOT EXISTS idx_players_tournament ON players(tournament_id);
CREATE INDEX IF NOT EXISTS idx_rounds_tournament ON rounds(tournament_id);
CREATE INDEX IF NOT EXISTS idx_pairings_round ON pairings(round_id);
"""


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        """Aplica cambios pequeños de esquema sin perder campeonatos existentes."""
        columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(tournaments)")}
        if "school_name" not in columns:
            self.connection.execute(
                "ALTER TABLE tournaments ADD COLUMN school_name TEXT NOT NULL DEFAULT 'CEIP Vista Alegre'"
            )
            self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        cursor = self.connection.execute(sql, params)
        self.connection.commit()
        return cursor

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return list(self.connection.execute(sql, params))

    def create_tournament(self, name: str, school_name: str = "CEIP Vista Alegre") -> int:
        name = name.strip()
        school_name = school_name.strip()
        if not name:
            raise ValueError("El grupo debe tener un nombre.")
        if not school_name:
            raise ValueError("El nombre del colegio es obligatorio.")
        active_count = self.connection.execute(
            "SELECT COUNT(*) FROM tournaments WHERE active = 1"
        ).fetchone()[0]
        if active_count >= 15:
            raise ValueError("Ya hay 15 grupos activos. Elimina uno antes de crear otro.")
        return self.execute(
            "INSERT INTO tournaments(name, school_name) VALUES (?, ?)", (name, school_name)
        ).lastrowid

    def list_tournaments(self, include_archived: bool = False) -> list[sqlite3.Row]:
        where = "" if include_archived else "WHERE active = 1"
        return self.query(f"SELECT * FROM tournaments {where} ORDER BY created_at, id")

    def archive_tournament(self, tournament_id: int) -> None:
        self.execute("UPDATE tournaments SET active = 0 WHERE id = ?", (tournament_id,))

    def delete_tournament(self, tournament_id: int) -> None:
        self.execute("DELETE FROM tournaments WHERE id = ?", (tournament_id,))

    def get_tournament(self, tournament_id: int) -> sqlite3.Row:
        row = self.connection.execute(
            "SELECT * FROM tournaments WHERE id = ?", (tournament_id,)
        ).fetchone()
        if row is None:
            raise ValueError("El grupo indicado no existe.")
        return row

    def export_tournament(self, tournament_id: int, path: str | Path) -> Path:
        """Guarda un grupo completo en un archivo JSON portable."""
        tournament = self.get_tournament(tournament_id)
        players = self.list_players(tournament_id, active_only=False)
        rounds = self.query(
            "SELECT * FROM rounds WHERE tournament_id=? ORDER BY number", (tournament_id,)
        )
        pairings = self.pairing_history(tournament_id)
        payload = {
            "format": "open-chess-backup",
            "version": 1,
            "tournament": {"name": tournament["name"], "school_name": tournament["school_name"]},
            "players": [
                {
                    "backup_id": p["id"], "first_name": p["first_name"],
                    "last_name": p["last_name"], "course": p["course"],
                    "center": p["center"], "active": bool(p["active"]),
                }
                for p in players
            ],
            "rounds": [
                {
                    "number": rnd["number"],
                    "pairings": [
                        {
                            "board": game["board"], "white": game["white_id"],
                            "black": game["black_id"], "result": game["result"],
                        }
                        for game in pairings if game["round_number"] == rnd["number"]
                    ],
                }
                for rnd in rounds
            ],
        }
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return destination

    def import_tournament(self, path: str | Path) -> int:
        """Restaura una copia como grupo nuevo dentro de una única transacción."""
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("No se pudo leer la copia de seguridad.") from exc
        self._validate_backup(payload)
        active_count = self.connection.execute(
            "SELECT COUNT(*) FROM tournaments WHERE active=1"
        ).fetchone()[0]
        if active_count >= 15:
            raise ValueError("Ya hay 15 grupos activos. Elimina uno antes de restaurar.")

        original_name = payload["tournament"]["name"].strip()
        school_name = payload["tournament"].get("school_name", "CEIP Vista Alegre").strip()
        name = original_name

        with self.connection:
            tournament_id = self.connection.execute(
                "INSERT INTO tournaments(name, school_name) VALUES (?, ?)", (name, school_name)
            ).lastrowid
            player_map: dict[int, int] = {}
            for player in payload["players"]:
                new_id = self.connection.execute(
                    "INSERT INTO players(tournament_id, first_name, last_name, course, center, active) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (tournament_id, player["first_name"].strip(), player["last_name"].strip(),
                     player.get("course", "").strip(), player.get("center", "").strip(),
                     int(player.get("active", True))),
                ).lastrowid
                player_map[player["backup_id"]] = new_id
            for round_data in payload["rounds"]:
                round_id = self.connection.execute(
                    "INSERT INTO rounds(tournament_id, number) VALUES (?, ?)",
                    (tournament_id, round_data["number"]),
                ).lastrowid
                for game in round_data["pairings"]:
                    black = player_map[game["black"]] if game["black"] is not None else None
                    self.connection.execute(
                        "INSERT INTO pairings(round_id, board, white_id, black_id, result) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (round_id, game["board"], player_map[game["white"]], black, game["result"]),
                    )
        return tournament_id

    @staticmethod
    def _validate_backup(payload: object) -> None:
        if not isinstance(payload, dict) or payload.get("format") != "open-chess-backup" or payload.get("version") != 1:
            raise ValueError("El archivo no es una copia compatible de Open Chess.")
        tournament = payload.get("tournament")
        players = payload.get("players")
        rounds = payload.get("rounds")
        if not isinstance(tournament, dict) or not isinstance(tournament.get("name"), str) or not tournament["name"].strip():
            raise ValueError("La copia no contiene un nombre de grupo válido.")
        school_name = tournament.get("school_name", "CEIP Vista Alegre")
        if not isinstance(school_name, str) or not school_name.strip():
            raise ValueError("La copia no contiene un nombre de colegio válido.")
        if not isinstance(players, list) or not isinstance(rounds, list):
            raise ValueError("La copia está incompleta.")
        player_ids = set()
        for player in players:
            if (not isinstance(player, dict) or not isinstance(player.get("backup_id"), int)
                    or not isinstance(player.get("first_name"), str)
                    or not player["first_name"].strip()
                    or not isinstance(player.get("last_name"), str)
                    or not player["last_name"].strip()):
                raise ValueError("La copia contiene un alumno no válido.")
            player_ids.add(player["backup_id"])
        valid_results = {"", "1-0", "0-1", "1/2-1/2", "BYE"}
        seen_rounds = set()
        for round_data in rounds:
            if (not isinstance(round_data, dict) or not isinstance(round_data.get("number"), int)
                    or round_data["number"] < 1 or round_data["number"] in seen_rounds
                    or not isinstance(round_data.get("pairings"), list)):
                raise ValueError("La copia contiene una ronda no válida.")
            seen_rounds.add(round_data["number"])
            for game in round_data["pairings"]:
                if (not isinstance(game, dict) or game.get("white") not in player_ids
                        or (game.get("black") is not None and game.get("black") not in player_ids)
                        or game.get("result") not in valid_results
                        or not isinstance(game.get("board"), int)):
                    raise ValueError("La copia contiene un emparejamiento no válido.")

    def add_player(
        self, tournament_id: int, first_name: str, last_name: str,
        course: str = "", center: str = ""
    ) -> int:
        first_name, last_name = first_name.strip(), last_name.strip()
        if not first_name or not last_name:
            raise ValueError("El nombre y los apellidos son obligatorios.")
        return self.execute(
            "INSERT INTO players(tournament_id, first_name, last_name, course, center) "
            "VALUES (?, ?, ?, ?, ?)",
            (tournament_id, first_name, last_name, course.strip(), center.strip()),
        ).lastrowid

    def add_players_batch(self, tournament_id: int, players: list[dict[str, str]]) -> int:
        """Añade una importación completa de alumnos en una única transacción."""
        cleaned: list[tuple[int, str, str, str, str]] = []
        for player in players:
            first_name = player.get("first_name", "").strip()
            last_name = player.get("last_name", "").strip()
            if not first_name or not last_name:
                raise ValueError("Todos los alumnos deben tener nombre y apellidos.")
            cleaned.append((tournament_id, first_name, last_name,
                            player.get("course", "").strip(),
                            player.get("center", "").strip()))
        if not cleaned:
            raise ValueError("No hay alumnos para importar.")
        with self.connection:
            self.connection.executemany(
                "INSERT INTO players(tournament_id, first_name, last_name, course, center) "
                "VALUES (?, ?, ?, ?, ?)", cleaned
            )
        return len(cleaned)

    def update_player(
        self, player_id: int, first_name: str, last_name: str,
        course: str = "", center: str = ""
    ) -> None:
        if not first_name.strip() or not last_name.strip():
            raise ValueError("El nombre y los apellidos son obligatorios.")
        self.execute(
            "UPDATE players SET first_name=?, last_name=?, course=?, center=? WHERE id=?",
            (first_name.strip(), last_name.strip(), course.strip(), center.strip(), player_id),
        )

    def remove_player(self, player_id: int) -> None:
        played = self.connection.execute(
            "SELECT COUNT(*) FROM pairings WHERE white_id=? OR black_id=?", (player_id, player_id)
        ).fetchone()[0]
        if played:
            self.execute("UPDATE players SET active=0 WHERE id=?", (player_id,))
        else:
            self.execute("DELETE FROM players WHERE id=?", (player_id,))

    def list_players(self, tournament_id: int, active_only: bool = True) -> list[sqlite3.Row]:
        extra = "AND active=1" if active_only else ""
        return self.query(
            f"SELECT * FROM players WHERE tournament_id=? {extra} "
            "ORDER BY last_name COLLATE NOCASE, first_name COLLATE NOCASE", (tournament_id,)
        )

    def current_round(self, tournament_id: int) -> int:
        row = self.connection.execute(
            "SELECT COALESCE(MAX(number), 0) FROM rounds WHERE tournament_id=?", (tournament_id,)
        ).fetchone()
        return int(row[0])

    def round_is_complete(self, tournament_id: int, number: int) -> bool:
        if number == 0:
            return True
        row = self.connection.execute(
            "SELECT COUNT(*), SUM(CASE WHEN p.result='' THEN 1 ELSE 0 END) "
            "FROM pairings p JOIN rounds r ON r.id=p.round_id "
            "WHERE r.tournament_id=? AND r.number=?", (tournament_id, number)
        ).fetchone()
        return row[0] > 0 and row[1] == 0

    def pairing_history(self, tournament_id: int) -> list[sqlite3.Row]:
        return self.query(
            "SELECT p.*, r.number AS round_number FROM pairings p "
            "JOIN rounds r ON r.id=p.round_id WHERE r.tournament_id=? "
            "ORDER BY r.number, p.board", (tournament_id,)
        )

    def create_round(self, tournament_id: int, pairs: list[tuple[int, int | None]]) -> int:
        number = self.current_round(tournament_id) + 1
        with self.connection:
            round_id = self.connection.execute(
                "INSERT INTO rounds(tournament_id, number) VALUES (?, ?)",
                (tournament_id, number),
            ).lastrowid
            for board, (white_id, black_id) in enumerate(pairs, 1):
                result = "BYE" if black_id is None else ""
                self.connection.execute(
                    "INSERT INTO pairings(round_id, board, white_id, black_id, result) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (round_id, board, white_id, black_id, result),
                )
        return round_id

    def get_round_pairings(self, tournament_id: int, number: int) -> list[sqlite3.Row]:
        return self.query(
            "SELECT p.id, p.board, p.white_id, p.black_id, p.result, "
            "w.first_name || ' ' || w.last_name AS white_name, "
            "CASE WHEN b.id IS NULL THEN 'DESCANSA' ELSE b.first_name || ' ' || b.last_name END AS black_name "
            "FROM pairings p JOIN rounds r ON r.id=p.round_id "
            "JOIN players w ON w.id=p.white_id LEFT JOIN players b ON b.id=p.black_id "
            "WHERE r.tournament_id=? AND r.number=? ORDER BY p.board", (tournament_id, number)
        )

    def set_result(self, pairing_id: int, result: str) -> None:
        if result not in {"", "1-0", "0-1", "1/2-1/2", "BYE"}:
            raise ValueError("Resultado no válido.")
        self.execute("UPDATE pairings SET result=? WHERE id=?", (result, pairing_id))
