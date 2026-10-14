"""Immutable editorial authorization and guide/asset evidence, not live availability."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import nauta_reference
import update_m3u as runner

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'contracts/trial-officialization-20261013.json'

class TrialOfficializationTest(unittest.TestCase):
    def test_authorization_is_closed_to_exact_existing_references(self):
        audit=json.loads(AUDIT.read_text(encoding='utf-8'))
        rows=audit['channels']
        self.assertEqual(247,len(rows))
        self.assertEqual(247,len({r['tvgId'] for r in rows}))
        self.assertTrue(all(r['previousTrial'] is True and r['trial'] is False for r in rows))
        nauta=[r for r in rows if r.get('nautaName')]
        self.assertEqual(38,len(nauta))
        self.assertEqual(42,len(runner.VERIFIED_NAUTA_OFFICIAL_REFERENCES))
        for row in nauta:
            self.assertEqual(row['tvgId'],nauta_reference.channel_id(row['nautaName']))
            self.assertEqual((row['nautaCatalog'],row['nautaName']),runner.VERIFIED_NAUTA_OFFICIAL_REFERENCES[row['tvgId']])

    def test_curated_guides_are_explicit_and_pending_rows_have_no_guessed_source(self):
        audit=json.loads(AUDIT.read_text(encoding='utf-8'))
        matched={r['tvgId']:r['epg'] for r in audit['channels'] if r['epg']['status']=='matched'}
        pending=[r for r in audit['channels'] if r['epg']['status']=='pending']
        self.assertEqual(51,len(matched));self.assertEqual(196,len(pending))
        self.assertTrue(all(not r['epg'].get('source') and r['epg']['reason'] for r in pending))
        self.assertTrue(all(g['source'] in runner.EPG_SOURCES and g['coverageHours']>=12 and g['evidence'] for g in matched.values()))
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'epg-overrides.json'
            entries={id:{'source':g['source'],'source_id':g['source_id']} for id,g in matched.items()}
            path.write_text(json.dumps({'channels':entries}),encoding='utf-8')
            before=dict(runner.EPG_PROGRAMME_SOURCES)
            try:
                applied=runner.apply_epg_overrides(path)
                self.assertEqual({id:(g['source'],g['source_id']) for id,g in matched.items()},applied)
                self.assertFalse(any(r['tvgId'] in applied for r in pending))
            finally:
                runner.EPG_PROGRAMME_SOURCES.clear();runner.EPG_PROGRAMME_SOURCES.update(before)

    def test_new_assets_are_local_originals_with_the_recorded_hash(self):
        audit=json.loads(AUDIT.read_text(encoding='utf-8'))
        self.assertEqual(232,sum(bool(r['logoPath']) for r in audit['channels']))
        for asset in audit['assets']:
            self.assertTrue(asset['path'].startswith('logos/catalogue/'))
            self.assertTrue(asset['path'].endswith(('.png','.svg')))
            self.assertEqual(asset['sha256'],hashlib.sha256((ROOT/asset['path']).read_bytes()).hexdigest())
            self.assertTrue(asset['url'].startswith('https://'))

if __name__=='__main__': unittest.main()
