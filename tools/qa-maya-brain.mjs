// tools/qa-maya-brain.mjs — LIVE brain test (T3 SAY-verbatim + T2 tag leak, end to end).
//
// Talks to a running maya_rt.py exactly as the pod page does, and asserts what she
// actually says. This is the half of the contract that a mock cannot cover: it costs a
// few cents of OpenAI Realtime and it is the only way to prove SAY is spoken WORD FOR
// WORD, which STATUS.md listed as unconfirmed.
//
//   node tools/qa-maya-brain.mjs wss://<pod>-8765.proxy.runpod.net/rt
//
// WARNING: this opens a REAL Realtime session. If the stage page is open at the same
// time she has two brains and speaks twice. Run it with the stage closed.
const URL = process.argv[2];
if (!URL) { console.error('usage: node tools/qa-maya-brain.mjs wss://<pod>-8765…/rt'); process.exit(2); }

let pass = 0, fail = 0;
const ok = (n, c, extra = '') => { if (c) { pass++; console.log('  PASS  ' + n); }
                                   else { fail++; console.log('  FAIL  ' + n + (extra ? ' — ' + extra : '')); } };

const log = [];
const ws = new WebSocket(URL);
const seen = [];
ws.addEventListener('message', e => { try { const m = JSON.parse(e.data); seen.push(m);
  if (m.type === 'log') log.push(m.msg); } catch {} });

const waitFor = (pred, ms, label) => new Promise(res => {
  const t0 = Date.now();
  const iv = setInterval(() => {
    const hit = seen.find(pred);
    if (hit) { clearInterval(iv); res(hit); }
    else if (Date.now() - t0 > ms) { clearInterval(iv); res(null); }
  }, 50);
});
const send = o => ws.send(JSON.stringify(o));
// Compare what she SAID to what we asked her to say. Punctuation and the niqqud-free
// spelling of a word are the model's business; the WORDS are the contract.
const norm = s => (s || '').replace(/[.,!?…"'׳״\-–—]/g, ' ').replace(/\s+/g, ' ').trim();

const main = async () => {
  console.log('MAYA BRAIN LIVE TEST — ' + URL);
  await new Promise((res, rej) => {
    ws.addEventListener('open', res);
    ws.addEventListener('error', () => rej(new Error('cannot connect')));
    setTimeout(() => rej(new Error('connect timeout')), 10000);
  });
  ok('brain socket open', true);

  // She greets herself on connect. Let that finish first — and use it as the T2 check,
  // because the opening line is exactly where the [WAVE] leak showed up.
  const greet = await waitFor(m => m.type === 'nova_done', 30000);
  if (greet) {
    ok('opening line has no bracketed tag (T2)', !/[\[\]]/.test(greet.text || ''), greet.text);
    ok('opening line is Hebrew (LANGUAGE LAW)', /[֐-׿]/.test(greet.text || ''), greet.text);
    const g = seen.find(m => m.type === 'gesture');
    ok('gesture fired from her own words (T2 keyword path)', !!g, 'no gesture frame');
    if (g) ok('greeting fired WAVE', g.tag === 'WAVE', g.tag);
  } else {
    ok('she opened the stream', false, 'no opening line in 30s');
  }

  // ── T3: SAY must be spoken VERBATIM ────────────────────────────────────────
  const LINE = 'הסרום הזה עולה מאה ארבעים ותשעה שקלים בלייב הזה בלבד';
  seen.length = 0;
  send({ type: 'say', text: LINE });
  const said = await waitFor(m => m.type === 'nova_done', 30000);
  if (said) {
    ok('SAY is spoken verbatim (T3)', norm(said.text) === norm(LINE),
       'sent: ' + LINE + ' | said: ' + said.text);
    ok('SAY line carries no bracketed tag', !/[\[\]]/.test(said.text || ''), said.text);
  } else {
    ok('SAY produced a line', false, 'nothing in 30s');
  }

  // ── hold gates EVERY speech path (the Nova pause bug) ──────────────────────
  seen.length = 0;
  send({ type: 'hold', on: true });
  await new Promise(r => setTimeout(r, 800));
  send({ type: 'say',  text: 'זה לא אמור להישמע' });
  send({ type: 'cue',  intent: 'tease the offer' });
  send({ type: 'chat', name: 'דנה', text: 'כמה עולה?' });
  const spokeWhileHeld = await waitFor(m => m.type === 'nova_done', 12000);
  ok('hold silences say + cue + chat', !spokeWhileHeld,
     spokeWhileHeld ? 'she spoke: ' + spokeWhileHeld.text : '');
  send({ type: 'hold', on: false });

  // ── chat answers BY NAME (the M2 promise) ─────────────────────────────────
  seen.length = 0;
  send({ type: 'product', notes: 'Product: Vitamin C Serum. Price: 149 ILS (was 249). In stock. Delivery 3-5 days.' });
  await new Promise(r => setTimeout(r, 600));
  send({ type: 'chat', name: 'דנה', text: 'כמה עולה הסרום?' });
  const answer = await waitFor(m => m.type === 'nova_done', 30000);
  if (answer) {
    ok('answers the viewer BY NAME', (answer.text || '').includes('דנה'), answer.text);
    ok('answer uses the price from PRODUCT NOTES (TRUTH LAW)',
       /149|מאה ארבעים ותשע/.test(answer.text || ''), answer.text);
  } else {
    ok('answered the viewer', false, 'nothing in 30s');
  }

  const errors = log.filter(l => /OAI|error/i.test(l));
  ok('no OpenAI errors in the session', errors.length === 0, errors.join(' | '));

  ws.close();
  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
};

main().catch(e => { console.error('HARNESS ERROR', e.message); process.exit(1); });
