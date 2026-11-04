#!/usr/bin/env node
// Обёртка npm: запускает модуль solo_sdd из корня пакета с теми же аргументами, потоками и кодом выхода.
"use strict";
const { spawnSync } = require("child_process");
const path = require("path");

const root = path.resolve(__dirname, "..");
const candidates = [process.env.SOLO_SDD_PYTHON, "python3", "python"].filter(Boolean);
const found = [];
let python = null;
for (const cmd of candidates) {
  const r = spawnSync(cmd, ["-c", "import sys; print('%d.%d' % sys.version_info[:2])"], { encoding: "utf8" });
  if (r.status !== 0 || !r.stdout) continue;
  const version = r.stdout.trim();
  found.push(version);
  const [major, minor] = version.split(".").map(Number);
  if (major > 3 || (major === 3 && minor >= 9)) {
    python = cmd;
    break;
  }
}
if (!python) {
  console.log(`solo-sdd: нужен Python 3.9+ (найден: ${found.length ? found.join(", ") : "нет"})`);
  process.exit(1);
}
const env = { ...process.env };
env.PYTHONPATH = env.PYTHONPATH ? root + path.delimiter + env.PYTHONPATH : root;
// Как python -m solo_sdd, но корень пакета в sys.path раньше текущей папки: клон solo-sdd в cwd не подменяет пакет.
const run = "import runpy, sys; sys.path.insert(0, sys.argv.pop(1)); runpy.run_module('solo_sdd', run_name='__main__', alter_sys=True)";
const r = spawnSync(python, ["-c", run, root, ...process.argv.slice(2)], { stdio: "inherit", env });
if (r.error) {
  console.error(`solo-sdd: ${r.error.message}`);
  process.exit(1);
}
process.exit(r.status === null ? 1 : r.status);
