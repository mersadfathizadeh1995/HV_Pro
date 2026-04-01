"""
Allow launching with ``python -m hvsr_pro.mcp`` or ``python -m hvsr_pro.mcp --transport http``.
"""
from hvsr_pro.mcp.server import mcp

if __name__ == "__main__":
    mcp.run()
