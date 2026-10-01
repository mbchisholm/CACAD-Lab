"""Shop sheets from params: one SVG per distinct member (its cut length, the
face the screws enter, every hole dimensioned from one end) and a build
sequence in markdown with the cut list and the screws per step. Nothing here
holds a number; every position is a screw head from params.derive projected
onto its member's face.

    .venv/bin/python projects/tote_rack/build_sheet.py [rack]     # -> out/sheets/*.svg, out/build_sheet_<rack>.md
"""
from __future__ import annotations

from projects.tote_rack.params import ACTIVE_RACKS, IN, LUMBER, derive

# Which face of each member the screws enter, in words for the sheet (fixed by the design, see params docstring)
FACE_WORDS = {"LEG": "outer face, away from the rack (the 3-1/2 in face)",
              "STR": "inner face, toward the rack centre (the 1-1/2 in face)",
              "RUN": "top face"}
PX_PER_MM = 0.55
MARGIN = 60


def holes_on(d: dict, member: str) -> tuple[int, int, int, list[tuple[float, float, str]]]:
    """(screw axis, long axis, across axis, [(along, across, screw name)]) for the screws whose head sits on `member`."""
    _, size, lo = d["boards"][member]
    mine = [s for s in d["screws"] if s[1] == member]
    if not mine:
        return -1, -1, -1, []
    axis = max(range(3), key=lambda i: abs(mine[0][4][i]))
    others = [i for i in range(3) if i != axis]
    long_ax = max(others, key=lambda i: size[i])
    across = [i for i in others if i != long_ax][0]
    holes = [(s[3][long_ax] - lo[long_ax], s[3][across] - lo[across], s[0]) for s in mine]
    return axis, long_ax, across, sorted(holes)


def sheet_groups(d: dict) -> dict[tuple, list[str]]:
    """Members sharing a cut and a hole pattern -> one sheet."""
    groups: dict[tuple, list[str]] = {}
    for nm, (kind, size, _) in d["boards"].items():
        _, _, _, holes = holes_on(d, nm)
        key = (kind, tuple(round(x, 3) for x in size), tuple((round(a, 3), round(b, 3)) for a, b, _ in holes))
        groups.setdefault(key, []).append(nm)
    return groups


def svg_sheet(d: dict, members: list[str]) -> str:
    nm = members[0]
    kind, size, _ = d["boards"][nm]
    L = LUMBER[kind]
    axis, long_ax, across, holes = holes_on(d, nm)
    length = max(size)
    if axis < 0:                                   # no screws enter this member: draw it edge-on with its cut length
        long_ax = max(range(3), key=lambda i: size[i])
        across = max((i for i in range(3) if i != long_ax), key=lambda i: size[i])
    width = size[across]
    w_px, h_px = length * PX_PER_MM, width * PX_PER_MM
    W, H = max(900.0, w_px + 2 * MARGIN), h_px + 2 * MARGIN + 60 * (1 + len(holes))
    end_a = {1: "y = 0, the front", 2: "z = 0, the floor end", 0: "x = 0, the left"}[long_ax]
    title = members[0] if len(members) == 1 else f"{members[0]} and {len(members) - 1} more"
    x0, y0 = MARGIN, MARGIN + 40
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" '
           f'font-family="Helvetica, Arial, sans-serif" font-size="12">',
           f'<rect width="100%" height="100%" fill="white"/>',
           f'<text x="{MARGIN}" y="24" font-size="16" font-weight="bold">{title}</text>',
           f'<text x="{MARGIN}" y="{H - 30}" font-size="11">{", ".join(members)}</text>',
           f'<text x="{MARGIN}" y="42">{L["label"]} ({L["t"] / IN:g} x {L["w"] / IN:g} in actual), cut {length / IN:g} in '
           f'({length:.0f} mm), qty {len(members)}</text>']
    face = FACE_WORDS.get(nm[:3])
    if holes:
        out.append(f'<text x="{MARGIN}" y="{y0 - 8}">{len(holes)} x #8 pilot holes on the {face}; '
                   f'dimensions from end A ({end_a}) in inches</text>')
    else:
        out.append(f'<text x="{MARGIN}" y="{y0 - 8}">no holes: screwed through the legs into this end grain (see the leg sheet)</text>')
    out.append(f'<rect x="{x0}" y="{y0}" width="{w_px:.1f}" height="{h_px:.1f}" fill="#f3e2c3" stroke="#333" stroke-width="1.5"/>')
    out.append(f'<text x="{x0 - 4}" y="{y0 + h_px / 2 + 4}" text-anchor="end" font-weight="bold">A</text>')
    out.append(f'<text x="{x0 + w_px + 4}" y="{y0 + h_px / 2 + 4}" font-weight="bold">B</text>')
    # overall length dimension under the piece
    yd = y0 + h_px + 22
    out += [f'<line x1="{x0}" y1="{yd}" x2="{x0 + w_px:.1f}" y2="{yd}" stroke="#333"/>',
            f'<line x1="{x0}" y1="{yd - 6}" x2="{x0}" y2="{yd + 6}" stroke="#333"/>',
            f'<line x1="{x0 + w_px:.1f}" y1="{yd - 6}" x2="{x0 + w_px:.1f}" y2="{yd + 6}" stroke="#333"/>',
            f'<text x="{x0 + w_px / 2:.1f}" y="{yd - 4}" text-anchor="middle">{length / IN:g} in</text>']
    # holes: crosshair on the face, a tiered dimension line from end A for each distinct along-position
    tiers = {}
    for along, acr, sn in holes:
        hx, hy = x0 + along * PX_PER_MM, y0 + (width - acr) * PX_PER_MM    # across drawn up = larger local value
        r = max(4.0, d["screw_spec"]["d"] / 2 * PX_PER_MM)
        out += [f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{r:.1f}" fill="none" stroke="#b00" stroke-width="1.5"/>',
                f'<line x1="{hx - r - 3:.1f}" y1="{hy:.1f}" x2="{hx + r + 3:.1f}" y2="{hy:.1f}" stroke="#b00"/>',
                f'<line x1="{hx:.1f}" y1="{hy - r - 3:.1f}" x2="{hx:.1f}" y2="{hy + r + 3:.1f}" stroke="#b00"/>']
        key = round(along, 3)
        if key not in tiers:
            tiers[key] = len(tiers)
            yt = yd + 22 + 18 * tiers[key]
            out += [f'<line x1="{x0}" y1="{yt}" x2="{hx:.1f}" y2="{yt}" stroke="#b00"/>',
                    f'<line x1="{hx:.1f}" y1="{hy:.1f}" x2="{hx:.1f}" y2="{yt + 4}" stroke="#b00" stroke-dasharray="3 3"/>',
                    f'<text x="{hx + 4:.1f}" y="{yt + 4}" fill="#b00">{along / IN:.3f}</text>']
    if holes:
        acrs = sorted({round(a, 3) for _, a, _ in holes})
        out.append(f'<text x="{MARGIN}" y="{H - 12}">across the face, from the bottom/outer edge: '
                   + ", ".join(f"{a / IN:.3f} in" for a in acrs) + "</text>")
    out.append("</svg>")
    return "\n".join(out)


def build_steps(d: dict) -> str:
    s, j = d, d["joints"]
    mm_in = lambda x: f"{x / IN:g} in"
    rt = [z / IN for z in d["railtops"]]
    str_bot = [z - d["run_h"] / IN - d["str_h"] / IN for z in rt]
    lines = [f"# Build sheet: tote rack `{d['rack']}`", "",
             f"Footprint {d['W'] / IN:g} x {d['D'] / IN:g} in, height {d['H'] / IN:g} in, {d['N']} levels. "
             "Origin is the floor at the front-left leg's outer corner; y runs front to back.", "",
             "## 1. Cut", ""]
    for kind, L in LUMBER.items():
        for i, st in enumerate(d["cut_plans"][kind], start=1):
            lines.append(f"- {L['label']} stick {i} (8 ft): " + ", ".join(f"{n} {ln / IN:g} in" for n, ln in st))
    lines += ["", "Kerf allowance " + mm_in(d["kerf"]) + " per cut is in the plan. Caliper the 1x1 before cutting; it is not a PS 20 size.", "",
              "## 2. Drill", "",
              "Pilot every hole on the sheets in `out/sheets/` (#8 screws; pine splits near ends). "
              "Runner holes are countersunk flush so the tote rim slides over them.", "",
              "## 3. Assemble", "",
              f"1. **Left side on the floor.** Lay LEG-FL and LEG-BL on their 3-1/2 in faces, inner faces up, "
              f"{mm_in(d['D'] - 2 * d['leg_d'])} apart (outer faces {mm_in(d['D'])} apart). Set the four stringers STR-L1..L4 across them, "
              f"ends flush with the legs' front and back faces, bottom edges at z = {', '.join(f'{z:g}' for z in str_bot)} in. "
              f"{d['screws_stringer_end']} x {mm_in(j['stringer->leg'][2])} screws per end through the stringer into the leg.",
              "2. **Right side** the same with LEG-FR, LEG-BR and STR-R1..R4.",
              f"3. **Stand both sides up** {mm_in(d['W'])} apart outside to outside. Fit TIE-BACK-BOT flat on the floor between the back legs, "
              f"flush with their back faces; TIE-BACK-TOP on edge between the back legs, flush with the top and back; "
              f"TIE-FRONT-TOP on edge between the front legs, flush with the top and front. "
              f"{d['screws_tie_end']} x {mm_in(j['tie->leg'][2])} screws per end through the leg's outer face into the tie's end grain. Square the frame before the last screws.",
              f"4. **Runners.** Set RUN-L1..L4 and RUN-R1..R4 on top of their stringers, outer faces flush with the stringers, ends flush. "
              f"{d['runner_screws_each']} x {mm_in(j['runner->stringer'][2])} screws each, countersunk, at the sheet positions.",
              "5. Glue every joint (spec S10). Anchor the rack to the wall before loading it; nothing in the frame resists a tote pulled out at the top.",
              "", "## Screws", ""]
    for jn, (through, into, ln) in j.items():
        n = sum(1 for scr in d["screws"] if (scr[1] if jn != "tie->leg" else scr[2]).startswith(jn.split("->")[0][:3].upper()))
        lines.append(f"- {jn}: {n} x {d['screw_spec']['label']} {mm_in(ln)}, through {mm_in(through)}, bites {mm_in(ln - through)}")
    return "\n".join(lines) + "\n"


def main(rack: str):
    d = derive(rack)
    here = __file__.rsplit("/", 1)[0]
    from pathlib import Path
    sheets = Path(here) / "out" / "sheets"
    sheets.mkdir(parents=True, exist_ok=True)
    written = []
    for key, members in sheet_groups(d).items():
        fn = sheets / (members[0].replace("-", "_") + (f"_and_{len(members) - 1}_more" if len(members) > 1 else "") + ".svg")
        fn.write_text(svg_sheet(d, members))
        written.append((fn.name, members))
    md = Path(here) / "out" / f"build_sheet_{rack}.md"
    md.write_text(build_steps(d) + "\n## Sheets\n\n" + "\n".join(f"- `{fn}`: {', '.join(m)}" for fn, m in written) + "\n")
    print(f"{rack}: {len(written)} sheets in {sheets}; {md}")
    for fn, m in written:
        print(f"  {fn}: {len(m)} members, {len(holes_on(d, m[0])[3])} holes each")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else ACTIVE_RACKS[0])
