"""Verify staged component files against the versioned package inventory."""
import hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
def verify(base=BASE):
 base=Path(base).resolve();m=json.loads((base/'catalog/components.json').read_text());out=[]
 if m.get('status')!='frozen':raise ValueError('Component inventory is not frozen')
 for x in m['files']:
  rel=Path(x['path']);p=(base/rel).resolve()
  if rel.is_absolute() or not p.is_relative_to(base):raise ValueError('Unsafe component path')
  h=hashlib.sha256();n=0
  with p.open('rb') as f:
   for b in iter(lambda:f.read(1048576),b''):h.update(b);n+=len(b)
  if n!=x['size'] or h.hexdigest()!=x['sha256']:raise ValueError('Component integrity failure: '+x['path'])
  out.append(x['path'])
 return {'status':'verified_now','component_files':len(out),'version':m['version'],'source_archive_embedded':False}
if __name__=='__main__':
 try:print(json.dumps(verify(),indent=2))
 except FileNotFoundError as e:raise SystemExit('Missing component: '+str(e.filename)+'. Restore the released data/ tree before full bundle verification; a source locator alone is not the embedded data.') from None
