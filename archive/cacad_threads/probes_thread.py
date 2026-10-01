"""assert_thread_present, removed from cacad.probes when the thread work was parked (2026-09-20)."""
from build123d import Part

from cacad.probes import is_inside


def assert_thread_present(part: Part, r: float, z0: float, pitch: float, label: str, n: int = 12):
    """Sample one pitch along Z at radius r (mid tooth height) on the +X side:
    a real thread has both material (tooth) and air (groove) there. A single
    point at the crest radius can land in a groove by chance (MISTAKES #2).
    Assumes the thread axis is Z."""
    hits = [is_inside(part, (r, 0, z0 + pitch * i / n)) for i in range(n)]
    assert any(hits), f"{label}: no thread material at r={r:.2f} between z={z0:.2f} and {z0 + pitch:.2f}"
    assert not all(hits), f"{label}: no thread groove at r={r:.2f} (solid all the way round)"


