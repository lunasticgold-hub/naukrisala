// Decrypt one TalentRecruit API response envelope (NaCl box).
// Usage: node talentrecruit_decrypt.js <Kd-base64>  (reads {"text","iv","key"} JSON on stdin, prints decrypted JSON)
// The Kd client key is the vendor's own constant shipped in its public
// career-page JS bundle (extracted fresh per run by the Python engine);
// it is NOT a user credential and grants no account access — the listings
// it decrypts are the public, anonymous career page.
const nacl = require('./tweetnacl.js');
const fs = require('fs');
const Kd = Buffer.from(process.argv[2], 'base64');
let input = '';
process.stdin.on('data', c => input += c);
process.stdin.on('end', () => {
  const d = JSON.parse(input);
  const pt = nacl.box.open(Buffer.from(d.text, 'base64'), Buffer.from(d.key, 'base64'), Buffer.from(d.iv, 'base64'), new Uint8Array(Kd));
  if (!pt) { console.error('box.open failed'); process.exit(1); }
  process.stdout.write(Buffer.from(pt).toString('utf8'));
});
