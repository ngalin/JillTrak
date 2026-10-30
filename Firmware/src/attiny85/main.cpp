// ---------------------------------------------------------------------------
// JillTrak: ferret collar transmitter, ATtiny85 firmware.
//
// An open replacement for the Deben ferret-finder collar transmitter, heard by
// the existing Deben handheld receiver. How the Deben was measured and how this
// matches it: ../../background/README.md. Board: ../../hardware/pcb/.
//
// Bare metal, no Arduino core: nothing may run Timer0 or an interrupt the
// design does not know about, and the part spends nearly all of its life in
// power-down.
//
// PINS (DIP-8)
//   pin 3  PB4  OC1B            carrier, tank end A through 220-330R
//   pin 2  PB3  OC1B inverted   carrier in antiphase, tank end B through 220-330R
//   pin 7  PB2  reed switch to ground, internal pull-up, wakes the chip
//   pin 6  PB1  scope trigger: high for the duration of each burst
//   pin 5  PB0  unused, pull-up on
//   pin 1  PB5  reset, left as reset so the chip stays programmable
//
// FUSES, set once with the Uno running ArduinoISP (see platformio.ini):
//   low  0x62  8 MHz internal RC oscillator, divided by 8 at power-on, so the
//              chip starts at 1 MHz, in spec at any voltage above 1.8 V; the
//              firmware then sets the divider to give F_CPU
//   high 0xDE  brown-out reset at 1.8 V, reset pin and SPI programming kept
//   ext  0xFF
// The CPU runs at 4 MHz, the fastest the ATtiny85 is rated for down to 1.8 V
// (8 MHz needs 2.7 V). The PLL takes the RC oscillator before the divider, so
// the carrier does not change. Boards 2 and 3 were built with 8 MHz, 0xE2 and
// 0xDD: their 2.7 V brown-out reset bursts on a sagging CR1632.
//
// SEQUENCE
//   Latch off: power-down, watchdog stopped, only a reed edge can wake it.
//   Magnet: the edge starts the watchdog; four agreeing samples 16 ms apart
//   confirm the closure and flip the latch. Latch on: the watchdog wakes the
//   chip every 16 ms and every eleventh wake sends an 11.1 ms burst, matching
//   the Deben's measured 11.1 ms bursts about every 184 ms.
// ---------------------------------------------------------------------------
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/power.h>
#include <avr/sleep.h>
#include <avr/wdt.h>
#include <util/delay.h>
#include <stdint.h>
#include <stdbool.h>

#if !defined(__AVR_ATtiny85__)
#error "This firmware is for the ATtiny85 only."
#endif

// --- Carrier ------------------------------------------------------------------
// Timer1 runs from the PLL in low speed mode, nominally 32 MHz, independent of
// the CPU clock. In PWM mode the period is OCR1C + 1 timer clocks.
//
// TARGET: the Deben's carrier, measured from SDR recordings at 149.12 kHz.
//
// CALIBRATED TO THE PROTOTYPE'S CHIP. With CARRIER_TOP = 217 this chip measured
// 145,476 Hz in the SDR recording, so its timer clock is really
//     145,476 x 218 = 31.71 MHz        (the RC oscillator runs about 0.9 % slow)
// and the nearest setting to the Deben is
//     31.71 MHz / (212 + 1) = 148.9 kHz, within 0.25 kHz of 149.12 kHz.
// On this chip one step of CARRIER_TOP is about 0.7 kHz:
//     211 -> 149.6    212 -> 148.9    213 -> 148.2    217 -> 145.5 kHz
// A DIFFERENT CHIP WILL NEED RE-MEASURING: its oscillator error differs. Read its
// carrier with any known CARRIER_TOP, then
//     new CARRIER_TOP = round((old CARRIER_TOP + 1) x measured / 149,120) - 1
// Set it per chip at upload time, without editing this file:
//     PLATFORMIO_BUILD_FLAGS="-DCARRIER_TOP=218" pio run -e attiny85_kick -t upload
// Known chips:
//     first prototype chip   212   (148.77 kHz measured)
//     second chip            218   (153.21 kHz measured at 212, so ~149.0 kHz)
// The RC oscillator also wanders by about +/-80 Hz from burst to burst, against
// the Deben's crystal, which does not move at all.
//
// COM1B = 01 drives OC1B on PB4 and its inverse on PB3 as a complementary pair,
// which is the bridge drive: the tank sees twice the swing of a single pin.
#ifndef CARRIER_TOP
#define CARRIER_TOP         212
#endif
#define CARRIER_MATCH       (CARRIER_TOP / 2)    // about 50 %, for the bridge drive
#if CARRIER_TOP < 150 || CARRIER_TOP > 255
#error "CARRIER_TOP outside 150..255; check the measurement"
#endif

// DRIVE_KICK selects the transistor test drive instead of the resistor bridge.
//   0  bridge: PB4 and PB3 in antiphase through resistors to the two tank ends.
//   1  kick:   PB4 alone, through a 220R base resistor, switches an NPN whose
//              collector pulls one end of the tank low; the other end sits on
//              the reservoir. PB4 is high for (KICK_MATCH + 1) of the
//              (CARRIER_TOP + 1) timer counts in every carrier period, and the
//              tank rings freely for the rest. PB3 stays a plain low output.
// Datasheet table "Compare Mode Select in PWM Mode": COM1B = 10 gives OC1B
// cleared on compare match and set at TCNT1 = 0, with the inverse output not
// connected. Sweep KICK_MATCH to find the strongest, cleanest signal:
//   32 -> 15 %    42 -> 20 %    52 -> 25 %    63 -> 30 %    84 -> 40 %
#ifndef DRIVE_KICK
#define DRIVE_KICK          0
#endif
#ifndef KICK_MATCH
#define KICK_MATCH          52     // 53 of 213 counts, about 25 %, 1.7 us on
#endif
#if DRIVE_KICK && (KICK_MATCH >= CARRIER_TOP / 2)
#error "KICK_MATCH must leave the transistor off for over half of each period"
#endif

// KICK_START flattens the burst. The reservoir and cell sag during a burst, so
// with a fixed pulse the level falls about 3 dB by the end (board 3 on LR936,
// SDR 30 Oct 2026; the Deben stays flat). The burst starts at KICK_START and
// steps up one count at a time, evenly spaced, to reach KICK_MATCH for the
// final part. Equal to KICK_MATCH, the default, gives a fixed pulse as before.
// Tune from SDR recordings: lower KICK_START until the envelope is flat.
#ifndef KICK_START
#define KICK_START          KICK_MATCH
#endif
#if DRIVE_KICK && (KICK_START > KICK_MATCH)
#error "KICK_START must not be above KICK_MATCH: the ramp only steps upward"
#endif
#define KICK_RAMP_STEPS     (DRIVE_KICK ? (KICK_MATCH - KICK_START) : 0)
// 11.1 ms, the Deben's measured burst length: 148.9 kHz x 11.1 ms = 1653 periods.
// This is 3.6 times the energy per burst of the old 3 ms setting, about 5.6 dB to
// a receiver that integrates over the burst, and 3.6 times the battery drain
// while transmitting. The Deben pays the same price.
#define CYCLES_PER_PACKET   1653

// BURST_IDLE 1: the CPU sleeps in idle through the burst and Timer0 times it.
// Timer0 counts the CPU clock / 256 and Timer1 the PLL, and both come from the
// same RC oscillator, so a fixed tick count is a fixed number of carrier
// periods on any chip: CYCLES_PER_PACKET x (CARRIER_TOP + 1) Timer1 counts.
// One tick is 64 us at 4 MHz, so the burst lands within 32 us of 1653 periods.
// BURST_IDLE 0: the CPU polls every Timer1 overflow at full power, as boards 2
// and 3 do. Kept to measure the difference in burst current.
#ifndef BURST_IDLE
#define BURST_IDLE          1
#endif
#if KICK_RAMP_STEPS && !BURST_IDLE
#error "The KICK_START ramp needs BURST_IDLE 1"
#endif
// Timer1 counts per Timer0 tick: 32 MHz / (F_CPU / 256), 2048 at 4 MHz. Divide
// by it rather than multiplying by F_CPU first, which overflows 32 bits.
#define T1_PER_T0_TICK  (32000000UL / (F_CPU / 256))
#define BURST_T0_TICKS  ((uint16_t)(((uint32_t)CYCLES_PER_PACKET * (CARRIER_TOP + 1) \
                         + T1_PER_T0_TICK / 2) / T1_PER_T0_TICK))
static_assert(BURST_T0_TICKS * T1_PER_T0_TICK / (CARRIER_TOP + 1) > 1600 &&
              BURST_T0_TICKS * T1_PER_T0_TICK / (CARRIER_TOP + 1) < 1700,
              "burst tick count does not give about 1653 carrier periods");

// Time from enabling the PLL to starting the carrier. Board 3's carrier sits
// in one of two bands about 350 Hz apart, picked afresh each burst (SDR 30 Oct
// 2026). If the PLL is still settling when the carrier starts, a longer wait
// should merge the bands. 100 us is the datasheet figure and the old value.
#ifndef PLL_SETTLE_US
#define PLL_SETTLE_US       100
#endif

// THE PLL IS LOCKED TO THE INTERNAL RC OSCILLATOR, so the carrier inherits its
// error. The datasheet specifies factory calibration only to +/-10 %, which is
// wider than the receiver's whole 145-150 kHz window. Measure the carrier once
// on PB4 with a scope, then trim:
//   carrier high  ->  make OSCCAL_TRIM more negative
//   carrier low   ->  make OSCCAL_TRIM more positive
// Each step moves the oscillator, and so the carrier, by very roughly half a
// percent, about 700 Hz. Iterate: change, reflash, measure. Do not trim the
// oscillator above 8 MHz; the PLL leaves its operating range if you do, and
// since the target is exactly 8 MHz a correctly trimmed part never needs to.
// Combined with CARRIER_TOP it gives finer steps than either alone, e.g. one
// OSCCAL step up with CARRIER_TOP one higher. Check every combination by SDR.
#ifndef OSCCAL_TRIM
#define OSCCAL_TRIM         0
#endif

// --- Timing, all in watchdog ticks --------------------------------------------
// The watchdog is the only timer that survives power-down. It runs only while
// transmitting or while the debounce settles; otherwise it is off and the reed's
// own edge is the alarm clock.
//
// The tick is 16 ms nominal. This chip's watchdog oscillator runs about 7 % slow
// (6 ticks of a nominal 32 ms measured 206 ms), so a tick is really about
// 17.2 ms. The Deben pulses every 183.6 ms; the closest whole number of ticks is
//     11 x 17.2 ms = 189 ms (5.3 Hz)        10 ticks would give 172 ms
// The debounce and lockout counts are doubled from the old 32 ms tick so they
// keep the same durations in milliseconds.
#ifndef WAKES_PER_PACKET
#define WAKES_PER_PACKET    11     // 11 x ~17.2 ms = ~189 ms on this chip
#endif
#define REED_STABLE_WAKES   4      // agreeing samples before a change counts, ~64 ms
#define REED_LOCKOUT_WAKES  16     // no second toggle for ~256 ms

#define SCOPE_TRIGGER       1      // PB1 marks each burst; 0 leaves it idle

// --- BENCH TEST MODE -----------------------------------------------------------
// 1: transmit from power-on and ignore the reed entirely, to rule the reed and
//    its latch out while bringing the board up. PB1 (pin 6) then TOGGLES at the
//    end of every burst instead of pulsing, giving a 2.6 Hz blink you can see
//    with an LED and 1k resistor from pin 6 to ground; a scope can still trigger
//    on either edge, each of which marks a switch-off.
// 0: normal operation, latched on and off by the reed.
// Set this back to 0 before the collar goes anywhere near a ferret.
#ifndef TX_ALWAYS_ON
#define TX_ALWAYS_ON        0
#endif

#define PIN_TX_A   PB4
#define PIN_TX_B   PB3
#define PIN_REED   PB2
#define PIN_TRIG   PB1
#define PIN_SPARE  PB0

static bool     txEnabled   = false;
static bool     reedState   = false;
static bool     reedRawLast = false;
static uint8_t  reedAgree   = 0;
static uint8_t  lockout     = 0;
static uint8_t  packetWakes = 0;
static bool     wdtRunning  = false;
static volatile bool wdtWoke = false;

static inline bool reedClosed(void) {
    return (PINB & (1 << PIN_REED)) == 0;     // pull-up, so LOW means closed
}

// A flag, so that a reed edge cannot be mistaken for a tick and shorten the
// packet interval. WDIE is re-armed in case the part clears it on the vector.
ISR(WDT_vect) {
    WDTCR |= (1 << WDIE);
    wdtWoke = true;
}

ISR(PCINT0_vect) {
    // Waking is the whole job.
}

#if BURST_IDLE
static volatile bool t0Hit = false;

ISR(TIMER0_COMPA_vect) {
    t0Hit = true;
}

// Idle sleep until Timer0 has counted `ticks` (1..255) on from the last target.
// OCR0A moves on by `ticks` and wraps with the counter, so successive calls add
// up exactly. A reed edge or a watchdog tick can wake the CPU early; it goes
// back to sleep. The flag is tested with interrupts off and sei() comes right
// before sleep_cpu(), so a match cannot slip in between and be missed.
static void idleFor(uint8_t ticks) {
    OCR0A = (uint8_t)(OCR0A + ticks);
    t0Hit = false;
    set_sleep_mode(SLEEP_MODE_IDLE);
    for (;;) {
        cli();
        if (t0Hit) break;
        sleep_enable();
        sei();
        sleep_cpu();
        sleep_disable();
    }
    sei();
}
#endif

// Watchdog in interrupt-only mode at 16 ms (all WDP bits zero). Changing WDE or the prescaler needs
// the timed sequence: WDCE and WDE together, then the new value within four
// cycles. A stale reset flag would force WDE on, so it is cleared first.
static void wdtOn(void) {
    if (wdtRunning) return;
    cli();
    wdt_reset();
    MCUSR &= ~(1 << WDRF);
    WDTCR |= (1 << WDCE) | (1 << WDE);
    WDTCR = (1 << WDIE);                      // WDP3..0 = 0000: 16 ms
    sei();
    wdtRunning = true;
}

static void wdtOff(void) {
    if (!wdtRunning) return;
    cli();
    wdt_reset();
    MCUSR &= ~(1 << WDRF);
    WDTCR |= (1 << WDCE) | (1 << WDE);
    WDTCR = 0;
    sei();
    wdtRunning = false;
}

// Power-down with the brown-out detector switched off for the duration of the
// sleep. BODS stays active for only three cycles, so the sequence must be
// exactly this: disable, sei, sleep. On parts before revision C the BODS bit is
// unimplemented and the write is harmless. BOD comes back on at every wake.
static void sleepUntilWake(void) {
    set_sleep_mode(SLEEP_MODE_PWR_DOWN);
    cli();
    sleep_enable();
    sleep_bod_disable();
    sei();
    sleep_cpu();
    sleep_disable();
}

// One packet. Brings the PLL up (it is off in power-down), lets it settle as
// the datasheet requires, runs Timer1 for CYCLES_PER_PACKET periods, then shuts
// everything down again.
static void sendBurst(void) {
    TCCR1 = 0;                                // Timer1 stopped before LSM changes
    GTCCR = 0;
    PLLCSR = (1 << LSM);                      // low speed mode: required < 2.7 V
    PLLCSR = (1 << LSM) | (1 << PLLE);        // start the PLL
    _delay_us(PLL_SETTLE_US);                 // datasheet: steady within 100 us
    // Bounded, so a PLL that never reports lock cannot hang the chip awake with
    // nothing coming out; after a millisecond it carries on regardless.
    for (uint8_t t = 0; t < 10 && !(PLLCSR & (1 << PLOCK)); t++) _delay_us(100);
    PLLCSR |= (1 << PCKE);                    // Timer1 now clocked at 32 MHz

    OCR1C = CARRIER_TOP;
#if DRIVE_KICK
    OCR1B = KICK_START;
#else
    OCR1B = CARRIER_MATCH;
#endif
    TCNT1 = 0;
    TIFR  = (1 << TOV1);                      // flags clear by writing 1
#if BURST_IDLE
    PRR   &= ~(1 << PRTIM0);                  // Timer0 on for the burst only
    TCCR0A = 0;                               // normal mode, outputs disconnected
    TCNT0  = 0;
    OCR0A  = 0;
    TIFR   = (1 << OCF0A);
    TIMSK |= (1 << OCIE0A);
#endif
#if SCOPE_TRIGGER && !TX_ALWAYS_ON
    PORTB |= (1 << PIN_TRIG);
#endif
#if DRIVE_KICK
    GTCCR = (1 << PWM1B) | (1 << COM1B1);     // OC1B only: short pulse on PB4
#else
    GTCCR = (1 << PWM1B) | (1 << COM1B0);     // OC1B and inverse both connected
#endif
#if BURST_IDLE
    TCCR0B = (1 << CS02);                     // Timer0 counts CPU clock / 256
#endif
    TCCR1 = (1 << CS10);                      // count PCK/1: the carrier starts

#if BURST_IDLE
    // The ramp steps come first, evenly spaced; the rest of the burst runs at
    // KICK_MATCH. A step can land mid-period: that one period gets a pulse
    // between the old and new widths, which the tank does not notice.
    uint16_t left = BURST_T0_TICKS;
    for (uint8_t k = 0; k < KICK_RAMP_STEPS; k++) {
        const uint8_t step = BURST_T0_TICKS / (KICK_RAMP_STEPS + 1);
        idleFor(step);
        left -= step;
        OCR1B++;
    }
    while (left > 255) { idleFor(255); left -= 255; }
    if (left) idleFor((uint8_t)left);
    // Finish on a period boundary so the switch-off is the same every burst.
    TIFR = (1 << TOV1);
    while (!(TIFR & (1 << TOV1))) { }
    TCCR0B = 0;
    TIMSK &= ~(1 << OCIE0A);
    PRR   |= (1 << PRTIM0);
#else
    // Each overflow is one carrier period: 27 CPU cycles at 4 MHz, against a
    // polling loop of under ten, so none is missed.
    for (uint16_t i = 0; i < CYCLES_PER_PACKET; i++) {
        while (!(TIFR & (1 << TOV1))) { }
        TIFR = (1 << TOV1);
    }
#endif

    // Disconnecting the compare outputs hands PB3 and PB4 back to PORTB, which
    // holds both low, so the tank is left with no drive and rings down freely.
    // The disconnect lands under a microsecond after the last period ends, a
    // fraction of a half-cycle, identical every burst.
    GTCCR = 0;
#if SCOPE_TRIGGER && TX_ALWAYS_ON
    PINB = (1 << PIN_TRIG);                   // writing PINB toggles: visible blink
#elif SCOPE_TRIGGER
    PORTB &= ~(1 << PIN_TRIG);                // falling edge marks the switch-off
#endif
    TCCR1 = 0;
    PLLCSR = (1 << LSM);                      // PCK and PLL off until next burst
}

// Trim the oscillator by a small signed amount, staying inside the half of the
// OSCCAL range the factory value sits in (bit 7 selects between two overlapping
// ranges, and stepping across it jumps the frequency).
static void applyOscTrim(void) {
    int16_t v = (int16_t)OSCCAL + OSCCAL_TRIM;
    const int16_t lo = (OSCCAL & 0x80) ? 0x80 : 0x00;
    const int16_t hi = lo + 0x7F;
    if (v < lo) v = lo;
    if (v > hi) v = hi;
    OSCCAL = (uint8_t)v;
}

#ifndef BRINGUP_BLINK
#define BRINGUP_BLINK 0
#endif

#ifndef RESET_CAUSE_PROBE
#define RESET_CAUSE_PROBE 0
#endif

int main(void) {
    // The fuse starts the chip at 1 MHz; this sets the divider for F_CPU. Every
    // _delay_ms() and _delay_us() assumes it, including the bring-up blink.
#if F_CPU == 8000000L
    clock_prescale_set(clock_div_1);
#elif F_CPU == 4000000L
    clock_prescale_set(clock_div_2);
#elif F_CPU == 1000000L
    clock_prescale_set(clock_div_8);
#else
#error "F_CPU must be 8, 4 or 1 MHz: the RC oscillator divided by 1, 2 or 8"
#endif
#if RESET_CAUSE_PROBE
    // Diagnostic: report why the chip last reset, then blink with the tank pins
    // left undriven. MCUSR must be read before anything clears it.
    // On every start, pin 6 gives a burst of short 20 us pulses. Count them:
    //   1 power-on    2 reset pin pulled low    4 brown-out    8 watchdog
    // Causes add: 5 is power-on plus brown-out, normal at first switch-on.
    // Then pin 6 toggles every 250 ms. PB3 and PB4 stay inputs throughout, so
    // if the resets stop in this build, driving the tank pins was causing them.
    {
        const uint8_t cause = MCUSR & 0x0F;
        MCUSR = 0;
        wdt_disable();
        DDRB  = (1 << PIN_TRIG);
        PORTB = 0;
        for (uint8_t i = 0; i < cause; i++) {
            PORTB |=  (1 << PIN_TRIG); _delay_us(20);
            PORTB &= ~(1 << PIN_TRIG); _delay_us(20);
        }
        _delay_ms(2);
        for (;;) { PINB = (1 << PIN_TRIG); _delay_ms(250); }
    }
#endif
    MCUSR = 0;
    wdt_disable();

#if BRINGUP_BLINK
    // Bring-up test: no sleep, no watchdog, no PLL, no Timer1. Pin 6 (PB1)
    // changes state every 250 ms, so a meter sees it flip twice a second. The
    // firmware sets the clock divider itself, so the rate does not depend on
    // the CKDIV8 fuse; it measures the RC oscillator. Tank pins held low.
    DDRB  = (1 << PIN_TRIG) | (1 << PIN_TX_A) | (1 << PIN_TX_B);
    PORTB = 0;
    for (;;) {
        PINB = (1 << PIN_TRIG);
        _delay_ms(250);
    }
#endif
    applyOscTrim();

    // Outputs low: both tank ends and the trigger. Inputs with pull-ups: the
    // reed, and the spare pin so it cannot float and draw current.
    DDRB  = (1 << PIN_TX_A) | (1 << PIN_TX_B) | (1 << PIN_TRIG);
    PORTB = (1 << PIN_REED) | (1 << PIN_SPARE);

    // Everything this design does not use, off.
    ADCSRA &= ~(1 << ADEN);                   // ADC off before gating its clock
    ACSR   |=  (1 << ACD);                    // analog comparator off
    PRR     = (1 << PRTIM0) | (1 << PRUSI) | (1 << PRADC);

#if !TX_ALWAYS_ON
    // Reed wakes the chip on any change of PB2.
    PCMSK = (1 << PCINT2);
    GIMSK |= (1 << PCIE);
#endif

    _delay_ms(5);                             // let the pull-up settle
    reedState   = reedClosed();
    reedRawLast = reedState;
    reedAgree   = REED_STABLE_WAKES;
    sei();
#if TX_ALWAYS_ON
    txEnabled = true;                         // on from power-up, reed ignored
    wdtOn();
#endif

    // Boots with the latch off and the watchdog stopped: nothing to pace.
    for (;;) {
        sleepUntilWake();

        // A bare reed edge carries no timing information. It only starts the
        // watchdog, which then delivers evenly spaced samples.
        if (!wdtWoke) {
            wdtOn();
            continue;
        }
        wdtWoke = false;
        if (lockout) lockout--;

        const bool raw = reedClosed();
        if (raw != reedRawLast) {
            reedRawLast = raw;
            reedAgree   = 0;
        } else if (reedAgree < REED_STABLE_WAKES) {
            reedAgree++;
        }

        if (reedAgree >= REED_STABLE_WAKES && raw != reedState) {
            reedState = raw;
            if (reedState && lockout == 0 && !TX_ALWAYS_ON) {  // closures toggle the latch
                lockout     = REED_LOCKOUT_WAKES;
                packetWakes = 0;
                txEnabled   = !txEnabled;
            }
        }

        if (txEnabled && ++packetWakes >= WAKES_PER_PACKET) {
            packetWakes = 0;
            sendBurst();
        }

        const bool settling = (reedRawLast != reedState) ||
                              (reedAgree < REED_STABLE_WAKES) || (lockout != 0);
        if (txEnabled || settling) wdtOn(); else wdtOff();
    }
}
