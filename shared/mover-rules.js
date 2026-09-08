// shared/mover-rules.js — the move library (one-line RULES on the MoverEngine, ENGINE-DETECT b0.11).
// Each rule reads engine primitives (moved/still/isolated/energy/dist) and returns a hit or null.
import { MoverEngine } from './mover-engine.js';

export const RULES = {
  // ISOLATIONS — mover + must-be-still references. Return {hit:true, side, iso} or null.
  shoulderPop:  E => { const l = E.moved('lShoulder', 'y', 0.3), r = E.moved('rShoulder', 'y', 0.3);
                       const side = l === 'UP' && r === 'UP' ? 'BOTH' : l === 'UP' ? 'L' : r === 'UP' ? 'R' : null;
                       return side ? { hit: true, side, iso: E.isolated('shoulderC', ['hipC']) } : null; },
  shoulderSlide: E => { const d = E.moved('shoulderC', 'x', 0.35); return d ? { hit: true, side: d, iso: E.isolated('shoulderC', ['hipC', 'head']) } : null; },
  ribSlide:     E => { const d = E.moved('shoulderC', 'x', 0.35);       // TRUE rib isolation: ribs travel, hips AND head stay
                       return d ? { hit: true, side: d, iso: E.isolated('shoulderC', ['hipC', 'head'], 0.10) } : null; },
  hipSlide:     E => { const d = E.moved('hipC', 'x', 0.35); return d ? { hit: true, side: d, iso: E.isolated('hipC', ['shoulderC']) } : null; },
  hipBounce:    E => { const d = E.moved('hipC', 'y', 0.25); return d ? { hit: true, side: d, iso: E.isolated('hipC', ['shoulderC']) } : null; },
  headSlide:    E => { const d = E.moved('head', 'x', 0.3); return d ? { hit: true, side: d, iso: E.isolated('head', ['shoulderC']) } : null; },
  headNod:      E => { const d = E.moved('head', 'y', 0.25); return d ? { hit: true, side: d, iso: E.isolated('head', ['shoulderC']) } : null; },
  armRaise:     E => { const l = E.moved('lWrist', 'y', 0.6), r = E.moved('rWrist', 'y', 0.6); const s = l === 'UP' && r === 'UP' ? 'BOTH' : l === 'UP' ? 'L' : r === 'UP' ? 'R' : null; return s ? { hit: true, side: s } : null; },
  // FREEZE
  freeze:       (E, thr = 0.12) => ({ still: E.energy(['shoulderC', 'hipC', 'lWrist', 'rWrist', 'head']) < thr }),
  // CLAP — wrists converge fast (fuse with audio transient if available: onsetMs within ±120ms → confident)
  clap:         (E, audioOnsetMs = null, t = (typeof performance !== 'undefined' ? performance.now() : Date.now())) => {
                       const d = E.dist('lWrist', 'rWrist'); const fast = (E.last?.lWrist?.mag ?? 0) > 0.8;
                       const visual = d != null && d < 0.06 && fast; if (!visual) return null;
                       const fused = audioOnsetMs != null && Math.abs(t - audioOnsetMs) < 120; return { hit: true, confidence: fused ? 1 : 0.6 }; },
  // JUMP — both hips rise fast together
  jump:         E => (E.last?.hipC?.dir === 'UP' && E.last.hipC.mag > 1.2) ? { hit: true } : null,
};

// WAVE — traveling peak along the arm chain (order + even spacing = smooth). Stateful.
export class WaveRule {
  constructor(E, arm) { this.E = E; this.chain = arm === 'R' ? ['rShoulder', 'rElbow', 'rWrist', 'rIndex'] : ['lShoulder', 'lElbow', 'lWrist', 'lIndex']; this.h = {}; this.lastT = 0; }
  push(t) { for (const n of this.chain) { const j = this.E.last?.[n]; if (!j) continue; (this.h[n] ||= []).push({ t, y: j.y }); this.h[n] = this.h[n].filter(p => t - p.t < 1200); } }
  peakT(n) { const h = this.h[n]; if (!h || h.length < 5) return null; for (let i = h.length - 3; i > 1; i--) if (h[i].y < h[i - 1].y && h[i].y < h[i + 1].y && (h[i - 1].y - h[i].y) > 0.02) return h[i].t; return null; }
  check(t = (typeof performance !== 'undefined' ? performance.now() : Date.now())) {
    this.push(t); if (t - this.lastT < 600) return null;
    const chain = this.chain.filter(n => this.E.last?.[n]);            // rIndex exists only on MediaPipe → chain adapts (3 or 4 links)
    const peaks = chain.map(n => this.peakT(n)); if (peaks.some(p => p == null)) return null;
    const gaps = peaks.slice(1).map((p, i) => p - peaks[i]); if (!gaps.every(g => g > 40 && g < 400)) return null;
    const spread = Math.max(...gaps) - Math.min(...gaps); this.lastT = t;
    const other = this.chain[0] === 'rShoulder' ? 'lWrist' : 'rWrist';
    return { hit: true, quality: spread < 90 ? 'smooth' : spread < 180 ? 'good' : 'rough', gaps, iso: this.E.still(other, 0.2) };
  }
}
