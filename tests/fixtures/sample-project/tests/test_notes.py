import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import accounts
import notes


class NotesTests(unittest.TestCase):
    def test_owner_can_list_notes(self) -> None:
        accounts.register("amy", "correct horse")
        notes.add_note("amy", "correct horse", "hello")
        self.assertEqual(notes.list_notes("amy", "correct horse"), ["hello"])

    def test_wrong_password_is_rejected(self) -> None:
        accounts.register("bob", "correct horse")
        with self.assertRaises(PermissionError):
            notes.add_note("bob", "wrong", "hello")


if __name__ == "__main__":
    unittest.main()
