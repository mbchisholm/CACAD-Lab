# seedling_wheel — spec and plan

## Question

Two 1020 seedling flats share one light. One is under the light and one is shaded below. An ESP32 swaps them on a
schedule by turning a two-gondola wheel through 180°. Choices made by the owner: a 1020 flat, gravity-hung
gondolas, 150 mm of plant headroom above the rim, and a light picked by us.

## Concept

- A Ferris wheel with two cabins between two A-frame towers.
- Each tower is three 2020 spokes, two legs and a mast. The spokes aim at the axis and end 45 mm short of it. There
  they bolt to a round printed hub disc (P5).
- The gearmotor bolts to P5 and passes between the spoke ends into a printed nacelle (P8). Its torque reacts into
  all three spokes.
- One ridge beam on the mast tops carries the light. One spine joins the feet. No cage, no side rails.
- A gondola hangs from each end of the arms on a plain pivot (ISO 7379 shoulder screw in a printed bore). Gravity
  keeps it level.
- No shaft or rod crosses the growing volume. The arms sit outboard of the tray ends, so the light sees only plants.
- The gondolas are passive: no wiring rotates, so there is no slip ring and the rotor may turn the same way every
  time.
- Rotor radius is set by the turn, not chosen: the two W × H gondola envelopes must pass at every angle, so
  R ≥ ½·√(W² + H²) + gap (`params.derive`, `R_min`). The test sweeps it at every degree.

## Parts

### Bought
| | Item | Source |
|---|---|---|
| B1 | 2020 extrusion (HFS5 type): legs, masts, feet, ridge, spine, arms, gondola rails, posts; 4× Misumi HBLFSN5 brackets | Misumi FA 2010 p.2239, p.2245 |
| B2 | 2× StepperOnline 17HS15-1584S-MG50 (NEMA 17, 50:1 planetary, 10 Nm permissible), one per tower | reseller spec table, UNVERIFIED drawing |
| B3 | 2× Pololu #2693 8 mm hub; 4× ISO 7379 Ø8 × 16 shoulder screw; ISO 7089 8 washers; ISO 4032 M6/M3 nuts; ISO 4762 M5 × 10/12 + HNTAJ5 T-nuts | standards |
| B4 | 3× Barrina T5 2 ft 10 W bars, linked, switched by a relay | barrina-led.com; length UNVERIFIED |
| B5 | Adafruit Feather ESP32-S3 (`boards.FEATHER_ESP32S3`), 2× TMC2209, 24 V supply, `RELAY_4409` for the light, 2× A3144-type hall sensors and magnets | registries / to source |
| B6 | 2× Bootstrap Farmer 1020 Extra Strength flats (21.1 × 11.0 × 2.5 in) | bootstrapfarmer.com |

### Printed (PETG)
| | Part | Qty | State |
|---|---|---|---|
| P1 | Rotor hub: Pololu hub to arm, keyed into the slot | 2 | built, checked |
| P2 | Pivot plate on each arm end: shoulder stop face and captive M6 nut | 4 | built, checked |
| P3 | Gondola hanger on each post top: the plain-bearing pivot | 4 | built, checked |
| P4 | Tray corner guide: the tray drops in with 4 mm all round (2 of each hand) | 8 | built, checked |
| P5 | Tower head: hub disc joining the three spokes, the gearbox face mount | 2 | built, checked |
| P6 | Home sensor bracket and arm magnet cup | 2 + 2 | to draw |
| P7 | Light hangers under the ridge, with height steps | 2 | envelope |
| P8 | Nacelle: a cone over each gearmotor, landing on the spokes | 2 | envelope |
| P9 | Electronics bay on the spine, and the feet | 1 + 4 | to draw |
| P10 | Leg shoe: leg to foot crossbar | 4 | envelope |

## Electronics and firmware

- Both TMC2209s share one STEP/DIR pair. Each tower homes on its own hall sensor, so the two ends cannot twist the
  gondolas: on a mismatch the swap stops and reports a fault.
- The light switches through the relay. The Barrina bars have no dimming input.
- Swap sequence:
  1. Turn the light off.
  2. Check both towers are home.
  3. Turn 180° in 40 s with 5 s ramps. The tray tilt bound is 0.02°, against a 0.86 s pendulum, so the water in a
     bottom-watering tray does not slosh.
  4. Settle for 10 s.
  5. Check both hall sensors.
  6. Turn the light on.
- If either driver stalls (StallGuard), stop, raise a fault, and do not retry by itself.
- Schedule: NTP time, a photoperiod per tray (for example 12 h each), and a manual swap button.
- On a power cut the planetary gearbox does not self-lock. An unbalanced wheel turns until the loaded tray hangs at
  the bottom. That is safe, and homing recovers it.

## Open
- Order-time checks:
  - The MG50 drawing: shaft length and flange pattern feed P5 and the `shaft_need` assert.
  - The Pololu #2693 hole pattern, which feeds P1.
  - The T5 bar length.
- Pivot friction is UNVERIFIED. The worst stick-slip estimate is 0.37°. Grease the shoulder.
- Racking along X is resisted only by the brackets at the ridge and spine corners. Add a second spine, or diagonal
  ties, if it sways in use.
- Draw P6–P10. P8's finish and P7's light hood decide most of what is left of the look.
