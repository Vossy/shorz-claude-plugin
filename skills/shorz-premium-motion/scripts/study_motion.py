"""Study the motion of a video: a reference film you want to learn from, or your own render.

usage: python study_motion.py VIDEO [VIDEO ...] [--out DIR]
needs: ffmpeg/ffprobe on PATH, numpy, opencv-python

For each video it writes into DIR (default: <video folder>/motion-study):
  <name>.study.json      cuts, shot lengths, light/dark background share, still share, and a
                         0.5 s timeline of camera motion (zoom %, pan px at 1080p, element motion)
                         with continuous camera runs (duration, amount, easing)
  <name>-half-NN.jpg     contact sheets at 0.5 s steps (12 s per sheet) — read these to see
                         exactly what moves where
  <name>-fast-N.jpg      10 fps sheets across the four fastest 1.5 s windows — read these to see
                         how the fastest moves are built frame by frame
and prints a one-line timeline: . hold  d drift  E elements  P pan  + zoom in  - zoom out  # change
"""
import argparse, json, os, subprocess
import numpy as np
import cv2

FPS, W = 10, 480


def probe_wh(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    w, h = [int(x) for x in out.strip().split(",")[:2]]
    return w, h


def read_gray(path):
    w, h = probe_wh(path)
    H = int(round(W * h / w / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={FPS},scale={W}:{H},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W), w


def pair_motion(a, b):
    diff = float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean())
    base = dict(s=1.0, dx=0.0, dy=0.0, local=0.0, inl=0.0, diff=diff, ok=False)
    pts = cv2.goodFeaturesToTrack(a, maxCorners=400, qualityLevel=0.01, minDistance=6)
    if pts is None or len(pts) < 12:
        return base
    nxt, st, _ = cv2.calcOpticalFlowPyrLK(a, b, pts, None, winSize=(21, 21), maxLevel=3)
    good = st.reshape(-1) == 1
    p0, p1 = pts[good].reshape(-1, 2), nxt[good].reshape(-1, 2)
    if len(p0) < 12:
        return base
    M, inl = cv2.estimateAffinePartial2D(p0, p1, method=cv2.RANSAC, ransacReprojThreshold=2.0)
    if M is None:
        return base
    c = np.array([W / 2, a.shape[0] / 2])
    cc = M[:, :2] @ c + M[:, 2]
    resid = np.linalg.norm(p1 - ((M[:, :2] @ p0.T).T + M[:, 2]), axis=1)
    moving = resid[resid > 1.0]
    return dict(s=float(np.hypot(M[0, 0], M[1, 0])), dx=float(cc[0] - c[0]), dy=float(cc[1] - c[1]),
                local=float(np.median(moving)) if len(moving) > 0.1 * len(resid) else 0.0,
                inl=float(inl.mean()), diff=diff, ok=True)


def classify(b):
    if b["diff"] < 0.6 and abs(b["zoom"]) < 0.5 and b["local"] < 1.5:
        return "HOLD"
    if b["change"]:
        return "CHANGE"
    z, pan = b["zoom"], float(np.hypot(*b["pan"]))
    if abs(z) >= 2.0 and abs(z) * 10 >= pan * 0.15:
        return "ZOOM IN" if z > 0 else "ZOOM OUT"
    if pan >= 25:
        return "PAN"
    return "ELEMENTS" if b["local"] >= 1.5 else "DRIFT"


def camera_runs(bins, pairs, K):
    out, cur = [], None
    for b in bins:
        if b["class"] in ("ZOOM IN", "ZOOM OUT", "PAN"):
            if cur and cur["class"] == b["class"]:
                cur["end"] = b["t"] + 0.5
            else:
                cur = {"class": b["class"], "start": b["t"], "end": b["t"] + 0.5}
                out.append(cur)
        else:
            cur = None
    for r in out:
        seg = pairs[int(r["start"] * FPS):int(r["end"] * FPS)]
        if r["class"] == "PAN":
            sp = np.array([np.hypot(p["dx"], p["dy"]) for p in seg]) * K
            r["amount"] = f"{sp.sum():.0f}px"
        else:
            sp = np.array([abs(np.log(p["s"])) for p in seg])
            r["amount"] = f"x{float(np.exp(sum(np.log(p['s']) for p in seg))):.2f}"
        if len(sp) >= 3 and sp.sum() > 0:
            pk = int(np.argmax(np.convolve(sp, np.ones(3) / 3, "same"))) / max(len(sp) - 1, 1)
            r["easing"] = "ease-out (fast start)" if pk < 0.33 else ("ease-in (fast end)" if pk > 0.67 else "ease-in-out")
        r["duration"] = round(r["end"] - r["start"], 1)
    return out


def cuts(path, thr=0.28):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-an", "-vf",
                          f"select='gt(scene,{thr})',showinfo", "-f", "null", "-"], capture_output=True, text=True).stderr
    return [float(x.split("pts_time:")[1].split()[0]) for x in err.splitlines() if "pts_time:" in x]


def sheet(path, out, start, dur, fps, cols, width):
    rows = max(1, int(round(dur * fps / cols)))
    label = f"drawtext=text='%{{eif\\:t+{start}\\:d}}.%{{eif\\:mod((t+{start})*100\\,100)\\:d\\:2}}s':x=4:y=4:fontsize=18:fontcolor=yellow:box=1:boxcolor=black@0.7"
    subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-ss", str(start), "-t", str(dur), "-i", path, "-vf",
                    f"fps={fps},scale={width}:-1,{label},tile={cols}x{rows}:padding=2:color=white", "-frames:v", "1", out])


def study(path, outdir):
    name = os.path.splitext(os.path.basename(path))[0]
    f, src_w = read_gray(path)
    K = 1920 / W
    dur = len(f) / FPS
    pairs = [pair_motion(f[i], f[i + 1]) for i in range(len(f) - 1)]
    bins = []
    for i in range(0, len(pairs), FPS // 2):
        seg = pairs[i:i + FPS // 2]
        ok = [p for p in seg if p["ok"] and p["inl"] > 0.35]
        zoom = (np.exp(sum(np.log(p["s"]) for p in ok)) - 1) * 100 if ok else 0.0
        b = {"t": round(i / FPS, 1), "zoom": round(float(zoom), 1),
             "pan": (round(sum(p["dx"] for p in ok) * K), round(sum(p["dy"] for p in ok) * K)),
             "local": round(float(np.median([p["local"] for p in seg])) * K, 1),
             "diff": round(float(np.mean([p["diff"] for p in seg])), 2),
             "change": any(p["diff"] > 12 and (not p["ok"] or p["inl"] < 0.35) for p in seg)}
        b["class"] = classify(b)
        bins.append(b)
    lum = f.reshape(len(f), -1).mean(axis=1)
    cc = cuts(path)
    shots = np.diff([0.0] + cc + [dur])
    energy = np.array([p["diff"] for p in pairs])
    sums = np.convolve(energy, np.ones(15), "valid")
    fast = []
    for i in np.argsort(-sums):
        t = i / FPS
        if all(abs(t - x) > 2.0 for x in fast):
            fast.append(round(float(t), 1))
        if len(fast) == 4:
            break
    share = {}
    for b in bins:
        share[b["class"]] = share.get(b["class"], 0) + 1
    result = {
        "name": name, "duration": round(dur, 2), "cuts": [round(c, 2) for c in cc],
        "median_shot_s": round(float(np.median(shots)), 2),
        "light_bg_share": round(float((lum > 170).mean()), 2), "dark_bg_share": round(float((lum < 60).mean()), 2),
        "still_share": round(float((energy < 0.3).mean()), 2),
        "class_share": {k: round(v / len(bins), 2) for k, v in share.items()},
        "camera_runs": camera_runs(bins, pairs, K), "bins": bins, "fast_windows": sorted(fast),
    }
    os.makedirs(outdir, exist_ok=True)
    json.dump(result, open(os.path.join(outdir, name + ".study.json"), "w"), indent=1)
    k = 0
    for s in range(0, int(dur + 0.999), 12):
        sheet(path, os.path.join(outdir, f"{name}-half-{k:02d}.jpg"), s, min(12, dur - s), 2, 6, 320)
        k += 1
    for j, t in enumerate(sorted(fast)):
        sheet(path, os.path.join(outdir, f"{name}-fast-{j}.jpg"), max(0.0, t - 0.2), 2.4, 10, 6, 320)
    tags = {"HOLD": ".", "DRIFT": "d", "ELEMENTS": "E", "PAN": "P", "ZOOM IN": "+", "ZOOM OUT": "-", "CHANGE": "#"}
    print(f"{name}: {dur:.1f}s, {len(cc)} cuts, median shot {result['median_shot_s']}s, "
          f"light bg {result['light_bg_share']:.0%}, still {result['still_share']:.0%}")
    print("  0.5s timeline: " + "".join(tags[b["class"]] for b in bins))
    for r in result["camera_runs"]:
        print(f"  {r['start']:5.1f}-{r['end']:5.1f}s {r['class']:8s} {r['amount']:>8s} in {r['duration']}s {r.get('easing', '')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--out")
    a = ap.parse_args()
    for v in a.videos:
        study(v, a.out or os.path.join(os.path.dirname(os.path.abspath(v)), "motion-study"))
