import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyse_iq2 import load, groups, find_line, narrow, bursts, db

ROOT = sys.argv[1]; OUT = sys.argv[2]
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
COL = {"Deben": "#2a78d6", "Mine": "#eb6834"}

data = {}
for who in ("Deben", "Mine"):
    key, paths = list(groups(os.path.join(ROOT, who)).items())[-1]   # 13:04 and 13:08 pair
    x, fc, sr = load(paths)
    f0, _ = find_line(x, fc, sr)
    y, ysr = narrow(x, fc, sr, f0)
    env2 = np.abs(y) ** 2
    st, en, noise = bursts(np.sqrt(env2), ysr)
    # per-burst carrier
    fb, tb = [], []
    for s, e in zip(st, en):
        n = e - s; mid = y[s + n // 4: e - n // 4]
        if len(mid) < 20: continue
        fb.append(f0 + np.angle(np.sum(mid[1:] * np.conj(mid[:-1]))) * ysr / (2 * np.pi)); tb.append(s / ysr)
    fb = np.array(fb)
    # spectrum during bursts, full rate
    nfft = 1 << 15; acc = np.zeros(nfft); c = 0; dec = sr // ysr
    for s, e in zip(st[:60], en[:60]):
        a, b = int(s * dec), int(e * dec); n = b - a
        seg = x[a + n // 10: b - n // 10]
        acc += np.abs(np.fft.fft(seg * np.hanning(len(seg)), nfft)) ** 2 / len(seg); c += 1
    fr = fc + np.fft.fftfreq(nfft, 1 / sr); o = np.argsort(fr)
    # average burst shape aligned to the start
    pre, post = int(0.002 * ysr), int(0.016 * ysr)
    stack = [env2[s - pre: s + post] for s in st[:60] if s - pre >= 0 and s + post <= len(env2)]
    shape = np.mean(stack, axis=0)
    data[who] = dict(env2=env2, ysr=ysr, st=st, en=en, fb=fb, tb=np.array(tb),
                     fr=fr[o], spec=acc[o] / c, shape=shape, pre=pre,
                     L=np.median((en - st) / ysr * 1e3), per=np.median(np.diff(st)) / ysr * 1e3,
                     f=np.median(fb))

# common dB reference: the Deben's in-burst level = 0 dB
ref = np.median(data["Deben"]["shape"][data["Deben"]["pre"] + 200: data["Deben"]["pre"] + 900])

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.titlecolor": INK, "axes.titleweight": "bold", "axes.titlesize": 11,
                     "axes.titlelocation": "left", "figure.facecolor": SURF, "axes.facecolor": SURF})
fig, ax = plt.subplots(2, 2, figsize=(13, 8.2))
fig.subplots_adjust(hspace=0.42, wspace=0.22, left=0.07, right=0.97, top=0.86, bottom=0.08)
fig.suptitle("Deben collar transmitter vs ours, from the SDR recordings", x=0.07, ha="left",
             fontsize=14, fontweight="bold", color=INK)
fig.text(0.07, 0.905, "RX888 MkII, 1 MS/s centred on 150 kHz, same SDR settings for both. Narrowband (±15 kHz) around each "
         "transmitter's own line. 0 dB = the Deben's level during a burst.", ha="left", color=INK2, fontsize=9.5)

def style(a):
    a.grid(True, color=GRID, lw=0.8); a.set_axisbelow(True)
    for s in ("top", "right"): a.spines[s].set_visible(False)

# 1. burst train
a = ax[0, 0]
for who, d in data.items():
    t0 = d["st"][1] / d["ysr"] - 0.05
    i0, i1 = int(t0 * d["ysr"]), int((t0 + 1.0) * d["ysr"])
    blk = 50                                            # 0.5 ms
    seg = d["env2"][i0:i1]; seg = seg[: len(seg) // blk * blk].reshape(-1, blk).max(axis=1)
    t = np.arange(len(seg)) * blk / d["ysr"] * 1e3
    a.plot(t, db(seg) - db(ref), color=COL[who], lw=1.6, label=f"{who}: one burst every {d['per']:.0f} ms")
a.set_title("Burst train over one second"); a.set_xlabel("time (ms)"); a.set_ylabel("level (dB)")
a.set_ylim(-78, 8); style(a); a.legend(frameon=False, loc="lower right", labelcolor=INK, ncol=2, fontsize=9)

# 2. one burst, averaged
a = ax[0, 1]
for who, d in data.items():
    t = (np.arange(len(d["shape"])) - d["pre"]) / d["ysr"] * 1e3
    a.plot(t, db(d["shape"]) - db(ref), color=COL[who], lw=2, label=f"{who}: {d['L']:.1f} ms long")
a.axhline(0, color=GRID, lw=1)
dlev = db(ref) - db(np.median(data["Mine"]["shape"][data["Mine"]["pre"] + 50: data["Mine"]["pre"] + 250]))
a.annotate("", xy=(1.5, 0), xytext=(1.5, -dlev), arrowprops=dict(arrowstyle="<->", color=INK2, lw=1))
a.text(1.8, -dlev / 2, f"{dlev:.0f} dB", va="center", color=INK, fontsize=10)
a.set_title("One burst, averaged over 60 bursts"); a.set_xlabel("time from burst start (ms)")
a.set_ylabel("level (dB)"); a.set_xlim(-2, 16); a.set_ylim(-60, 8); style(a)
a.legend(frameon=False, loc="center right", bbox_to_anchor=(1.0, 0.45), labelcolor=INK)

# 3. spectrum during bursts
a = ax[1, 0]
sref = data["Deben"]["spec"].max()
for who, d in data.items():
    sel = (d["fr"] > 138e3) & (d["fr"] < 157e3)
    a.plot(d["fr"][sel] / 1e3, db(d["spec"][sel]) - db(sref), color=COL[who], lw=1.4,
           label=f"{who}: {d['f']/1e3:.2f} kHz")
a.axvspan(145, 150, color="#ebeae6", zorder=0)
a.text(147.5, -90, "receiver passes 145–150 kHz", ha="center", va="bottom", color=INK2, fontsize=8.5)
a.set_title("Spectrum during the bursts"); a.set_xlabel("frequency (kHz)"); a.set_ylabel("power (dB)")
a.set_ylim(-95, 5); style(a); a.legend(frameon=False, loc="upper left", labelcolor=INK, fontsize=9)

# 4. carrier stability
a = ax[1, 1]
for who, d in data.items():
    dev = d["fb"] - np.median(d["fb"])
    a.plot(d["tb"] - d["tb"][0], dev, "o", ms=4, color=COL[who], mec=SURF, mew=0.8,
           label=f"{who}: spread {np.std(dev):.0f} Hz")
a.set_title("Carrier frequency, burst by burst"); a.set_xlabel("time into recording (s)")
a.set_ylabel("offset from its own average (Hz)"); style(a)
a.set_ylim(-300, 230); a.legend(frameon=False, loc="lower right", labelcolor=INK, ncol=2, fontsize=9)

fig.savefig(OUT, dpi=150, facecolor=SURF)
print("saved", OUT)
for who, d in data.items():
    print(f"{who}: carrier {d['f']:.0f} Hz, burst {d['L']:.2f} ms, period {d['per']:.1f} ms, carrier spread {np.std(d['fb']):.0f} Hz")
print(f"level gap during bursts: {dlev:.1f} dB")
