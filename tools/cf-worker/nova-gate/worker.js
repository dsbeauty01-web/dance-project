// nova-gate — a free Cloudflare Worker that wakes Nova's RunPod machine for a player, watches it, saves the game logs,
// and closes the machine when the game is over. Replaces the old paid Render worker (novapython, deleted 2026-11-23).
//
//   GET  /                 the lobby page (the link players open; always on, free)
//   POST /api/start        {code, lang} -> starts ONE Nova pod (or answers "busy" if a game is already running)
//   GET  /api/status?t=    booting | ready (+ game url) | failed | gone
//   POST /api/stop         {t} -> saves the logs, then terminates the pod
//   GET  /api/logs?admin=  list of saved games;  /api/logs/<key>?admin=  one saved file
//   cron (every 5 min)     closes a pod that is over MAX_MIN, idle for IDLE_MIN, or failed — always saving logs first
//
// Secrets (wrangler secret put): RUNPOD_API_KEY, OPENAI_API_KEY, LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET,
// MAYA_ASSETS_TOKEN, ACCESS_CODE (players), ADMIN_CODE (logs). Plain vars: see wrangler.toml. Keys are never returned
// to a browser and never logged. DRY_RUN=1 = every RunPod write is skipped (reads still happen).

const V2 = "https://api.runpod.io/v2";
const GQL = "https://api.runpod.io/graphql";
const UA = "nova-final/1.0";
const SOLD_OUT = ["no longer any instances", "not available", "insufficient", "no gpu", "capacity", "unavailable",
  "no instances currently available", "no instances available"];
const LOG_FILES = ["STAGES", "rtlk.log", "A-console.log", "boot.log"];

const cfg = (env) => ({
  name: env.POD_NAME || "nova-play",
  commit: env.NOVA_COMMIT || "",
  branch: env.NOVA_BRANCH || "nova-go4",
  volume: env.NOVA_VOLUME || "pqbavl4mct",
  image: env.NOVA_IMAGE || "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04",
  floor: parseFloat(env.FLOOR || "3"),
  maxMin: parseFloat(env.MAX_MIN || "30"),
  idleMin: parseFloat(env.IDLE_MIN || "10"),
  bootMin: parseFloat(env.BOOT_MIN || "20"),
  vcpus: String(env.MIN_VCPU_TRIES || "24,16,0").split(",").map((x) => parseInt(x, 10)),
  dry: env.DRY_RUN === "1",
});

// ------------------------------------------------------------------ RunPod
async function rp(env, method, path, body) {
  const r = await env.fetch(V2 + path, {
    method, headers: { Authorization: "Bearer " + env.RUNPOD_API_KEY, "Content-Type": "application/json", Accept: "application/json", "User-Agent": UA },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const t = await r.text();
  let d = null; try { d = t ? JSON.parse(t) : {}; } catch { d = t; }
  return { status: r.status, data: d, text: t };
}

async function gql(env, query, variables) {
  const r = await env.fetch(GQL, {
    method: "POST", headers: { Authorization: "Bearer " + env.RUNPOD_API_KEY, "Content-Type": "application/json", "User-Agent": UA },
    body: JSON.stringify({ query, variables: variables || {} }),
  });
  const d = await r.json();
  if (d.errors) throw new Error("graphql: " + d.errors.map((e) => e.message).join("; ").slice(0, 300));
  return d.data || {};
}

async function account(env) {
  const d = await gql(env, "query { myself { clientBalance networkVolumes { id dataCenterId } pods { id name desiredStatus lastStartedAt } } }");
  return d.myself || {};
}

async function ourPods(env, c) {
  const me = await account(env);
  return { me, pods: (me.pods || []).filter((p) => p.name === c.name) };
}

function startCmd(c) {
  const url = `https://raw.githubusercontent.com/dsbeauty01-web/dance-project/${c.commit}/tools/pod/nova_final_pod.sh`;
  return `mkdir -p /root/out; curl -fsSL ${url} -o /root/f4.sh >> /root/out/fetch.log 2>&1; NF_BRANCH=${c.branch} bash /root/f4.sh; sleep infinity`;
}

function createBody(env, c, dc, vcpu) {
  const gpu = { id: "NVIDIA GeForce RTX 4090", count: 1 };
  if (vcpu > 0) gpu.minVcpuCountPerGpu = vcpu;
  return {
    name: c.name, image: c.image, gpu, cloud: "SECURE", disk: 60,
    mounts: { network: [{ volumeId: c.volume, path: "/nfb" }] }, dataCenterIds: [dc],
    ports: ["8099/http", "8765/http"], entrypoint: ["/bin/bash", "-c"], cmd: [startCmd(c)],
    env: {
      OPENAI_API_KEY: env.OPENAI_API_KEY, LIVEKIT_URL: env.LIVEKIT_URL, LIVEKIT_API_KEY: env.LIVEKIT_API_KEY,
      LIVEKIT_API_SECRET: env.LIVEKIT_API_SECRET, MAYA_ASSETS_TOKEN: env.MAYA_ASSETS_TOKEN,
      // play-only pod: no proof run. The pod's own self-stop is a backstop only (cron closes it first).
      NF_SKIP_W: "1", NF_SKIP_A: "1", NF_GAMES: "none", NF_VOLUME_DIR: "/nfb",
      NF_WATCH_MIN: String(Math.round(c.maxMin + c.bootMin + 15)),
    },
  };
}

async function terminate(env, c, id) {
  if (c.dry) return { dry: true };
  const r = await rp(env, "DELETE", "/pods/" + encodeURIComponent(id));
  if (r.status >= 400 && r.status !== 404) {
    await gql(env, "mutation($id:String!){podTerminate(input:{podId:$id})}", { id });   // a kill must land
  }
  return { status: r.status };
}

// ------------------------------------------------------------------ the pod's own pages
const podUrl = (id, port, path) => `https://${id}-${port}.proxy.runpod.net/${path}`;
const gameUrl = (id, lang) => podUrl(id, 8765, `beta/freeze4?lang=${lang === "he" ? "he" : "en"}`);

async function podText(env, id, file, max) {
  try {
    const r = await env.fetch(podUrl(id, 8099, file), { headers: { "User-Agent": UA } });
    if (!r.ok) return null;
    const t = await r.text();
    return max && t.length > max ? t.slice(-max) : t;
  } catch { return null; }
}

async function podState(env, id) {
  const stages = await podText(env, id, "STAGES", 20000);
  if (stages === null) return { state: "booting", stage: "machine starting" };
  const last = stages.trim().split("\n").pop() || "";
  if (/FAILED/.test(stages)) return { state: "failed", stage: last };
  if (/face :8010 http=200/.test(stages)) {
    try {
      const r = await env.fetch(podUrl(id, 8765, "beta/freeze4"), { headers: { "User-Agent": UA } });
      if (r.ok) return { state: "ready", stage: last };
    } catch { /* not up yet */ }
  }
  return { state: "booting", stage: last };
}

// ------------------------------------------------------------------ logs (Cloudflare KV, free)
async function saveLogs(env, id, why) {
  if (!env.LOGS) return 0;
  const day = new Date().toISOString().slice(0, 16).replace(":", "");
  let n = 0;
  for (const f of LOG_FILES) {
    const t = await podText(env, id, f, 20 * 1024 * 1024);
    if (t) { await env.LOGS.put(`log:${day}:${id}:${f}`, t, { metadata: { why, size: t.length } }); n++; }
  }
  await env.LOGS.put(`log:${day}:${id}:CLOSED`, `${new Date().toISOString()} ${why}`, { metadata: { why } });
  return n;
}

async function closePod(env, c, id, why) {
  const saved = await saveLogs(env, id, why);
  const r = await terminate(env, c, id);
  if (env.LOGS) {
    const a = await env.LOGS.get("active", "json");
    if (a && a.pod === id) await env.LOGS.delete("active");
  }
  return { saved, ...r };
}

// ------------------------------------------------------------------ http
const J = (d, s = 200) => new Response(JSON.stringify(d), { status: s, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });

function token() {
  const b = new Uint8Array(18); crypto.getRandomValues(b);
  return Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
}

async function start(env, c, body) {
  if (env.ACCESS_CODE && body.code !== env.ACCESS_CODE) return J({ error: "wrong code" }, 403);
  if (!c.commit) return J({ error: "NOVA_COMMIT is not set" }, 500);
  const { me, pods } = await ourPods(env, c);
  if (pods.length) return J({ busy: true, message: "Nova is playing with someone else right now. Try again in a few minutes." }, 409);
  const bal = parseFloat(me.clientBalance);
  if (!(bal >= c.floor)) return J({ error: "Nova is resting (account low). The owner has been told." }, 503);
  const vol = (me.networkVolumes || []).find((v) => v.id === c.volume);
  if (!vol) return J({ error: "Nova's storage was not found" }, 500);
  let last = "";
  for (const v of c.vcpus) {
    const b = createBody(env, c, vol.dataCenterId, v);
    if (c.dry) {
      const t = token();
      return J({ dry: true, t, body: { ...b, env: Object.keys(b.env) } });
    }
    const r = await rp(env, "POST", "/pods", b);
    if (r.status < 300 && r.data && r.data.id) {
      const t = token();
      await env.LOGS?.put("active", JSON.stringify({ pod: r.data.id, t, lang: body.lang === "he" ? "he" : "en", started: Date.now() }));
      return J({ t, pod: r.data.id });
    }
    last = String(r.text || "").slice(0, 300);
    if (!SOLD_OUT.some((h) => last.toLowerCase().includes(h))) break;   // a real error, not "no machine": stop trying
  }
  return J({ error: "No machine free right now. Try again in a few minutes.", detail: last.replace(/sk-[A-Za-z0-9_-]+/g, "") }, 503);
}

async function status(env, c, t) {
  const a = await env.LOGS?.get("active", "json");
  if (!a || a.t !== t) return J({ state: "gone" });
  const s = await podState(env, a.pod);
  if (s.state === "ready") s.url = gameUrl(a.pod, a.lang);
  s.minutes = Math.round((Date.now() - a.started) / 60000);
  return J(s);
}

async function stop(env, c, t) {
  const a = await env.LOGS?.get("active", "json");
  if (!a || a.t !== t) return J({ ok: true, gone: true });
  return J(await closePod(env, c, a.pod, "player stopped"));
}

async function logs(env, url) {
  if (!env.ADMIN_CODE || url.searchParams.get("admin") !== env.ADMIN_CODE) return J({ error: "no" }, 403);
  const key = decodeURIComponent(url.pathname.slice("/api/logs/".length));
  if (url.pathname.startsWith("/api/logs/") && key) {
    const v = await env.LOGS.get(key);
    return v === null ? J({ error: "not found" }, 404) : new Response(v, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
  }
  const out = []; let cursor;
  do {
    const l = await env.LOGS.list({ prefix: "log:", cursor });
    out.push(...l.keys.map((k) => ({ key: k.name, ...(k.metadata || {}) })));
    cursor = l.list_complete ? null : l.cursor;
  } while (cursor && out.length < 2000);
  return J(out.reverse());
}

// ------------------------------------------------------------------ cron: nothing runs forever
async function sweep(env) {
  const c = cfg(env);
  const { pods } = await ourPods(env, c);
  const a = await env.LOGS?.get("active", "json");
  const did = [];
  for (const p of pods) {
    const started = a && a.pod === p.id ? a.started : Date.parse(p.lastStartedAt || "") || Date.now();
    const age = (Date.now() - started) / 60000;
    const s = await podState(env, p.id);
    let why = null;
    if (s.state === "failed") why = "failed: " + s.stage.slice(0, 120);
    else if (s.state === "booting" && age > c.bootMin) why = `not ready after ${Math.round(age)} min`;
    else if (age > c.maxMin + c.bootMin) why = `time limit (${Math.round(age)} min)`;
    else if (s.state === "ready" && env.LOGS) {
      // idle = the brain log has not grown for IDLE_MIN (the player closed the tab)
      const log = await podText(env, p.id, "rtlk.log");
      const size = log ? log.length : 0;
      const k = "idle:" + p.id, prev = await env.LOGS.get(k, "json");
      if (!prev || prev.size !== size) await env.LOGS.put(k, JSON.stringify({ size, since: Date.now() }), { expirationTtl: 86400 });
      else if ((Date.now() - prev.since) / 60000 >= c.idleMin) why = `idle ${c.idleMin} min`;
    }
    if (why) did.push({ pod: p.id, why, ...(await closePod(env, c, p.id, why)) });
  }
  if (a && !pods.some((p) => p.id === a.pod)) await env.LOGS.delete("active");   // the pod is gone: free the slot
  return did;
}

export default {
  async fetch(req, env0) {
    const env = { fetch: (...x) => fetch(...x), ...env0 };
    const c = cfg(env);
    const url = new URL(req.url);
    try {
      if (req.method === "GET" && url.pathname === "/") return new Response(LOBBY, { headers: { "Content-Type": "text/html; charset=utf-8" } });
      if (req.method === "POST" && url.pathname === "/api/start") return await start(env, c, await req.json().catch(() => ({})));
      if (req.method === "GET" && url.pathname === "/api/status") return await status(env, c, url.searchParams.get("t") || "");
      if (req.method === "POST" && url.pathname === "/api/stop") return await stop(env, c, (await req.json().catch(() => ({}))).t || "");
      if (req.method === "GET" && url.pathname.startsWith("/api/logs")) return await logs(env, url);
      if (req.method === "GET" && url.pathname === "/api/health") return J({ ok: true, dry: c.dry, branch: c.branch, commit: c.commit.slice(0, 7) });
      return J({ error: "not found" }, 404);
    } catch (e) {
      return J({ error: "Something went wrong. Try again in a minute." , detail: String(e.message || e).slice(0, 200) }, 500);
    }
  },
  async scheduled(ev, env0, ctx) {
    const env = { fetch: (...x) => fetch(...x), ...env0 };
    ctx.waitUntil(sweep(env));
  },
};

export const _test = { cfg, createBody, start, status, stop, sweep, podState, saveLogs };

// ------------------------------------------------------------------ the lobby page
const LOBBY = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Play with Nova</title><style>
:root{--bg:#0d0b14;--fg:#f4efe6;--dim:#a79fb6;--gold:#f2c14e}
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at 50% 30%,#2a2140,var(--bg) 70%);color:var(--fg);font:17px/1.5 system-ui,sans-serif;padding:16px}
main{max-width:420px;width:100%;text-align:center}h1{font-size:34px;margin:0 0 6px;color:var(--gold)}p{color:var(--dim);margin:0 0 20px}
input,select,button{font:inherit;width:100%;padding:14px;border-radius:12px;border:1px solid #3b3350;background:#1a1526;color:var(--fg);margin-bottom:10px}
button{background:var(--gold);color:#1a1200;font-weight:700;border:0;cursor:pointer}button:disabled{opacity:.5;cursor:default}
#msg{min-height:3em;margin-top:8px}.bar{height:6px;border-radius:3px;background:#2a2238;overflow:hidden;margin:14px 0}.bar i{display:block;height:100%;width:0;background:var(--gold);transition:width 1s}
</style></head><body><main>
<h1>Nova</h1><p>Your dance friend. She takes a few minutes to wake up.</p>
<input id="code" placeholder="Access code" autocomplete="off">
<select id="lang"><option value="en">English</option><option value="he">עברית</option></select>
<button id="go">Wake Nova</button>
<div class="bar"><i id="bar"></i></div><div id="msg"></div>
</main><script>
const $=(i)=>document.getElementById(i);let T=null,t0=0;
try{const q=new URLSearchParams(location.search);if(q.get("code"))$("code").value=q.get("code");if(q.get("lang"))$("lang").value=q.get("lang")}catch{}
async function poll(){const r=await fetch("/api/status?t="+T).then(r=>r.json()).catch(()=>({state:"booting"}));
 const m=Math.min(95,((Date.now()-t0)/1000/480)*100);$("bar").style.width=m+"%";
 if(r.state==="ready"){$("bar").style.width="100%";$("msg").textContent="Nova is awake!";location.href=r.url;return}
 if(r.state==="failed"||r.state==="gone"){$("msg").textContent="Nova could not wake up this time. Please try again.";$("go").disabled=false;return}
 $("msg").textContent="Waking Nova up… (about 5–8 minutes)";setTimeout(poll,10000)}
$("go").onclick=async()=>{$("go").disabled=true;$("msg").textContent="Starting…";
 const r=await fetch("/api/start",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({code:$("code").value.trim(),lang:$("lang").value})});
 const d=await r.json().catch(()=>({}));if(!r.ok||!d.t){$("msg").textContent=d.message||d.error||"Please try again.";$("go").disabled=false;return}
 if(d.dry){$("msg").textContent="Test mode: no machine was started.";$("go").disabled=false;return}
 T=d.t;t0=Date.now();poll()};
</script></body></html>`;
