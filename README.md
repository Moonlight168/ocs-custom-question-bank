# OCS 自定义题库 API 服务

为 [OCSJS](https://github.com/ocsjs/ocsjs) 油猴刷题脚本提供高性能的自定义题库 API 服务，基于 FastAPI + OpenAI 兼容协议开发，**单模型直答**，覆盖单选 / 多选 / 判断 / 填空 / 简答全题型。

> 💡 **模型无关：** 通过 `base_url` 一键切换火山方舟豆包、DeepSeek、火山接入点或任何 OpenAI 兼容服务，无需改代码。

## 功能特性

- 🚀 **OCSJS 题库对接** - 兼容 `AnswererWrapper` 接口规范，开箱即用
- 🤖 **OpenAI 兼容协议** - 一份代码接豆包 / DeepSeek / 火山接入点 / 其他厂商
- 📝 **全题型覆盖** - 单选 / 多选 / 判断 / 填空 / 简答，每种题型独立 prompt 约束
- 🧠 **深度思考** - 豆包 `reasoning_effort`（low / medium / high）
- 📜 **生产级日志** - 控制台 + 文件双输出，按日轮转 30 天
- 📦 **单文件打包** - 一行命令生成无依赖的 `.exe`（含隔离 venv，~25 MB）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
copy .env.example .env   # Windows
# 或
cp .env.example .env     # Linux/Mac
```

最少必填两项：

```env
ARK_API_KEY_GENERATOR=your_api_key_here
MODEL_NAME_GENERATOR=doubao-seed-1-6-flash-250828
```

完整配置见文末 [环境变量](#环境变量)。

### 3. 启动服务

```bash
python run.py                  # 默认监听 0.0.0.0:8086
python run.py --port 9000      # 自定义端口
python run.py --host 127.0.0.1 # 仅本机访问
```

或开发模式（带热重载）：

```bash
uvicorn src.server:app --host 0.0.0.0 --port 8086 --reload
```

## OCSJS 对接配置

完整 OCSJS 题库配置见项目根目录的 [`ocsjs_answerer.json`](./ocsjs_answerer.json)，**复制其内容到 OCSJS 油猴脚本的"自定义题库"**即可。

要点：

- `type: "GM_xmlhttpRequest"` —— 跨 localhost 必须用油猴 API
- `homepage` 指向 FastAPI 自动文档（`http://localhost:8086/docs`）
- 油猴脚本头部 `@connect` 需包含 `localhost`，或安装 [OCS 全域名通用版](https://docs.ocsjs.com/docs/other/api#common-version)

### 支持的题型

| 题型 | OCS `type` | 答案格式 |
|------|-----------|---------|
| 单选 | `single` | 一个大写字母，如 `A` |
| 多选 | `multiple` | 多个字母用 `#` 分隔，如 `A#C` |
| 判断 | `judgement` | `对` / `错`（OCS 按词表匹配） |
| 填空 | `completion` 或含 `__N__` / `（   ）` 占位符 | **多空用 `#` 分隔**，如 `北京#长城#故宫` |
| 简答 | （OCS 不一定传 type） | 纯文本 |

> 多空答案中 `#` 是 OCS 默认分隔符（OCS 还会按 `===` `---` `###` `|` `;` `；` 优先级回退）。

## 接口规范

### `GET /search`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 是 | 题目内容（含 OCS 占位符） |
| `type` | string | 否 | `single` / `multiple` / `judgement` / `completion`，缺省走启发式判断 |
| `options` | string | 否 | 选项内容，OCS 用 `\n` 分隔 |

**成功响应：**

```json
{
  "code": 1,
  "results": [
    { "question": "题目内容", "answer": "正确答案" }
  ]
}
```

**失败响应：**

```json
{ "code": 0, "msg": "错误信息" }
```

**示例：**

```bash
curl "http://localhost:8086/search?title=什么是光合作用？&type=single&options=A.%20植物制造养分%0AB.%20动物消化%0AC.%20细胞分裂"
```

## 模型服务商切换

通过 `ARK_BASE_URL` + `MODEL_NAME_GENERATOR` 切换，无需改任何代码：

| 服务商 | `ARK_BASE_URL` | `MODEL_NAME_GENERATOR` 示例 |
|--------|----------------|-----------------------------|
| 火山方舟（豆包） | `https://ark.cn-beijing.volces.com/api/v3` | `doubao-seed-1-6-flash-250828` |
| 火山方舟（第三方接入点） | `https://ark.cn-beijing.volces.com/api/v3` | `ep-20240101xxxxxx-xxxxx` |
| DeepSeek 官方 | `https://api.deepseek.com` | `deepseek-chat` / `deepseek-reasoner` |
| 其他 OpenAI 兼容 | 厂商提供的 URL | 厂商模型名 |

## 项目结构

```
local_api_ocs/
├── run.py                       # 入口（PyInstaller 也打这个）
├── ocsjs_answerer.json          # OCSJS 油猴脚本"自定义题库"配置
├── src/
│   ├── __init__.py
│   ├── server.py                # FastAPI 服务 + 题型 prompt 构建
│   └── config.py                # 环境变量加载
├── scripts/
│   └── package_project.bat      # 打包脚本（自动建 venv + 增量缓存 + 计时）
├── logs/                        # 日志目录（自动创建，按日轮转）
├── .env                         # 环境变量（不提交）
├── .env.example                 # 环境变量模板
├── requirements.txt
├── venv/                        # 打包时自动创建的隔离虚拟环境（不提交）
├── build/                       # PyInstaller 增量缓存（不提交）
└── dist/                        # 打包产物（不提交）
```

## 打包发布

```bash
scripts\package_project.bat
```

首次运行会自动：

1. 在 `venv/` 创建隔离虚拟环境（避免污染全局包）
2. 安装 `requirements.txt` + PyInstaller
3. 用 venv 里的 PyInstaller 打包（产物干净，~25 MB）

后续运行**复用 build/ 缓存**，通常 3–5 秒完成。

产物：`dist/DOUBAO_ASKED_QUICKLY.exe`

使用：把 `.env` 放在 `dist/` 同级目录后双击 exe；也可指定端口：`DOUBAO_ASKED_QUICKLY.exe --port 9000`

## 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `ARK_API_KEY_GENERATOR` | API Key | **必填** |
| `MODEL_NAME_GENERATOR` | 模型名称 | **必填** |
| `ARK_BASE_URL` | API 基础 URL | `https://ark.cn-beijing.volces.com/api/v3` |
| `SERVER_PORT` | 监听端口 | `8086` |
| `LOG_LEVEL` | 日志级别 | `DEBUG` |
| `ENABLE_THINKING` | 深度思考 | `true` |
| `THINKING_EFFORT` | 思考等级 low / medium / high | `high` |

## 开发与扩展

新增题型只需在 `src/server.py` 的 `build_prompt()` 加分支：

```python
elif qtype == "your_type":
    prompt += "答：你的格式约束"
```

新增日志过滤（如屏蔽某个第三方库）：

```python
logging.getLogger("your_lib").setLevel(logging.WARNING)
```

## 相关

- [OCSJS](https://github.com/ocsjs/ocsjs) - 目标油猴脚本
- [OCSJS 题库配置文档](https://docs.ocsjs.com/docs/other/api) - `AnswererWrapper` 接口规范
- [火山方舟](https://www.volcengine.com/product/ark) - 豆包大模型服务

## License

MIT