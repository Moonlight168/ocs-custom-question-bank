"""
配置文件模块 - 从.env 文件加载模型配置
支持双模型验证机制：一个生成答案，一个验证答案
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ------------------------------------------------------------
# 火山方舟 API 配置
# ------------------------------------------------------------
# 主要 API Key（用于生成答案的模型）
ARK_API_KEY_GENERATOR = os.getenv("ARK_API_KEY_GENERATOR")
# 验证 API Key（用于验证答案的模型）
ARK_API_KEY_VERIFIER = os.getenv("ARK_API_KEY_VERIFIER")

# 如果只配置了单个 ARK_API_KEY，则两个模型共用
if not ARK_API_KEY_GENERATOR:
    ARK_API_KEY_GENERATOR = os.getenv("ARK_API_KEY")
if not ARK_API_KEY_VERIFIER:
    ARK_API_KEY_VERIFIER = ARK_API_KEY_GENERATOR

# 模型名称配置
MODEL_NAME_GENERATOR = os.getenv("MODEL_NAME_GENERATOR", "doubao-seed-1-6-flash-250828")
MODEL_NAME_VERIFIER = os.getenv("MODEL_NAME_VERIFIER", "doubao-seed-1-6-flash-250828")

# API 基础 URL
ARK_BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

# ------------------------------------------------------------
# 应用配置
# ------------------------------------------------------------
CACHE_FILE = os.getenv("CACHE_FILE", "cache.json")
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")

# ------------------------------------------------------------
# 双模型验证配置
# ------------------------------------------------------------
# 是否启用双模型验证（默认启用）
ENABLE_DUAL_MODEL_VERIFICATION = os.getenv("ENABLE_DUAL_MODEL_VERIFICATION", "true").lower() == "true"
# 当两个模型答案不一致时的最大重试次数
MAX_VERIFICATION_RETRIES = int(os.getenv("MAX_VERIFICATION_RETRIES", "2"))
