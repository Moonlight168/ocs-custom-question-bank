# OCS 自定义题库 API 服务

为 [OCSJS](https://github.com/ocsjs/ocsjs) 油猴刷题脚本提供自定义题库 API 服务，基于 FastAPI 开发，内置双模型验证机制提高答案准确性。

> 📌 **当前版本适配说明：** 已完整适配字节跳动火山方舟豆包系列大模型，支持单/双模型灵活配置。

## 功能特性

- 🚀 **OCSJS 题库对接** - 兼容 OCSJS 油猴脚本的题库 API 接口规范
- 🤖 **双模型验证** - 一个模型生成答案，另一个模型验证，确保答案准确性
- 💾 **智能缓存** - 自动缓存已答题目，减少 API 调用，提升响应速度
- 🔄 **重试机制** - 当双模型答案不一致时自动重试
- 📝 **支持多种题型** - 单选题、多选题、填空题等

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写火山方舟 API Key：

```bash
copy .env.example .env
```

编辑 `.env` 文件：

```env
# 生成模型 API Key（必填）
ARK_API_KEY_GENERATOR=your_api_key_here
# 验证模型 API Key（可选，默认与生成模型共用）
# ARK_API_KEY_VERIFIER=your_api_key_here
# 生成模型名称（默认：doubao-seed-1-6-flash-250828）
# MODEL_NAME_GENERATOR=doubao-seed-1-6-flash-250828
# 验证模型名称（可选，默认与生成模型相同）
# MODEL_NAME_VERIFIER=doubao-seed-1-6-flash-250828
```

### 3. 启动服务

```bash
# 从项目根目录启动
python src/server.py
```

或使用 uvicorn：

```bash
uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
```

## OCSJS 对接配置

### 1. 启动 API 服务

确保 API 服务在 `http://localhost:8000` 运行。

### 2. 配置 OCSJS 油猴脚本

在 OCSJS 油猴脚本的自定义题库设置中，配置 API 地址：

```
http://localhost:8000/search
```

### 3. 接口规范

API 遵循 OCSJS 题库接口规范：

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | 题目内容 |
| type | string | 否 | 题目类型：`single`（单选）或 `multiple`（多选） |
| options | string | 否 | 选项内容，多选时用 `\n` 分隔 |

**响应格式：**

成功响应（code=1）：
```json
{
  "code": 1,
  "results": [
    {
      "question": "题目内容",
      "answer": "正确答案"
    }
  ]
}
```

失败响应（code=0）：
```json
{
  "code": 0,
  "msg": "错误信息描述"
}
```

**示例请求：**

```bash
curl "http://localhost:8000/search?title=什么是光合作用？&type=single&options=A. 植物制造养分的过程\nB. 动物消化食物的过程\nC. 细胞分裂的过程"
```

## 双模型验证机制

1. **生成模型** 首先生成答案
2. **验证模型** 独立验证答案（可配置为与生成模型相同或不同）
3. **答案一致** → 直接返回
4. **答案不一致** → 自动重试（最多 2 次，可配置）
5. **重试仍不一致** → 使用生成模型答案并记录警告
6. **可配置开关**：可通过 `ENABLE_DUAL_MODEL_VERIFICATION` 关闭验证，直接使用单模型

## 项目结构

```
local_api_ocs/
├── src/
│   ├── __init__.py
│   ├── server.py          # FastAPI API 服务主程序
│   └── config.py          # 双模型配置模块
├── tests/                 # pytest 测试文件
├── scripts/               # 工具脚本
│   └── package_project.bat # PyInstaller 打包脚本
├── logs/                  # 日志目录（自动创建，每日轮转）
├── cache.json             # 答案缓存（自动创建，持久化存储）
├── .env                   # 环境变量（不提交到仓库）
├── .env.example           # 环境变量模板
├── requirements.txt       # 生产依赖
└── requirements-dev.txt   # 开发依赖
```

## 开发

### 安装开发依赖

```bash
pip install -r requirements-dev.txt
```

### 运行测试

```bash
pytest tests/
```

## 打包发布

将项目打包为单个可执行文件：

```bash
# 运行打包脚本
scripts/package_project.bat
```

打包完成后，可执行文件位于 `dist/` 目录。

## 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| ARK_API_KEY_GENERATOR | 生成模型 API Key（火山方舟） | 必填 |
| ARK_API_KEY_VERIFIER | 验证模型 API Key | 同 ARK_API_KEY_GENERATOR |
| MODEL_NAME_GENERATOR | 生成模型名称 | doubao-seed-1-6-flash-250828 |
| MODEL_NAME_VERIFIER | 验证模型名称 | 同 MODEL_NAME_GENERATOR |
| ARK_BASE_URL | API 基础 URL | https://ark.cn-beijing.volces.com/api/v3 |
| CACHE_FILE | 缓存文件路径 | cache.json |
| LOG_LEVEL | 日志级别 | DEBUG |
| ENABLE_DUAL_MODEL_VERIFICATION | 启用双模型验证 | true |
| MAX_VERIFICATION_RETRIES | 答案不一致最大重试次数 | 2 |

## 相关项目

- [OCSJS](https://github.com/ocsjs/ocsjs) - 油猴刷题脚本，支持超星、智慧树等平台

## License

MIT
