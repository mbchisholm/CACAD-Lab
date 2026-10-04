"""Board-edge connector systems: the header on the board and the plug that
mates with it, so an enclosure can size an opening and reserve the room to
plug and unplug. Every value from the manufacturer's datasheet; cite it.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Mating:
    name: str
    header_h: float             # header height above the board top, mm
    header_len: float           # header length along the pitch direction, mm
    header_depth: float         # header depth along the mating axis, mm (its origin is its centre)
    plug_w: float | None        # plug housing width along the pitch direction, mm; None = not yet sourced
    plug_len: float | None      # plug housing length along the mating axis, mm
    plug_h: float | None        # plug housing height, mm; sits on the board top when mated
    source: str

    @property
    def plug_known(self) -> bool:
        return None not in (self.plug_w, self.plug_len, self.plug_h)


# JST SH 1.0 mm, 4 circuits, side entry: the STEMMA QT / Qwiic connector.
# JST eSH.pdf: header SM04B-SRSS-TB (p.3, side entry type: 2.9 high, 4.25
# deep, B = 6.0 long); housing SHR-04V-S-B (p.2: 2.8 high, 5 long, B with
# protrusions = 7.0 for 4 circuits). The mated projection beyond the header
# is not tabulated; the plug length is used for the pull-out room.
JST_SH4 = Mating(
    name="JST_SH4",
    header_h=2.9, header_len=6.0, header_depth=4.25,
    plug_w=7.0, plug_len=5.0, plug_h=2.8,
    source="JST SH connector datasheet eSH.pdf, pp. 2-3, read 2026-09-20",
)

# JST PH 2.0 mm, side entry, SMT: the Feather LiPo connector (2 circuits) and
# the Adafruit STEMMA JST PH input (3 circuits, MOSFET 5648, relay 4409).
# JST ePH.pdf: housing PHR-n (p.3: B = 5.8 / 7.8 for 2 / 3 circuits, drawing
# 4.5 across, 6.85 along the mating axis); SMT side-entry header
# Sn B-PH-SM4-TB (p.4: B = 7.9 / 9.9; side-entry drawing 5.5 tall, 6 deep
# plus 2.6 of pads). 2026-10-04: header_h and header_depth were swapped
# (6.0 tall, 5.5 deep) in the 2026-09-21 reading of the same drawing.
JST_PH2 = Mating(
    name="JST_PH2",
    header_h=5.5, header_len=7.9, header_depth=6.0,
    plug_w=5.8, plug_len=6.85, plug_h=4.5,
    source="JST PH connector datasheet ePH.pdf, pp. 3-4, read 2026-09-21, h/depth corrected 2026-10-04",
)

JST_PH3 = Mating(
    name="JST_PH3",
    header_h=5.5, header_len=9.9, header_depth=6.0,
    plug_w=7.8, plug_len=6.85, plug_h=4.5,
    source="JST PH connector datasheet ePH.pdf, p.3 PHR-3, p.4 S3B-PH-SM4-TB, read 2026-10-04",
)

# USB Type-C receptacle. The opening is 8.34 x 2.56, 6.20 deep (USB Type-C
# specification, via en.wikipedia.org/wiki/USB-C, read 2026-09-21). The plug
# overmold maximum is in the USB-IF specification, not read yet: an enclosure
# opening for it cannot be sized until it is. Header numbers are the
# receptacle's; the board file gives its position.
USB_C = Mating(
    name="USB_C",
    header_h=3.26, header_len=8.94, header_depth=6.20,   # receptacle shell, USB Type-C spec via Wikipedia (opening 8.34 x 2.56 inside)
    plug_w=None, plug_len=None, plug_h=None,
    source="USB Type-C Cable and Connector Specification (overmold max not read); opening via en.wikipedia.org/wiki/USB-C, 2026-09-21",
)

MATINGS = {m.name: m for m in (JST_SH4, JST_PH2, JST_PH3, USB_C)}
