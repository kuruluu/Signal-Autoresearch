import unittest
from paperlab.capabilities import inspect,PROBES
from paperlab.broker import ApiError


class CapabilityTests(unittest.TestCase):
    def test_probes_use_only_read_paths_and_presealed_dates(self):
        class Fake:
            def request(self,path,params=None,data=False):
                self.assert_no_order(path)
                if path=='/v2/account':return {'status':'ACTIVE','id':'private-not-reported'}
                if path=='/v2/calendar':return [{}]
                return {path.split('/')[-1]:[{'t':'2023-09-29T14:00:00Z'}]}
            def assert_no_order(self,path):
                if 'order' in path:raise AssertionError('order path forbidden')
        result=inspect(Fake())
        self.assertTrue(all(r['status'].startswith('accessible') for r in result))
        self.assertNotIn('private-not-reported',str(result))
        for _,_,params,_,_ in PROBES:
            if params:self.assertLess(params['end'][:4],'2024')

    def test_permissions_failure_is_reported_without_secret_exception_text(self):
        class Fake:
            def request(self,*args,**kwargs):raise ApiError(403,'private-path')
        result=inspect(Fake())
        self.assertTrue(all(r['http_status']==403 for r in result))
        self.assertNotIn('private-path',str(result))


if __name__=='__main__':unittest.main()
