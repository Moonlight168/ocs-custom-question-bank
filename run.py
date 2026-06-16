"""Entry point: launch the OCS API server via package import.

Packaging this file with PyInstaller (instead of src/server.py directly) keeps
src/ as a proper package, so internal imports like `from src.config import ...`
work in the frozen exe just like in dev.
"""
import argparse
import os
import sys

# Ensure project root is on sys.path so `from src.x import ...` resolves in
# both dev and frozen (PyInstaller) modes, regardless of working directory.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.config import SERVER_PORT
from src.server import app


def main():
    parser = argparse.ArgumentParser(description="OCS 自动答题 API 服务")
    parser.add_argument(
        "--port", type=int, default=SERVER_PORT,
        help=f"监听端口（默认 {SERVER_PORT}，可通过 SERVER_PORT 环境变量配置）",
    )
    parser.add_argument("--host", default="0.0.0.0", help="绑定地址（默认 0.0.0.0）")
    args = parser.parse_args()

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, reload=False, access_log=False)


if __name__ == "__main__":
    main()
