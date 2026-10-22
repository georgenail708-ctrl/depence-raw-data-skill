"""Read an explicitly transformed full record, preserving original-source identity."""
import argparse,gzip,json
from pathlib import Path
from context_query import read_component
BASE=Path(__file__).resolve().parents[1]
def load(song,base=BASE):
 manifest=json.loads(read_component(base,'data/hygiene_v3/sanitized_record_manifest.json'))
 rows=[r for r in manifest['records'] if r['source_song_id']==song]
 if len(rows)!=1:raise ValueError('No unique transformed record; use approved raw source catalog for unaffected records')
 row=rows[0];payload=read_component(base,row['bundle_relative_path']);record=json.loads(gzip.decompress(payload))
 return {'classification':'transformed_not_original','source_identity':row,'record':record}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--song',required=True);p.add_argument('--base',default=str(BASE));a=p.parse_args();print(json.dumps(load(a.song,Path(a.base)),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
