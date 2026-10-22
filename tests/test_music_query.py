import gzip,hashlib,json,pathlib,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from music_query import load,page
class MusicTests(unittest.TestCase):
 def test_source_and_derivative_tamper_gates(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'catalog').mkdir();(p/'data/music').mkdir(parents=True)
   raw=b'MThd synthetic bytes';sha=hashlib.sha256(raw).hexdigest()
   row={'source_song_id':'test','reference_midi':{'member':'requested.mid','raw_file':'raw.mid','events_file':'events.gz','source_sha256':sha}}
   payload={'data/music/song_music_catalog.jsonl':(json.dumps(row)+'\n').encode(),'data/music/raw.mid':raw,'data/music/events.gz':gzip.compress(b'{"source":{"archive_member":"canonical_alias.mid"},"events":[1,2],"all_track_events":[{"track":0,"source_byte_offset":22},{"track":1,"source_byte_offset":40}]}')}
   files=[]
   for rel,b in payload.items():(p/rel).write_bytes(b);files.append({'path':rel,'size':len(b),'sha256':hashlib.sha256(b).hexdigest()})
   (p/'catalog/components.json').write_text(json.dumps({'status':'frozen','files':files}))
   self.assertEqual(load('test',p)['reference_events']['events'],[1,2])
   first=page('test',cursor=0,limit=1,base=p);last=page('test',cursor=first['next_cursor'],limit=1,base=p)
   self.assertFalse(first['eof']);self.assertTrue(last['eof']);self.assertEqual(last['items'][0]['record']['source_byte_offset'],40);self.assertEqual(last['items'][0]['absolute_record_index'],1)
   self.assertEqual(first['requested_source_identity']['member'],'requested.mid');self.assertEqual(first['canonical_event_byte_source']['archive_member'],'canonical_alias.mid');self.assertIn('unverified',first['clock_domains']['saved_offsets'])
   (p/'data/music/events.gz').write_bytes(gzip.compress(b'{"events":[3]}'))
   with self.assertRaises(ValueError):load('test',p)
   with self.assertRaises(ValueError):load('other',p)
if __name__=='__main__':unittest.main()
