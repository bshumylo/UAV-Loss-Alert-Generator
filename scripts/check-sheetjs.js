#!/usr/bin/env node
/*
 * Checks that the SheetJS library embedded in Подання.html has not drifted
 * from the pinned version recorded in its header comment:
 *
 *   /* SheetJS <ver> (вбудовано; npm @e965/xlsx@<ver>, sha256 of xlsx.full.min.js: <hex>) *\/
 *
 * Verifies:
 *   1. sha256 of the embedded library (the text between the header line and
 *      the closing </script>, without the final newline) equals <hex>;
 *   2. the header version, the npm version and XLSX.version reported by the
 *      embedded code (evaluated in a Node vm sandbox) are all equal.
 *
 * Usage (Node.js >= 14, no dependencies):
 *   node scripts/check-sheetjs.js              # checks ./Подання.html
 *   node scripts/check-sheetjs.js path/to.html
 * Exit code 0 = OK, 1 = mismatch or parse error.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const vm = require('vm');

const file = process.argv[2] || path.join(__dirname, '..', 'Подання.html');
const html = fs.readFileSync(file, 'utf8');

function fail(msg) {
  console.error('FAIL: ' + msg);
  process.exit(1);
}

const headerRe = /^\/\* SheetJS (\S+) \(вбудовано; npm @e965\/xlsx@(\S+), sha256 of xlsx\.full\.min\.js: ([0-9a-f]{64})\) \*\/\r?\n/m;
const m = headerRe.exec(html);
if (!m) fail('SheetJS header comment not found or not in expected format');
const [header, headerVer, npmVer, expectedSha] = m;

const start = m.index + header.length;
const end = html.indexOf('</script>', start);
if (end < 0) fail('closing </script> after SheetJS header not found');
// Drop the trailing newline + indentation that precede </script>.
const lib = html.slice(start, end).replace(/\r?\n[ \t]*$/, '');

const actualSha = crypto.createHash('sha256').update(lib, 'utf8').digest('hex');

let reported;
try {
  const sandbox = {};
  sandbox.self = sandbox.window = sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(lib, sandbox, { filename: 'embedded-xlsx.js', timeout: 10000 });
  reported = sandbox.XLSX && sandbox.XLSX.version;
} catch (e) {
  fail('evaluating embedded SheetJS threw: ' + e.message);
}

let ok = true;
function check(cond, msg) {
  console.log((cond ? 'ok   ' : 'FAIL ') + msg);
  if (!cond) ok = false;
}
check(actualSha === expectedSha, `sha256 ${actualSha} ${actualSha === expectedSha ? '==' : '!='} header ${expectedSha}`);
check(headerVer === npmVer, `header version ${headerVer} == npm version ${npmVer}`);
check(reported === headerVer, `XLSX.version ${reported} == header version ${headerVer}`);
process.exit(ok ? 0 : 1);
