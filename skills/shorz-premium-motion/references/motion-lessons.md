# Motion lessons (dated log)

Every gap found between a Shorz render and the reference films, with the evidence and the rule it
produced. Rules that hold go into the MOTION CRAFT STANDARD
(`frontend/src/prompts/remotionMotionCraft.prompt.txt`); this log keeps the why. Add an entry
whenever a measurement or a review finds something the standard does not cover yet — newest first.

## 2026-09-28 — transition study (≈50 scene changes, 12 test renders per round)

- **Catalogue.** `elevenlabs-ref/transitions.py` found every scene change in the eleven films
  (peaks of 0.6 s colour-thumbnail change, hard cuts flagged); ~13 families recur. Each was measured
  with `tmeasure.py` (now `scripts/transition_measure.py`): camera zoom/pan chain, cross-fade
  progress, sharpness, brightness, saturation and content rect per frame.
- **The master pattern.** ElevenLabs almost never cuts from rest: the outgoing scene accelerates
  (converge, pull-back, push-in), the switch lands on the fastest frame, and the incoming scene
  arrives moving the same way and settles, blur peaking at the switch. → five laws + recipes T1–T13
  in section 5 of the standard, each with measured numbers.
- **Round 1 of tests (one Animation Studio render per recipe) and what each changed:**
  T1 grow matched (0.73s vs 0.78s, t50 0.41 vs 0.46). T2 shrink landed too fast (22 frames; the
  reference needs ~24–27) → T2 = T1's length. T3 burst lingered tiny: geometric scale from 0.1
  keeps an entrance small for 0.4s, while the reference card is 90% there in 4 frames → entrances
  pop in on a linear scale from 0.7; geometric only for big zooms and shrink-to-point. T4 converge
  close; the reference converge is ~16 frames, not 10–12. T5 scatter jumped: EASE_ENTER moved the
  camera ×0.84 in one frame; both reference pull-backs are half-way at 21–23% → new EASE_REVEAL
  (0.16, 0.26, 0.16, 0.84), fitted to both within 0.2%. T6 bloom timing matched (t50 0.56 both) but
  the colour field was a blank gradient; the reference keeps the subject's silhouette as a blurred
  pastel duotone → SVG duotone filter in the recipe. T9 burst collapsed its phases (contracted on
  the switch frame) → explicit frame offsets. T11 wipe: my first reading of the reference started
  mid-wipe (looked like a settle); the whole wipe is TRAVEL, 0.9s, from the frame edge. T12 morph
  order right, 40% too fast → 16–18 + 12–15 frames and a 3% push.
- **Round 2 (11 renders after the fixes).** Now matching their references: T2 (26 frames), T3
  (card 73% there in 4 frames), T4 (≈16-frame converge, next scene settles from 1.05), T5 (×0.47 in
  0.77s, t50 0.24 vs 0.21), T6 (duotone silhouette, brightness 205 → 227 vs 196 → 228), T7
  (washed defocus, sharp again at ≈0.9s), T9 (burst → hold → contract), T10 (4-frame flip + ×1.10
  push), T11 (plane from the frame edge, ≈27 frames). Two last findings: focus that clears
  linearly looks soft, then snaps (T8, T9) → blur radius decays geometrically, as the reference
  focus pulls do (20 → 10 → 5 → 2 → 1px); T12 still ran width and height together → height
  starts only when the width is ≥90% there (verified with a direct render). A drift test
  (3 holds) came out left → up-left → up-right with the bloom on an orbit.
- **Round 3 (9 renders + an event-aligned regression suite).** New families: caret zoom (matches
  Speech Engine: ×2.4 over 26 frames, match cut back), bloom recede (saturation 108 → 6 like Ads
  Engine's 156 → 9), in-card swap, dark-film grow. Findings turned into rules: the flex-gap `em`
  resolves against the CONTAINER's font size (a wordmark rendered "ShorzStudio"); a model added zoom
  blur to a ×1.10 push (references never blur zooms under ×1.3); blur must fall by a constant
  ratio per frame — geometric-but-eased holds soft then snaps (push-in detail ×0.92/frame, dissolves
  ×0.85); T4's ground stays dark and the switch is one frame (the test had faded the whole scene);
  T7 on dark films lifts before settling down; T9 phases are 10 + 11 frames with a focus snap on
  landing; grow duration depends on card size (Flows' 67%-wide card: 0.6s); the wipe uses
  EASE_TRAVEL itself, not the steep long-distance variant.
- **Rounds 4–6 (19 renders) — every recipe passes.** The regression suite
  (`shorz-promo-2026-09/ttests/tsuite.py`, results in `suite-final.md`) now aligns each test on its
  event frame against the reference and scores the recipe's key curve; 15 checks pass on numbers and
  5 on recorded visual evidence where blur, footage content or a blank frame defeats the numbers
  (T3, T7, T8b, T9, T6b). Four content variants (dark scatter, portrait bloom, dark shrink, light
  wipe) passed first time, which says the rules generalise. What the last rounds taught:
  - Blur clears at a CONSTANT RATIO PER FRAME, and the ratio depends on the transition: ×0.7 an
    element appearing, ×0.85 dissolves/bursts, ×0.92 pushing into a detail, ×0.95 the light
    softness after a converge. A geometric fade driven by an easing curve holds, then snaps.
  - One effect carries one job: a bloom recede whose opacity, slide and mask each ran the full
    curve emptied the frame in 8 frames; opacity alone on EASE_SETTLE over 46–48 frames matches the
    reference drain within 2%.
  - Measuring needs the right quantity per recipe: a one-frame switch is judged by the share of
    the brightness change in one frame, a flip or wipe by brightness, reveals by zoom, containers
    by rect, dissolves by the colour wash — whole-frame cross-fade progress is skewed by captions
    and footage cuts.
  - Wipes come in two measured forms (cover: the new plane rises; uncover: the old scene slides
    off) and last 0.9–1.3s; container grows last 0.6–0.85s by card size; lyric lines enter dim and
    brighten.
- **An editing accident, caught.** A scripted edit anchored on "T10 POLARITY" hit the table row
  instead of the recipe and duplicated T1–T9 (with a stale T9) for part of round 3. The standard now
  has a structure check (every section and recipe exactly once) run after each edit.
- **A second product bug.** One export rendered the PREVIOUS composition (byte-identical MP4) and
  reported success: the MCP flow waited for "one more compile" by counting preview keys, and a
  recompile of the old code bumped the key first. The export now waits for the compiled source to
  equal the latest reply's code.
- **Product bug found by the tests.** Code that referenced `REMOTION_IMAGE_URLS` /
  `REMOTION_VIDEO_URLS` with nothing attached died on a ReferenceError at export (3 of 12 tests).
  The modal now injects an empty array when the code references a media constant it does not
  declare.
- **Drift direction (user review).** Every clip of our film drifted right-to-left (the background
  bloom's `translate(-0.25f, 0.12f)` was inherited by all ten clips). 140 reference holds: the next
  hold almost never repeats the direction; diagonals 34%, horizontals 26% both ways. → "the
  direction changes with every hold" + ambient background on a slow orbit; `--check` flags a
  render whose holds ≥80% slide the same way.

## 2026-09-28 — retime pass, clip 5 (containers growing)

- **A container growing is a SETTLE, not a TRAVEL.** Measured Dubbing v2's two card → full-frame
  moves and its pill → card unfold: 0.78–0.85 s for 444–548 px of corner travel, half-way at
  40–48%, 90% at 69–73%, speed peaking at 38–49% — the settle profile. The standard had put every
  rect morph under TRAVEL with the distance rule; that gave 0.90 s peaking at 52%. The old v3 clip
  did it in 0.50 s. Retimed clip 5 with EASE_SETTLE over 26 frames: 0.77 s, t50 0.40, t90 0.70, peak
  0.39 — on top of the reference. → table rows split: GROWING (SETTLE 24–27f), SLIDING at the same
  size (TRAVEL), FULL FRAME SHRINKING AWAY (EXIT ≈12f, blur rising, hard cut).
- **The growth launches out of the drift.** The reference card is already growing slowly (~9% in
  0.4 s) before the move accelerates; nothing starts from a dead stop.
- **Growing containers stay sharp; shrinking full frames blur.** Sharpness during the grows stayed
  ≥90% of rest; the full-frame shrink into a cut fell to 20%. `motion_curves.py` was flagging
  "no motion blur" on our scale morphs and on cuts inside footage (538 px/frame on a cut). It now
  judges only translation-dominant frames the tracker can follow, and compares each fast frame
  with the resting frames within 0.7 s instead of the whole film's median — which had read Ads
  Engine's blurred pans as 241% sharp. References now read 66–92%; the >95% flag still separates
  "no blur at all".

## 2026-09-28 — retime pass, clip 4

- **Camera parked between two moves.** Push-in 18→48, hold, pull-back 96→132, hold to the end:
  every curve passed, but only 46% of quiet moments drifted (reference 55–76%) and the frame read
  as stopped for 1.6 s. Chaining the moves end to start (12→90→150) gave 88% and 1.4 %/s. →
  "chain camera moves end to start" in section 4 of the standard; the `--check` drift threshold
  rose from 45% to the reference floor of 55%, so this now fails instead of scraping through.

## 2026-09-27 — second pass (details that still separated us)

- **Long moves are steeper.** Peak ÷ average speed grows with distance: 2.9× under 250 px, 3.5×
  at 250–700 px, 3.9× (up to 8×) above 700 px. Our single travel curve was 2.7× everywhere, so long
  pans felt like even glides. → EASE_TRAVEL_MID (0.72,0.05,0.28,0.95), EASE_TRAVEL_LONG
  (0.75,0.04,0.25,0.96), `travelEase(px)`.
- **Motion blur on fast moves.** During fast pans their frame sharpness drops to 40–85% of rest
  (10% at 110–170 px/frame); ours stayed 100%. → directional blur via SVG feGaussianBlur,
  σ = 0.07 × (px/frame − 8), max 16 (calibrated by rendering a test and measuring sharpness).
- **Secondary moves ride on the primary one.** In Ads Engine the pause control shrinks to a dot and
  the next card grows in from the direction of travel *during* an 870 px pan. Our clips queued such
  changes after the move. → "one primary move, secondary moves ride on it".
- **Exits shrink to a point**, entrances from the side **unfold** (height first, then width),
  variants live in a **depth stack** (offset 14–24 px, scale 0.94–0.96, opacity 0.6–0.8).

## 2026-09-27 — first pass (curves)

- 68 clean moves, 34 fitted within 0.02 RMS. **No overshoot anywhere** → springs removed.
- Travel S-curve consensus (0.64,0.09,0.37,0.88); settle (0.5,0.2,0.18,0.95); entrances arrive
  fast then settle for ~1 s; exits (0.3,0,0.75,0); duration 0.14 + 0.038·√px s.
- Breathing: drift in 2/3 of quiet moments, ≈2 %/s zoom, ≈25 px/s, one direction.
- Our v3 film: a 108 px move in 0.13 s, a 418 px move peaking at 84% (abrupt landing), a camera
  spring overshoot, entrances chopped to 10–12 frames.

## How to extend this

1. Pick a reference moment that feels better than ours and the matching moment in our render.
2. Measure both the same way (`scripts/motion_curves.py`, or a targeted crop at the native frame
   rate), put numbers on the difference (duration, curve, peak speed, blur, what moves together).
3. If it is a real, repeatable difference, turn it into a rule with numbers, render a small test
   composition to calibrate it, add it to the standard and `scripts/motion_reference.json`, and log it
   here.
