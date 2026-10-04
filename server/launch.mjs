#!/usr/bin/env node
// Starts the Shorz MCP server that ships inside the user's Shorz desktop install.
//
// The plugin deliberately carries no copy of the server: the one bundled with the app always
// matches the app's bridge, so tools never drift from the installed version. This file only
// finds that server and loads it. It reads nothing else, sends nothing anywhere, and the server
// it loads talks only to the Shorz app on 127.0.0.1.
//
// Lookup order:
//   1. SHORZ_MCP_SERVER_PATH — an explicit path to mcp-server/index.js (custom install folders)
//   2. mcpServerPath in the bridge file the running Shorz app writes to the temp folder
//   3. The default install folders for Windows and macOS

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const SERVER_RELATIVE = ['resources', 'mcp-server', 'index.js'];
const MAC_SERVER_RELATIVE = ['Shorz.app', 'Contents', 'Resources', 'mcp-server', 'index.js'];

/** Every place the server can be, most specific first. Pure, so tests can force any platform. */
export function candidateServerPaths({ platform, env, homedir, bridgeServerPath }) {
  const p = platform === 'win32' ? path.win32 : path.posix;
  const candidates = [];
  if (env.SHORZ_MCP_SERVER_PATH) candidates.push(env.SHORZ_MCP_SERVER_PATH);
  if (bridgeServerPath) candidates.push(bridgeServerPath);
  if (platform === 'win32') {
    // NSIS installs per-user by default; the installer also lets people pick Program Files.
    if (env.LOCALAPPDATA) candidates.push(p.join(env.LOCALAPPDATA, 'Programs', 'Shorz', ...SERVER_RELATIVE));
    if (env.ProgramFiles) candidates.push(p.join(env.ProgramFiles, 'Shorz', ...SERVER_RELATIVE));
    if (env['ProgramFiles(x86)']) candidates.push(p.join(env['ProgramFiles(x86)'], 'Shorz', ...SERVER_RELATIVE));
  } else if (platform === 'darwin') {
    candidates.push(p.join('/Applications', ...MAC_SERVER_RELATIVE));
    if (homedir) candidates.push(p.join(homedir, 'Applications', ...MAC_SERVER_RELATIVE));
  }
  return candidates;
}

/** mcpServerPath from the running app's bridge file, or null when the app isn't running. */
export function readBridgeServerPath(tmpdir, readFile = fs.readFileSync) {
  try {
    const parsed = JSON.parse(readFile(path.join(tmpdir, '.mcp_bridge_config.json'), 'utf8'));
    return typeof parsed?.mcpServerPath === 'string' && parsed.mcpServerPath.trim()
      ? parsed.mcpServerPath.trim()
      : null;
  } catch {
    return null;
  }
}

// Only the folder variables the lookup needs. The launcher never touches the rest of the
// environment, and keeping it that way keeps the directory's credential scan clean.
function lookupEnv() {
  return {
    SHORZ_MCP_SERVER_PATH: process.env.SHORZ_MCP_SERVER_PATH,
    LOCALAPPDATA: process.env.LOCALAPPDATA,
    ProgramFiles: process.env.ProgramFiles,
    'ProgramFiles(x86)': process.env['ProgramFiles(x86)'],
  };
}

export function resolveServerPath({
  platform = process.platform,
  env = lookupEnv(),
  homedir = os.homedir(),
  tmpdir = os.tmpdir(),
  exists = fs.existsSync,
  readFile = fs.readFileSync,
} = {}) {
  const bridgeServerPath = readBridgeServerPath(tmpdir, readFile);
  const candidates = candidateServerPaths({ platform, env, homedir, bridgeServerPath });
  return { found: candidates.find((candidate) => exists(candidate)) || null, candidates };
}

async function main() {
  const { found, candidates } = resolveServerPath();
  if (!found) {
    // stdout is the MCP channel, so every message goes to stderr.
    console.error(
      'Shorz plugin: could not find the Shorz desktop app.\n' +
        'Install the Shorz desktop app for Windows or macOS (download link in this plugin\'s README) and open it, then restart Claude.\n' +
        'If Shorz is installed in a custom folder, set SHORZ_MCP_SERVER_PATH to its resources/mcp-server/index.js.\n' +
        'Looked in:\n' +
        candidates.map((candidate) => `  - ${candidate}`).join('\n')
    );
    process.exit(1);
  }
  await import(pathToFileURL(found).href);
}

const invokedDirectly =
  process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url;
if (invokedDirectly) {
  main().catch((error) => {
    console.error('Shorz plugin: failed to start the Shorz MCP server:', error);
    process.exit(1);
  });
}
