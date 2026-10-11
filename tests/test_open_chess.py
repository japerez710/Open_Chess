import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from open_chess.database import Database
from open_chess.excel_import import read_student_rows
from open_chess.swiss import calculate_standings, generate_pairings


class OpenChessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "test.db")
        self.tournament = self.db.create_tournament("Escolar")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def add_players(self, amount=4):
        return [self.db.add_player(self.tournament, f"Nombre{i}", f"Apellido{i}", "5º", f"Centro {i % 2}")
                for i in range(amount)]

    def test_limit_is_fifteen_active_tournaments(self):
        for i in range(14):
            self.db.create_tournament(f"Grupo {i}")
        with self.assertRaisesRegex(ValueError, "15 grupos"):
            self.db.create_tournament("Grupo extra")

    def test_first_round_pairs_every_player_once(self):
        ids = self.add_players(6)
        pairs = generate_pairings(self.db.list_players(self.tournament), [])
        paired = [player for pair in pairs for player in pair if player is not None]
        self.assertCountEqual(paired, ids)
        self.assertEqual(len(pairs), 3)

    def test_odd_player_receives_bye_and_not_twice(self):
        ids = self.add_players(5)
        pairs = generate_pairings(self.db.list_players(self.tournament), [])
        bye = next(white for white, black in pairs if black is None)
        self.db.create_round(self.tournament, pairs)
        for pairing in self.db.get_round_pairings(self.tournament, 1):
            if pairing["result"] != "BYE":
                self.db.set_result(pairing["id"], "1-0")
        next_pairs = generate_pairings(self.db.list_players(self.tournament), self.db.pairing_history(self.tournament))
        next_bye = next(white for white, black in next_pairs if black is None)
        self.assertIn(bye, ids)
        self.assertNotEqual(bye, next_bye)

    def test_standings_scores_and_buchholz(self):
        self.add_players(4)
        pairs = generate_pairings(self.db.list_players(self.tournament), [])
        self.db.create_round(self.tournament, pairs)
        round_rows = self.db.get_round_pairings(self.tournament, 1)
        self.db.set_result(round_rows[0]["id"], "1-0")
        self.db.set_result(round_rows[1]["id"], "1/2-1/2")
        standings = calculate_standings(self.db.list_players(self.tournament), self.db.pairing_history(self.tournament))
        self.assertEqual([s.points for s in standings], [1.0, 0.5, 0.5, 0.0])
        self.assertEqual(sum(s.points for s in standings), 2.0)

    def test_new_round_requires_results(self):
        self.add_players(4)
        self.db.create_round(self.tournament, generate_pairings(self.db.list_players(self.tournament), []))
        self.assertFalse(self.db.round_is_complete(self.tournament, 1))

    def test_result_can_be_corrected_with_one_of_three_scores(self):
        self.add_players(2)
        self.db.create_round(self.tournament, generate_pairings(self.db.list_players(self.tournament), []))
        pairing = self.db.get_round_pairings(self.tournament, 1)[0]
        for result in ("1-0", "1/2-1/2", "0-1"):
            self.db.set_result(pairing["id"], result)
            self.assertEqual(self.db.get_round_pairings(self.tournament, 1)[0]["result"], result)

    def test_backup_round_trip_preserves_players_rounds_and_results(self):
        self.add_players(5)
        pairs = generate_pairings(self.db.list_players(self.tournament), [])
        self.db.create_round(self.tournament, pairs)
        for pairing in self.db.get_round_pairings(self.tournament, 1):
            if pairing["result"] != "BYE":
                self.db.set_result(pairing["id"], "1-0")
        backup = Path(self.temp.name) / "escolar.openchess"
        self.db.export_tournament(self.tournament, backup)

        restored = self.db.import_tournament(backup)
        restored_players = self.db.list_players(restored)
        restored_history = self.db.pairing_history(restored)
        self.assertEqual(self.db.get_tournament(restored)["name"], "Escolar")
        self.assertEqual(self.db.get_tournament(restored)["school_name"], "CEIP Vista Alegre")
        self.assertEqual(len(restored_players), 5)
        self.assertEqual(len(restored_history), 3)
        self.assertEqual([row["result"] for row in restored_history].count("BYE"), 1)
        self.assertEqual([row["result"] for row in restored_history].count("1-0"), 2)

    def test_invalid_backup_is_rejected_without_creating_group(self):
        backup = Path(self.temp.name) / "incorrecta.openchess"
        backup.write_text('{"format": "otro-programa"}', encoding="utf-8")
        before = len(self.db.list_tournaments())
        with self.assertRaisesRegex(ValueError, "compatible"):
            self.db.import_tournament(backup)
        self.assertEqual(len(self.db.list_tournaments()), before)

    def test_school_name_is_stored_with_group(self):
        tournament = self.db.create_tournament("Intercentros", "CEIP Vista Alegre")
        self.assertEqual(self.db.get_tournament(tournament)["school_name"], "CEIP Vista Alegre")

    def test_deleting_group_removes_its_players_rounds_and_pairings(self):
        self.add_players(4)
        self.db.create_round(self.tournament, generate_pairings(self.db.list_players(self.tournament), []))
        self.db.delete_tournament(self.tournament)
        with self.assertRaisesRegex(ValueError, "no existe"):
            self.db.get_tournament(self.tournament)
        self.assertEqual(self.db.query("SELECT COUNT(*) AS total FROM players")[0]["total"], 0)
        self.assertEqual(self.db.query("SELECT COUNT(*) AS total FROM rounds")[0]["total"], 0)
        self.assertEqual(self.db.query("SELECT COUNT(*) AS total FROM pairings")[0]["total"], 0)

    def test_result_can_be_reset_to_pending(self):
        self.add_players(2)
        self.db.create_round(self.tournament, generate_pairings(self.db.list_players(self.tournament), []))
        pairing = self.db.get_round_pairings(self.tournament, 1)[0]
        self.db.set_result(pairing["id"], "1-0")
        self.db.set_result(pairing["id"], "")
        self.assertEqual(self.db.get_round_pairings(self.tournament, 1)[0]["result"], "")
        self.assertFalse(self.db.round_is_complete(self.tournament, 1))

    def test_excel_template_columns_are_imported(self):
        path = Path(self.temp.name) / "alumnos.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Alumno", "Curso", "Centro educativo"])
        sheet.append(["Ana García Pérez", "5º A", "CEIP Vista Alegre"])
        sheet.append(["Ruiz López, Pablo", "6º", "Colegio Norte"])
        workbook.save(path)

        students = read_student_rows(path)
        imported = self.db.add_players_batch(self.tournament, students)
        players = self.db.list_players(self.tournament)

        self.assertEqual(imported, 2)
        self.assertEqual(len(players), 2)
        self.assertEqual({f"{row['first_name']} {row['last_name']}" for row in players},
                         {"Ana García Pérez", "Pablo Ruiz López"})
        self.assertEqual({row["center"] for row in players},
                         {"CEIP Vista Alegre", "Colegio Norte"})

    def test_excel_with_wrong_headers_is_rejected(self):
        path = Path(self.temp.name) / "incorrecto.xlsx"
        workbook = Workbook()
        workbook.active.append(["Nombre", "Clase", "Colegio"])
        workbook.save(path)
        with self.assertRaisesRegex(ValueError, "fila 1"):
            read_student_rows(path)


if __name__ == "__main__":
    unittest.main()
