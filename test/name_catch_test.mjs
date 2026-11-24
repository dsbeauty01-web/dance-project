// node test/name_catch_test.mjs — beta/lib/name-catch.js (NOVA-GO5): the name that arms the shoulder light
import { catchName } from '../beta/lib/name-catch.js';
let bad = 0; const eq = (got, want, what) => { const ok = got === want; if (!ok) bad++; console.log((ok ? 'PASS ' : 'FAIL ') + what + ' -> ' + JSON.stringify(got) + (ok ? '' : ' (want ' + JSON.stringify(want) + ')')); };
const A = { asked: true };
// the commercial parser's own cases
eq(catchName('My name is Refael.'), 'Refael', 'my name is');
eq(catchName("I'm Dana!"), 'Dana', "I'm <name>");
eq(catchName('call me shuki'), 'Shuki', 'call me');
eq(catchName("I'm ready"), null, "I'm ready is not a name");
eq(catchName("I'm going to dance"), null, 'verb after I am');
eq(catchName('I am here now'), null, 'state after I am');
eq(catchName('Refael.'), 'Refael', 'bare word with a full stop (live transcript)');
eq(catchName('Why?'), null, 'bare WH word');
eq(catchName('hello'), null, 'greeting');
eq(catchName('Tom'), null, 'bare 3 letters, not asked (commercial 4-letter floor)');
// the direct answer to "What's your name?"
eq(catchName('Tom.', A), 'Tom', 'asked: 3 letters');
eq(catchName('Refael Sela', A), 'Refael', 'asked: first and last name');
eq(catchName('Hi Nova', A), null, 'asked: hi nova');
eq(catchName('Yes.', A), null, 'asked: yes');
eq(catchName('Thank you.', A), null, 'asked: thank you');
eq(catchName("What's up?", A), null, 'asked: what is up');
eq(catchName('Can you hear me?', A), null, 'asked: a question to her');
eq(catchName('No thanks', A), null, 'asked: no thanks');
eq(catchName('Not telling', A), null, 'asked: not telling');
// Hebrew
eq(catchName('קוראים לי שוקי'), 'שוקי', 'he: korim li');
eq(catchName('שמי נועם.'), 'נועם', 'he: shmi');
eq(catchName('אני רפאל'), 'רפאל', 'he: ani <name>');
eq(catchName('אני מוכן'), null, 'he: ani muchan is not a name');
eq(catchName('נועם'), 'נועם', 'he: bare name');
eq(catchName('דוב'), null, 'he: a game word is never a name');
eq(catchName('כן'), null, 'he: yes');
eq(catchName('היי נובה', A), null, 'he: hi nova');
eq(catchName(''), null, 'empty');
eq(catchName('对不起。', A), null, 'another script (noise transcript)');
console.log(bad ? bad + ' FAILED' : 'ALL PASS'); process.exit(bad ? 1 : 0);
