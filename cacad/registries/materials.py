"""Printer and material numbers shared by every project. Calibrated, not
guessed: date every change, and say which coupon it came from.

Values marked TODO are the starting guesses; nothing prints for fit until
coupons/fdm_coupon.py has been printed and measured.
"""
from types import MappingProxyType

MATERIAL = "PETG"
NOZZLE = 0.4
LAYER = 0.2

WALL = 1.6            # 4 perimeters
FLOOR = 1.2           # 6 layers
CLEAR_SLIP = 0.20     # TODO: replace after coupon (hole clearance ladder)
CLEAR_LOOSE = 0.40    # TODO: replace after coupon
INSERT_BORE_M3 = 4.00  # TODO: replace after coupon (insert bore ladder)
INSERT_DEPTH_M3 = 6.0
BOSS_OD_M3 = 7.0      # insert bore + 1.5 mm wall each side
