"""JillTrak figures from SDR recordings. Usage: python figs.py <data dir> <out dir>"""
import sys, os, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import analyse_iq2 as A
D, OUT = sys.argv[1], sys.argv[2]
BLUE, ORANGE = "#2a78d6", "#eb6834"; INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": INK2, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "font.size": 10, "axes.titlesize": 11,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "lines.linewidth": 2, "legend.frameon": False})
DEB = "30-Oct-2026 133755.859 0.150MHz 000.wav"; OUR = "30-Oct-2026 133725.915 0.150MHz 000.wav"
F0 = 149150.0
def get(f):
    x, fc, sr = A.load([os.path.join(D, f)]); y, ysr = A.narrow(x, fc, sr, F0)
    st, en, noise = A.bursts(np.abs(y), ysr); return x, fc, sr, y, ysr, list(zip(st, en))[1:-1], noise
deb, our = get(DEB), get(OUR)
runs = [("Deben", deb, ORANGE), ("JillTrak (board 3)", our, BLUE)]

# 1. packet timing: envelope over ~0.8 s
fig, ax = plt.subplots(figsize=(9, 2.8))
for name, (x, fc, sr, y, ysr, pr, nz), c in runs:
    s0 = pr[0][0] - int(0.02*ysr); seg = np.abs(y[s0:s0 + int(0.8*ysr)])
    seg = seg / np.median([np.median(np.abs(y[a:b])) for a, b in pr])
    ax.plot(np.arange(len(seg))/ysr*1e3, seg + (1.3 if name == "Deben" else 0), color=c, lw=1, label=name)
ax.set(xlabel="time (ms)", yticks=[], title="Bursts: 11 ms of carrier about every 184 ms")
ax.text(60, 1.42, "Deben", color=INK, fontsize=10); ax.text(60, 0.12, "JillTrak (board 3)", color=INK, fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "packet_timing.png"), dpi=130); plt.close(fig)

# 2. one burst: envelope and spectrum
fig, ax = plt.subplots(1, 2, figsize=(10, 3.4))
for name, (x, fc, sr, y, ysr, pr, nz), c in runs:
    s, e = pr[len(pr)//2]; pad = int(1.5e-3*ysr)
    ev = np.abs(y[s-pad:e+pad]); ref = np.median(np.abs(y[s:e]))
    ax[0].plot((np.arange(len(ev))-pad)/ysr*1e3, 20*np.log10(ev/ref + 1e-6), color=c, lw=1.2, label=name)
    S, E = int(s*sr/ysr), int(e*sr/ysr); seg = x[S:E]*np.hanning(E-S)
    Fs = np.fft.fftshift(np.fft.fft(seg, 1 << 18)); fr = (np.fft.fftshift(np.fft.fftfreq(1 << 18, 1/sr)) + fc)/1e3
    P = 20*np.log10(np.abs(Fs)+1e-9); m = (fr > 146) & (fr < 152)
    ax[1].plot(fr[m], P[m]-P[m].max(), color=c, lw=1.2, label=name)
ax[0].set(title="One burst, envelope", xlabel="ms from burst start", ylabel="dB relative to mid-burst", ylim=(-45, 6))
ax[1].set(title="One burst, spectrum", xlabel="frequency (kHz)", ylabel="dB relative to peak", ylim=(-60, 3))
ax[1].legend(loc="upper left", fontsize=9); fig.tight_layout(); fig.savefig(os.path.join(OUT, "burst_envelope_spectrum.png"), dpi=130); plt.close(fig)

# 3. frequency within each burst, overlaid
fig, ax = plt.subplots(1, 2, figsize=(10, 3.4), sharey=True)
for k, (name, (x, fc, sr, y, ysr, pr, nz), c) in enumerate(runs):
    w = int(0.2e-3*ysr); means = []
    for s, e in pr:
        ph = np.angle(y[s+1:e]*np.conj(y[s:e-1]))*ysr/(2*np.pi) + F0
        sm = np.convolve(ph, np.ones(w)/w, mode="valid")[int(0.2e-3*ysr):-int(0.2e-3*ysr)]
        ax[k].plot((np.arange(len(sm)) + w/2 + 0.2e-3*ysr)/ysr*1e3, sm/1e3, color=c, lw=0.6, alpha=0.35)
        means.append(ph[len(ph)//10:-len(ph)//10].mean())
    ax[k].set(title=f"{name}: {len(pr)} bursts overlaid", xlabel="ms from burst start")
    ax[k].text(0.98, 0.04, (f"burst averages vary by ±{np.std(means):.0f} Hz" if np.std(means) >= 1 else "burst averages agree to within 1 Hz"), transform=ax[k].transAxes, ha="right", color=INK2, fontsize=9)
ax[0].set(ylabel="carrier (kHz)", ylim=(147.6, 150.2))
fig.tight_layout(); fig.savefig(os.path.join(OUT, "frequency_within_burst.png"), dpi=130); plt.close(fig)

# 4. new firmware, supply sweep (board 4)
V = [3.1, 2.6, 2.2, 1.9]; L = np.array([47.0, 47.0, 44.2, 43.1]); Fc = [149.115, 149.099, 148.459, 148.020]
fig, ax = plt.subplots(1, 2, figsize=(10, 3.0))
ax[0].plot(V, L - L[0], "o-", color=BLUE, ms=8); ax[0].set(title="Level vs supply", xlabel="supply (V)", ylabel="dB relative to 3.1 V", ylim=(-5, 1))
ax[1].plot(V, Fc, "o-", color=BLUE, ms=8); ax[1].axhspan(147.85, 149.3, color=ORANGE, alpha=0.12, lw=0)
ax[1].text(3.12, 149.36, "shaded: the Deben's own sweep within a burst", color=INK2, fontsize=9)
ax[1].set(title="Carrier vs supply", xlabel="supply (V)", ylabel="kHz", ylim=(147.6, 149.6))
for a in ax: a.invert_xaxis()
fig.tight_layout(); fig.savefig(os.path.join(OUT, "supply_sweep.png"), dpi=130); plt.close(fig)
print("ok")
