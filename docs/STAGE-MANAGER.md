# STAGE-MANAGER — one owner for every Nova show (timing · gestures · bakes · facts · memory) · code written and tested (24/24)

## 0 · WHY (what the research found)
Every product that makes a live talking character work with real-time input has a **stage manager** that is not the AI:
- **Duolingo (Lily):** fixed call phases; the *system* tells Lily when to wrap up; memory = a short list of facts loaded next call.
- **Sword Health (Phoenix):** an orchestration layer owns turn-taking and when to speak; motion-tracking events stream in as facts.
- **Baidu (AI livestream host, ¥55M in one stream):** a huge pre-written script and **8,300 pre-coordinated movements**; the live AI answers questions in the gaps.
- **Praktika:** memory is retrieved right after the user's turn, so replies are about what was just said.
- **Reachy Mini:** a dance move is a *command* that runs in the background — it never interrupts speech.

Nova today has pieces of this spread across pages and the brain. This pack makes it ONE module every game uses: `shared/stage.js`.

## 1 · THE RULES (the stage enforces them in code)
1. **Only the stage makes her speak live.** Pages never call the brain's speak directly — they call `stage.requestSpeak(text, {fallbackClip})`.
2. **She speaks only at a quiet moment in a live phase:** nobody talking (kid or her) for ≥ 600ms, and the phase is marked `live`. Show phases (rounds) never get live speech.
3. **A request that can't find a quiet moment in 3s** plays its recorded fallback — or is dropped. Never spoken late.
4. **Facts go in silently** (`stage.event(...)` → a time-stamped, confidence-tagged note, at most once per second). Bursts collapse to the latest; facts expire after 2.5s. Right before she speaks, the fresh facts are written in first — so her line is true.
5. **Gestures are commands:** `stage.gesture(id)` changes her body and returns to rest when the bake ends. It never touches speech.
6. **Cue sheets** (the Baidu backbone): lines + gestures + lights on a timeline; a gesture can be *peak-aligned* so its pose lands exactly on the beat.
7. **Praise follows confidence:** high → specific ("Perfect flamingo!"), mid → generic ("STATUE!"), low → stay quiet. Never a detail the camera didn't confirm.
8. **Memory:** up to 12 short facts per child (name, favorite animal, best freeze…), loaded at the intro as a silent note.

## 2 · THE MODULE (shared/stage.js) — how a page uses it
```js
import { Stage } from '/shared/stage.js';
const stage = new Stage({
  now: () => performance.now(),
  remember: text => K.bridge.note({ kind:'remember', text }),
  speakNow: text => K.bridge.note({ kind:'section-end', speak:true, text }),
  playClip: (id) => play(id),                       // the page's recorded-line player
  setBody:  id => K.bridge.setBody(id),
  light:    cmd => lightFx(cmd),
  log:      s => console.log(s),
});
stage.loadGestures(GESTURES);                       // from data/gestures.json (measured values only)
stage.loadMemory(JSON.parse(localStorage.getItem(`nova-mem-${childName}`) || '[]'));
setInterval(() => stage.tick(), 100);               // the heartbeat

// turn state — wire once:
K.bridge.onSpeech?.({ started: () => stage.setKidSpeaking(true), stopped: () => stage.setKidSpeaking(false) });   // [ADAPT] rt_lk VAD events
K.bridge.onHerAudio({ playing: () => stage.setNovaSpeaking(true), ended: () => stage.setNovaSpeaking(false) });

// phases:
stage.phase('intro', { live:true });  …  stage.phase('round1', { live:false });  …  stage.phase('breather', { live:true });

// in a round (show phase): facts only, instant recorded reactions
stage.event('freeze_result', { animal:'flamingo', result:'held' }, { key:'freeze', conf: hold.confidence() });
const line = stage.praise(PRAISE.freeze, hold.confidence()); if (line) play(line);

// at a breather: one live line, with a recorded backup
await stage.requestSpeak('Round 1 ended. Say ONE excited line to the child by name, max 10 words.', { fallbackClip:'fallback.card1' });
```

## 3 · WIRING THE BRIDGE AND THE BRAIN (the CLI adapts; logs every [ADAPT])
- **Kid speech events:** the bridge must expose `onSpeech({started, stopped})` from rt_lk's VAD (`input_audio_buffer.speech_started/stopped`). If missing, add it (one relay each).
- **Her audio:** `onHerAudio({playing, ended})` already exists.
- **rt_lk:** keep PRODUCER-SILENT (remember = silent; speak only via section-end). Add/confirm: `note({kind:'show', on})` → silence timer off + transcripts dropped while on. Turn detection for kids: if the model supports `semantic_vad`, use it with low eagerness; otherwise server VAD with silence ≥ 800ms. Log which one.
- **Gender/Hebrew/intro:** unchanged.

## 4 · FAST-BAKE SPEC (the bakes are the biggest timing problem today)
Measured: `gest_clap` peaks at 2.08s, `gest_lefthand` 2.48s, `gest_righthand` 2.64s (and doesn't return to standing), `gest_bear` 3.84s. A game can't wait that long. New gestures (list in `data/gestures.json → new_to_bake`) must meet:
- **Peak ≤ 600-700ms** from the first frame (clap contact ≤ 500ms).
- **Total length ≤ 1.2-1.8s** (freeze pose: reach ≤ 400ms, then hold ≥ 2.5s).
- **First and last frame within 4% of the rest pose** (`nova_idle2`) so the switch in and out is invisible.
- **Face steady** (head moves ≤ small) so lip-sync can run on top if ever needed.
- Source: short motion clips of the same character, trimmed tight; bake through the normal Bake Factory with its verify gate.
- **After baking:** measure `durMs` and `peakMs` from the actual file (the same method that produced the numbers above) and write them into `gestures.json`. Never type a guessed number.

## 5 · CUE SHEETS (write one per game moment that is scripted)
```js
// "Nova says… arms UP!" — the pose lands exactly when she says "UP"
stage.runCue([
  { atMs: 0,    clip: 'cmd.armsUp.real' },
  { atMs: 900,  gesture: 'armsUpFast', peakAlign: true },   // starts 900 − peakMs early
  { atMs: 900,  light: 'wrists' },
]);
```
Freeze v2 round start, the countdown, round cards, the ending celebration (cheer + confetti + line) → all cue sheets. The live AI never drives these.

## 6 · PRAISE TEMPLATES (per game, recorded lines only)
```js
const PRAISE = {
  freeze: { high:['held.flamingo','held.frog','held.bear','held.star'], mid:['held.statue'], low:[] },
  simon:  { high:['fb.listened','fb.held'],                          mid:['fb.yes'],        low:[] },
};
```
`conf` comes from the judge: `hold.confidence()` (added to beta/freeze2/hold.js in this pack) → 0.9 when the whole hold was seen and clearly still, 0.65 when held but borderline, 0.3 when the body was barely visible.

## 7 · MEMORY (between sessions)
- Store only game facts and things the child said about themselves in the game: name, favorite animal, best freeze, favorite game, how many times played. Nothing sensitive.
- `localStorage['nova-mem-<name>']` on the device (no server needed now).
- At the intro: `stage.remember(stage.memoryNote())` before her greeting, so she can say "Noam! Your flamingo freeze last time was amazing!" — true, because it's stored.

## 8 · "YOUR TURN" (turn-taking for kids)
When the stage is waiting for the child (a question is open, nobody speaking): show a glowing 👂 chip + her `pointYou` gesture once. Kids take long pauses mid-sentence — the 600ms quiet rule plus low-eagerness VAD stops her from cutting in.

## 9 · MIGRATION ORDER
1. **Freeze v2** (beta) — replace its direct `brainSpeak/remember/setBody` calls with the stage; praise via `stage.praise`; memory at the intro. Smallest change, already built on the skill.
2. **The intro** (all games) — memory note + "your turn" chip + stage speech.
3. **Nova Says FAST** — cue sheets for every command once the fast bakes exist.
4. Bake the fast gestures (§4) in parallel.

## 10 · PROOFS (paste before any founder play)
- `node test/stage_test.mjs` → 24/24.
- One Freeze v2 run log: every live line preceded by a `[STAGE] speak` with ≥ 600ms of silence before it; zero live lines in rounds; any fallback logged; facts notes ≤ 1/s.
- The measured `gestures.json` for every new bake (peak ≤ target, first/last frame check).
- One cue-sheet recording: the pose visibly lands on the spoken word.
