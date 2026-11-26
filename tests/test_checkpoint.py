import unittest
from researchlab.checkpoint import allowed,ROOT


class CheckpointTests(unittest.TestCase):
    def test_checkpoint_excludes_credentials_raw_data_and_thirdparty_text(self):
        for path in ['.env','research/data/SPY.csv','research/replication_first/p40_audit/author_appendix.pdf',
                     'research/replication_first/p40_audit/author_appendix.txt',
                     'research/replication_first/p45_audit/SPY_2004_2011.json','reports/alpaca_capabilities.json']:
            self.assertFalse(allowed(ROOT/path),path)
        for path in ['paperlab/broker.py','researchlab/p45_strategy.py',
                     'research/replication_first/p45_strategy_001/registration.json',
                     'research/replication_first/p45_strategy_001/results.json']:
            self.assertTrue(allowed(ROOT/path),path)


if __name__=='__main__':unittest.main()
