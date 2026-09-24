#!/usr/bin/env node
// Sets the app version everywhere it is declared, so installers and the
// version the app reports (About window, update check) always agree.
//
//   node scripts/set-version.mjs 2.1.0      (or: npm run set-version -- 2.1.0)
//
// The release workflow runs it with the version taken from the pushed tag
// (v2.1.0 -> 2.1.0), which then names the installers
// (ecriture_2.1.0_amd64.deb, ecriture_2.1.0_aarch64.dmg, ..._x64-setup.exe).
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const version = (process.argv[2] || "").replace(/^v/, "");

// Plain MAJOR.MINOR.PATCH: Windows installers can't carry a pre-release
// suffix (2.1.0-beta), and the in-app update check compares numbers only.
if (!/^\d+\.\d+\.\d+$/.test(version)) {
  console.error(`Invalid version "${process.argv[2] ?? ""}": expected MAJOR.MINOR.PATCH, e.g. 2.1.0`);
  process.exit(1);
}

function update(relativePath, edit) {
  const path = join(root, relativePath);
  const before = readFileSync(path, "utf8");
  const after = edit(before);
  if (after === before && !before.includes(version)) {
    console.error(`Could not find the version in ${relativePath}`);
    process.exit(1);
  }
  writeFileSync(path, after);
  console.log(`${relativePath}: ${version}`);
}

const jsonVersion = (text) => text.replace(/("version"\s*:\s*)"[^"]*"/, `$1"${version}"`);
// First `version = "..."` of the file, i.e. the [package] one.
const cargoTomlVersion = (text) => text.replace(/^version = "[^"]*"/m, `version = "${version}"`);
// This workspace's own packages in a Cargo.lock.
const cargoLockVersion = (text) =>
  text.replace(/(\[\[package\]\]\nname = "(?:ecriture|ecriture-core)"\nversion = )"[^"]*"/g, `$1"${version}"`);

update("package.json", jsonVersion);
update("package-lock.json", (text) => {
  // Top-level "version" and the root package entry (packages[""]).
  const data = JSON.parse(text);
  data.version = version;
  if (data.packages && data.packages[""]) data.packages[""].version = version;
  return JSON.stringify(data, null, 2) + "\n";
});
update("src-tauri/tauri.conf.json", jsonVersion);
update("src-tauri/Cargo.toml", cargoTomlVersion);
update("ecriture-core/Cargo.toml", cargoTomlVersion);
update("src-tauri/Cargo.lock", cargoLockVersion);
update("ecriture-core/Cargo.lock", cargoLockVersion);
