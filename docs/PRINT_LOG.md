# Print log

`docs/FINDINGS.md` holds geometry and kernel facts; this file holds
manufacturing assumptions and, once anything is printed, what the print showed.

None of them gates a print: clearances come from ISO 273 plus a
DESIGN FDM allowance, insert bores from the insert vendor, printed-to-PVC
fits from published FDM guidance (`cacad/registries/materials.py`), and a
part is designed to tolerate them (clamped, sealed, or free; never
press-fit).

- [ ] **Optional: tune the clearances with the coupon** (`python coupons/fdm_coupon.py`
  → `coupons/out/fdm_coupon.stl`: five M5 clearance holes 5.10..5.30, five M3
  heat-set insert bores 3.8..4.2 × 6 deep on a raised pad, one 20 mm cube;
  PETG, 0.4 nozzle, labelled and dated). If it is printed, record the results
  here and date any change to `FDM_HOLE_ALLOWANCE`, `FIT_CLEAR` or the insert
  bores in `cacad/registries/materials.py`.
- [ ] Sliver exclusion threshold (`nozzle_d²`) and the 60° flank acceptance
  are slicer-side assumptions, not measured.
- [ ] **Slicer settings: brim, stringing and holes.** Wanted now for the
  2026-10-15 standoff plate (below): Bambu Studio's X-Y hole compensation,
  bridge flow and speed, and retraction decide whether a printed bore is clear.
  Earlier note: on the cable gland's first
  print the brim made the threaded parts hard to fit together, and the
  covers tested showed stringy overlap. Not measured, and the settings used
  were not recorded. Before the next fit print, record the Bambu Studio
  profile (brim type and gap, retraction, travel, temperature), and check
  whether any mating face touches the bed where a brim would sit.

## Prints

Add one dated entry per print: part, printer profile, what fit, what did not,
and any change made to `cacad/registries/materials.py`.

### 2026-10-15: standoff_plate ANALOG_NODE + nutrient_controller lean box (V1)

Bambu A1, PETG. The owner reported the result; the Bambu Studio profile is not
recorded yet (the owner offered the project file, see the open item above).

- Fit: the SEN0244 and ADS1115 hole patterns land on their bosses. The
  registry positions are right.
- Failed: the M2 bores had filament in them and the screws were hard to drive.
  One boss broke off the plate.
- Cause, from the geometry: the bore was screw + 0.40 (2.4 for M2) with no FDM
  allowance, so it printed undersize. Each 5.6 OD boss stood on a 1.2 mm
  bridged web over its nut pocket. Its footprint (r 2.8) reached past the
  pocket corners (r 2.48) by only 0.3. The pocket ceiling was bridged with the
  bore cut through it, so the bore's first perimeter printed in air and could
  sag into the hole. The bridge, any stringing and the slicer's hole
  compensation are slicer-side; the profile will say which applied.
- Change (standoff_plate, every plate): the bores are now ISO 273 medium plus
  `FDM_HOLE_ALLOWANCE` (M2 2.6, M2.5 3.1, M3 3.6; M2 and M2.5 rows added to
  `ISO_273`). Every boss gets a 1 mm 45° flare where it meets the plate. The
  web over the pocket is now 1.6. A stepped bridge (slot, then square, then
  bore) means no bore perimeter prints in air. M2 boss walls are 1.51 where
  the Adafruit pin keep-out allows no more.
- Lean box (V1 enclosure): the lid has no retention, and the cable
  pass-throughs did not suit the owner's wiring. The layout will change with
  different sensors, so the box is not being revised. Its own M2 bosses
  (`lean_params.py`) still use the old bore rule.
