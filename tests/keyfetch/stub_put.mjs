// Stand-in for tools/infisical_setup.py in the keyfetch tests: `put` and `last4` only.
//   STUB_OUT      file that gets one JSON line {argv, stdin} per call
//   STUB_FAIL     comma list of secret names whose `put` exits 3
//   STUB_PRESENT  comma list of secret names that `last4` finds (exit 0); others: "has no secret"
//   STUB_ERROR    comma list of names whose `last4` fails for another reason
// Values here are synthetic test strings; the stub prints the last 4 only, like the real tool.
import { appendFileSync } from 'node:fs';

const argv = process.argv.slice(2);
const [cmd, , , name] = argv;
const list = k => (process.env[k] || '').split(',').filter(Boolean);
let stdin = '';
if (cmd === 'put') for await (const chunk of process.stdin) stdin += chunk;
appendFileSync(process.env.STUB_OUT, JSON.stringify({ argv, stdin }) + '\n');

if (cmd === 'last4') {
  if (list('STUB_ERROR').includes(name)) { console.error('Infisical API error: HTTP 500'); process.exit(1); }
  if (list('STUB_PRESENT').includes(name)) { console.log(`stub ${name} · last4=abcd`); process.exit(0); }
  console.error(`stub has no secret ${name}`);
  process.exit(1);
}
if (list('STUB_FAIL').includes(name)) { console.error('stub put refused'); process.exit(3); }
console.log(`created stub ${name} · last4=${stdin.trim().slice(-4)}`);
