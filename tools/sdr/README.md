# SDR analysis tools

Scripts used to measure the Deben collar and compare our boards with it. They
read I/Q recordings saved by [SDR Console](https://www.sdr-radio.com/) as WAV
files (the centre frequency is read from the file's `auxi` chunk), with the radio
tuned to 150 kHz at 1 MS/s.

| Script | What it does |
|---|---|
| `analyse_iq2.py` | Finds the transmitter's carrier (the most "bursty" line in the spectrum), mixes it to 0 Hz and measures each burst: carrier frequency, length, spacing, level, SNR, harmonics, build-up and ring-down. Also usable as a library (`load`, `narrow`, `bursts`, `analyse`). |
| `plot_compare.py` | Side-by-side plots of a Deben and a JillTrak recording. |
| `make_figures.py` | The figures in [`background/`](../../background/). |

```
pip install numpy scipy matplotlib
python analyse_iq2.py <folder with Deben/ and Mine/ subfolders>
python make_figures.py <folder with the recordings> <output folder>
```

Tips for comparing levels: keep the collar and the antenna in exactly the same
place for every recording. The field falls about 18 dB each time the distance
doubles, so a few centimetres matters more than most design changes.

The recordings themselves are too large for the repository (60 to 100 MB each).
