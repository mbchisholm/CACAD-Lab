"""Run a part file in build123d-mcp and print the checks an agent would run.

    uv run --python 3.12 --with mcp tools/verify_mcp.py archive/mount_plate/enclosure.py archive/mount_plate/out/tray

Only needed outside a Claude Code session (inside one, call the MCP tools
directly). The part file must assign a Shape to `result`.
"""
import asyncio, base64, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = StdioServerParameters(
    command="uv",
    args=["tool", "run", "--python", "3.12", "build123d-mcp@latest",
          "--allow-imports", "cacad,projects,coupons,types"],
    cwd=ROOT, env={**os.environ, "PYTHONPATH": ROOT},
)
VIEWS = {"iso": dict(direction="iso", quality="high"),
         "az": dict(direction="iso", azimuth=200, elevation=40, quality="high"),
         "top": dict(direction="top")}


def text(res, limit=3000):
    for c in res.content:
        if c.type == "text":
            print(c.text[:limit])


async def main(path, prefix):
    async with stdio_client(SERVER) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            print("=== execute_file"); text(await s.call_tool("execute_file", {"path": os.path.abspath(path), "result_name": "result"}), 800)
            print("=== validate"); text(await s.call_tool("validate", {}), 600)
            print("=== find_holes"); text(await s.call_tool("find_holes", {}), 4000)
            print("=== analyze_printability"); text(await s.call_tool("analyze_printability", {}))
            for name, kw in VIEWS.items():
                res = await s.call_tool("render_view", kw)
                for c in res.content:
                    if c.type == "image":
                        p = f"{prefix}_{name}.png"
                        open(p, "wb").write(base64.b64decode(c.data)); print("wrote", p)

asyncio.run(main(sys.argv[1], sys.argv[2]))
