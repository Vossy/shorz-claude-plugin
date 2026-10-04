"""Measure one transition window frame by frame: what moves, what fades, what blurs.

usage: python transition_measure.py VIDEO T0 T1 [--table] [--json out.json]

Run it on the reference transition and on your render over windows of the same length, and compare
the numbers (see references/transitions.md for the measured reference values per recipe).

Per frame (native fps):
  zoom   cumulative camera scale vs the first frame (similarity chain, tracked features)
  pan    cumulative camera translation in px at 1080p
  alpha  cross-fade progress: frame ~ (1-a)*first + a*last  (least squares on 64x36 colour thumbs)
  resid  how much of the frame the cross-fade does NOT explain (0 = a pure dissolve)
  sharp  Laplacian variance as % of the sharper of the first/last frame (blur profile)
  luma   mean luma 0-255 (dips to black / flashes to white)
  sat    mean saturation 0-255 (colour blooms)
  rect   bounding box of sharp content at 1080p (container size / position)
Summary: active span, duration, curve fit (bezier, t50, t90, peak speed) of alpha, zoom and rect
width, minimum sharpness and where it falls, luma/sat excursions.
"""
import json, subprocess, sys
import numpy as np
import cv2
from motion_curves import probe, fit_bezier, describe

PW, PH = 960, 540


def load(path, t0, t1):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", path,
                          "-vf", f"scale={PW}:{PH}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, PH, PW, 3)


def sim(a, b):
    pts = cv2.goodFeaturesToTrack(a, maxCorners=600, qualityLevel=0.01, minDistance=5)
    if pts is None or len(pts) < 25:
        return None
    nxt, st, _ = cv2.calcOpticalFlowPyrLK(a, b, pts, None, winSize=(21, 21), maxLevel=3)
    g = st.reshape(-1) == 1
    if g.sum() < 25:
        return None
    M, inl = cv2.estimateAffinePartial2D(pts[g], nxt[g], method=cv2.RANSAC, ransacReprojThreshold=1.0)
    if M is None or inl.mean() < 0.5:
        return None
    return M


def sharp_rect(g):
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    m = np.hypot(gx, gy) > 60
    cols = np.where(m.sum(0) > 3)[0]
    rows = np.where(m.sum(1) > 3)[0]
    if len(cols) < 2 or len(rows) < 2:
        return None
    k = 1080 / PH
    return [int(cols[0] * k), int(rows[0] * k), int((cols[-1] - cols[0]) * k), int((rows[-1] - rows[0]) * k)]


def curve_of(t, y):
    """Normalise y over its active span (5%..95% of total change) and fit a bezier."""
    y = np.asarray(y, float)
    if not np.isfinite(y).all() or abs(y[-1] - y[0]) < 1e-6:
        return None
    p = (y - y[0]) / (y[-1] - y[0])
    pm = np.maximum.accumulate(np.clip(p, -0.2, 1.2))
    i0 = int(np.argmax(pm > 0.02))
    i1 = int(np.argmax(pm >= 0.98)) if (pm >= 0.98).any() else len(p) - 1
    i0 = max(0, i0 - 1)
    if i1 - i0 < 3:
        return {"dur_s": round(float(t[i1] - t[i0]), 3), "note": "too short to fit"}
    tt = (t[i0:i1 + 1] - t[i0]) / (t[i1] - t[i0])
    pp = (p[i0:i1 + 1] - p[i0]) / (p[i1] - p[i0])
    bz, e = fit_bezier(tt, pp)
    return {"start_s": round(float(t[i0]), 3), "dur_s": round(float(t[i1] - t[i0]), 3), "bezier": bz, "rms": e,
            **describe(tt, pp)}


def measure(path, t0, t1, table=False):
    fps = probe(path)[2]
    F = load(path, t0, t1)
    n = len(F)
    t = t0 + np.arange(n) / fps
    gray = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in F]
    thumbs = [cv2.resize(f, (64, 36), interpolation=cv2.INTER_AREA).astype(np.float32) for f in F]
    A, B = thumbs[0], thumbs[-1]
    D = (B - A).ravel()
    dd = float(D @ D) or 1.0
    zoom, panx, pany = [1.0], [0.0], [0.0]
    for i in range(1, n):
        M = sim(gray[i - 1], gray[i])
        if M is None:
            zoom.append(np.nan); panx.append(np.nan); pany.append(np.nan)
            continue
        s = float(np.hypot(M[0, 0], M[1, 0]))
        base = zoom[-1] if np.isfinite(zoom[-1]) else np.nan
        zoom.append(base * s if np.isfinite(base) else np.nan)
        k = 1080 / PH
        panx.append((panx[-1] + M[0, 2] * k) if np.isfinite(panx[-1]) else np.nan)
        pany.append((pany[-1] + M[1, 2] * k) if np.isfinite(pany[-1]) else np.nan)
    rows = []
    lap0 = cv2.Laplacian(gray[0], cv2.CV_32F).var()
    lap1 = cv2.Laplacian(gray[-1], cv2.CV_32F).var()
    ref = float(max(lap0, lap1, 1.0))
    for i in range(n):
        F_ = thumbs[i].ravel() - A.ravel()
        a = float(F_ @ D) / dd
        resid = float(np.linalg.norm(F_ - a * D) / (np.linalg.norm(D) + 1e-6))
        hsv = cv2.cvtColor(F[i], cv2.COLOR_BGR2HSV)
        rows.append({"t": round(float(t[i]), 3), "zoom": None if not np.isfinite(zoom[i]) else round(zoom[i], 4),
                     "pan": None if not np.isfinite(panx[i]) else [round(panx[i]), round(pany[i])],
                     "alpha": round(a, 3), "resid": round(resid, 3),
                     "sharp": round(float(100 * cv2.Laplacian(gray[i], cv2.CV_32F).var() / ref), 1),
                     "luma": round(float(gray[i].mean()), 1), "sat": round(float(hsv[..., 1].mean()), 1),
                     "rect": sharp_rect(gray[i])})
    al = np.array([r["alpha"] for r in rows])
    sh = np.array([r["sharp"] for r in rows])
    lu = np.array([r["luma"] for r in rows])
    sa = np.array([r["sat"] for r in rows])
    summ = {"video": path, "t0": t0, "t1": t1, "fps": fps, "frames": n,
            "alpha": curve_of(t, al), "max_resid": round(float(max(r["resid"] for r in rows)), 3),
            "sharp_min_pct": round(float(sh.min()), 1), "sharp_min_at_s": round(float(t[int(sh.argmin())]), 3),
            "blur_span_s": round(float((sh < 80).sum() / fps), 3),
            "luma": [round(float(lu[0])), round(float(lu.min())), round(float(lu.max())), round(float(lu[-1]))],
            "sat": [round(float(sa[0])), round(float(sa.min())), round(float(sa.max())), round(float(sa[-1]))]}
    z = np.array([r["zoom"] if r["zoom"] is not None else np.nan for r in rows], float)
    if np.isfinite(z).sum() > 0.8 * n:
        zi = np.interp(np.arange(n), np.where(np.isfinite(z))[0], z[np.isfinite(z)])
        summ["zoom_total"] = round(float(zi[-1]), 3)
        summ["zoom_range"] = [round(float(zi.min()), 3), round(float(zi.max()), 3)]
        if abs(np.log(zi[-1])) > 0.03:
            summ["zoom_curve"] = curve_of(t, np.log(zi))
    w = np.array([r["rect"][2] if r["rect"] else np.nan for r in rows], float)
    if np.isfinite(w).sum() > 0.8 * n and abs(np.nanmax(w) - np.nanmin(w)) > 80:
        wi = np.interp(np.arange(n), np.where(np.isfinite(w))[0], w[np.isfinite(w)])
        summ["rect_w"] = [int(wi[0]), int(wi.min()), int(wi.max()), int(wi[-1])]
        summ["rect_w_curve"] = curve_of(t, wi)
    if table:
        for r in rows:
            print(f"{r['t']:8.3f} zoom {str(r['zoom']):>7} pan {str(r['pan']):>13} a {r['alpha']:6.3f} res {r['resid']:5.2f} "
                  f"sharp {r['sharp']:6.1f} luma {r['luma']:6.1f} sat {r['sat']:6.1f} rect {r['rect']}")
    return summ, rows


if __name__ == "__main__":
    path, a, b = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    summ, rows = measure(path, a, b, "--table" in sys.argv)
    print(json.dumps(summ, indent=1))
    if "--json" in sys.argv:
        json.dump({"summary": summ, "rows": rows}, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
