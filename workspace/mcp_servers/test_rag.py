"""Comprehensive test for RAG MCP server."""
import json
import subprocess
import sys
from pathlib import Path

SERVER_PATH = Path(__file__).parent / "rag_server.py"
VENV_PYTHON = Path(__file__).parent.parent.parent / "venv" / "Scripts" / "python.exe"

print("=" * 60)
print("RAG MCP Server — Comprehensive Test")
print("=" * 60)

proc = subprocess.Popen(
    [str(VENV_PYTHON), str(SERVER_PATH)],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True,
)

# Wait for ready
print("\nWaiting for server startup...")
stderr_lines = []
for _ in range(200):  # max 200 lines of stderr
    line = proc.stderr.readline()
    if not line:
        break
    stderr_lines.append(line.strip())
    if "ChromaDB cache" in line:
        print(f"  {line.strip()}")
    if "RAG server ready" in line:
        print("  Server ready!")
        break
    if "Error" in line or "Traceback" in line:
        print(f"  ERROR: {line.strip()}")
        proc.kill()
        sys.exit(1)

# Helper
def call_tool(name, args):
    proc.stdin.write(json.dumps({
        "jsonrpc": "2.0", "id": 99, "method": "tools/call",
        "params": {"name": name, "arguments": args}
    }) + "\n")
    proc.stdin.flush()
    return json.loads(json.loads(proc.stdout.readline())["result"]["content"][0]["text"])

# Test cases
tests = [
    ("How do I reset my password?", "general.md", "How to reset my password?"),
    ("I want to pay with Alipay", "billing.md", "payment methods"),
    ("I keep getting error 429", "api.md", "429"),
    ("My dashboard is slow", "troubleshooting.md", "dashboard"),
    ("怎么注册账号？", "general.md", "register"),
    ("CS-ERR-5001", "troubleshooting.md", "CS-ERR-5001"),
    ("what payment methods are accepted?", "billing.md", "payment methods"),
    ("how to get an API key?", "api.md", "API key"),
]

passed = 0
failed = 0

for query, expected_file, expected_keyword in tests:
    has_special = any(ch.isdigit() for ch in query) or "-" in query
    alpha = 0.5 if has_special else 0.3
    result = call_tool("search_knowledge_base", {"query": query, "top_k": 3, "alpha": alpha})
    top = result["results"][0]
    ok = expected_file in top["source"] and (expected_keyword.lower() in top["heading"].lower() or expected_keyword.lower() in top["text"].lower())
    status = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"  [{status}] {query[:50]:50s} → {top['source']:25s} | {top['heading'][:50]:50s} | score={top['score']:.4f}")

proc.terminate()
proc.wait(timeout=5)

print(f"\n{'=' * 60}")
print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
if failed == 0:
    print("ALL TESTS PASSED!")
else:
    print(f"{failed} TESTS FAILED!")
    sys.exit(1)
