"""Immutable editorial authorization and guide/asset evidence, not live availability."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import update_m3u as runner

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'contracts/trial-officialization-20261013.json'
OPTIMIZED=json.loads((ROOT/'contracts/logos-optimizados-20261031.json').read_text(encoding='utf-8'))['logos']

class TrialOfficializationTest(unittest.TestCase):
    def test_authorization_is_closed_to_exact_existing_references(self):
        audit=json.loads(AUDIT.read_text(encoding='utf-8'))
        rows=audit['channels']
        self.assertEqual(247,len(rows))
        self.assertEqual(247,len({r['tvgId'] for r in rows}))
        self.assertTrue(all(r['previousTrial'] is True and r['trial'] is False for r in rows))
        # Las 38 filas Nauta del registro son historia: Nauta se retiró por completo el 2026-10-29.
        self.assertEqual(38,len([r for r in rows if r.get('nautaName')]))

    def test_curated_guides_are_explicit_and_pending_rows_have_no_guessed_source(self):
        audit=json.loads(AUDIT.read_text(encoding='utf-8'))
        matched={r['tvgId']:r['epg'] for r in audit['channels'] if r['epg']['status']=='matched'}
        pending=[r for r in audit['channels'] if r['epg']['status']=='pending']
        self.assertEqual(93,len(matched));self.assertEqual(154,len(pending))
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

    def test_emulator_confirmed_guides_have_exact_sources_and_coverage(self):
        audit=json.loads(AUDIT.read_text(encoding='utf-8'))
        expected={
            'PublicDirect.749260224cb34a60ab4d8755':('co1','Sony.co','My Wife and Kids'),
            'PublicDirect.be7f7ba12ab6004903c96227':('co1','HBO.Family.co','Andrew Garfield'),
            'PublicDirect.5218fd5abba92fea1b812142':('co1','E!.Entertainment.TV.co','Vanderpump Rules'),
            'PublicDirect.36a879c02cd2241bb94ff8dc':('ar1','Canal.Lifetime.(Argentina).ar','República Argentina'),
            'PublicDirect.c6bd3a96018cbeb2a0f28f3b':('co1','A&E.co','Orígenes de un crimen'),
            'PublicDirect.d9973a3bfb28634698473218':('co1','A&E.co','Orígenes de un crimen'),
            'PublicDirect.5551093bff52d29b38509588':('co1','Animal.Planet.co','Guardianes al rescate'),
            'PublicDirect.e6a2bc5a013c1c5b9656d441':('co1','Animal.Planet.co','Guardianes al rescate'),
            'PublicDirect.9840c70e010eb35fb900c6b4':('co1','Cinecanal.co','Eco en el cañón'),
            'PublicDirect.56a9657c934115ec2f1481ae':('cl','Canal.Disney.Channel.(Chile).cl','Star vs. Las Fuerzas del Mal'),
            'PublicDirect.971215bf53db3488f848d6c6':('ar1','Canal.ESPN.2.(Bolivia).ar','Manchester City vs. Paris Saint-Germain'),
            'PublicDirect.3d519bc9027bf3427d250d7c':('mx1','ESPN.3.mx','NBA discussion'),
            'PublicDirect.9fc08fec9b53b602b7ce875e':('mx1','ESPN.3.mx','NBA discussion'),
            'PublicDirect.f01cdfce2a440e1aac5e8c70':('co1','ESPN.6.HD.co','SHK 1-1 AEK'),
            'PublicDirect.796c17a762ce69be57ec714d':('fr','France.24.Espanol.fr','Invitado del día'),
            'PublicDirect.0ef1ce174fa5aaee3811b04f':('cl','Canal.History.2.(Chile).cl','El código de Dios'),
            'PublicDirect.8db5a974dc4b6ed483cf2bf9':('cl','Canal.HBO.Xtreme.cl','Te van a matar'),
            'PublicDirect.c1ed48f37448ded5dca7e8bd':('pa1','Canal.History.(Panamá).pa','Misterios inexplorados con Danny Trejo'),
            'PublicDirect.747adbe6694514eee98e7ed5':('es','A3CINE.es','Ninette'),
            'PublicDirect.51b11c161840f9db76a04904':('co1','RCN.Novelas.co',"Lala's spa"),
            'PublicDirect.590828755b8ac040706c8575':('co1','Studio.Universal.co','Spider-Man: Un nuevo universo'),
            'PublicDirect.52f6bff32710f7c83abeda34':('co1','Studio.Universal.co','Spider-Man: Into the Spider-Verse'),
            'PublicDirect.ae75ddaa5bf1de03760155d8':('co1','TNT.Novelas.co','Quiéreme siempre'),
            'PublicDirect.b8b5b69e22a2787006d8bf21':('co1','Telemundo.co','Caso Cerrado'),
            'PublicDirect.67f76c9db1d9d67dc2af39fb':('co1','Telemundo.co','Caso cerrado'),
            'PublicDirect.d48635571a0af3b28d47db03':('uy1','[UNICR].Universal.Crime.uy','Kristen Wagner'),
            'PublicDirect.9193ba6e85578f4486a958d7':('uy1','[UNIPR].Universal.Premiere.uy','El futuro es promisorio'),
            'PublicDirect.fe8012537d4b52a34d2778bd':('uy1','[UNIPRMH].UNIPRMH.uy','House M.D.'),
            'PublicDirect.6d8f767d72df832a0dcaf1b3':('uy1','UNIVISION.HD.uy','La historia de Juana'),
            'PublicDirect.792c9413cb2a98e7c3d972f6':('mx1','Canal.Sky.Sports.16.mx','Deportivo Alavés vs. Atlético de Madrid'),
            'PublicDirect.5c8f98d3876cb07b0c0884f6':('co1','AMC.co','John Lake'),
            'PublicDirect.21d595905b477139407f7250':('cl','Canal.Animal.Planet.(Chile).cl','El acuario'),
            'PublicDirect.b4a12e148b15b71efbcda5e7':('pa1','Canal.Cinemax.(Panamá).pa','Master Z'),
        }
        rows={r['tvgId']:r for r in audit['channels']}
        for tvg_id,(source,source_id,evidence_token) in expected.items():
            guide=rows[tvg_id]['epg']
            self.assertEqual('matched',guide['status'])
            self.assertEqual((source,source_id),(guide['source'],guide['source_id']))
            self.assertGreaterEqual(guide['coverageHours'],12)
            self.assertIn(evidence_token,guide['evidence'])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'epg-overrides.json'
            path.write_text(json.dumps({'channels':{id:{'source':source,'source_id':source_id} for id,(source,source_id,_) in expected.items()}}),encoding='utf-8')
            before=dict(runner.EPG_PROGRAMME_SOURCES)
            try:
                runner.apply_epg_overrides(path)
                layout=json.loads((ROOT/'data/channel-editor-layout.json').read_text(encoding='utf-8'))
                layout_by_id={row['tvgId']:row for row in layout['channels'] if row.get('tvgId')}
                for tvg_id,(source,source_id,_) in expected.items():
                    self.assertEqual((source,source_id),runner.EPG_PROGRAMME_SOURCES[tvg_id])
                    self.assertIn((source,source_id),runner.epg_source_chain(tvg_id))
                    row=layout_by_id[tvg_id]
                    if row['state']=='active':
                        # Lista 2 no publica guía; la fila activa vive allí.
                        self.assertEqual('2.m3u',row.get('sourceList'))
                    else:
                        self.assertEqual('deleted',row['state'])
            finally:
                runner.EPG_PROGRAMME_SOURCES.clear();runner.EPG_PROGRAMME_SOURCES.update(before)
            real=dict(runner.EPG_PROGRAMME_SOURCES)
            try:
                runner.apply_epg_overrides()
                for tvg_id in expected:
                    lrow=layout_by_id[tvg_id]
                    if lrow['state']=='active' and lrow.get('sourceList')=='2.m3u':
                        # Desde 2026-10-21 Lista 2 puede tener EPG, pero solo
                        # mediante un mapeo explícito en epg-l2-map.json.
                        allowed=set(runner.load_epg_l2_map())
                        for name,_ in runner.epg_source_chain(tvg_id):
                            if name=='epg-publicada-conservada':
                                continue
                            self.assertIn(tvg_id,allowed)
            finally:
                runner.EPG_PROGRAMME_SOURCES.clear();runner.EPG_PROGRAMME_SOURCES.update(real)

    def test_unidentified_channels_stay_pending_after_emulator_review(self):
        audit=json.loads(AUDIT.read_text(encoding='utf-8'))
        rows={r['tvgId']:r for r in audit['channels']}
        reviewed={
            'PublicDirect.3ee2b2a286f1ba55a0be9723':'repeat the same scene',
            'PublicDirect.c6f31bbf9b3a8d4f6dbca07d':'no programme title',
            'PublicDirect.be33d60d2f78170c97c37514':'runner has no configured sv XMLTV part',
            'PublicDirect.1a0c2a31bd9c634459c58380':'no programme title',
            'PublicDirect.1efd0c13d73c9caaf88077f4':'no matching Semillitas XMLTV source',
            'PublicDirect.6d1b04a9ccdf4197fbbc3ef6':'no programme title',
            'PublicDirect.1426399def5c52eee57f4bb0':'no programme title',
            'PublicDirect.0d0b3a195eb01f1ab454cd75':'no programme title',
            'PublicDirect.ba69f9b8ca828f79a3b8b9cf':'No current-programme title is visible',
            'PublicDirect.1592ac20e79b21ae24514be4':'No programme title is visible',
            'PublicDirect.60b05b1433d087260f3b5c2d':'no configured Costa Rica/TD+/TDMAX XMLTV schedule',
            'PublicDirect.9233d81ff5fd6c6c02c26e15':'none can be selected without an exact current-programme title',
            'PublicDirect.58d292da8d99dd4d16ed3b57':'candidateCount 0 for Dominican Televida',
            'PublicDirect.796284d305206eaee4223955':'no exact programme title is visible',
            'PublicDirect.db00a6066635f39312f74380':'no programme title appears',
            'PublicDirect.760b2c3b1354cd82b8a647bc':'no exact title can be matched',
            'PublicDirect.391630d2ff5eec427fa516f1':'Play with Fire Part 2',
            'PublicDirect.19fbfbd8b220cd0fb65ac244':'promo for El precio de la historia',
        }
        for tvg_id,evidence_token in reviewed.items():
            guide=rows[tvg_id]['epg']
            self.assertEqual('pending',guide['status'])
            self.assertFalse(guide.get('source'))
            self.assertIn(evidence_token,guide['evidence'])
        svu=rows['PublicDirect.391630d2ff5eec427fa516f1']['epg']
        self.assertEqual('no_exact_current_programme_match',svu['reason'])
        self.assertEqual(5,svu['candidateCount'])
        ae=rows['PublicDirect.19fbfbd8b220cd0fb65ac244']['epg']
        self.assertEqual('no_exact_current_programme_match',ae['reason'])
        self.assertEqual(5,ae['candidateCount'])

    def test_guatemala_feed_maps_only_the_five_explicit_guatemala_channels(self):
        audit=json.loads(AUDIT.read_text(encoding='utf-8'))
        expected={
            'PublicDirect.7a597c8a2d6c1e6c97015c28':'Canal13-Trecevision.gt',
            'PublicDirect.43557d465d973d608c6bb19a':'Canal3.gt',
            'PublicDirect.563319274daa44463f7c9f6c':'Canal7-Televisiete.gt',
            'PublicDirect.eb3b17bc3573e55b2c56cf95':'CanalAntigua.gt',
            'PublicDirect.407a6cdf00bb64c25fb341f4':'Guatevision.gt',
        }
        mapped={r['tvgId']:r['epg']['source_id'] for r in audit['channels'] if r['epg'].get('source')=='gt'}
        self.assertEqual(expected,mapped)
        self.assertIn('gt',runner.EPG_SOURCES)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'epg-overrides.json'
            path.write_text(json.dumps({'channels':{id:{'source':'gt','source_id':source_id} for id,source_id in expected.items()}}),encoding='utf-8')
            before=dict(runner.EPG_PROGRAMME_SOURCES)
            try:
                runner.apply_epg_overrides(path)
                layout=json.loads((ROOT/'data/channel-editor-layout.json').read_text(encoding='utf-8'))
                layout_by_id={row['tvgId']:row for row in layout['channels'] if row.get('tvgId')}
                for tvg_id,source_id in expected.items():
                    row=next(r for r in audit['channels'] if r['tvgId']==tvg_id)
                    self.assertIn('GUA',row['name'].upper())
                    self.assertEqual('matched',row['epg']['status'])
                    self.assertGreaterEqual(row['epg']['coverageHours'],12)
                    self.assertIn(('gt',source_id),runner.epg_source_chain(tvg_id))
                    lrow=layout_by_id[tvg_id]
                    if lrow['state']=='active':
                        # Lista 2 no publica guía; la fila activa vive allí.
                        self.assertEqual('2.m3u',lrow.get('sourceList'))
                    else:
                        self.assertEqual('deleted',lrow['state'])
            finally:
                runner.EPG_PROGRAMME_SOURCES.clear();runner.EPG_PROGRAMME_SOURCES.update(before)
            real=dict(runner.EPG_PROGRAMME_SOURCES)
            try:
                runner.apply_epg_overrides()
                for tvg_id in expected:
                    self.assertFalse(
                        any(name=='gt' for name,_ in runner.epg_source_chain(tvg_id)),
                        'la purga de Lista 2 ya no debe conservar fuentes gt',
                    )
            finally:
                runner.EPG_PROGRAMME_SOURCES.clear();runner.EPG_PROGRAMME_SOURCES.update(real)

    def test_lum_devotional_without_exact_current_programme_stays_pending(self):
        audit=json.loads(AUDIT.read_text(encoding='utf-8'))
        row=next(r for r in audit['channels'] if r['tvgId']=='PublicDirect.a712127b104cc2260c6fedc0')
        guide=row['epg']
        self.assertEqual('pending',guide['status'])
        self.assertEqual('no_exact_current_programme_match',guide['reason'])
        self.assertEqual(0,guide['candidateCount'])
        self.assertFalse(guide.get('source'))
        self.assertIn('3er Plan de Salvación',guide['evidence'])
        self.assertIn('at least 12 continuous future hours',guide['evidence'])

    def test_aym_baseball_without_exact_event_stays_pending(self):
        audit=json.loads(AUDIT.read_text(encoding='utf-8'))
        row=next(r for r in audit['channels'] if r['tvgId']=='PublicDirect.7e481ae905cfde3a83c3ccfe')
        guide=row['epg']
        self.assertEqual('pending',guide['status'])
        self.assertEqual('regional_feed_not_identified',guide['reason'])
        self.assertEqual(0,guide['candidateCount'])
        self.assertFalse(guide.get('source'))
        self.assertIn('baseball game',guide['evidence'])
        self.assertIn('exact current event/feed',guide['evidence'])

    def test_multicinema_without_movie_title_stays_pending(self):
        audit=json.loads(AUDIT.read_text(encoding='utf-8'))
        row=next(r for r in audit['channels'] if r['tvgId']=='PublicDirect.7d829b68f0e63dbdd397a468')
        guide=row['epg']
        self.assertEqual('pending',guide['status'])
        self.assertEqual('programme_title_not_identified',guide['reason'])
        self.assertEqual(0,guide['candidateCount'])
        self.assertFalse(guide.get('source'))
        self.assertIn('HLS reopening/retry 3/3',guide['evidence'])
        self.assertIn('544x480 and 6.9 FPS',guide['evidence'])

    def test_fox_sports_el_salvador_match_has_no_exact_epg_candidate(self):
        audit=json.loads(AUDIT.read_text(encoding='utf-8'))
        row=next(r for r in audit['channels'] if r['tvgId']=='PublicDirect.cbbf16d047322fe020949bf8')
        guide=row['epg']
        self.assertEqual('pending',guide['status'])
        self.assertEqual('no_exact_current_programme_match',guide['reason'])
        self.assertEqual(2,guide['candidateCount'])
        self.assertFalse(guide.get('source'))
        self.assertIn('Liga de Ascenso de El Salvador',guide['evidence'])
        self.assertIn('Fox Gol Femenil',guide['evidence'])
        self.assertIn('AEW Collision',guide['evidence'])

    def test_new_assets_are_local_originals_with_the_recorded_hash(self):
        audit=json.loads(AUDIT.read_text(encoding='utf-8'))
        self.assertEqual(234,sum(bool(r['logoPath']) for r in audit['channels']))
        for asset in audit['assets']:
            self.assertTrue(asset['path'].startswith('logos/catalogue/'))
            self.assertTrue(asset['path'].endswith(('.png','.svg')))
            # Logos optimizados el 2026-10-31: se acepta la versión liviana solo si el
            # contrato de optimización registra la cadena original -> optimizado.
            current=hashlib.sha256((ROOT/asset['path']).read_bytes()).hexdigest()
            optimized=OPTIMIZED.get(asset['path'],{})
            if optimized.get('original_sha256')==asset['sha256']:
                self.assertEqual(optimized['optimized_sha256'],current)
            else:
                self.assertEqual(asset['sha256'],current)
            self.assertTrue(asset['url'].startswith('https://'))

if __name__=='__main__': unittest.main()
