---
name: shorz-premium-motion
description: >-
  Make premium, launch-film-quality motion graphics with Shorz Animation Studio — product promos, launch videos, feature explainers, app demos, intros and outros, animated ads, website hero videos — by planning a continuous story, briefing each 5-second clip, rendering one clip at a time and verifying it frame by frame before the next, then scoring it with ElevenLabs sound effects and joining it. Also covers studying a reference video (a competitor's launch film, a style you want to match) to measure its motion. Use when the ask is quality-critical animation: "make a promo video", "launch video like ElevenLabs/Apple/Linear", "premium motion graphics", "animated product demo", "hero video for the website", "match the style of this video", "study how this animation moves". For graphics over existing footage use shorz-motion-graphics; for the raw Animation Studio tool contract see shorz-mcp (references/panel-workflows/animation-studio.md).
---

# Premium motion with Shorz Animation Studio

Animation Studio's system prompt already carries the **MOTION CRAFT STANDARD** — universal rules
distilled from frame-by-frame and optical-flow study of top launch films: one continuous shot, a
hero object that transforms, a camera that never parks (with measured magnitudes and easings),
the result shown large, one dominant motion at a time, readable holds, and an SFX cue sheet in
every composition. **You do not repeat those rules in briefs.** Your job is the part the model
cannot do alone: the story, the continuity between clips, the references, verification, sound,
and assembly.

## 1. Plan the whole piece first

- **Name the result.** What does the viewer walk away having *seen happen*? Premium films show the
  subject working (the output appearing, the change happening), not a list of features.
- **One story thread.** Pick one concrete example and follow it through the whole piece (one
  video being edited, one document being translated, one product being used). Every beat acts on
  that same example.
- **One hero object.** Decide what the eye follows and how it changes role across beats (e.g. a
  card → a player → a strip of frames → a vertical short). Write the chain down.
- **Focus.** Show what is distinctive. Cut anything every competitor also has.
- **Beats.** 2–4 beats per 5 s clip; 8–12 clips for a 40–60 s piece. Each beat is one dominant
  motion. Mark where the music drop or the logo lands.
- **References.** Collect real material before briefing: UI screenshots (captured from the real
  app, not redrawn), the real outputs as video, exact logos. Faithful beats invented.

Write the plan as a numbered clip list: for each clip the start state (exactly what is on screen
at frame 0 — the previous clip's end state), the beats, the end state, and the references.

## 2. Brief one clip

Animation Studio handles ~5 s / 3–4 beats reliably in one generation; more fails upstream. Each
brief contains, in plain language:

- The shared look line (one sentence reused in every clip so the whole piece matches).
- **Start state** (for every clip after the first: "starts on …, no intro") and **end state**
  ("ends holding …"). Prose is not enough for a seamless join: extract the previous clip's last
  frame (`ffmpeg -ss <dur-0.03> -i prev.mp4 -frames:v 1 prev-last.png`), attach it as the first
  image ("this IS frame 0 — layout reference only, do not place it"), and give the exact geometry
  read from the previous clip's `sourcePath` (positions, sizes, font sizes, colours, camera
  scale). Prefer a defined, holdable end state over "ends mid-motion" — the next clip can match it.
  When the start frame is too rich to describe (a full editor, many layers), paste the previous
  clip's `.tsx` into the brief as the **base code**: "build on it, drive its animation with
  `const f = frame + <its duration>`, keep its media indices" — frame 0 then matches by
  construction, and the new beats are added on top. Attach the same media in the same order.
- **Frame targets** for each beat ("frames 28–64: types…, press at frame 88"). Without them the
  model spends the clip on the first beats and the last one never happens.
- The beats, describing **what transforms into what** ("the timeline's clips fold into one frame
  that becomes the player") rather than what appears.
- Which attached reference is which, and that it must be reproduced or placed exactly.
- On-screen words, verbatim. Short lines; bold; one idea each.

Call `animation_studio_send_compile_export` with `newSession: true` (every clip gets a clean chat —
otherwise the model copies earlier code and earlier images crowd out this clip's references),
`durationInFrames: 150`, `fps: 30`, the canvas, and a fresh `outputPath` (never overwrite a file a
previous run wrote). The reply returns `sfxCues`, `sfxCueSheetPath` (`<name>.mp4.sfx.json`) and
`sourcePath` (`<name>.tsx` — the exact code, readable when something looks wrong).

## 3. Verify the clip before the next one

Never batch-render a whole piece blind. After each clip:

1. Run `scripts/study_motion.py <clip.mp4> --out <dir>` (ffmpeg + numpy + opencv) and **read the
   0.5 s contact sheet** (`-half-00.jpg`) and the **10 fps sheets of the fastest windows**
   (`-fast-N.jpg`). Without Python, use `extract_video_frames` at 0.5 s steps.
   Then run `scripts/motion_curves.py <clip.mp4> --check` (+ scipy): it fits every clean move's
   progress curve at native fps and flags overshoot, travel shorter than the distance rule, moves
   whose speed peaks too late (abrupt landings), a camera that parks and a drift that always slides
   the same way. Footage-heavy clips have few *isolated* moves, so an empty curve list there is
   normal — read the sheets instead.
   For every scene change, run `scripts/transition_measure.py <clip.mp4> T0 T1` over the
   transition and compare with the reference values of its recipe in `references/transitions.md`
   (duration and curve of the move, where the blur peaks, the wash in brightness/saturation).
2. Check, frame by frame:
   - Words keep their spaces; every readable line holds long enough; nothing is cut off the frame.
   - The start state matches the previous clip's end state (continuity), and the end state is
     what the next clip's brief will assume. Stack the previous clip's last frame over this
     clip's frame 0 and compare — including the *footage inside* cards (see Footage below).
   - No text overlaps other text in any frame (crop the headline area at 30 fps across every
     text change; a roll that is not clipped reads as a double exposure).
   - The camera is alive (the printed timeline is not all `.` holds) and moves look intentional.
   - References were used faithfully (real UI, real logos, real footage not altered).
   - One dominant motion at a time; nothing flashes, shakes or glows without reason.
3. If something is wrong, fix the brief (or read `sourcePath` to see why) and regenerate *that*
   clip. Only move on when it passes. When the clip is right except for a detail you can
   change in code (a footage offset, a colour, a timing), don't regenerate — a new generation
   can break what already works. Edit the saved `.tsx` and render it with `remotion_render`
   (see *Re-render from source*).
4. When a person is reviewing, send them the clip and stop until they approve.

## 4. Study a reference (to match a style)

`scripts/study_motion.py reference.mp4` gives: cut count and median shot length (continuous vs
cut-based), light/dark background share, still share (how much the piece rests), a 0.5 s camera
timeline with every continuous zoom/pan run (amount, duration, easing), and the contact sheets.
Read every 0.5 s sheet end to end and write down, per beat, *what transforms into what* and how
long it takes; use the numbers for magnitudes. Translate what you learn into principles, not a
copy of their shots.

For the *feel* (smooth, breathing, natural), measure curves, not bins:
`scripts/motion_curves.py reference.mp4` tracks every clean move frame by frame (camera moves from
the global transform, element moves by tracking the element backward from where it lands) and
fits a cubic-bezier to each progress curve, with duration, distance, overshoot and where the speed
peaks; it also reports breathing (drift %/s and px/s during holds). Compare a reference and your
render with the same script.

### Curves, measured (ElevenLabs launch films; already in the MOTION CRAFT STANDARD)

| Motion means… | Curve | Timing |
|---|---|---|
| something appears (card, chip, word, logo) | EASE_ENTER `bezier(0.16,1,0.3,1)` | 24–33 f; words 18–24 f, 3–4 f apart; blur clears over the whole entrance |
| something relocates / camera pans / a rect slides to another slot | `travelEase(px)`: <250 px `(0.65,0.05,0.35,0.95)`, 250–700 px `(0.72,0.05,0.28,0.95)`, ≥700 px `(0.75,0.04,0.25,0.96)` — longer moves are steeper | 0.14 + 0.038·√px s (100 px 0.52 s, 400 px 0.91 s, 1200 px 1.47 s) |
| anything moving faster than ~8 px/frame | directional motion blur (SVG `feGaussianBlur`, σ = 0.07·(px/frame − 8), max 16) | only while fast; crisp at rest |
| other changes during a big move | ride on it (start 0–6 f after, finish inside it); exits shrink to a point | — |
| a move lands into a hold, neighbours reflow, a reveal pulls back | EASE_SETTLE `bezier(0.5,0.2,0.18,0.95)` | distance rule; reveals 1.0–1.5 s |
| a container grows: pill → card, strip → player, card → full frame | EASE_SETTLE, launched out of the drift, no blur | 24–27 f for 400–550 px (measured 0.78–0.85 s) |
| a full frame shrinks away into the next scene | EASE_EXIT, blur rising to ~8 px, then a hard cut | ≈12 f; the next scene sharpens over ≈12 f |
| something leaves / a zoom-through | EASE_EXIT `bezier(0.3,0,0.75,0)` | 8–20 f; zoom-through ≈1 s |
| the camera pulls back to reveal more (detail → context, one → many) | EASE_REVEAL `bezier(0.16,0.26,0.16,0.84)`, in log space | 0.8–1.3 s; half-way at 22 % |
| breathing, conveyors, tickers, typing | linear | drift ≈2 %/s scale + ≈25 px/s, one direction per hold — and a NEW direction every hold (never always right-to-left) |
| one scene becomes the next | a recipe T1–T13 (section 5 of the standard; evidence in `references/transitions.md`) | accelerate out, switch at the fastest frame, settle in, blur peaking at the switch |

Never overshoot (0 of 34 measured moves did). The full situation → curve table is section 3 of
the standard.

### Keep improving (the loop)

The standard is never finished. Every piece you make is also a measurement:

1. After each clip, run `scripts/motion_curves.py <clip> --check`; it compares the clip with
   `scripts/motion_reference.json` (curves, steepness by distance, motion blur, breathing).
2. When a reviewer says "still not like the reference", find the matching moment in a reference
   film and in your clip, look at both at the native frame rate (30 fps sheets of a crop), and name
   the difference with a number (duration, peak speed, blur, what moves together, depth).
3. Calibrate the fix with a tiny test composition rendered through `remotion_render`, measured the
   same way, before it touches a real clip.
4. A difference that repeats becomes a rule: add it to the MOTION CRAFT STANDARD (with numbers),
   update `motion_reference.json`, and log the evidence in `references/motion-lessons.md`.
5. Re-render the affected clips from their saved source with the new rule and compare before/after.

## 5. Sound

- Each clip's cue sheet lists moments and physical descriptions. Build a small **palette** of
  10–14 sounds with `generate_sound_effect` (≈16 credits each: click, whoosh, typing, tick, pop,
  thud, snip, morph swish, shimmer, riser, impact, counter) and reuse them — don't generate one per
  cue. Map each cue to a palette sound by keyword (use word boundaries: "sub" in "subtle" is not an
  impact) and thin repeats closer than ~0.2 s.
- Music: `generate_music` with `elevenlabs/eleven_music` at the exact length; measure where its drop
  lands and offset it so the drop hits the key reveal.
- Mix: music under everything, SFX at 0.35–0.8 gain by type, a limiter, a short fade at the end.

## 6. Assemble

- Join clips on their **video streams only** with the ffmpeg concat *filter*
  (`[0:v:0][1:v:0]…concat=n=N:v=1:a=0`). Exported clips carry a silent audio track slightly longer
  than the video; the concat *demuxer* drifts the seams by that much per clip.
- Check both sides of every seam (frames at seam ± 0.05 s).
- Web delivery: 1280×720 H.264 `-tune animation -crf 26–28`, `+faststart`; give re-cuts a new file
  name when the host caches aggressively.

## Footage across clips

Every clip's `<OffthreadVideo>` starts at the file's first frame, so a video that appears in
consecutive clips jumps back at each seam. Continue it instead: in clip k (counting the first
appearance as 0) ask for `startFrom={k × durationInFrames}`, and attach files long enough for
every clip they appear in. When a video runs out — or the story pauses playback (an editor
stopping to edit) — freeze it: `<Freeze frame={n} active={(f) => f >= n}>` from `remotion`.
Trimming a shared source differently per clip breaks continuity the same way: cut every
per-clip file from the same in-point.

## Re-render from source (deterministic, no model call)

`remotion_render` takes raw code. To render a saved `<clip>.tsx` with a change:

1. Edit the code (e.g. add `startFrom={150}` to each `<OffthreadVideo`).
2. If it uses attached media, declare them right after the imports the way the app injects
   them, as ONE pre-encoded string literal per file:
   `const REMOTION_VIDEO_URLS = ["local-resource://C%3A%2Fpath%2Ftake1.mp4", …] as const;`
   (`"local-resource://" + encodeURIComponent(path)` of a forward-slash path, computed by you and
   pasted as the literal; `REMOTION_AUDIO_URLS` likewise). The renderer rewrites each literal to
   its loopback media server with a regex over the source text, so a runtime expression such as
   `"local-resource://" + encodeURIComponent(…)` is NOT rewritten and the render fails with
   "Can only download URLs starting with http:// or https://" (learned 2026-09-28).
3. Call `remotion_render` with `code`, `durationInFrames`, `fps`, `aspectRatio`,
   `overrideOutputPath`, `revealInFolder: false`. It returns a `jobId` at once — poll
   `get_job_status` (or wait for the file to appear and stop growing).
4. Diff the result against the old render frame by frame: only the intended region may change.

## Gotchas

- A run that finishes through the file-exists fallback returns no `sfxCues`/`sourcePath` — cue that
  clip by hand from its 0.5 s sheet.
- Upstream "invalid or expired token": call `get_shorz_credits` once (refreshes the session) and retry.
- `upstream error` at ~300 s (builds before 2026-09-28) or an error naming the 30-minute limit means the clip took too long to generate. Split it; don't re-send it.
- End every clip brief with a budget line: *"Keep it compact: repeated elements from data arrays with map(), no long comments."*
- Asking for sound in the brief ("with sound effects", "with background music") makes the export generate and mix it itself (result `soundtrack`). Don't score that clip again.
- After each send, poll `get_job_status` every ~30 s. A failed run never writes the MP4, so a file-only wait hides the error.
- "Chat request is too large even after shrinking images and code": images go to the model as
  base64 alongside any base code. Attach reference frames as JPEG (not full-HD PNG) and logos
  or marks at ≤512 px — they only need to be as large as they appear on screen.
- Up to 8 videos can be attached. Many embedded videos make renders memory-heavy; the app
  bounds this, but keep off-screen cards unmounted and prefer short, small source files.
