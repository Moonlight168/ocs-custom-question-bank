"""配置文件 - 从 .env 加载模型与 API 配置"""

import os
from dotenv import load_dotenv

load_dotenv()

# 生成模型 API Key（必填）
ARK_API_KEY_GENERATOR = os.getenv("ARK_API_KEY_GENERATOR")

# 生成模型名称（必填）
MODEL_NAME_GENERATOR = os.getenv("MODEL_NAME_GENERATOR")

# API 基础 URL（OpenAI 兼容协议，默认火山方舟）
ARK_BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

# 日志级别
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")

# 服务监听端口（默认 8086）
SERVER_PORT = int(os.getenv("SERVER_PORT", "8086"))

# 是否开启深度思考
ENABLE_THINKING = os.getenv("ENABLE_THINKING", "true").strip().lower() in ("true", "1", "yes", "on")

# 思考等级：low / medium / high
_VALID_EFFORTS = ("low", "medium", "high")
THINKING_EFFORT = os.getenv("THINKING_EFFORT", "high").strip().lower()
if THINKING_EFFORT not in _VALID_EFFORTS:
    raise ValueError(f"THINKING_EFFORT 必须是 {list(_VALID_EFFORTS)} 之一，当前: {THINKING_EFFORT!r}")
