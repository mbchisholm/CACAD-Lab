"""Geometry + function (check_rack: per-part envelope and hand volume, pairwise interference, rail contact, open
site holes, supply continuity and insertion depths measured on the geometry, drop tips inside the collector, return
falling into the tote), the source tags on every value, the AM Hydro numbers the inactive layout must reproduce, the
mitred-leg hand formulas against OCC, and must-fail controls so a pass is not vacuous."""
import math

import pytest
from build123d import GeomType, Pos
from cacad import interference_volume
from projects.nft_rack import legs as L_
from projects.nft_rack import params
from projects.nft_rack.params import IN, spec
from projects.nft_rack.rack import build_channel, build_geom, build_leg, check_fall, check_rack, measure_insertion


def test_geometry_and_function(rack_name, parts):
    check_rack(rack_name, parts)


def test_every_rack_validates():
    """nft_table fails here until the tote is calipered and the PLACEHOLDER parts are measured: by design."""
    for name in params.RACKS:
        params.validate(name)


def test_inactive_rack_still_validates():
    params.validate("growing_up_pro")


def test_table_failure_names_every_gap():
    """The table's validate() names each unsourced load-bearing value, registry fields included."""
    with pytest.raises(AssertionError) as e:
        params.validate("nft_table")
    msg = str(e.value)
    for f in ("lid_outer", "lid_thickness", "rim_lip", "wall_draft_deg", "inner_depth", "fill_depth"):
        assert f"HDX_27GAL.{f} is None" in msg, f
    for g in ("drain_cap.spigot_len", "AAPW400.size", "collector: hub air", "collector: lid air", "waterline unknown"):
        assert g in msg, g
    assert params.gaps("growing_up_pro") == []


def test_every_value_is_tagged():
    for k, (v, tag, src) in params.SPEC.items():
        assert tag in params.TAGS and src, k
    for name, r in params.RACKS.items():
        assert set(r) == set(params.RACK_SOURCES[name]), name
    for row, r in list(params.PLUMBING.items()) + list(params.PUMPS.items()):
        assert r["what"] and r["ref"], row
        for k, v in r.items():
            if isinstance(v, tuple):
                assert len(v) == 3 and v[1] in params.TAGS and v[2], (row, k)


def test_untagged_input_is_refused(monkeypatch):
    monkeypatch.setitem(params.RACKS, "untagged", dict(params.RACKS["nft_table"]))
    monkeypatch.setitem(params.RACK_SOURCES, "untagged", {k: v for k, v in params.RACK_SOURCES["nft_table"].items() if k != "slope"})
    with pytest.raises(AssertionError, match="without a source tag"):
        params.validate("untagged")


def test_amhydro_numbers():
    """The inactive layout still reproduces what AM Hydro states: 60 x 46 x 92 in frame, 20 x 52 in channels on the
    top two levels, 16 finishing + 4 nursery, 96 finishing sites."""
    d = params.derive("growing_up_pro")
    assert (d["W"] / IN, d["D"] / IN, d["H"] / IN) == pytest.approx((60, 46, 92))
    assert len(d["channels"]) == 20 and {c["level"] for c in d["channels"]} == {2, 3}
    assert d["channels_by_kind"]["F"] == 16 and d["channels_by_kind"]["N"] == 4
    assert d["sites"]["F"] == 96 and d["sites"]["N"] == 40


def test_table_numbers(d):
    """The owner's choices: one level, six Growrilla 2 m channels at 250 mm, 8 sites each, floor 36 in at the high end."""
    assert len(d["levels_derived"]) == 1 and len(d["channels"]) == 6
    assert d["sites"]["G"] == 48
    assert [c["xc"] for c in d["channels"]] == pytest.approx([d["x1"] + 250 * j for j in range(6)])
    assert d["channels"][0]["z_hi"] == pytest.approx(36 * IN)


def test_slope_sets_the_drop(d, monkeypatch):
    """Drop is derived from the slope over the support span; the community model's 1:120 is refused."""
    assert d["drop"] == pytest.approx(d["support_span"] / 40)
    monkeypatch.setitem(params.RACKS, "_tmp", dict(params.RACKS["nft_table"], slope=1 / 120))
    monkeypatch.setitem(params.RACK_SOURCES, "_tmp", params.RACK_SOURCES["nft_table"])
    with pytest.raises(AssertionError, match="outside 1:30..1:40"):
        params.validate("_tmp")


def test_floor_line_through_both_contacts(d):
    """The floor passes through the front rail's back top edge and the back rail's outer top edge."""
    a = spec("frame_a")
    lv = d["levels_derived"][0]
    for c in d["channels"]:
        z_at = lambda y: c["z_hi"] - math.tan(d["theta"]) * (y - c["y_hi"])
        assert z_at(a) == pytest.approx(lv["z_f"], abs=1e-9)
        assert z_at(d["D"]) == pytest.approx(lv["z_b"], abs=1e-9)


def test_pump_duty(d):
    """Required flow 6 x 1-2 L/min; the AAPW400 chart at the worst-case static head (waterline at the tote floor)."""
    duty = d["pump_duty"]
    assert duty["req_lpm"] == pytest.approx((6.0, 12.0))
    assert duty["waterline"] is None and duty["head"] is None       # fill_depth not measured
    assert duty["gph_at_bound"] >= duty["req_gph"][1]
    assert params.pump_gph("AAPW400", 3.0) == pytest.approx(248.0)


@pytest.mark.parametrize("bend", [90.0, 87.0, 60.0, 30.0])
def test_mitred_leg_formulas_against_occ(bend):
    """Rule 8: the hand volume and box of a mitred stepped elbow, at four bends spanning the parameter, against OCC."""
    phi = math.radians(180 - bend)
    o1 = L_.unit((0.3, 1.0, -0.2))
    p = L_.perp(o1)
    o2 = tuple(math.cos(phi) * x + math.sin(phi) * y for x, y in zip(o1, p))
    lg = L_.elbow((10.0, 20.0, 30.0), o1, [(None, 20.0, 22.0, 14.0), (20.0, 45.0, 22.0, 16.0)], o2, [(None, 60.0, 16.0, 13.0)])
    e = L_.legs_expect("fitting", lg)
    solid = build_geom(e)
    assert len(solid.solids()) == 1 and solid.is_valid
    assert solid.volume == pytest.approx(e["volume"], rel=1e-6)
    bb = solid.bounding_box()
    assert (*tuple(bb.min), *tuple(bb.max)) == pytest.approx((*e["lo"], *e["hi"]), abs=1e-3)


def test_sites_and_feed_hole_on_every_lid(d, parts):
    """Hole count per lid from its faces: one cylinder per site plus the feed hole."""
    for c in d["channels"]:
        cyl = [f for f in parts[f"{c['name']}-lid"].faces() if f.geom_type == GeomType.CYLINDER]
        n_site = sum(1 for f in cyl if abs(2 * f.radius - spec("site_hole_d")) < 1e-3)
        n_feed = sum(1 for f in cyl if abs(2 * f.radius - spec("feed_tube_od")) < 1e-3)
        assert n_site == params.CHANNEL_KINDS[c["kind"]]["sites"] and n_feed == 1, (c["name"], n_site, n_feed)


def test_tube_volume_matches_sweep_length(d, parts):
    t = d["tubes"][0]
    r = t["r"]
    assert parts[t["name"]].volume == pytest.approx(math.pi * r * r * d["tube_len"][t["name"][:-5]], rel=1e-3)


def test_hose_volume_matches_pappus(d, parts):
    e = d["expect"]["SUP-hose"]
    ro, ri = params.pv("hose_34", "od") / 2, params.pv("hose_34", "id") / 2
    assert parts["SUP-hose"].volume == pytest.approx(math.pi * (ro * ro - ri * ri) * e["path_len"], rel=1e-4)


# ---- must-fail controls ----
def test_control_channel_lowered_into_the_rails_is_caught(d, parts):
    """Interference layer: the same channel 1 mm lower overlaps its front rail."""
    c = d["channels"][0]
    rail = parts["L1-RAIL-F"]
    assert interference_volume(parts[f"{c['name']}-body"], rail) < 1e-3
    low = build_channel(d, dict(c, z_hi=c["z_hi"] - 1.0))
    assert interference_volume(low[f"{c['name']}-body"], rail) > 1.0


def test_control_shifted_envelope_is_caught(rack_name, d, parts):
    """Envelope layer: a 1 mm shift in one expectation fails check_rack."""
    name = "L1-C03-lid"
    e = d["expect"][name]
    shifted = dict(e, lo=(e["lo"][0] + 1, *e["lo"][1:]), hi=(e["hi"][0] + 1, *e["hi"][1:]))
    orig = params.derive

    def patched(rack, **kw):
        out = orig(rack, **kw)
        out["expect"] = dict(out["expect"], **{name: shifted})
        return out

    import projects.nft_rack.rack as rack_mod
    rack_mod.derive, saved = patched, rack_mod.derive
    try:
        with pytest.raises(AssertionError, match=name):
            check_rack(rack_name, parts)
    finally:
        rack_mod.derive = saved


def test_control_valve_seated_1mm_high_is_caught(d, parts):
    """Supply layer: the valve 1 mm up its riser overlaps the pipe, and the measured insertion grows by 1 mm (the pipe
    now runs past the socket bottom into the valve body), so it disagrees with the socket depth."""
    riser, valve = parts["SUP-riser"], parts["SUP-valve"]
    assert interference_volume(riser, valve) < 1e-3
    assert interference_volume(riser, valve.moved(Pos(0, 0, 1.0))) > 100.0
    want = next(j[3] for j in d["joints"] if j[0] == "SUP-riser" and j[1] == "SUP-valve")
    assert measure_insertion(d, "SUP-riser", "SUP-valve", params.pv("pvc1_pipe", "od") / 2) == pytest.approx(want, abs=0.05)
    moved = dict(d, expect=dict(d["expect"]))
    e = d["expect"]["SUP-valve"]
    lg = [dict(x, c=L_.add(x["c"], (0, 0, 1.0))) for x in e["geom"][1]]
    moved["expect"]["SUP-valve"] = dict(e, geom=("legs", lg))
    got = measure_insertion(moved, "SUP-riser", "SUP-valve", params.pv("pvc1_pipe", "od") / 2)
    assert got == pytest.approx(want + 1.0, abs=0.05)


def test_control_collector_lid_3mm_high_hits_an_elbow(d, parts):
    """Return layer: the elbow hubs clear the collector lid by the reported margin; 3 mm more and channel 6's hub hits."""
    air = d["collector_tip_air"]["hub"]
    assert 0 < air < 3.0
    lid, elbow = parts["COLL-lid"], parts["L1-C06-elbow"]
    assert interference_volume(lid, elbow) < 1e-3
    assert interference_volume(lid.moved(Pos(0, 0, 3.0)), elbow) > 1.0


def test_control_uphill_return_is_refused(d):
    """Fall check: a path with one point lifted 1 mm above its predecessor is refused."""
    check_fall(d["return_paths"])
    name, pts = next(iter(d["return_paths"].items()))
    bad = list(pts)
    bad[3] = (bad[3][0], bad[3][1], bad[2][2] + 1.0)
    with pytest.raises(AssertionError, match="does not fall"):
        check_fall({name: bad})


def test_straight_leg_builds_one_solid():
    """build_leg returns one valid solid for a straight stepped part (t = 0)."""
    lg = L_.straight((0, 0, 0), (0, 0.1, -1), [(30.0, 20.0, 15.0), (20.0, 25.0, 10.0)])[0]
    s = build_leg(lg)
    assert len(s.solids()) == 1 and s.volume == pytest.approx(L_.leg_volume(lg), rel=1e-9)
