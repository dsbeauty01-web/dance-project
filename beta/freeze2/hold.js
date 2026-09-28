/* beta/freeze2/hold.js — judges ONE freeze hold. Pure (no DOM/audio) → tested in Node.
   Uses the calibrated motion energy from judges.js (per-second, fps-independent, teleports rejected).
   Result: 'held' | 'almost' | 'missed' | 'noshow'. Written by the architect. */

export class Hold {
  /* J = createJudges(tune) instance · t0 = the music-stop time (s) · dur = hold length (s) · T = tune */
  constructor(J, t0, dur, T){
    this.J = J; this.t0 = t0; this.dur = dur; this.T = T;
    this.graceEnd = t0 + T.stopGraceS;              // a real child needs ~0.6s to STOP after the music cuts
    this.moveSince = null; this.brokeAt = null; this.seen = 0; this.frames = 0; this.result = null;
  }
  feed(k, t){
    if (this.result) return this.result;
    this.frames++;
    if (this.J.sw(k)) this.seen++;
    if (t >= this.graceEnd && this.J.sw(k)){
      const moving = this.J.st.energy > this.J.st.thr.move;       // a clear movement, not a fidget
      if (moving){ this.moveSince ??= t; if (!this.brokeAt && t - this.moveSince >= this.T.breakHoldS) this.brokeAt = this.moveSince; }
      else this.moveSince = null;
    }
    if (t >= this.t0 + this.dur) return this.finish();
    return null;
  }
  finish(){
    if (this.result) return this.result;
    if (this.frames === 0 || this.seen / this.frames < this.T.seenMin) return (this.result = 'noshow');   // out of frame: never judged
    if (!this.brokeAt) return (this.result = 'held');
    const into = (this.brokeAt - this.t0) / this.dur;
    return (this.result = into >= this.T.almostFrom ? 'almost' : 'missed');
  }
}
