"""Measure the exact motion curves of a film, frame by frame at its native frame rate, and check a
render against the measured launch-film rules (the MOTION CRAFT STANDARD's section 3).

usage: python motion_curves.py VIDEO [VIDEO ...] [--out DIR] [--check]
  --check   also print rule violations: overshoot, travel shorter than the distance rule, travel
            whose speed peaks too early/late, and a camera that parks during holds.
needs: ffmpeg/ffprobe on PATH, numpy, opencv-python, scipy

For every CLEAN move (motion bounded by stillness before and after, 4 frames to 3 s):
  * kind: camera (whole frame transforms: zoom / pan) or element (a region moves / scales / appears)
  * progress curve p(t), t and p normalised to 0..1, from
      - camera: cumulative global similarity transform (log-scale for zooms, path length for pans)
      - element: features tracked BACKWARD from the settled end frame (translation + scale)
      - appear/disappear/fade: the region's pixel change toward its final state
  * a cubic-bezier fit (x1, y1, x2, y2), fit RMS error, overshoot % (peak beyond 1), whether it
    springs (oscillates around 1), where peak speed falls (0 = at the start, 1 = at the end),
    time to 50% / 90%, duration (frames, s) and amplitude (px at 1080p, or scale factor).
Writes <name>.curves.json and prints a table.
"""
import argparse, json, os, subprocess
import numpy as np
import cv2
from scipy.optimize import minimize

W = 640


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate", "-of", "json", path], capture_output=True, text=True).stdout
    s = json.loads(out)["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return s["width"], s["height"], float(num) / float(den)


def read_frames(path):
    w, h, fps = probe(path)
    H = int(round(W * h / w / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W), fps, 1080.0 / H


# ---------------------------------------------------------------- bezier
def bez(p1, p2, u):
    return 3 * (1 - u) ** 2 * u * p1 + 3 * (1 - u) * u ** 2 * p2 + u ** 3


def bez_y_at(x1, y1, x2, y2, t):
    u = np.linspace(0, 1, 400)
    xs, ys = bez(x1, x2, u), bez(y1, y2, u)
    order = np.argsort(xs)
    return np.interp(t, xs[order], ys[order])


def fit_bezier(t, p):
    def err(v):
        x1, y1, x2, y2 = v
        if not (0 <= x1 <= 1 and 0 <= x2 <= 1):
            return 10.0
        return float(np.sqrt(np.mean((bez_y_at(x1, y1, x2, y2, t) - p) ** 2)))
    best = None
    for s in ([0.25, 0.1, 0.25, 1], [0.16, 1, 0.3, 1], [0.65, 0, 0.35, 1], [0.7, 0, 0.84, 0], [0.33, 0, 0.67, 1], [0.2, 0.9, 0.3, 1.1]):
        r = minimize(err, s, method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-5, "maxiter": 3000})
        if best is None or r.fun < best.fun:
            best = r
    return [round(float(v), 3) for v in best.x], round(float(best.fun), 4)


def _ease_families():
    import math
    c1 = 1.70158
    F = {"linear": lambda x: x,
         "sine-in-out": lambda x: -(np.cos(np.pi * x) - 1) / 2, "sine-out": lambda x: np.sin(x * np.pi / 2),
         "quad-out": lambda x: 1 - (1 - x) ** 2, "cubic-out": lambda x: 1 - (1 - x) ** 3,
         "quart-out": lambda x: 1 - (1 - x) ** 4, "quint-out": lambda x: 1 - (1 - x) ** 5,
         "expo-out": lambda x: np.where(x >= 1, 1, 1 - 2 ** (-10 * x)), "circ-out": lambda x: np.sqrt(1 - (x - 1) ** 2),
         "quad-in-out": lambda x: np.where(x < .5, 2 * x * x, 1 - (-2 * x + 2) ** 2 / 2),
         "cubic-in-out": lambda x: np.where(x < .5, 4 * x ** 3, 1 - (-2 * x + 2) ** 3 / 2),
         "quart-in-out": lambda x: np.where(x < .5, 8 * x ** 4, 1 - (-2 * x + 2) ** 4 / 2),
         "quint-in-out": lambda x: np.where(x < .5, 16 * x ** 5, 1 - (-2 * x + 2) ** 5 / 2),
         "expo-in-out": lambda x: np.where(x <= 0, 0, np.where(x >= 1, 1, np.where(x < .5, 2 ** (20 * x - 10) / 2, (2 - 2 ** (-20 * x + 10)) / 2))),
         "cubic-in": lambda x: x ** 3, "quart-in": lambda x: x ** 4, "expo-in": lambda x: np.where(x <= 0, 0, 2 ** (10 * x - 10)),
         "back-out": lambda x: 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2}
    return F


FAMILIES = _ease_families()


def best_family(t, p):
    best = min(((float(np.sqrt(np.mean((f(t) - p) ** 2))), k) for k, f in FAMILIES.items()))
    return best[1], round(best[0], 4)


def describe(t, p):
    dp = np.gradient(p, t)
    peak_v = float(t[int(np.argmax(dp))])
    over = float(max(0.0, p.max() - 1.0))
    after = p[int(np.argmax(p >= 0.999)):] if (p >= 0.999).any() else np.array([])
    springs = bool(len(after) > 3 and np.sum(np.diff(np.sign(after - 1.0)) != 0) >= 2 and over > 0.01)
    t50 = float(np.interp(0.5, np.maximum.accumulate(p), t))
    t90 = float(np.interp(0.9, np.maximum.accumulate(p), t))
    return {"peak_speed_at": round(peak_v, 2), "overshoot_pct": round(over * 100, 1), "springs": springs,
            "t50": round(t50, 2), "t90": round(t90, 2)}


# ---------------------------------------------------------------- motion
def global_sim(a, b):
    pts = cv2.goodFeaturesToTrack(a, maxCorners=500, qualityLevel=0.01, minDistance=6)
    if pts is None or len(pts) < 20:
        return None
    nxt, st, _ = cv2.calcOpticalFlowPyrLK(a, b, pts, None, winSize=(21, 21), maxLevel=3)
    g = st.reshape(-1) == 1
    if g.sum() < 20:
        return None
    M, inl = cv2.estimateAffinePartial2D(pts[g], nxt[g], method=cv2.RANSAC, ransacReprojThreshold=1.0)
    if M is None:
        return None
    return M, float(inl.mean())


def events(f, fps):
    d = np.array([np.abs(f[i + 1].astype(np.int16) - f[i].astype(np.int16)).mean() for i in range(len(f) - 1)])
    still, move = 0.25, 0.6
    mv = d > move
    out, i = [], 0
    while i < len(d):
        if not mv[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(d) and (mv[j + 1] or (j + 3 < len(d) and mv[j + 2:j + 4].any())):
            j += 1
        a, b = i, j
        while a > 0 and d[a - 1] > still:
            a -= 1
        while b + 1 < len(d) and d[b + 1] > still:
            b += 1
        pre = d[max(0, a - 4):a]
        post = d[b + 1:b + 5]
        n = b - a + 1
        peak = d[a:b + 1].max()
        calm = max(still * 1.6, peak * 0.22)   # the scene may keep breathing; the move must dominate it
        if 4 <= n <= 3 * fps and len(pre) >= 3 and len(post) >= 3 and pre.max() < calm and post.max() < calm:
            if not out or out[-1] != (a, b + 1):
                out.append((a, b + 1))   # frames a .. b+1 (inclusive of the settled end frame)
        i = max(j + 1, b + 1)
    return out, d


def camera_curve(f, a, b):
    s_log, path, inl = [0.0], [0.0], []
    x = y = 0.0
    for k in range(a, b):
        r = global_sim(f[k], f[k + 1])
        if r is None:
            return None
        M, q = r
        inl.append(q)
        sc = float(np.hypot(M[0, 0], M[1, 0]))
        c = np.array([f.shape[2] / 2, f.shape[1] / 2])
        cc = M[:, :2] @ c + M[:, 2]
        x += cc[0] - c[0]
        y += cc[1] - c[1]
        s_log.append(s_log[-1] + np.log(sc))
        path.append(np.hypot(x, y))
    if np.mean(inl) < 0.55:
        return None
    s_log, path = np.array(s_log), np.array(path)
    zoom = abs(s_log[-1])
    if zoom > 0.02 and zoom * 300 > path[-1]:
        return "zoom", s_log / s_log[-1], float(np.exp(s_log[-1]))
    if path[-1] > 6:
        return "pan", path / path[-1], float(path[-1])
    return None


def element_curve(f, a, b):
    end = f[b]
    mask = (np.abs(end.astype(np.int16) - f[a].astype(np.int16)) > 18).astype(np.uint8) * 255
    mask = cv2.dilate(mask, np.ones((9, 9), np.uint8))
    if mask.mean() < 0.3:
        return None
    ys, xs = np.nonzero(mask)
    box = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    pts = cv2.goodFeaturesToTrack(end, maxCorners=200, qualityLevel=0.01, minDistance=4, mask=mask)
    res = {}
    if pts is not None and len(pts) >= 8:
        p0 = pts.copy()
        cur = pts.copy()
        alive = np.ones(len(pts), bool)
        tx, ty, ls = [0.0], [0.0], [0.0]
        for k in range(b, a, -1):
            nxt, st, err = cv2.calcOpticalFlowPyrLK(f[k], f[k - 1], cur, None, winSize=(21, 21), maxLevel=3)
            alive &= st.reshape(-1) == 1
            cur = nxt
            if alive.sum() < 6:
                break
            M, _ = cv2.estimateAffinePartial2D(p0[alive], cur[alive], method=cv2.RANSAC, ransacReprojThreshold=2.0)
            if M is None:
                break
            d = np.median(cur[alive] - p0[alive], axis=0).reshape(-1)
            tx.append(float(d[0]))
            ty.append(float(d[1]))
            ls.append(float(np.log(np.hypot(M[0, 0], M[1, 0]))))
        n_tracked = len(tx)
        if n_tracked == b - a + 1:
            tx, ty, ls = np.array(tx[::-1]), np.array(ty[::-1]), np.array(ls[::-1])
            # position relative to the END (settled) state; progress = 1 - remaining/initial
            dist = np.hypot(tx, ty)
            if dist[0] > 4:
                res["move"] = (1 - dist / dist[0], float(dist[0]))
            if abs(ls[0]) > 0.03:
                res["scale"] = (1 - ls / ls[0], float(np.exp(-ls[0])))
    # region appearance: how far each frame is toward the final pixels, inside the changed region
    x0, y0, x1, y1 = box
    r0 = f[a][y0:y1 + 1, x0:x1 + 1].astype(np.float32)
    r1 = end[y0:y1 + 1, x0:x1 + 1].astype(np.float32)
    denom = np.abs(r1 - r0).mean()
    if denom > 3:
        prog = [1 - np.abs(r1 - f[k][y0:y1 + 1, x0:x1 + 1].astype(np.float32)).mean() / denom for k in range(a, b + 1)]
        res["appear"] = (np.array(prog), float(denom))
    return res, box


def study(path, outdir):
    name = os.path.splitext(os.path.basename(path))[0]
    f, fps, k = read_frames(path)
    ev, d = events(f, fps)
    rows = []
    for a, b in ev:
        n = b - a
        t = np.linspace(0, 1, n + 1)
        base = {"film": name, "t0": round(a / fps, 2), "frames": n, "dur_s": round(n / fps, 3), "fps": fps}
        cam = camera_curve(f, a, b)
        curves = []
        if cam:
            kind, p, amp = cam
            curves.append((f"camera-{kind}", p, round(amp * (k if kind == "pan" else 1), 3)))
        else:
            er = element_curve(f, a, b)
            if er:
                res, box = er
                base["box_1080"] = [int(v * k) for v in box]
                if "move" in res:
                    curves.append(("element-move", res["move"][0], round(res["move"][1] * k, 1)))
                if "scale" in res:
                    curves.append(("element-scale", res["scale"][0], round(res["scale"][1], 3)))
                if not curves and "appear" in res:
                    curves.append(("element-appear", res["appear"][0], round(res["appear"][1], 1)))
        for kind, p, amp in curves:
            p = np.clip(p, -0.5, 1.6)
            if p[-1] < 0.9:
                continue
            bz, e = fit_bezier(t, p)
            if e > 0.045:
                continue          # not a clean single move (tracking lost, a cut, or two moves)
            fam, fe = best_family(t, p)
            rows.append({**base, "kind": kind, "amplitude": amp, "bezier": bz, "fit_rms": e, "family": fam, "family_rms": fe, **describe(t, p),
                         "curve": [round(float(v), 3) for v in p]})
    os.makedirs(outdir, exist_ok=True)
    json.dump(rows, open(os.path.join(outdir, name + ".curves.json"), "w"), indent=1)
    print(f"{name}: {len(ev)} clean moves, {len(rows)} curves  ({fps:g} fps)")
    for r in rows:
        print(f"  {r['t0']:6.2f}s {r['kind']:15s} {r['frames']:3d}f {r['dur_s']:5.2f}s amp={r['amplitude']!s:>8} "
              f"{r['family']:13s}({r['family_rms']:.3f}) bez={r['bezier']} rms={r['fit_rms']:.3f} peakV@{r['peak_speed_at']:.2f} over={r['overshoot_pct']}% "
              f"{'SPRING' if r['springs'] else ''} t50={r['t50']} t90={r['t90']}")
    return rows


def breathing(path):
    """How alive the frame is while nothing big moves: share of quiet moments that still drift, and
    the drift rates. Launch-film reference: drifting in ~2/3 of quiet moments, ~2%/s zoom, ~25 px/s."""
    f, fps, k = read_frames(path)
    step = max(1, int(round(fps / 10)))
    zr, pr, vec, idx = [], [], [], []
    for i in range(0, len(f) - step, step):
        r = global_sim(f[i], f[i + step])
        if r is None:
            continue
        M, q = r
        if q < 0.7:
            continue
        d = np.abs(f[i + step].astype(np.int16) - f[i].astype(np.int16)).mean()
        z = abs(float(np.hypot(M[0, 0], M[1, 0])) - 1) * 100 * (fps / step)
        pan = float(np.hypot(M[0, 2], M[1, 2])) * k * (fps / step)
        if z < 12 and pan < 120 and d < 2.5:
            zr.append(z)
            pr.append(pan)
            vec.append((float(M[0, 2]), float(M[1, 2])))
            idx.append(i)
    zr, pr = np.array(zr), np.array(pr)
    if not len(zr):
        return None
    drifting = (zr > 0.3) | (pr > 3)
    # direction of each hold (a run of consecutive quiet samples >= 0.5 s): the way the CONTENT slides
    dirs, run = [], []
    names = ["right", "down-right", "down", "down-left", "left", "up-left", "up", "up-right"]

    def close(run):
        if len(run) * step / fps < 0.5:
            return
        dx = np.mean([vec[j][0] for j in run]); dy = np.mean([vec[j][1] for j in run])
        if np.hypot(dx, dy) * k * (fps / step) > 3:
            dirs.append(names[int(((np.degrees(np.arctan2(dy, dx)) + 22.5) % 360) // 45)])

    for j in range(len(idx)):
        if run and idx[j] != idx[run[-1]] + step:
            close(run)
            run = []
        run.append(j)
    close(run)
    return {"quiet_samples": int(len(zr)), "drifting_share": round(float(drifting.mean()), 2),
            "zoom_pct_per_s": round(float(np.median(zr[zr > 0.3])) if (zr > 0.3).any() else 0.0, 2),
            "pan_px_per_s": round(float(np.median(pr[pr > 3])) if (pr > 3).any() else 0.0, 1),
            "content_drift_by_hold": dirs}


def motion_blur(path):
    """Frame sharpness while the frame TRANSLATES fast (> 20 px/frame at 1080p) relative to rest.
    Reference: 40-85% of rest (as low as 10% at 110-170 px/frame); ~100% means no motion blur.
    Only translation counts: frames whose similarity scale changes by more than 1% are a container
    growing or shrinking (the reference keeps growing cards sharp, >= 90% of rest), and frames the
    tracker cannot follow (inliers < 50%) are cuts inside footage, not motion. Both are reported
    separately and never judged as missing blur."""
    f, fps, k = read_frames(path)
    rows = []
    for i in range(len(f) - 1):
        r = global_sim(f[i], f[i + 1])
        if r is None:
            continue
        M, q = r
        rows.append((float(np.hypot(M[0, 2], M[1, 2])) * k, float(cv2.Laplacian(f[i], cv2.CV_64F).var()),
                     float(np.hypot(M[0, 0], M[1, 0])), q))
    if not rows:
        return None
    a = np.array(rows)
    tracked = a[:, 3] >= 0.5
    morph = tracked & (np.abs(a[:, 2] - 1) > 0.01)
    pan = tracked & ~morph
    resting = pan & (a[:, 0] < 1.5)
    fast_idx = np.where(pan & (a[:, 0] > 20))[0]
    info = {"scale_morph_frames": int((morph & (a[:, 0] > 20)).sum()), "untracked_frames": int((~tracked).sum())}
    # Compare each fast frame with the resting frames NEAREST in time (same content), not the whole
    # film's median: a film whose fast frames carry footage and whose rests are plain canvas would
    # otherwise read as "sharper while moving".
    win = int(round(0.7 * fps / 1))
    ratios = []
    for i in fast_idx:
        near = np.where(resting[max(0, i - win):i + win + 1])[0]
        if len(near):
            ratios.append(a[i, 1] / np.median(a[max(0, i - win) + near, 1]))
    if not ratios:
        return {"fast_frames": int(len(fast_idx)), **info}
    return {"fast_frames": int(len(fast_idx)), "judged_frames": len(ratios),
            "very_fast_frames": int((a[pan, 0] > 30).sum()),
            "max_speed_px_per_frame": round(float(a[pan, 0].max()), 1),
            "fast_sharpness_pct_of_rest": round(float(np.median(ratios)) * 100, 1), **info}


REF_STEEP = {250: 2.9, 700: 3.5, 10 ** 9: 3.9}


def check(rows, br, mb=None):
    issues = []
    for r in rows:
        if r["fit_rms"] > 0.02 or r["kind"] not in ("camera-pan", "element-move") or not (0.3 <= r["t50"] <= 0.65):
            continue
        tt = np.linspace(0, 1, 400)
        ratio = float(np.max(np.gradient(bez_y_at(*r["bezier"], tt), tt)))
        want = next(v for lim, v in REF_STEEP.items() if abs(r["amplitude"]) < lim)
        if ratio < 0.75 * want:
            issues.append(f"{r['t0']:.2f}s {r['kind']}: {r['amplitude']:.0f}px peaks at {ratio:.1f}x its average speed - "
                          f"reference {want}x for this distance (use travelEase(px))")
    # judge blur only on genuinely fast whole-frame motion: >= 3 frames faster than 30 px/frame
    very_fast = min(mb.get("very_fast_frames", 0), mb.get("judged_frames", 0)) if mb else 0
    if mb and mb.get("fast_sharpness_pct_of_rest") is not None and very_fast >= 3 and mb["fast_sharpness_pct_of_rest"] > 95:
        issues.append(f"no motion blur: fast frames keep {mb['fast_sharpness_pct_of_rest']}% sharpness (reference 40-85%)")
    for r in rows:
        if r["fit_rms"] > 0.02:
            continue
        if r["overshoot_pct"] > 1.0 or r["springs"]:
            issues.append(f"{r['t0']:.2f}s {r['kind']}: overshoots {r['overshoot_pct']}% - measured films never pass the target")
        if r["kind"] in ("camera-pan", "element-move"):
            want = 0.14 + 0.038 * np.sqrt(abs(r["amplitude"]))
            if r["dur_s"] < 0.55 * want:   # the reference films themselves range down to ~0.56x
                issues.append(f"{r['t0']:.2f}s {r['kind']}: {r['amplitude']:.0f}px in {r['dur_s']:.2f}s - distance rule wants ~{want:.2f}s")
            if r["peak_speed_at"] > 0.75:
                issues.append(f"{r['t0']:.2f}s {r['kind']}: speed peaks at {r['peak_speed_at']:.0%} - lands abruptly (use EASE_TRAVEL/EASE_SETTLE)")
    if br:
        dirs = br.get("content_drift_by_hold") or []
        horiz = [("left" if "left" in d else "right" if "right" in d else None) for d in dirs]
        horiz = [h for h in horiz if h]
        if len(dirs) >= 3 and horiz and max(horiz.count("left"), horiz.count("right")) >= 0.8 * len(dirs):
            side = "left" if horiz.count("left") >= horiz.count("right") else "right"
            issues.append(f"drift always slides {side} ({len(horiz)} of {len(dirs)} holds) - reference films change "
                          f"direction almost every hold (diagonals, both horizontals, vertical, zoom-only)")
        if br["drifting_share"] < 0.55 or br["zoom_pct_per_s"] < 0.8:
            issues.append(f"camera parks: drifting in {br['drifting_share']:.0%} of quiet moments at {br['zoom_pct_per_s']}%/s "
                          f"(reference ~2/3 at ~2%/s, ~25 px/s)")
    return issues


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--out", default="curves")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    allrows = []
    for v in a.videos:
        rows = study(v, a.out)
        allrows += rows
        if a.check:
            br = breathing(v)
            mb = motion_blur(v)
            print(f"  breathing: {br}")
            print(f"  motion blur: {mb}")
            issues = check(rows, br, mb)
            print("  RULE CHECK: " + ("pass" if not issues else f"{len(issues)} issue(s)"))
            for i in issues:
                print("   - " + i)
    json.dump(allrows, open(os.path.join(a.out, "_all.curves.json"), "w"), indent=1)
