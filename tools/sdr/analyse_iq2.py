"""Narrowband comparison of two ferret transmitters from SDR Console I/Q WAVs.

1. Find each transmitter's spectral line: the bin whose power is most bursty
   (high peak-to-median over time), which rejects steady broadcast carriers.
2. Mix that line to 0 Hz, low-pass 15 kHz, decimate to 100 kS/s.
3. On that narrowband signal: burst timing, level, SNR, carrier, rise and decay.
4. Harmonics: same narrowband level at 2f and 3f, relative to the fundamental.
"""
import glob, os, re, struct, sys
import numpy as np
from scipy import signal

def wav_info(path):
    with open(path, "rb") as f:
        f.seek(12); info = {}
        while True:
            h = f.read(8)
            if len(h) < 8: break
            cid, cl = h[:4], struct.unpack("<I", h[4:])[0]; pos = f.tell()
            if cid == b"fmt ":
                fmt, ch, sr = struct.unpack("<HHI", f.read(8)); info.update(fmt=fmt, ch=ch, sr=sr)
            elif cid == b"auxi":
                x = f.read(cl).decode("utf-16-le", errors="ignore")
                info["fc"] = float(re.search(r'RadioCenterFreq="(\d+)"', x).group(1))
            elif cid == b"data":
                info.update(off=pos, n=cl // 8)
            f.seek(pos + cl + (cl & 1))
    return info

def load(paths):
    parts = []
    for p in paths:
        i = wav_info(p)
        raw = np.memmap(p, dtype=np.float32, mode="r", offset=i["off"], shape=(i["n"], 2))
        parts.append((raw[:, 0] + 1j * raw[:, 1]).astype(np.complex64))
    return np.concatenate(parts), i["fc"], i["sr"]

db = lambda v: 10 * np.log10(np.maximum(v, 1e-30))

def find_line(x, fc, sr, fmin=100e3, fmax=500e3, nfft=2048, secs=10):
    """Bin with the most bursty power, i.e. a pulsed transmitter."""
    m = min(len(x), int(secs * sr))
    f, t, Z = signal.stft(x[:m], fs=sr, nperseg=nfft, noverlap=nfft // 2,
                          return_onesided=False, boundary=None)
    f = fc + f
    sel = (f >= fmin) & (f <= fmax)
    P = np.abs(Z[sel]) ** 2
    ratio = np.percentile(P, 99.5, axis=1) / np.median(P, axis=1)
    k = np.argmax(ratio)
    return f[sel][k], db(ratio[k])

def narrow(x, fc, sr, f0, out_sr=100_000, bw=15_000):
    n = np.arange(len(x), dtype=np.float64)
    lo = np.exp(-2j * np.pi * (f0 - fc) / sr * n).astype(np.complex64)
    y = x * lo
    dec = int(sr // out_sr)
    taps = signal.firwin(401, bw, fs=sr)
    y = signal.lfilter(taps, 1.0, y)[::dec]
    return y.astype(np.complex64), out_sr

def bursts(env, sr, min_ms=0.3):
    noise = np.median(env); peak = np.percentile(env, 99.8)
    thr = 10 ** ((db(noise) + db(peak)) / 20)          # halfway in dB, amplitude
    on = env > thr
    d = np.diff(on.astype(np.int8))
    st = np.flatnonzero(d == 1) + 1; en = np.flatnonzero(d == -1) + 1
    if len(en) and len(st) and en[0] < st[0]: en = en[1:]
    k = min(len(st), len(en)); st, en = st[:k], en[:k]
    keep = (en - st) / sr * 1e3 >= min_ms
    return st[keep], en[keep], noise

def analyse(name, paths):
    x, fc, sr = load(paths)
    f_line, burst_db = find_line(x, fc, sr)
    y, ysr = narrow(x, fc, sr, f_line)
    env = np.abs(y)
    st, en, noise = bursts(env, ysr)
    L = (en - st) / ysr * 1e3
    per = np.diff(st) / ysr * 1e3
    lev, offs, ups, dns = [], [], [], []
    for s, e in zip(st, en):
        n = e - s
        mid = y[s + n // 4: e - n // 4]
        if len(mid) < 20: continue
        lev.append(np.mean(np.abs(mid) ** 2))
        dph = np.angle(np.sum(mid[1:] * np.conj(mid[:-1])))
        offs.append(dph * ysr / (2 * np.pi))
        top = np.median(np.abs(mid))
        seg = env[max(0, s - 100): e + 300]
        a = seg[: (s - max(0, s - 100)) + n // 2]
        i10 = np.argmax(a > 0.1 * top); i90 = np.argmax(a > 0.9 * top)
        if i90 > i10: ups.append((i90 - i10) / ysr / np.log(9))
        b = env[e - 5: e + 300]
        j0 = np.argmax(b < 0.9 * top); j1 = np.argmax(b < 0.3 * top)
        if j1 > j0: dns.append((j1 - j0) / ysr / np.log(3))
    lev = np.array(lev)
    f_car = f_line + np.median(offs)
    sig_db = db(np.median(lev)); noise_db = db(noise ** 2)
    harm = {}
    for h in (2, 3):
        fh = h * f_car
        if fh > fc + 0.45 * sr: harm[h] = None; continue
        yh, _ = narrow(x[: min(len(x), 5 * sr)], fc, sr, fh)
        eh = np.abs(yh); m = len(eh)
        on = np.zeros(m, bool)
        for s, e in zip(st, en):
            if e < m: on[s + (e - s) // 4: e - (e - s) // 4] = True
        harm[h] = db(np.mean(eh[on] ** 2)) - sig_db if on.any() else None
    td = np.median(dns) if dns else np.nan
    return dict(name=name, dur=len(x) / sr, line=f_line, bursty=burst_db, f=f_car,
                fsd=np.std(offs), n=len(st), L=np.median(L), Lsd=np.std(L),
                per=np.median(per), sig=sig_db, noise=noise_db, snr=sig_db - noise_db,
                harm=harm, up=np.median(ups) if ups else np.nan, dn=td, Q=np.pi * f_car * td)

def groups(folder):
    g = {}
    for f in sorted(glob.glob(os.path.join(folder, "*.wav"))):
        g.setdefault(re.sub(r" \d{3}\.wav$", "", os.path.basename(f)), []).append(f)
    return g

if __name__ == "__main__":
    res = []
    for who in ("Deben", "Mine"):
        for key, paths in groups(os.path.join(sys.argv[1], who)).items():
            res.append(analyse(f"{who:<5} {key[12:18]}", paths))
    for r in res:
        print(f"\n=== {r['name']}   {r['dur']:.1f} s, {r['n']} bursts   (line found at {r['line']/1e3:.2f} kHz, {r['bursty']:.0f} dB bursty)")
        print(f"  carrier         {r['f']:,.0f} Hz   (burst-to-burst sd {r['fsd']:.0f} Hz)")
        print(f"  burst length    {r['L']:.2f} ms  (sd {r['Lsd']:.2f})     period {r['per']:.1f} ms  = {1000/r['per']:.2f} Hz")
        print(f"  level           {r['sig']:.1f} dB   noise {r['noise']:.1f} dB   SNR {r['snr']:.1f} dB")
        print("  harmonics       " + ", ".join(f"{h}f {v:+.1f} dB" if v is not None else f"{h}f n/a" for h, v in r['harm'].items()))
        print(f"  build-up tau    {r['up']*1e6:.0f} us    ring-down tau {r['dn']*1e6:.0f} us   -> loaded Q about {r['Q']:.0f}")
    deb = [r for r in res if r['name'].startswith('Deben')]
    mine = [r for r in res if r['name'].startswith('Mine')]
    if deb and mine:
        d = deb[-1]; m = mine[-1]
        print(f"\nLEVEL DIFFERENCE (Deben {d['name'][6:]} minus Mine): {d['sig'] - m['sig']:+.1f} dB")
