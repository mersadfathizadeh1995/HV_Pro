"""Allow ``python -m hvsr_pro.packages.batch_processing.mcp`` to start the server."""

from .server import mcp

if __name__ == "__main__":
    mcp.run()
