// tiny static server (localhost = secure context → camera works) WITH HTTP Range support
// (range = required so <audio>/<video> can play + seek; without it currentTime stays 0).
import { createServer } from 'http';
import { readFile, stat } from 'fs/promises';
import { createReadStream } from 'fs';
import { join, extname, normalize } from 'path';
import { fileURLToPath } from 'url';
const root = fileURLToPath(new URL('.', import.meta.url));
const port = Number(process.argv[2]) || 8850;
const T = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.mp4':'video/mp4', '.mp3':'audio/mpeg', '.png':'image/png', '.jpg':'image/jpeg', '.riv':'application/octet-stream', '.y4m':'video/x-yuv4mpeg' };
createServer(async (req,res)=>{
  try{
    let p=decodeURIComponent(req.url.split('?')[0]); if(p==='/') p='/nova-play.html';
    const f=normalize(join(root,p)); if(!f.startsWith(root)){ res.writeHead(403).end('no'); return; }
    const ct = T[extname(f)]||'application/octet-stream';
    const st = await stat(f);
    const range = req.headers.range;
    if(range){                                   // 206 Partial Content (seek/stream)
      const m = /bytes=(\d*)-(\d*)/.exec(range);
      let start = m && m[1] ? parseInt(m[1],10) : 0;
      let end   = m && m[2] ? parseInt(m[2],10) : st.size-1;
      if(isNaN(start)) start=0; if(isNaN(end)||end>=st.size) end=st.size-1;
      if(start>end || start>=st.size){ res.writeHead(416,{'Content-Range':`bytes */${st.size}`}); res.end(); return; }
      res.writeHead(206,{ 'Content-Type':ct, 'Accept-Ranges':'bytes', 'Content-Range':`bytes ${start}-${end}/${st.size}`,
        'Content-Length':(end-start+1), 'Cache-Control':'no-store' });
      createReadStream(f,{start,end}).pipe(res);
    } else {
      const body=await readFile(f);
      res.writeHead(200,{ 'Content-Type':ct, 'Accept-Ranges':'bytes', 'Content-Length':st.size, 'Cache-Control':'no-store' });
      res.end(body);
    }
  }catch{ if(!res.headersSent) res.writeHead(404); res.end('not found'); }
}).listen(port,()=>console.log('nova on http://localhost:'+port+' (range-enabled)'));
