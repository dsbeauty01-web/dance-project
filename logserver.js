// Tiny local server: serves the dance-project files AND records session telemetry.
// Open the game at  http://localhost:8787/nova-join.html  (or nova-wave.html).
// Every session auto-appends detection data to sessions.jsonl, which Claude reads.
const http=require('http'), fs=require('fs'), path=require('path');
const ROOT=__dirname, LOG=path.join(ROOT,'sessions.jsonl');
const MIME={'.html':'text/html','.js':'text/javascript','.css':'text/css','.mp4':'video/mp4',
  '.png':'image/png','.jpg':'image/jpeg','.json':'application/json','.riv':'application/octet-stream'};
http.createServer((req,res)=>{
  res.setHeader('Access-Control-Allow-Origin','*');
  res.setHeader('Access-Control-Allow-Headers','content-type');
  if(req.method==='OPTIONS'){ res.writeHead(204); res.end(); return; }
  if(req.method==='POST' && req.url==='/log'){
    let b=''; req.on('data',c=>b+=c); req.on('end',()=>{ try{ fs.appendFileSync(LOG, b.replace(/\r?\n/g,' ')+'\n'); }catch(e){} res.writeHead(200); res.end('ok'); });
    return;
  }
  let p=decodeURIComponent((req.url||'/').split('?')[0]); if(p==='/') p='/nova-join.html';
  const fp=path.join(ROOT,p);
  if(!fp.startsWith(ROOT)){ res.writeHead(403); res.end('no'); return; }
  fs.readFile(fp,(e,data)=>{
    if(e){ res.writeHead(404); res.end('not found'); return; }
    res.writeHead(200,{'Content-Type':MIME[path.extname(fp).toLowerCase()]||'application/octet-stream'});
    res.end(data);
  });
}).listen(8787,()=>console.log('logserver on http://localhost:8787  → sessions.jsonl'));
