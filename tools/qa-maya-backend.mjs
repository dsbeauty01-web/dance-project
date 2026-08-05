// tools/qa-maya-backend.mjs — CONTRACT TEST for maya-server (08 standing rule 5).
//
// "The freeze game died on an untested contract; Maya won't."
//
// What this proves: every director/n8n route actually REACHES the stage socket with
// the right shape. It does NOT need a pod, a GPU or an OpenAI key — it stands in for
// the stage with a plain websocket client and asserts what arrives. That is the whole
// point: the switchboard can be verified in seconds, on any machine, before a stream.
//
// Run:  node tools/qa-maya-backend.mjs [base-url]        (default http://localhost:8000)
// Exit: 0 all passed · 1 any failure
const BASE = (process.argv[2] || 'http://localhost:8000').replace(/\/+$/, '');
const WSU = BASE.replace(/^http/, 'ws') + '/ws/stage';

let pass = 0, fail = 0;
const inbox = [];
const ok = (name, cond, extra = '') => {
  if (cond) { pass++; console.log('  PASS  ' + name); }
  else { fail++; console.log('  FAIL  ' + name + (extra ? ' — ' + extra : '')); }
};
const post = async (path, body) => {
  const r = await fetch(BASE + path, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body || {})
  });
  return { status: r.status, json: await r.json().catch(() => null) };
};
// Wait for a frame matching `pred`, up to `ms`. Waiting on the EVENT, never on a fixed
// quiet window — the GATE-1 harness scored two false failures because a late response
// crossed a fixed phase boundary (STATUS.md §4, "test harness pacing").
const waitFor = (pred, ms = 4000) => new Promise((res, rej) => {
  const hit = inbox.find(pred);
  if (hit) return res(hit);
  const t0 = Date.now();
  const iv = setInterval(() => {
    const h = inbox.find(pred);
    if (h) { clearInterval(iv); res(h); }
    else if (Date.now() - t0 > ms) { clearInterval(iv); rej(new Error('timeout')); }
  }, 25);
});

const main = async () => {
  console.log('MAYA CONTRACT TEST — ' + BASE);

  // 0) server alive
  const health = await fetch(BASE + '/health').then(r => r.json()).catch(() => null);
  ok('server health', !!(health && health.ok), JSON.stringify(health));
  if (!health) { console.log('\nno server — start it: python app.py'); process.exit(1); }

  // 1) NO SILENT DROPS: with no stage connected, a director call must FAIL LOUDLY.
  const orphan = await post('/say', { text: 'nobody is listening' });
  ok('say with no stage -> 409 (not a silent drop)', orphan.status === 409,
     'got ' + orphan.status);

  // 2) connect a stand-in stage
  const ws = new WebSocket(WSU);
  ws.addEventListener('message', e => { try { inbox.push(JSON.parse(e.data)); } catch {} });
  await new Promise((res, rej) => {
    ws.addEventListener('open', res);
    ws.addEventListener('error', () => rej(new Error('stage socket failed')));
    setTimeout(() => rej(new Error('stage socket timeout')), 5000);
  });
  await waitFor(m => m.act === 'hello').then(
    h => ok('stage gets hello + state + notes', !!h.state && typeof h.notes === 'string'),
    () => ok('stage gets hello + state + notes', false, 'no hello'));

  await post('/session/start', { answer_mode: 'approve' });

  // 3) every director route lands on the stage with the right shape
  const cases = [
    ['say',     { text: 'שלום לכולם' },              m => m.act === 'say' && m.text === 'שלום לכולם'],
    ['cue',     { intent: 'tease the price' },        m => m.act === 'cue' && m.intent === 'tease the price'],
    ['gesture', { name: 'wave' },                     m => m.act === 'gesture' && m.name === 'wave'],
    ['hold',    { on: true },                         m => m.act === 'hold' && m.on === true],
    ['hold',    { on: false },                        m => m.act === 'hold' && m.on === false],
    ['kill',    {},                                   m => m.act === 'kill'],
  ];
  for (const [route, body, pred] of cases) {
    await post('/' + route, body);
    await waitFor(pred).then(() => ok(route + ' reaches the stage', true),
                             () => ok(route + ' reaches the stage', false, 'never arrived'));
  }

  // 4) scene carries the product AND its notes together (no stale-notes window)
  await post('/hold', { on: false });
  await post('/scene', { scene: 'offer', product_id: 'cream-night' });
  await waitFor(m => m.act === 'scene').then(
    m => {
      ok('scene reaches the stage', m.name === 'offer');
      ok('scene carries the new product', m.product && m.product.id === 'cream-night');
      ok('scene carries matching notes (TRUTH LAW)',
         typeof m.notes === 'string' && m.notes.includes('119 ILS'), m.notes);
    },
    () => ok('scene reaches the stage', false, 'never arrived'));

  // 5) unknown product must be refused, not silently ignored
  const bad = await post('/scene', { scene: 'open', product_id: 'does-not-exist' });
  ok('unknown product -> 404', bad.status === 404, 'got ' + bad.status);

  // 6) chat path: approve mode queues, approval releases, rail still shows it
  const q = await post('/chat-in', { name: 'דנה', text: 'כמה עולה?', priority: 'question_product', msg_id: 'qa1' });
  ok('chat-in queues in approve mode', q.json && q.json.queued === 'qa1', JSON.stringify(q.json));
  await waitFor(m => m.act === 'rail' && m.name === 'דנה').then(
    () => ok('queued message still shows on the rail', true),
    () => ok('queued message still shows on the rail', false));
  await post('/chat-approve/qa1', {});
  await waitFor(m => m.act === 'chat' && m.name === 'דנה').then(
    m => ok('approve releases it to the brain', m.text === 'כמה עולה?'),
    () => ok('approve releases it to the brain', false, 'never arrived'));

  // 7) moderation: abuse never reaches the queue or the public rail
  const abusive = await post('/chat-in', { name: 'troll', text: 'you fuck', msg_id: 'qa2' });
  ok('abusive message dropped', abusive.json && abusive.json.dropped === 'abuse',
     JSON.stringify(abusive.json));

  // 8) auto mode answers without the operator
  await post('/answer-mode', { mode: 'auto' });
  await post('/chat-in', { name: 'יוסי', text: 'יש משלוח?', msg_id: 'qa3' });
  await waitFor(m => m.act === 'chat' && m.name === 'יוסי').then(
    () => ok('auto mode sends straight to the brain', true),
    () => ok('auto mode sends straight to the brain', false, 'never arrived'));

  // 9) forbidden claim in an outbound line raises an alert (post-check alarm)
  ws.send(JSON.stringify({ ev: 'said', text: 'this cream is clinically proven to work' }));
  await new Promise(r => setTimeout(r, 300));
  const st = await fetch(BASE + '/state').then(r => r.json());
  ok('outbound forbidden claim alerts', st.vitals.said_lines >= 1);

  // 10) latency loop closes: an answered message produces a median
  ok('answered count tracked', st.vitals.messages_answered >= 1,
     JSON.stringify(st.vitals));

  // 11) lead mirror
  await post('/lead', { name: 'מיכל', message: 'אני רוצה' });
  const st2 = await fetch(BASE + '/state').then(r => r.json());
  ok('lead counted for the director', st2.vitals.leads === 1);

  // 12) session report is written with honest nulls, not invented numbers
  const end = await post('/session/end', {});
  const rep = end.json && end.json.report;
  ok('session report written', !!rep && rep.peak_viewers === null && rep.pod_cost_usd === null,
     JSON.stringify(rep && { peak: rep.peak_viewers, pod: rep.pod_cost_usd }));

  ws.close();
  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
};

main().catch(e => { console.error('HARNESS ERROR', e); process.exit(1); });
