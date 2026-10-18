"""Calculator host prototype safety and offline layout contract."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/"experimental"/"calculator-v01"

class TestCalculatorHostAssets(unittest.TestCase):
    def test_offline_six_column_keypad_and_scripts(self):
        html=(APP/"index.html").read_text(encoding="utf-8")
        js=(APP/"calculator-app.js").read_text(encoding="utf-8")
        core=(APP/"calculator-core.js").read_text(encoding="utf-8")
        for item in ('grid-template-columns:repeat(6,minmax(0,1fr))',
                     '--touch-target:2.75rem','id="calc-expression"',
                     'id="calc-result"','role="alert"','id="calc-angle"',
                     'src="../shared/virtual_keyboard.js"',
                     'src="calculator-core.js"','src="calculator-app.js"'):
            self.assertIn(item,html)
        self.assertIn('VK.edit(',js)
        self.assertIn('C.evaluate(',js)
        self.assertNotIn('eval(',core+js)
        self.assertNotIn('new Function(',core+js)
        self.assertNotIn('fetch(',core+js)
        self.assertNotIn('localStorage',core+js)
        self.assertNotIn('https://',html)
        self.assertNotIn('http://',html)

if __name__=="__main__":
    unittest.main()
