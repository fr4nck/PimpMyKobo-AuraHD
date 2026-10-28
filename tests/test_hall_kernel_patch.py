"""Read-only contracts for an OFFLINE kernel source patch, never installed."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "experimental/power-lab/candidates/tle4913-hall-wakeup-off-v0.patch"
DOC = ROOT / "docs/hall-irq-wakeup-candidate-fr.md"

class HallWakeCandidateTests(unittest.TestCase):
    def setUp(self):
        self.lines = PATCH.read_text(encoding="utf-8").splitlines()

    def test_one_source_file_one_hunk_one_expression(self):
        lines = self.lines
        name = "drivers/input/keyboard/tle4913_keypad.c"
        self.assertEqual([f"diff --git a/{name} b/{name}"],
                         [line for line in lines if line.startswith("diff --git ")])
        self.assertEqual([f"--- a/{name}"],
                         [line for line in lines if line.startswith("--- ")])
        self.assertEqual([f"+++ b/{name}"],
                         [line for line in lines if line.startswith("+++ ")])
        self.assertEqual(["@@ -39,7 +39,7 @@ static GPIODATA gtTLE4913_GPIO_data = {"],
                         [line for line in lines if line.startswith("@@ ")])
        self.assertEqual(["\t.iWakeup = 1,"],
                         [line[1:] for line in lines
                          if line.startswith("-") and not line.startswith("---")])
        self.assertEqual(["\t.iWakeup = -1,"],
                         [line[1:] for line in lines
                          if line.startswith("+") and not line.startswith("+++")])

    def test_irq_and_key_callback_context_preserved(self):
        hunk = "\n".join(self.lines)
        for required in (
            '.szName = "TLE4913"',
            '.tPADCtrl = MX50_PAD_SD3_D5__GPIO_5_25',
            '.uiIRQType = IRQF_TRIGGER_RISING|IRQF_TRIGGER_FALLING',
            '.dwDebounceTicks = 1',
            '.iActive = 0',
        ):
            self.assertIn(required, hunk)
        for forbidden in ("gpiofn.c", "ntx_report_power", "GPIO_PWR_SW",
                          "gpio_free", "disable_irq(", "mxckpd", "/dev/"):
            self.assertNotIn(forbidden, hunk)

    def test_patch_and_document_marked_not_for_installation(self):
        doc = DOC.read_text(encoding="utf-8")
        self.assertIn("d7d3e3632b15526f1dcd06027f7bdbea74eef7a4", doc)
        self.assertIn("iWakeup=-1", doc)
        self.assertIn("CANDIDAT", doc)
        self.assertIn("non appliqué", doc)
        self.assertIn("KEY_POWER", doc)
        self.assertIn("aucune", doc.lower())

if __name__ == "__main__":
    unittest.main()
