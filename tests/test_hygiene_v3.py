import pathlib,sys,json,tempfile,unittest,gzip,hashlib
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import archive_reader
class HygieneTests(unittest.TestCase):
 def test_approved_catalog_only_before_any_read(self):
  class NoRead:
   def read(self,*args):raise AssertionError('Excluded input must never be read')
  for name in ['02_工具链/private.py','00_private.md','01_数据集_songs/土库曼斯坦_blk0_0s.record.json']:
   with self.assertRaises(ValueError):archive_reader.extract({'name':name},NoRead(),'unused')
 def test_changed_locator_rejected(self):
  entries=json.loads((ROOT/'catalog/archive_entries.json').read_text())['entries'];e=dict(entries[0]);e['local_header_offset']+=1
  with self.assertRaises(ValueError):archive_reader.approved_entry(e)
 def test_sanitized_record_hashes_and_declared_scope(self):
  manifest=json.loads((ROOT/'data/hygiene_v3/sanitized_record_manifest.json').read_text())
  self.assertEqual(len(manifest['records']),8)
  for row in manifest['records']:
   payload=(ROOT/row['bundle_relative_path']).read_bytes();raw=gzip.decompress(payload)
   self.assertEqual(hashlib.sha256(payload).hexdigest(),row['sanitized_gzip_sha256'])
   self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sanitized_sha256'])
   self.assertEqual(row['removed_json_pointers'],['/provenance/archive_decrypted'])
   self.assertEqual(row['status'],'transformed_not_original')
   self.assertNotIn('archive_decrypted',json.loads(raw).get('provenance',{}))
 def test_approved_entry_unchanged(self):
  e=json.loads((ROOT/'catalog/archive_entries.json').read_text())['entries'][0]
  self.assertEqual(archive_reader.approved_entry(e),e)
if __name__=='__main__':unittest.main()
