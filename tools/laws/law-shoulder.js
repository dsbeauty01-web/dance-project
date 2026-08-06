// LAW: SHOULDER / CHIT-CHAT GATE. On intro, Nova chit-chats first and does NOT
// fire the shoulder challenge for the first 25s; a 35s fallback fires it if the
// natural moment never comes. Removing either timer breaks the intro pacing.
const { runLaw } = require('./_lib');
const NC = 'nova-commercial.html';
runLaw({
  id: 'law-shoulder', title: 'Intro chit-chat gate (25s) + 35s shoulder fallback', status: 'active',
  why: 'Firing the challenge too early skips the warm-up chat; never firing it strands the intro.',
  checks: [
    { desc: 'chit-chat clock present',      rel: NC, present: /__introChatT0/ },
    { desc: '25s chit-chat gate present',    rel: NC, present: /25000/ },
    { desc: '35s fallback present',          rel: NC, present: /35s fallback/ },
  ],
});
