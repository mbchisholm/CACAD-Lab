"""Bending-strain allowables, removed from cacad.registries.materials when the
gland (collet fingers) was parked, 2026-09-20. cantilever.py reads them."""
from types import MappingProxyType

# Allowable bending strain at a living-hinge or finger root, by material:
# BULK yield-class numbers for FDM parts, not datasheet elongation-at-break,
# and not across layer lines (multiply by LAYER_ADHESION_FACTOR for that).
# UNVERIFIED against a printed coupon; PLA is listed to document why it is
# excluded from flexing parts.
MAX_BENDING_STRAIN = MappingProxyType(dict(
    PLA=0.020,
    PETG=0.045,
    PA12=0.080,
    TPU95A=0.500,
))
LAYER_ADHESION_FACTOR = 0.5   # across-layer allowable = bulk * this. TODO: derive from the collet finger coupon
