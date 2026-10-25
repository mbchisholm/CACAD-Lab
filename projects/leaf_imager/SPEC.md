---
title: "Leaf NDVI imager — v0 bench build"
register: 2
status: draft
pairs_with: projects/camera_reader/ref/camera-reader-v0.md (same camera, same read method, pointed at a leaf; local only, ref/ is gitignored)
---

# Leaf NDVI imager — v0 bench build

The camera reader's hardware and read method, turned from water to leaves. A Pi
Camera v2 NoIR looks straight down at a leaf on a platen, in a dark chamber, lit
by a ring of LEDs at 45°. It takes one raw frame per wavelength and turns them
into per-pixel reflectance. Every pixel then gets NDVI, red-edge NDRE and a
true-colour image.

Active light is the point. Filter-based NDVI (a NoIR camera with a blue gel,
under daylight) uses whatever the sun and the filter give it. Here every band is
a known narrow LED, ambient is shut out, and a white reference in every frame
cancels LED drift. That is the same trick as v0's reference window.

It answers three questions:

1. Can a $50 camera map leaf NDVI repeatably enough to track one plant over days?
2. Does NDRE see nutrient stress in dense, healthy-looking hydroponic leaves where
   NDVI saturates?
3. Does a deficiency show up in the maps before it shows to the eye?

Not in scope: canopy imaging from above under grow lights (ambient light, unknown
geometry), and absolute chlorophyll in µg/cm² (needs a SPAD meter or extraction to
calibrate against).

Tags as in `docs/PARAMS_CONVENTION.md`: VENDOR, NOTES (camera-reader v0 spec),
STANDARD, INFERRED, DESIGN, UNVERIFIED.

## Acceptance

| Criterion | Target |
|---|---|
| Same leaf, pulled out and reinserted 10×, mean NDVI over a fixed patch | σ ≤ 0.01 |
| White reference, 2 h, all LEDs cycling | drift ≤ 1 % per channel after reference correction |
| Grey-card ladder (white, mid grey, black flock) | reflectance linear, R² ≥ 0.999 per channel |
| Platen (black flock) reflectance at 850 nm | ≤ 3 % |

DESIGN estimates, like v0's. Revise after L1.

## How a read works

As v0, per pixel instead of per window:

1. **Dark.** All LEDs off, raw frames: black level plus any leak.
2. **Per LED.** One channel on, settle, N raw frames at that channel's fixed
   exposure, off.
3. **Reflectance.** `R = (S − dark) / (F − dark_F) × (ref_F / ref_now)`.
   - `F` is the flat-field: the same channel imaged once with a white card covering
     the platen.
   - `ref` is the mean over the in-frame white strip, at flat-field time and now.
   - The flat-field takes out the ring's fixed unevenness and the lens shading. The
     strip takes out LED drift.
4. **Indices.**
   - NDVI = (R850 − R660) / (R850 + R660).
   - NDRE = (R850 − R730) / (R850 + R730).
   - Red-edge chlorophyll index = R850 / R730 − 1.
5. **Mask.** Leaf pixels are where NDVI clears the bare platen by a margin. The
   platen is black flock, so it reads near zero in both bands.

Capture is raw Bayer with AE/AWB off, gain 1.0, fixed exposure per channel and
steady DC LEDs, exactly as v0. Binned 1640 × 1232 for the index maps (quieter);
full 3280 × 2464 for leaf detail.

## Bands

| LED | Bayer pixels | Why |
|---|---|---|
| 450 nm | B | True colour; carotenoid / browning |
| 525 nm | G | True colour; green reflectance peak |
| 660 nm | R | NDVI red: chlorophyll absorption |
| 730 nm | R | NDRE red edge: stays sensitive where NDVI saturates |
| 850 nm | R+G+B | NIR plateau: leaf structure |

Nominal bands. The parts' datasheet wavelengths are in *The LED ring* (448,
525–535 dominant, 660, 727, 850 nm). Above ~800 nm every Bayer dye passes, so
850 sums all four pixels, as in v0.

## Geometry

Lens 100 mm above the platen (DESIGN):

| Lens to leaf | Field | Binned | Full res | Depth of field, 1 px blur |
|---|---|---|---|---|
| 60 mm | 72 × 54 mm | 44 µm/px | 22 µm/px | 1.7 mm (full) |
| **100 mm** | **121 × 91 mm** | **74 µm/px** | **37 µm/px** | **4.8 mm (full), 9.7 mm (binned)** |
| 150 mm | 181 × 136 mm | 110 µm/px | 55 µm/px | 10.9 mm (full) |

From the 62.2 × 48.8° FOV and the 3.04 mm f/2.0 lens (VENDOR, docs table). 100 mm
takes a whole basil or small lettuce leaf, resolves veins, and tolerates a leaf that
curls a few millimetres.

**Focus is required here**, unlike the water reader. Left at its far factory focus,
the blur on the leaf is about the lens's aperture, 1.5 mm, at any distance. Refocus
the v2 lens to 100 mm with the lens tool, as v0's spec already does for 150 mm.
Raspberry Pi's spec table gives the v2 focus as "Adjustable, approx 10 cm to ∞"
(VENDOR, documentation `hardware_specification.adoc`), so 100 mm is at the edge
of the documented range. Raspberry Pi publishes no factory focus distance and no
refocusing procedure. A camera refocused to 100 mm stays there, so it is this
instrument's camera, not v0's.

**45°/0° geometry** (CIE 15 standard illuminating/viewing geometry): the camera
looks along the normal, and the LEDs hit the leaf at 45°. The leaf's waxy cuticle
reflects them away from the lens, not into it. No glass covers the leaf, because a
cover glass would put its own glare in the picture.

**The LED ring.** One flat annular PCB, 60 mm up, LEDs facing straight down on a
60 mm radius. N/E/S/W per band at minimum, 20 LEDs in all. The LED's position
sets the 45° illumination at the field centre. Aiming each LED at the centre is
not needed. The beam angle matters more than the count or the aim.

The brightest-to-darkest irradiance ratio over 80 % of the field, from a cosⁿ beam
model (INFERRED; it becomes `validate()` check 4 when `params.py` is written):

| LED beam (half-power half-angle) | 4 aimed | 4 flat | 8 flat |
|---|---|---|---|
| ±15° (Kingbright 5 mm diffused; clear 5 mm 730 nm) | 41 : 1 | 474 : 1 | 328 : 1 |
| ±30° (for comparison) | 4.1 : 1 | 3.4 : 1 | 2.6 : 1 |
| ±40° (widest 5 mm 850 nm) | 2.4 : 1 | 1.8 : 1 | 1.5 : 1 |
| ±55° | 1.6 : 1 | 1.4 : 1 | 1.2 : 1 |
| **±60° (the chosen parts: 120° Lambertian)** | 1.5 : 1 | **1.4 : 1** | **1.15 : 1** |

The earlier draft put 8 : 1 against a "30°" aimed LED. This model gives 4.1 : 1
for ±30° and 41 : 1 for ±15°. Either way the conclusion stands.

So **the rule is wide-beam (±55° or more), the same beam in every band** (DESIGN).
The flat-field corrects whatever unevenness is left, but a dim corner stays noisy,
and beams that differ by band give each band a different noise map.

**No 5 mm through-hole LED meets it** (datasheet survey, 2026-10):
- Every Kingbright 5 mm diffused part checked is ±15° (30° full).
- The only 730 nm parts with datasheets are clear, ±10–15° (Roithner IB5-43B8-730,
  ELD-740-524, LED740-01AU).
- The widest 5 mm 850 nm is ±40° (Roithner LED850-05UP).
- The "120° flat-top" hobby parts publish no FWHM, so they fail the sourcing rule.

So the ring is SMD on one PCB. That suits the repo, because KiCad is already the
board tool here.

**Source: distributor parts, ams-OSRAM, Cree LED and Vishay** (decided
2026-10-07).
- Each part has a current datasheet, and each maker lists it as active.
- Every beam is 120° full (Lambertian), except the green at 135°.
- `params.LEDS` holds every number, with its page.

Roithner's SMC family has a near-identical beam and runs at lower current. It
was dropped because it cannot be shown to be buyable:
- its catalogue page shows no price, stock or order terms for any SMC part;
- the SMC525 and SMC735 datasheets are "on request" only.

| Band | Part | Peak / FWHM | Beam | Vf | Min. current |
|---|---|---|---|---|---|
| 450 | ams-OSRAM GD CSSPM1.14 (OSLON SSL 120 deep blue) | 445 / not stated | 120° | 2.85 V @ 350 mA | 100 mA |
| 525 | Cree LED XLamp XP-E2 green, XPEBGR-L1-0000-00K03 (bin G3–G4) | 525–535 dominant / UNVERIFIED | 135° | 2.7 V @ 350 mA | none stated |
| 660 | ams-OSRAM GH CSSPM1.24 (OSLON SSL 120 hyper red) | 660 / 25 nm | 120° | 2.07 V @ 350 mA | 100 mA |
| 730 | ams-OSRAM GF CSSRML.24 (OSLON Optimal far red) | 727 / 30 nm | 120° | 1.84 V @ 350 mA | 30 mA |
| 850 | Vishay VSMY3850X01 (PLCC-2) | 850 / 30 nm | ±60° | 1.6 V @ 100 mA | none; **100 mA absolute max** |

Sources:
- The ams-OSRAM and Vishay numbers are from their datasheets (VENDOR):
  - `look.ams-osram.com/.../GD-CSSPM1-14.pdf` (v1.4)
  - `look.ams-osram.com/.../GH-CSSPM1-24.pdf` (v1.15)
  - `look.ams-osram.com/.../GF-CSSRML-24.pdf` (v1.3)
  - `vishay.com/docs/80225`
- XP-E2 green numbers are from Cree LED datasheet CLD-DS56 rev 25B
  (`downloads.cree-led.com/files/ds/x/XLamp-XPE2.pdf`). The order code is in
  its current table, not the "not recommended for new designs" appendix. The
  datasheet gives the spectrum only as a plot, so FWHM is UNVERIFIED. The XPEBGR
  family is listed at Digi-Key and RS.
  - Its 135° beam against the others' 120° is within the same-beam rule: ±67.5°
    against ±60° changes the 4-flat ratio by under 0.05 (INFERRED, same model).
- Production status:
  - ams-OSRAM's product pages list GD CSSPM1.14, GH CSSPM1.24 and GF CSSRML.24
    as full production. GF CSSRML.24 is also listed at Farnell (4035474) and RS
    (2490443).
  - The first picks, GD CSSRML.14 and GH CSSRM4.24, are **discontinued** on the
    same pages. ams-OSRAM names GD CSSPM1.14 as the blue's replacement.
- Stock at order time is UNVERIFIED for every part.

## Layout

```
          [Pi 4B on the roof, rotated so its CSI connector sits on the ribbon's line]
               | 117 mm ribbon path: up through a felt-flapped roof slot, over the Pi
          [roof, on the chamber's tongue]  [camera carrier under it]
               |  100 mm
   [LED ring PCB on the chamber's ledge: 4 x 5 bands, 60 mm out, 60 mm up]
               |
   [base: black platen lining + white PTFE strip + pins for the hold-down frame]
```

The chamber is 140.3 mm square inside and 118 mm from the leaf plane to the roof.
The whole stack is 151 × 154 × 141 mm, with the Pi overhanging the roof by 6 mm at
its USB end. `params.py` prints every number.

- **Pi on the roof.** The Camera Module 2 ships with a 150 mm ribbon (VENDOR:
  raspberrypi.com Camera Module 2 product page, "15cm ribbon cable"; that the NoIR
  ships the same cable is UNVERIFIED). Camera on the roof's underside, Pi on its
  top: about 30–60 mm of ribbon, through a light-trapped slot. A Pi in a base
  would need about 235 mm. Heat rises away from the leaf.
- **The chamber lifts off; there is no drawer** (DESIGN, 2026-10-07).
  - A drawer has to carry the pins, frame and strip out under the chamber's front
    wall. That needs a full-width opening, and its lintel would be a 140 mm
    bridge in an upright print.
  - So the base is a fixed platen. It carries the black lining, the white
    reference strip (8 mm wide, along one field edge, face in the leaf plane) and
    two pins.
  - The open hold-down frame drops over the pins and holds the leaf's edges flat.
  - The chamber, carrying the roof, camera and Pi, is lowered back on. A rim on
    all four sides of the base locates it and laps the joint against light.
  - Same reference, same place, every read.
  - Foam-lined notches in the chamber's front wall and the base rim line up, so a
    leaf still on its plant goes in with its petiole through them.
- **The platen must be dark in NIR.** Leaves pass a good share of 850 nm light, so
  what is under the leaf adds to its NIR reading. Many black plastics and dyes are
  bright at 850 nm, and black PETG passes NIR (v0 README). "Black flock" is not
  enough on its own. Total reflectance near 850 nm, read off published curves:

  | Material | ~850 nm | Source |
  |---|---|---|
  | Fineshut KIWAMI | 0.6 % | Schmidt, SPIE 12188 (2022), fig. 4 |
  | Acktar Metal Velvet | 0.8 % | Marshall, SPIE (2014), fig. 4 |
  | Edmund Flock 65 | ~2 % | Marshall 2014 |
  | Black PLA, bare (Polyterra Charcoal) | 2.5–2.9 % | Schmidt 2022 |
  | Thorlabs BKF12 foil | ~4.5 % (fails) | Marshall 2014 |
  | **Edmund Flock 55** | **~23 % (fails: it turns NIR-bright above 700 nm)** | Marshall 2014 |

  Pick a material with a published number under 3 %. Protostar flock and Thorlabs
  BFP1 publish none (UNVERIFIED), so they need L2 before they count.
- **The white references.** Thin PTFE is translucent, so its reflectance depends
  on what is behind it:
  - Skived 1.6 mm reads 84.6 % of thick PTFE at 450 nm, and 100.3 % on foil.
  - 5 mm reads 96 %.
  - (Ghosh et al., JINST 15 P11031, 2020, at 450 nm only. No 850 nm data was
    found, and translucency should be worse there.)
  - Sintered PTFE runs 0.93/0.92 at 450/850 nm at 1 mm, and stops changing with
    thickness at about 5 mm (Labsphere Spectralon tech guide).

  So:
  - **Strip: PTFE ≥ 5 mm thick** (DESIGN, from those sources), set into a pocket so
    its face is in the leaf plane. The strip only cancels drift, so any stable
    backing would do. 5 mm takes the backing out of the question.
  - **Flat-field card: the same ≥ 5 mm.** The card sets the reflectance scale per
    band, so a 450-to-850 slope in the card shifts NDVI directly.
  - L2 checks both against the grey ladder.

## Parts

Five printed parts, one file each in this folder. `assembly.py` checks them
together.

| Part | Job | Print |
|---|---|---|
| **Base** (`base.py`) | Platen: PTFE strip pocket, two frame pins; rim all round with the petiole notch | On its bottom |
| **Chamber** (`chamber.py`) | Open square tube: LED-board ledge on a 45° corbel, four corner bosses for M3 inserts, tongue on top, petiole notch | Upright on its bottom edge; the notch top is a 10 mm bridge |
| **Hold-down frame** (`hold_down.py`) | Open frame on the leaf's edges, tabs over the pins | Flat |
| **Roof** (`roof.py`) | Groove over the chamber's tongue, four Pi bosses with an M2.5 nut in each top, ribbon slot, LED cable hole, two M3 holes for the carrier | On its underside; the groove ceiling is a 2.4 mm bridge |
| **Camera carrier** (`carrier.py`) | Holds the camera face down on four bosses, lens on the axis; M2 nuts in its top, M3 nuts in its bottom | Upside down; the M2 pocket ceilings are bridged |
| **LED board** (bought, fabbed from KiCad) | Square PCB with a round hole, SMD LEDs facing down on a 60 mm radius, an M3 hole in each corner | n/a |

The LED board screws straight into the chamber's corner inserts, so the separate
board clamp is gone.

**Hardware** (ISO 7045 pan head screws, ISO 4032 nuts; lengths from `params.py`)
- LED board: 4 × M3 × 6 into M3 heat-set inserts (CNC Kitchen standard, 4.0 mm
  bore), 4.4 mm of thread in each.
- Camera: 4 × M2 × 10 up through the camera into nuts captured in the carrier's
  top. The spacer under the camera is 4.2 mm, so one length fits any board from
  0.8 to 1.6 mm thick. The board thickness is unpublished.
- Carrier: 2 × M3 × 8 down from the roof top, nuts in the carrier's bottom.
- Pi: 4 × M2.5 × 5 down into nuts in the boss tops. The bores are blind, so
  there is no hole into the chamber.

## Electronics

v0's read method, but not its LED driver. Each LED has its own series resistor
from Pi 5 V. Each band's four LEDs are in parallel and switched low-side by one
logic-level N-MOSFET, with its gate on a GPIO.
- **Currents per band** (DESIGN, `params.COMMON.i_led`):
  - 100 mA per LED for the four visible and red bands. That is the ams-OSRAM
    parts' datasheet minimum, and a tenth of their 1000 mA maximum.
  - 60 mA for the 850 nm band. Its 100 mA is an absolute maximum, so the drive
    stays under 0.7 × that after the resistor is rounded to E24 (65 mA).
  - At most about 420 mA per band, one band on at a time.
- **Why not the ULN2803A.** At 400 mA a ULN2803A output's saturation voltage
  eats most of the headroom a 3 V blue or green LED leaves on a 5 V rail. Its
  current would then hang on the transistor, not the resistor.
- **Resistors:** the largest E24 value at or under (5 V − Vf − 0.1 V) / I:
  - 20 Ω blue, 22 Ω green, 27 Ω red, 30 Ω far red, 51 Ω NIR.
  - Each dissipates at most 0.31 W, so use 0.5 W parts.
  - Vf is the datasheet's typical at its test current, which is higher than at
    100 mA, so the real current runs a little over the design value.
  - The 0.1 V is the drop the MOSFET is allowed at 400 mA.
- **Drift is fine.** Resistor drive lets current drift a little with LED
  temperature, and the in-frame white strip cancels that drift.
- **Power budget:** about 1.3 A on the official 5 V / 3 A supply:
  - the Pi 4B's typical 600 mA;
  - a 300 mA allowance for the camera and sensor;
  - the worst band, about 420 mA.
- A DS18B20 logs chamber temperature.

## Bill of materials (new parts only)

The Pi 4B and DS18B20 are shared with or bought for v0. The camera is not shared:
this instrument gets its own Camera Module 2 NoIR, refocused to 100 mm for good.

| Part | Spec | Qty |
|---|---|---|
| Camera Module 2 NoIR | Dedicated, refocused to 100 mm | 1 |
| LEDs: GD CSSPM1.14, XPEBGR-L1-0000-00K03, GH CSSPM1.24, GF CSSRML.24, VSMY3850X01 | Datasheets above; 120–135° | 4 per band + spares |
| Logic-level N-MOSFET | One per band, low-side; part to pick | 5 |
| Resistors, 0.5 W | 4 each of 20, 22, 27, 30, 51 Ω | 20 |
| LED ring PCB | KiCad, fabbed; annulus, 60 mm LED radius | 1 (fab minimum 5) |
| PTFE sheet, ≥ 5 mm | White reference strip and flat-field card | strip 108.6 × 8 + one card covering the platen |
| NIR-dark black: Fineshut KIWAMI, Acktar Metal Velvet or Edmund Flock 65 | ≤ 3 % at 850 nm, published | platen + chamber lining |
| Grey card / matte grey sample | L2 linearity ladder | 1 |
| Foam strip, black | Petiole notch seals (chamber and base rim) | small |
| Felt | Flaps over the roof's ribbon slot and cable hole | small |
| Screws and nuts | 6 × M3 (4 × 6, 2 × 8) + 2 M3 nuts, 4 × M2 × 10 + 4 nuts, 4 × M2.5 × 5 + 4 nuts, 4 × M3 heat-set inserts | — |

## Experiments

| ID | Test | Answers |
|---|---|---|
| L1 | One leaf, reinserted 10× (chamber lifted and lowered each time), fixed patch | Repeatability, the platen's and chamber's registration |
| L2 | White / grey / black ladder, plus bare platen | Linearity, PTFE flatness, platen NIR darkness |
| L3 | Dark-green vs yellowing leaf of one plant | Whether NDVI saturates and NDRE separates them |
| L4 | One plant, daily, through a deliberate feed cut | Whether stress shows in the maps before it shows to the eye |

## What `validate()` checks

`params.validate()` checks 1–5 and the drive. `assembly.py` checks 6.

1. The field at 100 mm covers the leaf area and the white strip, inside
   90 % of the half-field.
2. No LED, ring part or hold-down frame is in the camera's view cone.
3. The line from every LED to the field centre is at 45 ± 1° to the platen.
4. Ring uniformity ≤ 2 : 1 over 80 % of the field, from the chosen LED's
   datasheet beam angle (an UNVERIFIED beam angle fails), and the same beam in
   every band.
5. The ribbon path from the CSI connector to the camera, with bends, ≤ 130 mm
   (150 mm VENDOR ribbon, 20 mm slack).
6. Parts clear pairwise, every LED's light reaches the field and the strip, and
   overhangs are ≤ 45° in each part's print orientation.

## Decisions (owner, 2026-10-07)

1. **Camera: Camera Module 2 NoIR**, a second unit, refocused to 100 mm and
   dedicated to this instrument.
   - v0's board model (`hardware.py`) and the IMX219's documented raw linearity
     (Pagnutti et al., JEI 26 013014, 2017) carry over.
   - The rejected option was a Camera Module 3 NoIR: autofocus, but 120 mm away, a
     bigger chamber, and a quad-Bayer re-mosaic in its full-resolution raw.
2. **Light from above: reflectance**, 45°/0°, so the NDVI compares with the
   literature.
   - The rejected option was transmission through the leaf on a backlight, a
     per-pixel SPAD meter.
3. **LEDs: distributor parts** (ams-OSRAM, Cree LED and Vishay), about 120°,
   100 mA (60 mA at 850 nm), one MOSFET per band.
   - Roithner's SMC family was dropped because it cannot be shown to be buyable.

## Open

- Stock for every LED at order time.
- The MOSFET part: logic-level, at most 0.1 V drop at 400 mA with a 3.3 V gate.
- Measure each band's current on the bench. Vf at 100 mA is not tabulated, so
  the computed current is an upper-side estimate.
- Whether the v2 lens refocuses to 100 mm cleanly.
- The image's long axis is INFERRED to run parallel to the camera's connector
  edge. If it is the other way, the field turns 90° and `params` needs the swap.
- The camera's back-side connector height (≤ 3.5 mm allowed) and the SD card's
  overhang at the Pi's end (4 mm allowed) are unpublished.
- Line the hold-down frame's top black. Black PETG can be bright at 850 nm, and
  the frame is in the picture.
- The MOSFET board has no home yet. The roof has room beside the Pi.
- PTFE's flatness at 850 nm (L2). No published 850 nm number for skived sheet was
  found.
