"""Client for the Figma desktop MCP server (http://127.0.0.1:3845/mcp).

Usage:
  python3 figma_mcp.py get_metadata '{"nodeId":"12:300"}'
  python3 figma_mcp.py get_design_context '{"nodeId":"12:340"}'
  python3 figma_mcp.py get_screenshot '{"nodeId":"12:340"}' --out block.png
Without nodeId the tool works on the current selection in Figma.
"""
import base64
import json
import sys
import urllib.request

URL = "http://127.0.0.1:3845/mcp"
_session = {"id": None}


def _post(payload):
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if _session["id"]:
        headers["Mcp-Session-Id"] = _session["id"]
    req = urllib.request.Request(URL, json.dumps(payload).encode(), headers)
    with urllib.request.urlopen(req, timeout=180) as resp:
        _session["id"] = resp.headers.get("Mcp-Session-Id") or _session["id"]
        body = resp.read().decode()
    if not body.strip():
        return None
    if body.lstrip().startswith("{"):
        return json.loads(body)
    # split("\n"), not splitlines(): splitlines breaks the JSON on U+2028 inside design text
    data = "\n".join(line[5:].lstrip() for line in body.split("\n") if line.startswith("data:"))
    return json.loads(data) if data else None


def call(tool, args):
    _post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
           "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                      "clientInfo": {"name": "ild", "version": "1"}}})
    _post({"jsonrpc": "2.0", "method": "notifications/initialized"})
    return _post({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                  "params": {"name": tool, "arguments": args}})


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    out = argv[argv.index("--out") + 1] if "--out" in argv else None
    args = json.loads(argv[2]) if len(argv) > 2 and not argv[2].startswith("--") else {}
    res = call(argv[1], args) or {}
    if "error" in res:
        print("error:", res["error"], file=sys.stderr)
        return 1
    images = 0
    for item in res.get("result", {}).get("content", []):
        if item["type"] == "text":
            print(item["text"])
        elif item["type"] == "image":
            path = out if (out and images == 0) else f"{out or 'figma'}-{images}.png"
            with open(path, "wb") as fh:
                fh.write(base64.b64decode(item["data"]))
            print("image:", path)
            images += 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
