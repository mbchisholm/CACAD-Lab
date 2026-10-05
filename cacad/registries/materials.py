"""Printer and material numbers shared by every project.

A number here comes from a standard, a vendor's published sheet, or it is a
DESIGN choice; each says which. A printed part is designed to tolerate its
DESIGN clearances (clamped, sealed with an O-ring or sealant, or free), never
press-fit against a bought part. The coupon (coupons/fdm_coupon.py) is an
optional tool for tuning these, not a gate.
"""
from types import MappingProxyType

MATERIAL = "PETG"
NOZZLE = 0.4
LAYER = 0.2

# Bambu Lab A1 build volume 256 x 256 x 256 mm (bambulab.com A1 specifications).
BED = (256.0, 256.0, 256.0)

WALL = 1.6            # DESIGN: 4 perimeters at the 0.4 nozzle
FLOOR = 1.2           # DESIGN: 6 layers

# ISO 273 clearance holes, mm (fine H12 / medium H13 / coarse H14).
ISO_273 = MappingProxyType({
    "M3": (3.2, 3.4, 3.6),
    "M4": (4.3, 4.5, 4.8),
    "M5": (5.3, 5.5, 5.8),
    "M6": (6.4, 6.6, 7.0),
})
CLEAR_SLIP = 0.20     # diametral, M3: ISO 273 fine 3.2 - 3.0
CLEAR_LOOSE = 0.40    # diametral, M3: ISO 273 medium 3.4 - 3.0
# DESIGN: diametral allowance added to a printed clearance hole, because FDM holes print undersize.
# Prusa's guidance gives printer accuracy as about 0.2 mm (help.prusa3d.com, "Modeling with 3D printing in mind").
# Older projects (standoff_plate, mount_plate, standoffs) use CLEAR_LOOSE without it.
FDM_HOLE_ALLOWANCE = 0.20


def clearance_bore(size: str) -> float:
    """Printed clearance hole: ISO 273 medium plus the DESIGN FDM allowance."""
    return ISO_273[size][1] + FDM_HOLE_ALLOWANCE


# DESIGN: radial clearance between a printed part and a bought part it slips over or around (PVC pipe, channel
# body). Prusa: 'at least 0.3 mm' for movable parts; Hubs: 0.5 mm for FDM connectors. The part is clamped, sealed
# or free, never press-fit.
FIT_CLEAR = 0.40

# Heat-set inserts, CNC Kitchen standard (3djake.com CNC Kitchen pages; Ruthex drill set 4.0 / 5.6 agrees).
# Hole depth: insert length + about 1 mm (cnckitchen.com, 'Tips and tricks for heat-set inserts').
INSERT_BORE_M3 = 4.00
INSERT_LEN_M3 = 5.7
INSERT_DEPTH_M3 = 6.0       # DESIGN for the coupon; vendor guidance would be 5.7 + 1
INSERT_WALL_M3 = 1.6        # vendor minimum wall around the hole
BOSS_OD_M3 = 7.0            # DESIGN, older projects: 1.5 wall each side, under the vendor's 1.6 minimum (7.2)
INSERT_BORE_M4 = 5.60
INSERT_LEN_M4 = 8.1
INSERT_WALL_M4 = 2.1
