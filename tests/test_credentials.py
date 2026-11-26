import tempfile
import unittest
from pathlib import Path
from paperlab.credentials import read_credentials


class CredentialTests(unittest.TestCase):
    def test_bom_file_loads_only_whitelisted_keys_without_expansion(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'.env'
            p.write_text('# local\nAPCA_API_KEY_ID="dummy"\nAPCA_API_SECRET_KEY=literal$VALUE\nOTHER=ignored\n',encoding='utf-8-sig')
            result=read_credentials(p,{})
            self.assertEqual(result,{'APCA_API_KEY_ID':'dummy','APCA_API_SECRET_KEY':'literal$VALUE'})
            self.assertEqual(read_credentials(p,{'APCA_API_KEY_ID':'override'})['APCA_API_KEY_ID'],'override')

    def test_missing_credentials_remain_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertTrue(all(v is None for v in read_credentials(Path(temp)/'missing',{}).values()))


if __name__=='__main__':unittest.main()
