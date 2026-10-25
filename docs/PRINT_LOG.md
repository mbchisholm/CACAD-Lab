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
- [ ] **Slicer settings: brim and stringing.** On the cable gland's first
  print the brim made the threaded parts hard to fit together, and the
  covers tested showed stringy overlap. Not measured, and the settings used
  were not recorded. Before the next fit print, record the Bambu Studio
  profile (brim type and gap, retraction, travel, temperature), and check
  whether any mating face touches the bed where a brim would sit.

## Prints

Nothing has been printed since the cable gland (2026-09). Add one dated entry per
print: part, printer profile, what fit, what did not, and any change made to
`cacad/registries/materials.py`.
