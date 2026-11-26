import unittest,tempfile
from pathlib import Path
from researchlab.p07_baseline import portfolios


class PortfolioTests(unittest.TestCase):
    def test_missing_duplicate_decile_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'panel.txt';rows=[f'20000103 {i} .01 100 10\n' for i in range(1,11)]
            p.write_text(''.join(rows));self.assertEqual(portfolios(p).shape,(1,10))
            p.write_text(''.join(rows[:-1]))
            with self.assertRaises(ValueError):portfolios(p)
            p.write_text(''.join(rows+[rows[0]]))
            with self.assertRaises(ValueError):portfolios(p)
