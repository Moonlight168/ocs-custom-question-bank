# OCS 自定义题库 API 服务

为 [OCSJS](https://github.com/ocsjs/ocsjs) 油猴刷题脚本提供自定义题库 API 服务，基于 FastAPI + 火山方舟 / DeepSeek / 其他 OpenAI 兼容协议。

> 📌 **单模型架构：** 一个模型生成答案，OpenAI SDK 通过 `base_url` 切换服务商（火山方舟豆包、DeepSeek、第三方接入点等）。

## 功能特性

- 🚀 **OCSJS 题库对接** - 兼容 OCSJS 油猴脚本的题库 API 接口规范
- 🤖 **OpenAI 兼容协议** - 一个 SDK 切换任意 OpenAI 协议服务（豆包 / DeepSeek / 火山接入点）
- 🧠 **深度思考** - 支持豆包 `reasoning_effort`（low / medium / high）
- 📝 **支持多种题型** - 单选题、多选题
- 📜 **生产级日志** - 控制台 + 文件双输出，按日写入 `logs/`
- 📦 **单文件打包** - 一行命令生成无依赖的 `.exe`

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写真实值：

```bash
copy .env.example .env
```

最少必填两项：

```env
ARK_API_KEY_GENERATOR=your_api_key_here
MODEL_NAME_GENERATOR=doubao-seed-1-6-flash-250828
```

可选：

```env
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3   # 默认火山方舟
LOG_LEVEL=DEBUG                                          # 日志级别
SERVER_PORT=8086                                         # 监听端口
ENABLE_THINKING=true                                     # 深度思考
THINKING_EFFORT=high                                     # low / medium / high
```

### 3. 启动服务

```bash
python run.py            # 默认 8086
python run.py --port 9000 # 自定义端口
```

或开发模式：

```bash
uvicorn src.server:app --host 0.0.0.0 --port 8086 --reload
```

## OCSJS 对接配置

API 默认在 `http://localhost:8086` 监听。完整 OCSJS 题库配置见项目根目录的 [`ocsjs_answerer.json`](./ocsjs_answerer.json)，直接复制其内容到 OCSJS 油猴脚本的"自定义题库"中即可。

支持 4 种题型：

| 题型 | OCS `type` | 答案格式 |
|------|-----------|---------|
| 单选 | `single` | 一个大写字母，如 `A` |
| 多选 | `multiple` | 多个字母用 `#` 分隔，如 `A#C` |
| 判断 | `judgement` | `A`（对）或 `B`（错） |
| 填空 | `completion` / 含 `__N__` 占位符 | **多行字符串**，每行一个答案，如 `"北京\n长城\n故宫"` |
| 简答 | （OCS 不一定传 type） | 纯文本 |

> 端口需要与 `.env` 中的 `SERVER_PORT` 保持一致（默认 8086）。

## 接口规范

### `GET /search`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | 题目内容 |
| type | string | 否 | `single`（单选，默认） / `multiple`（多选） |
| options | string | 否 | 选项内容，多选时用 `\n` 分隔 |

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
curl "http://localhost:8086/search?title=什么是光合作用？&type=single&options=A.%20植物制造养分的过程%0AB.%20动物消化食物的过程%0AC.%20细胞分裂的过程"
```

## 模型服务商切换

通过 `ARK_BASE_URL` + `MODEL_NAME_GENERATOR` 切换：

| 服务商 | `ARK_BASE_URL` | `MODEL_NAME_GENERATOR` 示例 |
|--------|----------------|-----------------------------|
| 火山方舟（豆包） | `https://ark.cn-beijing.volces.com/api/v3` | `doubao-seed-1-6-flash-250828` |
| 火山方舟（第三方接入点） | `https://ark.cn-beijing.volces.com/api/v3` | `ep-20240101xxxxxx-xxxxx` |
| DeepSeek 官方 | `https://api.deepseek.com` | `deepseek-chat` / `deepseek-reasoner` |
| 其他 OpenAI 兼容 | 厂商提供的 URL | 厂商模型名 |

> 不需要换 SDK 代码——`base_url` 一键切换。

## 项目结构

```
local_api_ocs/
├── run.py                # 入口脚本（PyInstaller 也打这个）
├── src/
│   ├── __init__.py
│   ├── server.py         # FastAPI 服务
│   └── config.py         # 环境变量加载
├── scripts/
│   └── package_project.bat  # 打包脚本
├── logs/                 # 日志目录（自动创建）
├── .env                  # 环境变量（不提交）
├── .env.example          # 环境变量模板
├── requirements.txt
├── venv/                 # 打包时自动创建的虚拟环境（不提交）
├── build/                # PyInstaller 增量缓存（不提交）
└── dist/                 # 打包产物（不提交）
```

## 打包发布

```bash
scripts\package_project.bat
```

首次运行会：
1. 在 `venv/` 创建隔离虚拟环境
2. 安装 `requirements.txt` + PyInstaller
3. 清理上一次脏环境留下的 `build/` 缓存
4. 用 venv 里的 PyInstaller 打包

产物：`dist/DOUBAO_ASKED_QUICKLY.exe`（单文件，约 20–30 MB）。

> 把 `.env` 放在 `dist/` 同级目录后双击 exe 即可运行。也可 CLI 指定端口：`DOUBAO_ASKED_QUICKLY.exe --port 9000`

## 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `ARK_API_KEY_GENERATOR` | API Key | **必填** |
| `MODEL_NAME_GENERATOR` | 模型名称 | **必填** |
| `ARK_BASE_URL` | API 基础 URL | `https://ark.cn-beijing.volces.com/api/v3` |
| `LOG_LEVEL` | 日志级别 | `DEBUG` |
| `SERVER_PORT` | 监听端口 | `8086` |
| `ENABLE_THINKING` | 深度思考 | `true` |
| `THINKING_EFFORT` | 思考等级 low/medium/high | `high` |

## 相关

- [OCSJS](https://github.com/ocsjs/ocsjs) - 目标油猴脚本
- [火山方舟](https://www.volcengine.com/product/ark) - 豆包大模型服务
- [OpenAI 兼容协议](https://platform.openai.com/docs/api-reference) - API 规范

## License

MIT
