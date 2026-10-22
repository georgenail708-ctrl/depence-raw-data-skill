import hashlib, importlib.util, io, json, pathlib, struct, sys, subprocess, tempfile, unittest, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from archive_reader import Parts, extract
from unittest.mock import patch
class ArchiveReaderTests(unittest.TestCase):
 def setUp(self):
  self.catalog_guard=patch('archive_reader.approved_entry',side_effect=lambda e:e);self.catalog_guard.start()
 def tearDown(self):self.catalog_guard.stop()

 def build(self, root, payload, method=zipfile.ZIP_DEFLATED, zip64=False, descriptor=False):
  class NonSeek(io.BytesIO):
   def seekable(self):return False
   def seek(self,*a):raise io.UnsupportedOperation()
  b=NonSeek() if descriptor else io.BytesIO()
  with zipfile.ZipFile(b,'w',compression=method) as z:
   if zip64:
    with z.open('测试/raw.bin','w',force_zip64=True) as f:f.write(payload)
   else:z.writestr('测试/raw.bin',payload)
  raw=b.getvalue()
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   i=z.infolist()[0];e={'name':i.filename,'compressed_size':i.compress_size,'uncompressed_size':i.file_size,'flags':i.flag_bits,'method':i.compress_type,'crc32':f'{i.CRC:08x}','local_header_offset':i.header_offset,'sha256':hashlib.sha256(payload).hexdigest()}
  ps=[]
  for n,o in enumerate(range(0,len(raw),71)):
   part=raw[o:o+71];name=f'input.{n:03d}';(root/name).write_bytes(part)
   ps.append({'filename':name,'offset':o,'size':len(part),'sha256':hashlib.sha256(part).hexdigest()})
  m={'parts':ps,'archive_sha256':hashlib.sha256(raw).hexdigest()}
  return Parts(root,m),e
 def test_variants_cross_part_and_hash(self):
  for method,zip64,descriptor in [(0,False,False),(8,False,False),(8,True,False),(8,True,True),(8,False,True)]:
   with self.subTest(method=method,zip64=zip64,descriptor=descriptor), tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d);raw=bytes(range(256))*100;parts,e=self.build(p,raw,method,zip64,descriptor)
    self.assertEqual(parts.verify()['status'],'verified_now')
    r=extract(e,parts,p/'out');self.assertEqual((p/'out').read_bytes(),raw);self.assertTrue(r['expected_member_sha256_checked'])
 def test_crc_and_sha_failure_do_not_publish(self):
  for key,val in [('crc32','00000000'),('sha256','0'*64)]:
   with tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d);parts,e=self.build(p,b'abc'*100);e[key]=val
    with self.assertRaises(ValueError):extract(e,parts,p/'out')
    self.assertFalse((p/'out').exists());self.assertFalse(list(p.glob('.member-*')))
 def test_budget_missing_size_and_no_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);parts,e=self.build(p,b'abc'*100)
   with self.assertRaises(ValueError):extract(e,parts,p/'out',2)
   (p/'out').write_bytes(b'keep')
   with self.assertRaises(FileExistsError):extract(e,parts,p/'out')
   self.assertEqual((p/'out').read_bytes(),b'keep')
   (p/'input.000').write_bytes(b'bad')
   with self.assertRaises(ValueError):parts.verify()
   with self.assertRaises(ValueError):parts.read(0,10)
 def test_cli_excludes_unlisted_member(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);r=subprocess.run([sys.executable,str(ROOT/'scripts/archive_reader.py'),'--parts-dir',d,'extract','--member','../../not-allowed','--out',str(p/'out')],capture_output=True,text=True)
   self.assertNotEqual(r.returncode,0);self.assertIn('excluded',r.stderr);self.assertFalse((p/'out').exists())
 def test_empty_payload(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);parts,e=self.build(p,b'');extract(e,parts,p/'out');self.assertEqual((p/'out').read_bytes(),b'')
if __name__=='__main__':unittest.main()
