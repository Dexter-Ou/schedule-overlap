import contextlib
import hashlib
import io
import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import schedule_overlap as app


class Check(unittest.TestCase):
    def run_csv(self, body):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'input.csv'
            p.write_text('resource,start,end\n' + body, encoding='utf-8')
            before = hashlib.sha256(p.read_bytes()).digest()
            result = app.check(p)
            self.assertEqual(before, hashlib.sha256(p.read_bytes()).digest())
            return result

    def test_example(self):
        self.assertEqual(app.check('example.csv'), {'rows': 4, 'overlap_count': 1, 'overlaps': [[1, 2]]})

    def test_offsets_touching_and_other_resources(self):
        r = self.run_csv('x,2026-01-01T10:00:00+01:00,2026-01-01T11:00:00+01:00\n'
                         'x,2026-01-01T09:30:00Z,2026-01-01T10:00:00Z\n'
                         'x,2026-01-01T10:00:00Z,2026-01-01T11:00:00Z\n'
                         'y,2026-01-01T09:30:00Z,2026-01-01T10:00:00Z\n')
        self.assertEqual(r['overlaps'], [[1, 2]])

    def test_nesting_unsorted_and_duplicates(self):
        r = self.run_csv('x,2026-01-01T09:30:00Z,2026-01-01T10:00:00Z\n'
                         'x,2026-01-01T09:00:00Z,2026-01-01T12:00:00Z\n'
                         'x,2026-01-01T09:30:00Z,2026-01-01T10:00:00Z\n')
        self.assertEqual(r['overlaps'], [[1, 2], [1, 3], [2, 3]])

    def test_invalid_rows(self):
        for body in ['x,2026-01-01T09:00:00,2026-01-01T10:00:00Z\n',
                     'x,2026-01-01T09:00:00Z,2026-01-01T09:00:00Z\n',
                     ' ,2026-01-01T09:00:00Z,2026-01-01T10:00:00Z\n',
                     'x,2026-01-01T09:00:00Z\n',
                     'x,2026-01-01T09:00:00Z,2026-01-01T10:00:00Z,extra\n']:
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.run_csv(body)
        for stamp in ['2026-01-01T09:00:00-00:00', '2026-01-01T09:00:00+00:99', '2026-02-30T09:00:00Z']:
            with self.assertRaises(ValueError):
                app.timestamp(stamp)

    def test_limits_and_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'a.csv'
            for text in ['start,end,resource\n', 'resource,start,end\nx,' + 'a' * app.MAX_BYTES]:
                p.write_text(text)
                with self.assertRaises(ValueError):
                    app.check(p)
        with patch.object(app, 'MAX_ROWS', 0), self.assertRaises(ValueError):
            app.check('example.csv')

    def test_empty_bom_multiline(self):
        self.assertEqual(self.run_csv('')['overlaps'], [])
        self.assertEqual(self.run_csv('"room\na",2026-01-01T09:00:00Z,2026-01-01T10:00:00Z\n')['rows'], 1)
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'a.csv'
            p.write_bytes(b'\xef\xbb\xbfresource,start,end\n')
            self.assertEqual(app.check(p)['rows'], 0)

    def test_randomized_against_pairwise_oracle(self):
        rng = random.Random(43)
        base = app.timestamp('2026-01-01T00:00:00Z')
        for _ in range(25):
            rows = [(rng.randrange(3), rng.randrange(120), rng.randrange(1, 40)) for _ in range(30)]
            body = ''.join(f'{g},{(base+app.dt.timedelta(minutes=s)).isoformat()},{(base+app.dt.timedelta(minutes=s+d)).isoformat()}\n' for g, s, d in rows)
            expected = [[i+1, j+1] for i,(g,s,d) in enumerate(rows) for j,(h,t,e) in enumerate(rows) if i<j and g==h and s<t+e and t<s+d]
            self.assertEqual(self.run_csv(body)['overlaps'], expected)

    def test_cli_error_redacts_path_and_data(self):
        out = io.StringIO()
        with patch('sys.argv', ['schedule_overlap.py', '/nonexistent/private-name']), contextlib.redirect_stdout(out):
            self.assertEqual(app.main(), 2)
        self.assertNotIn('private-name', out.getvalue())
        self.assertIn('error', json.loads(out.getvalue()))


if __name__ == '__main__':
    unittest.main()
