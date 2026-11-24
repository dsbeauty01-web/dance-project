// node tools/cf-worker/nova-gate/test.mjs  — offline tests with a fake RunPod, fake pod pages and a fake KV. No network.
import assert from "node:assert/strict";
import { _test } from "./worker.js";
const { cfg, start, status, stop, sweep } = _test;

function kv() {
  const m = new Map();
  return { m,
    async get(k, t) { const v = m.get(k); return v === undefined ? null : t === "json" ? JSON.parse(v) : v; },
    async put(k, v, o) { m.set(k, v); },
    async delete(k) { m.delete(k); },
    async list({ prefix }) { return { keys: [...m.keys()].filter((k) => k.startsWith(prefix)).map((name) => ({ name })), list_complete: true }; },
  };
}

function world(o = {}) {
  const w = { pods: o.pods || [], bal: o.bal ?? 12, created: [], deleted: [], stages: o.stages ?? null, page: o.page ?? false,
    rtlk: o.rtlk ?? "", soldOut: o.soldOut ?? 0 };
  w.fetch = async (url, init = {}) => {
    const R = (s, b) => new Response(typeof b === "string" ? b : JSON.stringify(b), { status: s });
    if (url.endsWith("/graphql")) {
      const q = JSON.parse(init.body).query;
      if (q.includes("podTerminate")) return R(200, { data: {} });
      return R(200, { data: { myself: { clientBalance: w.bal, networkVolumes: [{ id: "pqbavl4mct", dataCenterId: "EU-RO-1" }], pods: w.pods } } });
    }
    if (url.endsWith("/v2/pods") && init.method === "POST") {
      const b = JSON.parse(init.body); w.created.push(b);
      if (w.soldOut-- > 0) return R(400, { error: "There are no longer any instances available with the requested specifications." });
      const p = { id: "pod" + w.created.length, name: b.name, desiredStatus: "RUNNING", lastStartedAt: new Date().toISOString() };
      w.pods.push(p); return R(200, p);
    }
    if (url.includes("/v2/pods/") && init.method === "DELETE") { const id = url.split("/").pop(); w.deleted.push(id); w.pods = w.pods.filter((p) => p.id !== id); return R(200, {}); }
    if (url.includes("-8099.proxy.runpod.net/")) {
      const f = url.split("/").pop();
      if (f === "STAGES") return w.stages === null ? R(502, "") : R(200, w.stages);
      if (f === "rtlk.log") return R(200, w.rtlk);
      return R(404, "");
    }
    if (url.includes("-8765.proxy.runpod.net/")) return w.page ? R(200, "<html>") : R(502, "");
    throw new Error("unexpected " + url);
  };
  return w;
}

const base = { RUNPOD_API_KEY: "rp", OPENAI_API_KEY: "sk-x", LIVEKIT_URL: "wss://x", LIVEKIT_API_KEY: "a", LIVEKIT_API_SECRET: "b",
  MAYA_ASSETS_TOKEN: "t", NOVA_COMMIT: "77055579e5d3e0c1b9ee473bce5b5032fb7c3be9", ACCESS_CODE: "nova1" };
const mk = (w, extra = {}) => ({ ...base, ...extra, fetch: w.fetch, LOGS: extra.LOGS || kv() });
const body = async (r) => ({ s: r.status, d: JSON.parse(await r.text()) });
let n = 0; const ok = (m) => { n++; console.log("ok", n, m); };

{ // wrong code
  const w = world(), env = mk(w);
  const r = await body(await start(env, cfg(env), { code: "no" })); assert.equal(r.s, 403); assert.equal(w.created.length, 0); ok("wrong code refused, nothing created");
}
{ // low balance
  const w = world({ bal: 2.5 }), env = mk(w);
  const r = await body(await start(env, cfg(env), { code: "nova1" })); assert.equal(r.s, 503); assert.equal(w.created.length, 0); ok("balance under $3 refused");
}
{ // busy
  const w = world({ pods: [{ id: "old", name: "nova-play" }] }), env = mk(w);
  const r = await body(await start(env, cfg(env), { code: "nova1" })); assert.equal(r.s, 409); assert.equal(w.created.length, 0); ok("second player gets busy, no second pod");
}
{ // dry run
  const w = world(), env = mk(w, { DRY_RUN: "1" });
  const r = await body(await start(env, cfg(env), { code: "nova1" })); assert.equal(r.d.dry, true); assert.equal(w.created.length, 0);
  assert.ok(!JSON.stringify(r.d).includes("sk-x")); ok("dry run creates nothing and returns no key");
}
{ // sold out twice, then a machine; body shape; then booting -> ready -> stop with logs
  const w = world({ soldOut: 2 }), env = mk(w);
  const r = await body(await start(env, cfg(env), { code: "nova1", lang: "he" }));
  assert.equal(r.s, 200); assert.equal(w.created.length, 3);
  assert.equal(w.created[0].gpu.minVcpuCountPerGpu, 24); assert.equal(w.created[1].gpu.minVcpuCountPerGpu, 16); assert.equal(w.created[2].gpu.minVcpuCountPerGpu, undefined);
  const b = w.created[2];
  assert.deepEqual(b.dataCenterIds, ["EU-RO-1"]); assert.equal(b.mounts.network[0].volumeId, "pqbavl4mct"); assert.equal(b.cloud, "SECURE");
  assert.equal(b.env.NF_SKIP_A, "1"); assert.equal(b.env.NF_VOLUME_DIR, "/nfb"); assert.match(b.cmd[0], /77055579e5d3e0c1b9ee473bce5b5032fb7c3be9\/tools\/pod\/nova_final_pod\.sh/);
  assert.match(b.cmd[0], /NF_BRANCH=nova-go4/); assert.ok(!JSON.stringify(r.d).includes("sk-x"));
  ok("sold out -> retries 24/16/any cores; body = fast-boot nova-go4 play-only pod; no key returned");
  let s = await body(await status(env, cfg(env), r.d.t)); assert.equal(s.d.state, "booting"); ok("status booting before the pod answers");
  w.stages = "10:00 boot\n10:05 face :8010 http=200 {...}\n"; s = await body(await status(env, cfg(env), r.d.t)); assert.equal(s.d.state, "booting"); ok("face up but page not yet -> still booting");
  w.page = true; s = await body(await status(env, cfg(env), r.d.t)); assert.equal(s.d.state, "ready"); assert.equal(s.d.url, "https://pod3-8765.proxy.runpod.net/beta/freeze4?lang=he"); ok("ready -> game url with the chosen language");
  s = await body(await status(env, cfg(env), "wrongtoken")); assert.equal(s.d.state, "gone"); ok("someone else's token sees nothing");
  w.rtlk = "brain log";
  s = await body(await stop(env, cfg(env), r.d.t)); assert.deepEqual(w.deleted, ["pod3"]); assert.ok(s.d.saved >= 2);
  assert.ok([...env.LOGS.m.keys()].some((k) => k.endsWith(":pod3:rtlk.log"))); assert.equal(await env.LOGS.get("active"), null); ok("stop saves logs first, then terminates, frees the slot");
}
{ // cron: failed pod closed with logs
  const w = world({ pods: [{ id: "f1", name: "nova-play", lastStartedAt: new Date().toISOString() }], stages: "x\nFAILED: Ditto not ready\n" }), env = mk(w);
  const d = await sweep(env); assert.equal(d.length, 1); assert.match(d[0].why, /failed/); assert.deepEqual(w.deleted, ["f1"]); ok("cron closes a failed pod");
}
{ // cron: never ready after boot limit
  const w = world({ pods: [{ id: "s1", name: "nova-play", lastStartedAt: new Date(Date.now() - 25 * 60000).toISOString() }] }), env = mk(w);
  const d = await sweep(env); assert.match(d[0].why, /not ready/); ok("cron closes a pod stuck booting > 20 min");
}
{ // cron: idle
  const w = world({ pods: [{ id: "i1", name: "nova-play", lastStartedAt: new Date().toISOString() }], stages: "face :8010 http=200", page: true, rtlk: "same" }), env = mk(w);
  assert.equal((await sweep(env)).length, 0);
  const k = JSON.parse(env.LOGS.m.get("idle:i1")); k.since -= 11 * 60000; env.LOGS.m.set("idle:i1", JSON.stringify(k));
  const d = await sweep(env); assert.match(d[0].why, /idle/); assert.deepEqual(w.deleted, ["i1"]); ok("cron closes a pod whose brain log stopped growing for 10 min");
}
{ // cron: busy game keeps running
  const w = world({ pods: [{ id: "g1", name: "nova-play", lastStartedAt: new Date().toISOString() }], stages: "face :8010 http=200", page: true, rtlk: "a" }), env = mk(w);
  await sweep(env); w.rtlk = "ab"; const k = JSON.parse(env.LOGS.m.get("idle:g1")); k.since -= 11 * 60000; env.LOGS.m.set("idle:g1", JSON.stringify(k));
  assert.equal((await sweep(env)).length, 0); assert.equal(w.deleted.length, 0); ok("an active game is never closed as idle");
}
{ // cron: time limit
  const w = world({ pods: [{ id: "t1", name: "nova-play", lastStartedAt: new Date(Date.now() - 55 * 60000).toISOString() }], stages: "face :8010 http=200", page: true }), env = mk(w);
  const d = await sweep(env); assert.match(d[0].why, /time limit/); ok("cron closes at the time limit");
}
{ // cron never touches other pods
  const w = world({ pods: [{ id: "z1", name: "zq-cohost-live", lastStartedAt: new Date(Date.now() - 90 * 60000).toISOString() }] }), env = mk(w);
  assert.equal((await sweep(env)).length, 0); assert.equal(w.deleted.length, 0); ok("cron never touches Zara/Maya or any other pod");
}
console.log(`ALL ${n} PASSED`);
