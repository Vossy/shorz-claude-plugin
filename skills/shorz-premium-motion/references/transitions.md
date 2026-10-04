# Transitions — measured reference values

The recipes (T1–T13) live in section 5 of the MOTION CRAFT STANDARD
(`frontend/src/prompts/remotionMotionCraft.prompt.txt`); Animation Studio follows them without being
told. This file keeps the evidence: which reference moment each recipe comes from and the numbers to
compare a render against. Measure a render with `scripts/transition_measure.py VIDEO T0 T1` over a
window of the same length as the reference window and compare the lines below.

Columns: `alpha` = cross-fade progress from the first to the last frame of the window; `sharp` =
Laplacian variance as % of the sharper end frame (≈50% at 1px blur, ≈10% at 2px, ≈1% at ≥4px —
use `elevenlabs-ref/blurfit.py` for larger radii); `W` = width of the sharp content.

## The five laws, as measured

| Law | Evidence |
|---|---|
| Accelerate out, settle in, switch at the fastest frame | Studio 4.0 converge: the card cloud's width 1752 → 622px in 11 frames, each frame shrinking more than the last; the next scene appears at 1.065× and settles to 1.0 over 20 frames. Studio 4.0 Generate: the UI zooms out ×0.80 over 8 frames accelerating, the result appears mid-motion. Studio 4.0 push-in: the panel accelerates up 2 → 18px/frame, then the field appears. |
| Blur peaks at the switch | Defocus dissolves: outgoing sharpness 60 → 40% in 2 frames; incoming focus 20px → 1px over 0.65s (Ads Engine title). Converge: sharpness 100 → 4% over 11 frames. |
| Scale is geometric | Speech Engine orb 1 → 0.22 in 0.67s at a near-constant ×0.83–0.85 per frame, easing only at the end. Avatars scatter: ×0.54 pull-back, 57% of the log-zoom done in 0.2s. |
| Never mix two busy images | Studio 4.0 dissolves pass through a pastel wash: saturation 67 → 10–27, brightness +20–100; Avatars image → colour: saturation 42 → 27, brightness 196 → 228 in 3 frames. |
| The camera never stops | Polarity flip: push-in ×1.115 over 0.6s starts on the same frame as the fade. Bloom recede: push-in ×1.05 accelerating under the fade. |

## Per recipe

| Recipe | Reference (film, seconds) | Measured |
|---|---|---|
| T1 container → full frame | Dubbing v2 5.9–7.0, 38.8–39.9 | W 950 → 1918 in 0.78–0.85s; t50 0.40–0.48, t90 0.69–0.73, peak 0.38–0.49; sharpness ≥ 69%; content zooms 1.85× with the card |
| T2 full frame → container | Composer 26.4–27.3 | W 1906 → 702 in 0.8s; slow first 4 frames, t50 ≈ 0.32, t90 ≈ 0.65; brightness 100 → 18 as the black surround appears |
| T3 dot ↔ card | Ads Engine 2.05–3.0; Speech Engine 45.4–46.1 | burst: sharpness 4 → 72% in 5 frames, → 100% by 0.6s; shrink: scale 1 → 0.22 in 0.67s geometric |
| T4 converge → fly through | Studio 4.0 9.4–10.5; Flows 40.9–42.4 | converge 11 frames accelerating, sharpness → 4%; switch luma 63 → 205 in one frame; incoming 1.065 → 1.0 and sharpness 58 → 100% over 0.63s. Flows: dot grows ≈120px/frame linear to full frame in ≈16 frames, saturation 9 → 182 |
| T5 scatter | Avatars 14.9–15.9 | zoom ×0.54 in 0.78s in log space: t50 0.21, t90 0.62 — EASE_REVEAL (0.16, 0.26, 0.16, 0.84), fitted with Composer's pull-back 19.8–21.1 (×0.38 in 1.23s, t50 0.23) |
| T6 colour-bloom morph | Avatars 23.9–25.4 | snap 3 frames at 60fps (sharpness 100 → 6%, sat 42 → 28, luma 196 → 227) into a blurred pastel DUOTONE that keeps the subject's silhouette; drift 0.5s (silhouette re-coloured, then B's silhouette); resolve α 0.08 → 0.99 over 0.8s; card 702 → 864px |
| T7 defocus dissolve | Studio 4.0 30.0–31.2, 31.3–32.5; MCP 15.6–16.9; Ads Engine 47.6–49.0 | cross 4–6 frames (α 0.03 → 0.76) through a wash; incoming holds soft ≈12 frames then pulls focus in 5 (Studio 4.0), or focuses 20 → 1px over 0.65s (Ads Engine) |
| T8 push into a detail | Studio 4.0 11.4–12.7 | outgoing accelerates 0.37s; detail arrives ≥10px soft and focuses over ≈0.9s |
| T9 output burst | Studio 4.0 15.1–16.8 | UI ×0.80 in 8 frames accelerating; result full frame, sharpness 1%, luma 189 → 80 and sat 22 → 91 over 0.3s; contracts W 1898 → 1450 over 0.5s; focus snaps 26 → 63% then → 100% over 0.5s |
| T10 polarity flip | Speech Engine 6.3–7.1, 26.9–28.0 | light → dark: luma 243 → 59 in 4 frames + push-in ×1.115 SETTLE 0.6s; dark → light: 8 frames, with a pull-back |
| T11 plane wipe | Scribe v2 6.9–8.5, 20.8–21.9 | coverage per 1/15s 1 5 10 16 22 30 39 49 62 73 84 90 95 97 99% — TRAVEL (t50 0.52, peak 0.56), 0.9s from the first sliver at the frame edge |
| T12 shape morph | Composer 16.6–17.9 | width ≈0.55s, then height ≈0.4s (≈1.1s in all), lines fade in as the height lands, camera push ≈3% |
| T13 bloom recede | Ads Engine 1.3–2.3 | α steady over ≈1.0s, saturation 119 → 9, luma 181 → 238, push-in ×1.05 accelerating |

## Added in round 3 (2026-09-28)

| Recipe | Reference | Measured |
|---|---|---|
| T1 by card size | Flows 32.7–33.35 | a card already 67% wide goes full frame in 0.6s (≈410px corner travel), TRAVEL-shaped; Dubbing's smaller cards take 0.78–0.85s, SETTLE-shaped |
| T4 switch | Studio 4.0 9.77→9.80 | brightness 63 → 205 between two frames; the ground stays dark while only the cards pale; a warm glow builds around the cluster |
| T7 on dark films | MCP 35.6–36.6 | the outgoing shot LIFTS (luma 48 → 71) as it softens, switch at 35.87s, then settles to the dark ground (71 → 25) over 0.5s while the title focuses (sharpness 1 → 100% in 0.7s) |
| T8 vector variant | Speech Engine 3.1–3.9 | zoom ×2.43 in 0.73s, TRAVEL in log space (fastest at 40%), text slides out, caret stays; return = a match cut to the same line in its input card |
| Focus pulls | Ads Engine 48.3–48.9; Studio 4.0 12.05–12.95 | blur falls by a constant ratio per frame: ×0.85 (20 → 1px in 0.6s) for dissolves; ×0.92 for a push into a detail (still 1.2px after 0.9s) |
| Camera zooms under ×1.3 | Speech Engine 6.3–7.0 | sharpness stays ≥90% through a ×1.115 push — never zoom-blurred |
| T13 recede | Ads Engine 1.3–2.3 | the cloud withdraws toward the right edge rather than fading in place; the title dissolves letter by letter |

A regression suite (`shorz-promo-2026-09/ttests/tsuite.py`) aligns each recipe's test render with
its reference on the event frame and compares the key curve (cross-fade, brightness, rect or zoom)
on duration / t50 / t90, plus blur and wash where the recipe has them.

## Status after round 6 (2026-09-28)

All 13 recipes and 4 content variants pass the regression suite against their reference moments
(duration within 30%, t50/t90 within 0.15, blur and colour wash agreeing; 5 entries confirmed by
recorded side-by-side evidence where the whole-frame numbers are skewed). Blur-clearing ratios per
frame: ×0.7 entrance, ×0.85 dissolve/burst, ×0.92 push-in detail, ×0.95 after a converge switch.
Plane wipes: cover (new plane rises) and uncover (old scene slides off), 0.9–1.3s. Bloom recede:
opacity alone, EASE_SETTLE over 46–48 frames.

## Test log

See `motion-lessons.md` for the tests that calibrated these recipes and what each one changed.
