import csv
import io
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from core import APIError, csv_text, money
from app import AccessPath


class BusinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.routes = AccessPath(Path(self.temp.name)/"test.db")

    def tearDown(self):
        self.temp.cleanup()

    def call(self, app, method, path, data=None, query=None):
        return app.handle(method, path, data or {}, query or {})

    def test_step_free_route_avoids_shorter_stairs(self):
        base = {'start':'gate','end':'lab','max_slope':8,'min_width':90}
        accessible = self.call(self.routes,'POST','/plan',{**base,'step_free':True})
        unrestricted = self.call(self.routes,'POST','/plan',{**base,'step_free':False})
        self.assertEqual(accessible['distance'],220)
        self.assertEqual(accessible['nodes'],['gate','ramp','hall','lab'])
        self.assertEqual(unrestricted['distance'],170)

    def test_closed_route_reroutes_then_becomes_unreachable(self):
        self.call(self.routes,'PATCH','/edges/6',{'blocked':True})
        result = self.call(self.routes,'POST','/plan',{'start':'gate','end':'lab'})
        self.assertFalse(result['found'])
        self.call(self.routes,'PATCH','/edges/6',{'blocked':False})
        self.assertTrue(self.call(self.routes,'POST','/plan',{'start':'gate','end':'lab'})['found'])

    def test_same_node_route_has_zero_distance(self):
        result=self.call(self.routes,'POST','/plan',{'start':'gate','end':'gate'})
        self.assertEqual((result['nodes'],result['distance']),(['gate'],0))

    def test_route_invalid_preferences(self):
        for data in [{'start':'unknown','end':'lab'}, {'start':'gate','end':'lab','max_slope':float('nan')}, {'start':[],'end':'lab'}]:
            with self.subTest(data=data), self.assertRaises(APIError):
                self.call(self.routes,'POST','/plan',data)
