import unittest
from researchlab.p40_inputs_v2 import validate_bounds


class BoundsTests(unittest.TestCase):
    def test_sealed_dates_and_unbounded_intervals_rejected(self):
        validate_bounds('2016-01-01T00:00:00Z','2023-12-31T23:59:59Z')
        for start,end in [('2023-01-01T00:00:00Z','2024-01-02T00:00:00Z'),
                          ('2023-01-01T00:00:00Z','2024-01-01T00:00:00Z'),
                          ('2015-12-31T00:00:00Z','2016-01-02T00:00:00Z'),
                          ('2023-01-01','2023-12-31')]:
            with self.assertRaises(ValueError):validate_bounds(start,end)


if __name__=='__main__':unittest.main()
