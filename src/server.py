import os
import json
import re
import hashlib
import logging
from datetime import datetime
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from volcenginesdkarkruntime import Ark
from fastapi import Request

from .config import (
    ARK_API_KEY_GENERATOR,
    ARK_API_KEY_VERIFIER,
    MODEL_NAME_GENERATOR,
    MODEL_NAME_VERIFIER,
    ARK_BASE_URL,
    CACHE_FILE,
    LOG_LEVEL,
    ENABLE_DUAL_MODEL_VERIFICATION,
    MAX_VERIFICATION_RETRIES,
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
logger = logging.getLogger("OCS-API")

logger.info("🚀 日志系统已初始化")

# ------------------------------------------------------------
# 2. 验证 API Key 配置
# ------------------------------------------------------------
if not ARK_API_KEY_GENERATOR:
    logger.critical("❌ 未检测到 ARK_API_KEY_GENERATOR，请在 .env 文件中配置")
    raise ValueError("❌ 请在项目根目录的 .env 文件中配置 ARK_API_KEY_GENERATOR")

logger.info(f"✅ 生成模型：{MODEL_NAME_GENERATOR}")
logger.info(f"✅ 验证模型：{MODEL_NAME_VERIFIER}")
logger.info(f"✅ 双模型验证：{'已启用' if ENABLE_DUAL_MODEL_VERIFICATION else '已禁用'}")

# ------------------------------------------------------------
# 3. 初始化缓存
# ------------------------------------------------------------
CACHE_FILE = os.path.join(BASE_DIR, CACHE_FILE)
if not os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)

try:
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        cache = json.load(f)
except json.JSONDecodeError:
    cache = {}
    logger.warning("⚠️ cache.json 格式错误，已重置为空缓存。")

def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

# ------------------------------------------------------------
# 4. 缓存 Key 工具函数
# ------------------------------------------------------------
def normalize_text(text: str) -> str:
    """去除空白和符号差异"""
    if not text:
        return ""
    text = re.sub(r"\s+", "", text)
    text = text.replace("．", ".").replace("。", ".")
    text = text.replace("，", ",").replace("：", ":")
    return text.strip()

def make_cache_key(title: str, qtype: str, options=None) -> str:
    """生成稳定的 MD5 缓存 Key"""
    norm_title = normalize_text(title)
    norm_qtype = qtype.strip().lower() if qtype else "single"
    norm_opts = [normalize_text(opt) for opt in (options or [])]
    data = f"{norm_title}|{norm_qtype}|{'|'.join(norm_opts)}"
    return hashlib.md5(data.encode("utf-8")).hexdigest()

# ------------------------------------------------------------
# 5. 统一格式化选项
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

# ------------------------------------------------------------
# 6. 初始化火山方舟客户端
# ------------------------------------------------------------
client_generator = Ark(api_key=ARK_API_KEY_GENERATOR, base_url=ARK_BASE_URL)
client_verifier = Ark(api_key=ARK_API_KEY_VERIFIER, base_url=ARK_BASE_URL)
logger.info("✅ 火山方舟 SDK 初始化成功（生成模型 + 验证模型）")

# ------------------------------------------------------------
# 7. 构建 Prompt
# ------------------------------------------------------------
def build_prompt(title: str, qtype: str, options=None) -> str:
    """
    精简版提示词生成函数，减少 tokens 消耗同时保持格式约束
    """
    # 基础信息（精简题型说明）
    qtype_cn = "单选 (仅 1 个)" if qtype == "single" else "多选 (可多个)"
    prompt = f"题：{title}\n型：{qtype_cn}\n"

    # 处理选项（保留字母标识核心功能）
    if options and isinstance(options, list) and options:
        opts_text = "\n".join([f"{chr(65+i)}. {opt.strip()}" for i, opt in enumerate(options)])
        prompt += f"选：\n{opts_text}\n"

        # 核心规则（合并条目，用短句强化关键约束）
        if qtype == "single":
            prompt += "答：仅 1 个大写字母（如 A），无其他字符/文字"
        elif qtype == "multiple":
            prompt += "答：多选项大写字母用#分隔（如 A#C），无其他字符/文字"
        else:
            prompt += "答：仅输出选项字母或简洁答案，无多余内容"
    else:
        # 无选项场景（压缩字数）
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
    letters = ai_answer.replace(" ", "").split("#")
    mapped = []
    for letter in letters:
        idx = ord(letter.upper()) - ord("A")
        if 0 <= idx < len(options):
            mapped.append(options[idx])
        else:
            # 超出范围，保留原值
            mapped.append(letter)
    return "#".join(mapped)


# ------------------------------------------------------------
# 8. 单模型调用工具函数
# ------------------------------------------------------------
def call_model(client: Ark, model_name: str, prompt: str) -> str:
    """
    调用单个模型生成答案
    """
    completion = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "system", "content": prompt}],
        temperature=0.0,
        max_tokens=50,
        stop=["。", "\n"],
        thinking={"type": "disabled"},
    )
    return str(completion.choices[0].message.content).strip()


def normalize_answer(answer: str) -> str:
    """
    标准化答案以便比较
    """
    # 去除空格，转大写
    answer = answer.replace(" ", "").upper()
    # 排序选项（用于多选题比较）
    if "#" in answer:
        parts = sorted(answer.split("#"))
        return "#".join(parts)
    return answer


def answers_match(answer1: str, answer2: str) -> bool:
    """
    比较两个答案是否一致（忽略顺序和格式差异）
    """
    return normalize_answer(answer1) == normalize_answer(answer2)


# ------------------------------------------------------------
# 9. 获取 AI 答案（含双模型验证 + 缓存 + 日志）
# ------------------------------------------------------------
def get_ai_answer(title: str, qtype: str, options=None):
    key = make_cache_key(title, qtype, options)

    if key in cache:
        logger.info(f"缓存命中：{title}")
        cached_answer = cache[key]["answer"]
        if options:
            return map_ai_answer_to_options(cached_answer, options)
        return cached_answer

    prompt = build_prompt(title, qtype, options)

    try:
        # 步骤 1: 生成模型生成答案
        logger.info(f"📝 生成模型 ({MODEL_NAME_GENERATOR}) 正在生成答案...")
        generated_answer = call_model(client_generator, MODEL_NAME_GENERATOR, prompt)
        logger.info(f"   生成答案：{generated_answer}")

        # 步骤 2: 验证模型验证答案（如果启用）
        if ENABLE_DUAL_MODEL_VERIFICATION:
            logger.info(f"🔍 验证模型 ({MODEL_NAME_VERIFIER}) 正在验证答案...")
            verified_answer = call_model(client_verifier, MODEL_NAME_VERIFIER, prompt)
            logger.info(f"   验证答案：{verified_answer}")

            # 步骤 3: 比较答案
            if answers_match(generated_answer, verified_answer):
                logger.info(f"✅ 双模型验证通过：答案一致")
                final_answer = generated_answer
            else:
                logger.warning(f"⚠️ 双模型验证不一致，尝试重试...")
                # 重试机制
                retry_count = 0
                verified = False
                while retry_count < MAX_VERIFICATION_RETRIES and not verified:
                    retry_count += 1
                    logger.info(f"   第 {retry_count} 次重试验证...")
                    verified_answer = call_model(client_verifier, MODEL_NAME_VERIFIER, prompt)
                    if answers_match(generated_answer, verified_answer):
                        verified = True
                        logger.info(f"✅ 第 {retry_count} 次重试验证通过")
                        final_answer = generated_answer
                    else:
                        logger.warning(f"   第 {retry_count} 次重试验证仍不一致")

                if not verified:
                    # 重试后仍不一致，使用生成模型的答案并记录警告
                    logger.warning(f"⚠️ 重试 {MAX_VERIFICATION_RETRIES} 次后仍不一致，使用生成模型答案")
                    final_answer = generated_answer
        else:
            logger.info(f"ℹ️ 双模型验证已禁用，直接使用生成模型答案")
            final_answer = generated_answer

        # 保存到缓存
        cache[key] = {
            "title": title,
            "type": qtype,
            "options": options,
            "answer": final_answer,
            "time": datetime.now().isoformat(timespec="seconds"),
        }
        save_cache()
        logger.info(f"新答案已缓存：{title} → {final_answer}")

        # 将 AI 返回的答案映射到选项文字
        if qtype == "multiple":
            return map_ai_answer_to_options(final_answer, options)
        return final_answer

    except Exception as e:
        logger.exception(f"模型调用失败：{title}")
        raise e


# ------------------------------------------------------------
# 10. FastAPI 初始化
# ------------------------------------------------------------
app = FastAPI(title="OCS 自动答题 API 服务", description="支持 OCS 脚本 + AI 答题 + 缓存 + 双模型验证")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------
# 11. 接口定义
# ------------------------------------------------------------
@app.get("/search")
async def search (
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
        return {"code": 0, "msg": f"获取答案失败：{str(e)}"}

# ------------------------------------------------------------
# 12. 启动入口
# ------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 FastAPI 服务启动中... 访问 http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
