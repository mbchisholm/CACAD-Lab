# seedling_wheel

A two-level seedling stand that swaps which 1020 flat sits under the light. Two gravity-hung gondolas ride a
Ferris-wheel rotor. An ESP32 turns the rotor 180° with two NEMA 17 50:1 gearmotors, one per end tower. Nothing
crosses the growing volume. Overall about 776 L × 705 W × 813 H mm (sweep included; motors add 91 mm per end).
Not printed yet.

![Rotor at 0°: tray A under the light](../../docs/img/seedling_wheel_iso.png)

![End view at 60°: gondolas stay level through the turn](../../docs/img/seedling_wheel_turning.png)

## Status

STATUS is `concept`.
- **Passes:** `validate()`, the three load-path prints (P1 hub, P2 pivot plate, P3 hanger) with their checks, an
  every-degree sweep, solid overlap checks at 0/45/90/135° with a negative control, and designed-contact checks.
- **Open:** the gearbox drawing, the hub hole pattern and the light bar length (all UNVERIFIED); P4–P9 are envelopes
  or not yet drawn. See `SPEC.md`.

## Sources

`SPEC.md` names every bought part.
- Each number in `params.py` is a (value, TAG, source) triple: VENDOR (Bootstrap Farmer tray, Misumi HFS5, the
  StepperOnline MG50 spec table as relisted, Pololu #2693), STANDARD (ISO 7379, 7089, 4032, 4762, 273, NEMA ICS 16)
  or DESIGN.
- Estimated values are tagged UNVERIFIED and listed by `params.py` under `UNVERIFIED:`. None of them may pass a part
  that has to fit.

## Run

```
.venv/bin/python projects/seedling_wheel/params.py         # the design, validated
.venv/bin/python projects/seedling_wheel/p1_hub.py         # one part -> out/*.step, *.stl (also p2_pivot, p3_hanger)
.venv/bin/python projects/seedling_wheel/assembly.py [deg] # overlap checks -> out/seedling_wheel_<deg>.step, .3mf
.venv/bin/python -m pytest projects/seedling_wheel
```
