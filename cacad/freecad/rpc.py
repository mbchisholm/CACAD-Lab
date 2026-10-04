"""Thin client for the freecad-mcp XML-RPC server."""
from __future__ import annotations

import json
import time
import xmlrpc.client

RPC_URL = "http://127.0.0.1:9875"


class FreeCADRPC:
    """`run(code)` executes `code` inside FreeCAD and returns the JSON the code
    printed after a `JSON:` marker. Keep each call small: the GUI dispatcher
    gives one call about 90 s (FINDINGS F17)."""

    def __init__(self, url: str = RPC_URL):
        self.srv = xmlrpc.client.ServerProxy(url, allow_none=True)
        if not self.srv.ping():
            raise RuntimeError("FreeCAD RPC server did not answer ping")

    def run(self, code: str, label: str = ""):
        t0 = time.time()
        r = self.srv.execute_code(code)
        msg = r.get("message", "")
        if not r.get("success"):
            raise RuntimeError(f"FreeCAD execute_code failed ({label}):\n{msg}")
        if "JSON:" not in msg:
            raise RuntimeError(f"FreeCAD code printed no JSON ({label}):\n{msg}")
        if label:
            print(f"  [rpc] {label} {time.time() - t0:.1f}s")
        return json.loads(msg.split("JSON:", 1)[1].strip().splitlines()[0])

    def version(self) -> dict:
        return self.run('import FreeCAD, Part, json; print("JSON:" + json.dumps('
                        '{"fc": ".".join(FreeCAD.Version()[:3]), "occ": Part.OCC_VERSION}))')
