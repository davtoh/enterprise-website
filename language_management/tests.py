import unittest
from language_management.management.commands.auto_translate import Command


class AutoTranslatePlaceholdersTest(unittest.TestCase):
    def setUp(self):
        self.cmd = Command()

    def test_protect_and_restore_named_placeholders(self):
        original = "Invoice %(number)s updated successfully."
        safe, placeholders = self.cmd._protect_placeholders(original)
        self.assertIn("__PH_0__", safe)
        self.assertEqual(placeholders, ["%(number)s"])

        # Simulated translation where token casing / spaces might slightly shift
        translated = "Factura __PH_0__ actualizada con éxito."
        restored = self.cmd._restore_placeholders(translated, placeholders)
        self.assertEqual(restored, "Factura %(number)s actualizada con éxito.")

    def test_protect_and_restore_percent_s(self):
        original = "Company '%s' created successfully."
        safe, placeholders = self.cmd._protect_placeholders(original)
        self.assertIn("__PH_0__", safe)
        self.assertEqual(placeholders, ["%s"])

        translated = "Empresa '__PH_0__' creada con éxito."
        restored = self.cmd._restore_placeholders(translated, placeholders)
        self.assertEqual(restored, "Empresa '%s' creada con éxito.")

    def test_validation_detects_dropped_placeholders(self):
        msgid = "Company '%s' created successfully."
        # Corrupted translation where %s is missing
        corrupted_msgstr = "Empresa creada con éxito."
        valid = self.cmd._validate_format_specs(msgid, corrupted_msgstr, is_python_format=True)
        self.assertFalse(valid)

        # Correct translation where %s is preserved
        correct_msgstr = "Empresa '%s' creada con éxito."
        self.assertTrue(self.cmd._validate_format_specs(msgid, correct_msgstr, is_python_format=True))

    def test_preserve_boundary_whitespace(self):
        msgid = "\n          There is 1 product.\n          "
        translated = "Hay 1 producto."
        result = self.cmd._preserve_boundary_whitespace(msgid, translated)
        self.assertTrue(result.startswith("\n"))
        self.assertTrue(result.endswith("\n          "))
        self.assertIn("Hay 1 producto.", result)
