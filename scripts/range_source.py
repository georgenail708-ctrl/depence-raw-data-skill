"""Optional credential-free bounded range adapter. Grants live only in caller memory."""
import bisect, time, urllib.request, urllib.error

class RangeParts:
    """fetch(part_index, local_start, byte_count, expected_part_size) -> exact bytes.
    Caller authenticates only official, metadata-pinned source IDs. No automatic fetch.
    Compatible with archive_reader.extract(entry, range_parts, target).
    """
    def __init__(self, manifest, fetch, max_request=1024*1024):
        self.parts=manifest['parts']; self.starts=[p['offset'] for p in self.parts]
        self.size=sum(p['size'] for p in self.parts);self.fetch=fetch;self.max_request=max_request
    def read(self,offset,length):
        if offset<0 or length<0 or length>self.max_request or offset+length>self.size:raise ValueError('Range bounds')
        out=bytearray()
        while length:
            i=bisect.bisect_right(self.starts,offset)-1;p=self.parts[i];local=offset-p['offset'];n=min(length,p['size']-local)
            b=self.fetch(i,local,n,p['size'])
            if not isinstance(b,bytes) or len(b)!=n:raise ValueError('Range returned wrong byte count')
            out.extend(b);offset+=n;length-=n
        return bytes(out)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

class EphemeralHTTP:
    """Caller supplies grant(part) -> {url, expires_at_epoch}; never serialize grants.
    Caller must pin Drive id, filename, size and modified_time before issuing a grant.
    Expired/failed grant stops without retry; inspect metadata before requesting a new one.
    """
    def __init__(self,grant,opener=None,refresh_margin=60):
        self.grant=grant;self.opener=opener or urllib.request.build_opener(NoRedirect())
        self.refresh_margin=refresh_margin;self.failed=set()
    def __call__(self,part,start,length,total):
        if part in self.failed:raise RuntimeError('Previous range failed; caller must investigate and replace adapter')
        g=self.grant(part)
        if time.time()+self.refresh_margin>=g['expires_at_epoch']:raise RuntimeError('Grant expiry too near; no request sent')
        if not g['url'].startswith('https://'):raise ValueError('HTTPS grant required')
        request=urllib.request.Request(g['url'],headers={'Range':f'bytes={start}-{start+length-1}','Accept-Encoding':'identity'})
        try:
            with self.opener.open(request,timeout=60) as r:
                if r.status!=206 or r.headers.get('Content-Range')!=f'bytes {start}-{start+length-1}/{total}':raise ValueError('Range status or Content-Range mismatch')
                if r.headers.get('Content-Encoding','identity')!='identity':raise ValueError('Unexpected HTTP content encoding')
                cl=r.headers.get('Content-Length')
                if cl is not None and int(cl)!=length:raise ValueError('Range Content-Length mismatch')
                b=r.read(length+1)
                if len(b)!=length:raise ValueError('Range response length mismatch')
                return b
        except Exception as e:
            self.failed.add(part)
            # Deliberately omit exception URL, headers, response body and credential.
            raise RuntimeError('Range request failed: '+type(e).__name__+'; stopped without retry') from None
