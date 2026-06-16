import os
import json
import re
import logging
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

from src.config import (
    ARK_API_KEY_GENERATOR,
    MODEL_NAME_GENERATOR,
    ARK_BASE_URL,
    LOG_LEVEL,
    ENABLE_THINKING,
    THINKING_EFFORT,
)

# ------------------------------------------------------------
# 1. 初始化日志系统
# ------------------------------------------------------------
# 获取项目根目录（src 的父目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.DEBUG),
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(),  # 控制台输出
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),  # 文件输出
    ],
)
# Third-party libs that spam DEBUG/INFO under a permissive root logger
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.WARNING)
# uvicorn has its own access log; silence it (our own logger.info already logs requests)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logger = logging.getLogger("OCS-API")

logger.info("🚀 日志系统已初始化")

# ------------------------------------------------------------
# 2. 启动校验
# ------------------------------------------------------------
if not ARK_API_KEY_GENERATOR:
    logger.critical("❌ ARK_API_KEY_GENERATOR 未配置（请在 .env 中设置）")
    raise ValueError("缺少 ARK_API_KEY_GENERATOR")

if not MODEL_NAME_GENERATOR:
    logger.critical("❌ MODEL_NAME_GENERATOR 未配置（请在 .env 中设置）")
    raise ValueError("缺少 MODEL_NAME_GENERATOR")

logger.info(f"✅ 生成模型：{MODEL_NAME_GENERATOR}")
logger.info(f"✅ Base URL：{ARK_BASE_URL}")
logger.info(f"✅ 深度思考：{'开启' if ENABLE_THINKING else '关闭'} (effort={THINKING_EFFORT})")

# ------------------------------------------------------------
# 3. 初始化 OpenAI 兼容客户端（火山方舟 / DeepSeek / 其他 OpenAI 协议服务）
# ------------------------------------------------------------
# 使用 OpenAI SDK + 火山方舟 base_url，火山方舟官方完全支持 OpenAI 兼容协议
# - 豆包系列（doubao-*）: https://ark.cn-beijing.volces.com/api/v3
# - DeepSeek 系列（deepseek-*）: https://ark.cn-beijing.volces.com/api/v3 (通过接入点 ep-xxx)
# - DeepSeek 官方: https://api.deepseek.com
# 好处：统一 /chat/completions 端点，第三方模型和豆包共用一套代码
client_generator = OpenAI(api_key=ARK_API_KEY_GENERATOR, base_url=ARK_BASE_URL)
logger.info("✅ OpenAI 兼容客户端初始化成功")

# ------------------------------------------------------------
# 4. 工具函数
# ------------------------------------------------------------
def normalize_options(options):
    if not options:
        return None

    # 如果是字符串，尝试解析 JSON
    if isinstance(options, str):
        try:
            parsed = json.loads(options)
            options = parsed
        except:
            # 普通换行分割
            return [o.strip() for o in options.split("\n") if o.strip()]

    # 如果是 dict
    if isinstance(options, dict):
        return [f"{k}. {v}" for k, v in options.items()]

    # 如果是 list
    if isinstance(options, list):
        return [str(o).strip() for o in options if str(o).strip()]

    # 其他类型
    return [str(options)]


def build_prompt(title: str, qtype: str, options=None) -> str:
    """
    精简版提示词生成函数，减少 tokens 消耗同时保持格式约束
    """
    # 多空题自动检测（兼容 OCS 4.0 前后两种占位符）：
    #   - __1__ / __2__ 编号式（4.0+，会在内部拆成 2 段，需合并）
    #   - ___ / ____    连续下划线式
    #   - （   ） / (   )  中文/英文空白括号式（最常见，4.0 之前）
    numbered = re.findall(r"__\d+__", title)
    plain_underscores = re.findall(r"_{3,}", title)
    blank_parens = re.findall(r"（\s*）|\(\s*\)", title)
    blank_count = len(numbered) + len(plain_underscores) + len(blank_parens)

    # 基础信息（精简题型说明）
    qtype_cn = (
        "单选 (仅 1 个)" if qtype == "single" else
        "多选 (可多个)" if qtype == "multiple" else
        "判断 (A=对, B=错)" if qtype == "judgement" else
        f"填空 (共 {blank_count} 空)" if blank_count >= 2 else
        "单选 (仅 1 个)"
    )
    prompt = f"题：{title}\n型：{qtype_cn}\n"

    # 优先级：多空填空 > 单空填空/简答 > 有 options 的单/多/判断
    # 关键：填空题即使 OCS 把用户已填答案塞进 options（仅 "A"/"B" 这种字母垃圾），
    # 也不能让 AI 误以为这是单选去选字母。
    is_completion = qtype == "completion" or blank_count >= 2

    if is_completion and blank_count >= 2:
        # 多空填空：忽略 options
        prompt += f"答：共 {blank_count} 个空，**用 # 分隔每个答案**（如 北京#长城#故宫），不要编号、不要标点、不要解释，按空出现的顺序输出"
    elif is_completion and qtype == "completion":
        # 显式 completion 但只有 1 个空 → 简洁文本
        prompt += "答：简洁答案（≤50 字），无解释/符号"
    elif options and isinstance(options, list) and options:
        opts_text = "\n".join([f"{chr(65+i)}. {opt.strip()}" for i, opt in enumerate(options)])
        prompt += f"选：\n{opts_text}\n"

        # 核心规则（合并条目，用短句强化关键约束）
        if qtype == "single":
            prompt += "答：仅 1 个大写字母（如 A），无其他字符/文字"
        elif qtype == "multiple":
            prompt += "答：多选项大写字母用#分隔（如 A#C），无其他字符/文字"
        elif qtype == "judgement":
            prompt += "答：仅输出一个字 —— 「对」或「错」（全角中文），无其他字符/文字"
        else:
            prompt += "答：仅输出选项字母或简洁答案，无多余内容"
    else:
        # 简答题 / 无选项场景（压缩字数）
        prompt += "答：简洁答案（≤50 字），无解释/符号"

    return prompt


def map_ai_answer_to_options(ai_answer: str, options: list[str]) -> str:
    """
    将 AI 返回的字母答案（如 "C#D"）映射到页面选项文字。

    :param ai_answer: AI 返回的答案，可能是 "C#D", "A", 或 "B#C#D"
    :param options: 页面选项文字列表，顺序对应 A/B/C/D
    :return: 用 # 拼接的文本答案，例如 "聚合#组合"
    """
    if not ai_answer or not options:
        return ai_answer  # 如果没有选项或答案，直接返回原始

    # 支持多选，用 # 分隔
    letters = [c for c in ai_answer.replace(" ", "").strip().lstrip("#").split("#") if c]
    mapped = []
    for letter in letters:
        idx = ord(letter.upper()) - ord("A")
        if 0 <= idx < len(options):
            mapped.append(options[idx])
        else:
            # 超出范围，保留原值
            mapped.append(letter)
    return "#".join(mapped)


def call_model(client: OpenAI, model_name: str, prompt: str) -> str:
    """调用单个模型生成答案，统一用 OpenAI 协议的 reasoning_effort 控制思考"""
    kwargs = {
        "model": model_name,
        "messages": [{"role": "system", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 150,
        "stop": ["。", "\n", ".", ","],
    }
    if ENABLE_THINKING:
        kwargs["reasoning_effort"] = THINKING_EFFORT
    completion = client.chat.completions.create(**kwargs)
    return str(completion.choices[0].message.content).strip()


# ------------------------------------------------------------
# 5. 获取 AI 答案（单模型）
# ------------------------------------------------------------
def get_ai_answer(title: str, qtype: str, options=None):
    prompt = build_prompt(title, qtype, options)
    try:
        logger.info(f"📝 模型 ({MODEL_NAME_GENERATOR}) 正在生成答案...")
        answer = call_model(client_generator, MODEL_NAME_GENERATOR, prompt)
        logger.info(f"   答案：{answer}")
        if qtype == "multiple":
            return map_ai_answer_to_options(answer, options)
        return answer
    except Exception as e:
        logger.exception(f"模型调用失败：{title}")
        raise


# ------------------------------------------------------------
# 6. FastAPI 初始化
# ------------------------------------------------------------
app = FastAPI(title="OCS 自动答题 API 服务", description="支持 OCS 脚本 + AI 答题")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------
# 7. 接口定义
# ------------------------------------------------------------
@app.get("/search")
async def search(
    title: str = Query(..., description="题目内容（必填）"),
    type: str = Query("single", description="题目类型（默认 single，可选 multi）"),
    options: str = Query(None, description="题目选项（多选时用\n分隔）"),
):
    logger.info(f"接收到查询：{title}")
    logger.debug(f"选项标准化前：\n{options}")
    opts = normalize_options(options)
    logger.debug(f"选项标准化后：{opts}")

    try:
        answer = get_ai_answer(title, type, opts)
        return {"code": 1, "results": [{"question": title, "answer": answer}]}
    except Exception as e:
        logger.error(f"获取答案失败：{title} → {e}")
        return {"code": 0, "msg": "获取答案失败，请稍后重试"}

# ------------------------------------------------------------
# 8. 启动入口
# ------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn  # noqa: F401  (kept for dev: `python src/server.py`)
    logger.info("🚀 FastAPI 服务启动中... 访问 http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False, access_log=False)
