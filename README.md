# Shorz for Claude

Turn Claude into a video editor. This plugin connects Claude to [Shorz](https://shorz.ai), the AI video editing agent for Mac and Windows. Claude can then drive Shorz's 180+ tools: auto-edit raw footage, cut long videos into clips, add subtitles, b-roll and overlays, build talking-avatar, podcast, text-to-video and music videos, generate motion graphics and thumbnails, and publish to YouTube, TikTok and other connected accounts.

Ask in plain language, for example:

- "Auto-edit `C:\Videos\vlog.mp4` into a 60-second vertical short with subtitles."
- "Find the three best moments in this podcast and make clips."
- "Make a 30-second text-to-video ad for my coffee shop."
- "Put an animated lower third over my interview."

## What's inside

- **MCP server `shorz`**: the tool surface. The plugin starts the MCP server that ships inside your Shorz install, so the tools always match your app version.
- **Skills**:
  - `shorz-mcp`: workflows and guardrails for every Shorz project type and panel.
  - `shorz-motion-graphics`: green-screen motion-graphics overlays keyed onto existing footage.
  - `shorz-premium-motion`: launch-film-quality animation, built and checked one clip at a time.

## Requirements

- **The Shorz desktop app, installed and open.** Download it for Windows or macOS from [shorz.ai/download](https://shorz.ai/download). Sign in to it once.
- **Node.js 18 or later** on your `PATH`. It runs the local MCP server.
- **Claude Code, or Cowork running on your computer.** The Shorz tools work through a local MCP server, and local servers don't run in claude.ai chat on the web or on mobile. There, only the skills load.

If Shorz is installed somewhere other than the default folder, set `SHORZ_MCP_SERVER_PATH` to the full path of `resources/mcp-server/index.js` inside the install. On macOS that's `Shorz.app/Contents/Resources/mcp-server/index.js`.

## What it runs, sends and costs

- `server/launch.mjs` finds the MCP server inside your Shorz install and loads it. It looks in this order: `SHORZ_MCP_SERVER_PATH`, then the path that the running Shorz app writes to `.mcp_bridge_config.json` in your temp folder, then the default install folders (`%LOCALAPPDATA%\Programs\Shorz` and `%ProgramFiles%\Shorz` on Windows, `/Applications/Shorz.app` and `~/Applications/Shorz.app` on macOS). It reads nothing else and sends nothing.
- The MCP server sends tool calls to the Shorz app on `127.0.0.1`. It authenticates with a per-session token that the app writes to that same bridge file. It also reads Shorz's public model catalog (`/v1/catalog`, no user data) from the Shorz API so it can list current AI models.
- The Shorz app does the work on your computer. It uses Shorz's cloud and its AI providers for generation, transcription and publishing. Those calls spend Shorz credits from your Shorz account, as they do when you use the app directly. Your media stays on your computer unless a tool you ask for needs to upload it, such as AI generation, transcription or publishing.
- Publishing tools post only to accounts you've connected in Shorz, and only when you ask.

Privacy policy: [shorz.ai/privacy-policy](https://shorz.ai/privacy-policy). Terms: [shorz.ai/terms-of-service](https://shorz.ai/terms-of-service).

## Troubleshooting

- **"Shorz does not appear to be running"**: open the Shorz app. The tools reconnect on the next call.
- **The `shorz` server fails to start**: run `node --version` to check that Node.js is on your `PATH`, and check that Shorz is installed (see Requirements).

## Support

Email [info@shorz.ai](mailto:info@shorz.ai) or open an issue in [this repository](https://github.com/Vossy/shorz-claude-plugin/issues).

## License

MIT. See [LICENSE](LICENSE).
