import hashlib,json,pathlib,sys,tempfile,unittest,zlib
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from traversal import initialize,summary,record_window,verify_member,covered
class TraversalTests(unittest.TestCase):
 def test_empty_member_requires_explicit_disposition(self):
  self.assertFalse(covered([],0))
  a={'bytes':0,'bytes_verified':{'bytes':0},'raw_read':[],'semantic_reviewed':[]}
  record_window(a,'raw_read',0,0,'empty-member-check','Confirmed empty source, no payload')
  record_window(a,'semantic_reviewed',0,0,'empty-member-check','No semantic payload; explicit disposition')
  self.assertTrue(covered(a['semantic_reviewed'],0))
 def test_no_alias_skip_no_silent_extra_no_hash_means_review(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'registry').mkdir();(p/'music').mkdir();(p/'dmx').mkdir();(p/'dmx/dmx_manifest_v1.jsonl').write_text('');raw=b'1234';sha=hashlib.sha256(raw).hexdigest()
   entries=[{'name':'a','uncompressed_size':4,'sha256':sha,'crc32':f'{zlib.crc32(raw):08x}'},{'name':'unassigned','uncompressed_size':4,'crc32':f'{zlib.crc32(raw):08x}'}]
   registry=[{'source_song_id':x,'group_id':x,'assets':{'record':{'member':'a'}},'duplicate_of_source_song_id':'a' if x=='b' else None} for x in ['a','b']]
   (p/'registry/canonical_registry_v3.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in registry));(p/'registry/registry_policy_overlay_v4.jsonl').write_text('');(p/'music/song_music_catalog.jsonl').write_text('')
   l=initialize(p,entries);self.assertEqual(summary(l)['source_groups'],2);self.assertEqual(summary(l)['unique_members'],2);self.assertFalse(summary(l)['all_available_assets_review_reported'])
   a=l['sources'][0]['assets'][0]
   with self.assertRaises(ValueError):record_window(a,'raw_read',0,4,'e','n')
   (p/'raw').write_bytes(raw);verify_member(a,p/'raw');self.assertEqual(summary(l)['bytes_verified'],1);self.assertEqual(summary(l)['unique_members_bytes_verified'],1);self.assertEqual(summary(l)['raw_read_full_reported'],0)
   with self.assertRaises(ValueError):record_window(a,'semantic_reviewed',0,4,'e','n')
   record_window(a,'raw_read',0,2,'e','n');self.assertFalse(covered(a['raw_read'],4));record_window(a,'raw_read',2,4,'e','n');self.assertTrue(covered(a['raw_read'],4))
   record_window(a,'semantic_reviewed',0,4,'e','complete actual parsed sequence');self.assertEqual(summary(l)['semantic_review_full_reported'],1);self.assertFalse(summary(l)['all_available_assets_review_reported'])
if __name__=='__main__':unittest.main()
