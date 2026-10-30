# JillTrak firmware

Bare-metal C++ for the ATtiny85 on the [tx-kick board](../hardware/pcb/), built
with [PlatformIO](https://platformio.org/). There is no Arduino core: the chip
spends nearly all its life asleep, and nothing runs that the design does not
know about. Everything is in [`src/attiny85/main.cpp`](src/attiny85/main.cpp),
which is commented throughout.

## What it does

- **Off:** the chip sleeps in power-down with everything stopped. Only the reed
  switch can wake it.
- **Switching on and off:** hold a magnet over the ring marked on the case. Four
  agreeing samples 16 ms apart confirm the reed has closed, then the latch
  flips. One swipe turns it on, the next turns it off. There is a 256 ms
  lockout, so one swipe cannot count twice.
- **On:** the watchdog wakes the chip every ~16 ms. Every 12th wake (set per
  chip, see calibration) it sends a burst: 1653 periods of the carrier, about
  11.1 ms, copying the Deben's 11.1 ms bursts every ~184 ms.
- **The carrier:** Timer1 runs from the chip's PLL at 32 MHz and divides it down
  by `CARRIER_TOP + 1` to about 149.1 kHz. Pin PB4 drives the MOSFET, which
  pulls one end of the tuned coil low for about a quarter of each cycle (the
  "kick"). The coil rings at its own frequency for the rest.

| Pin | Port | Use |
|---|---|---|
| 3 | PB4 | carrier to the kick MOSFET |
| 2 | PB3 | held low |
| 7 | PB2 | reed switch to ground, internal pull-up (also SCK when programming) |
| 6 | PB1 | test pad J3: marks each burst (see bench mode) |
| 5 | PB0 | unused, pull-up on |
| 1 | PB5 | reset, kept so the chip stays programmable |

## Status

| Build | Where it runs | State |
|---|---|---|
| 8 MHz, polls through the burst, brown-out reset at 2.7 V | boards 2 and 3; env `attiny85_kick_8mhz` | **Working** on SR936 and LR936 cells, matched to the Deben by SDR. Resets mid-burst on a CR1632 after a few hours. |
| **4 MHz, sleeps through the burst, brown-out reset at 1.8 V** | board 4; env `attiny85_kick` (the default) | **Experimental.** Bench-tested on board 4: full bursts down to 1.9 V, carrier and timing unchanged. A CR1632 endurance test is running now. |

### What changed for the CR1632 test, and why

A single CR1632 is the easiest cell to build into a collar, but it cannot supply
a burst's current without its voltage sagging. The old firmware resets the
chip at 2.7 V, and a CR1632 starts at only about 3.0 V. After a few hours the
sag during each burst crossed 2.7 V and the chip reset in the middle of every
burst.

1. **CPU at 4 MHz, brown-out reset at 1.8 V.** The ATtiny85 is rated for 8 MHz
   only above 2.7 V, but for 4 MHz down to 1.8 V. The PLL that makes the
   carrier takes the oscillator before the CPU divider, so the carrier does not
   change. The fuses start the chip at 1 MHz, in spec at any voltage, and the
   firmware sets 4 MHz itself.
2. **The CPU sleeps (idle mode) through each burst.** Timer0 times the burst
   instead of the CPU counting carrier periods at full power. Timer0 and Timer1
   run from the same oscillator, so the burst is still 1653 carrier periods
   on any chip. This cuts the current drawn during each burst.
3. **Optional ramp** (`KICK_START`): the kick starts short and lengthens through
   the burst, to keep the level flat as the supply sags. Being tuned.
4. **Optional longer PLL settling time** (`PLL_SETTLE_US`): board 3's carrier
   sits in one of two bands 350 Hz apart, chosen afresh at each burst. Board 4
   doesn't do this, so it may be specific to that chip.

Measured on board 4 on a bench supply:

| Supply | Carrier | Level | Burst | Spacing |
|---|---|---|---|---|
| 3.1 V | 149.12 kHz | 0 dB | 11.28 ms | 191.6 ms |
| 2.6 V | 149.10 kHz | 0 dB | 11.28 ms | 191.6 ms |
| 2.2 V | 148.46 kHz | −2.8 dB | 11.33 ms | 189.9 ms |
| 1.9 V | 148.02 kHz | −3.9 dB | 11.36 ms | 189.4 ms |

The old firmware would reset at every burst at 2.6 V and below.

## You will need

- [PlatformIO](https://platformio.org/install) (the command-line `pio`, or the VS Code extension).
- An Arduino Uno as the programmer, running ArduinoISP from
  [`tools/arduinoisp/`](../tools/arduinoisp/): `cd tools/arduinoisp && pio run -t upload`.
- Six wires from the Uno to the board:

| Uno | Board |
|---|---|
| D10 | J1.1 RST |
| D13 | J1.2 SCK |
| D12 | J1.3 MISO |
| D11 | J1.4 MOSI |
| 5V | battery + pin (BT1) |
| GND | battery − pin (BT2) |

Set `upload_port` in [`platformio.ini`](platformio.ini) to your Uno's port.

## Bring-up order

Do all the soldering and programming with the board **out of the case**.
Once it is glued into the insert you cannot reach the programming pads.

1. **Inspect** the board under magnification; check the supply pins for shorts.
2. **Fuses** (once per chip): `pio run -e attiny85_kick -t fuses`
   (low `0x62`, high `0xDE`, extended `0xFF`).
3. **Blink test:** `pio run -e attiny85_blink -t upload`. Pin 6 (J3) changes
   state every 250 ms. Measure its frequency with a meter. Nominal is 2.000 Hz;
   the difference is this chip's oscillator error, which sets the carrier.
4. **Pick `CARRIER_TOP`:**
   `CARRIER_TOP = round(32,000,000 × (blink / 2.000) / 149,120) − 1`.
   For example, a 2.041 Hz blink gives 218. The blink only gets within about
   one step, so confirm with an SDR or receiver in the next step.
5. **Bench build** (transmits from power-on, ignores the reed, pin 6 toggles
   once per burst):
   ```
   PLATFORMIO_BUILD_FLAGS="-DCARRIER_TOP=218 -DWAKES_PER_PACKET=12 -DTX_ALWAYS_ON=1" pio run -e attiny85_kick -t upload
   ```
   - Check the carrier with an SDR, or the receiver, using a temporary coil on flying leads.
   - Pin 6 toggles at about 2.7 Hz. The burst spacing is 1 / (2 × that).
   - Adjust `WAKES_PER_PACKET` so the spacing lands closest to 184 ms. This chip's watchdog tick is the spacing divided by the wakes.
6. **Final build:** the same command without `-DTX_ALWAYS_ON=1`.
7. **Test the latch** by briefly shorting the reed pads: the first short starts
   bursts, the next stops them.
8. **Remove the programming wires,** then solder the reed switch. The reed sits
   on PB2, which is also SCK, so it must not be fitted while programming.
9. **Magnet test,** including through a printed shell, then fit the board into
   the insert and solder the coil.

## Build switches

Pass these with `PLATFORMIO_BUILD_FLAGS="-DNAME=value ..."`.

| Switch | Default | What it does |
|---|---|---|
| `CARRIER_TOP` | 212 | carrier = 32 MHz / (CARRIER_TOP + 1); set per chip |
| `OSCCAL_TRIM` | 0 | nudges the chip's oscillator; combine with `CARRIER_TOP` for finer steps |
| `WAKES_PER_PACKET` | 11 | watchdog wakes between bursts; set per chip |
| `TX_ALWAYS_ON` | 0 | 1 = bench mode: transmit from power-on, ignore the reed |
| `KICK_MATCH` | 52 | kick length in timer counts (52 of 213 ≈ 25 %) |
| `KICK_START` | = `KICK_MATCH` | start of the ramp; lower it to flatten the burst |
| `BURST_IDLE` | 1 | 1 = CPU idles through the burst; 0 = polls, as the 8 MHz build |
| `PLL_SETTLE_US` | 100 | wait between starting the PLL and starting the carrier |

Other builds: `attiny85_blink` (oscillator check), `attiny85_why` (reports why
the chip last reset, as a count of pulses on pin 6), `attiny85_kick_8mhz` (the
older 8 MHz behaviour, for comparison).

Known chips so far:

| Board | `CARRIER_TOP` | `WAKES_PER_PACKET` | Carrier | Spacing |
|---|---|---|---|---|
| 2 | 215 | 12 | 149.8 kHz | 190.0 ms |
| 3 | 220 | 12 | 149.15 kHz | 184.0 ms |
| 4 | 218 | 12 | 149.12 kHz | 191.6 ms |
