# Changelog

## Firmware

- **2026-10-30, experimental.** CPU at 4 MHz with brown-out reset at 1.8 V (fuses
  low `0x62`, high `0xDE`). The CPU sleeps through each burst, with Timer0 timing it.
  New build options: `KICK_START` (level ramp), `PLL_SETTLE_US`, `OSCCAL_TRIM`,
  `BURST_IDLE`. Board 4 keeps transmitting down to 1.9 V. The CR1632 endurance
  test is running. The previous behaviour is kept as the `attiny85_kick_8mhz` build.
- **2026-10-29.** Per-chip `WAKES_PER_PACKET` and `TX_ALWAYS_ON` from the command line.
  Board 3 calibrated: 149.15 kHz, 11.18 ms bursts every 184 ms on two SR936 cells.
- **2026-10-01.** Carrier and burst timing matched to SDR measurements of a Deben:
  1653 periods (11.1 ms) per burst. Transistor ("kick") drive added.
- **2026-09-30.** First ATtiny85 firmware: carrier from Timer1 and the PLL, reed-switch
  latch, power-down sleep between bursts.

## Circuit board

- **tx-kick, 2026-10-15.** 20 mm round, two layers. ATtiny85-20SU, AO3400A kick
  drive and reverse-polarity protection, 100 nF C0G tank, MK24-B-2 reed switch,
  220 µF reservoir fed through 47 Ω. Assembled by JLCPCB, reed and pins fitted
  by hand.

## Enclosure

- **v11, 2026-10-30.** The coil leads pass through the floor to the cell side for
  easier soldering. The cells are turned 12° to clear the lead holes. GALT logo
  on the front.
- **v10.** Two SR936 cells side by side (12.8 mm thick instead of 16.3 mm when
  stacked). Contact disc in the cap links the cells in series.
- **v8 to v9.** Two-start screw thread timed so the ears line up; insert glued
  into the shell.
- **v7.** First printed version: Deben-style halves with strap ears, one CR1632.
