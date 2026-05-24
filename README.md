# 📄 简历智能解析与岗位匹配系统

一个基于 **阿里云函数计算** 的无服务器简历解析与岗位匹配应用，支持 PDF 简历上传、AI 信息提取、岗位匹配评分及结果缓存。前端轻量页面部署于 **GitHub Pages**，后端使用 **Python Flask** 并集成 **通义千问** 大模型。

---

## 🌟 功能模块

| 模块 | 说明 |
|------|------|
| **简历上传与解析** | 上传单页或多页 PDF 简历，自动提取文本并清洗 |
| **关键信息提取** | 利用大模型提取姓名、电话、邮箱、教育经历（多段、含学校/专业/起止时间）、项目经历（名称、时间、技术栈、描述）等 |
| **岗位匹配评分** | 输入岗位描述，基于关键词规则或 AI 生成匹配度评分（技能匹配率、经验匹配度） |
| **结果缓存** | 对已处理的简历+岗位描述进行 Redis 缓存，避免重复计算（支持内存降级） |
| **前端交互页面** | 简洁的 Web 页面，上传简历、填写职位描述，即可实时查看解析结果与匹配分数 |

---

## 🛠️ 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| **后端运行时** | 阿里云函数计算 FC（Web函数 + Python 3.10） | 无服务器架构，免运维，按量付费 |
| **Web 框架** | Flask + flask-cors | 提供 RESTful API |
| **AI 模型** | 通义千问 (qwen-plus) via DashScope API | 简历实体抽取、岗位匹配评分 |
| **PDF 解析** | pdfplumber | 提取文本，兼容多页文档 |
| **缓存** | Redis（阿里云 Tair/Redis 标准版） | 基于简历内容哈希的缓存，TTL 1 小时 |
| **前端** | 原生 HTML/CSS/JavaScript | 无框架依赖，部署于 GitHub Pages |
| **跨域处理** | flask-cors | 允许前端页面跨域请求 API |
| **环境变量** | python-dotenv（本地）+ FC 环境变量（线上） | 安全存储 API Key 等敏感信息 |



## 🚀 部署方式

### 一、后端部署到阿里云函数计算（FC）

#### 1. 准备工作
- 开通 [阿里云函数计算](https://fc.console.aliyun.com/) 服务，创建 **Web 函数**。
- 获取 [通义千问 API Key](https://bailian.console.aliyun.com/)（DashScope）。
- （可选）开通 [阿里云 Redis](https://redis.console.aliyun.com/) 实例，记录内网地址和密码。

#### 2. 配置后端代码
- 确保 `backend/app.py` 中 Flask 实例监听 `0.0.0.0:5000`。
- 代码中使用 `requests` 直接调用 DashScope API（避免 `openai` 库与 FC 内置 `httpx` 冲突）。
- `config.py` 通过环境变量读取配置。

#### 3. 打包与上传
- 进入 `backend` 目录，将所有 `.py` 文件和 `requirements.txt` **直接** 压缩为 ZIP（不要包含文件夹本身，解压后根目录即为源码）。
- 在 FC 控制台创建 Web 函数：
  - 运行环境：`Python 3.10`（内置运行时）
  - 启动命令：`python app.py`
  - 监听端口：`5000`
  - 执行超时时间：`120 秒`（建议）
  - 上传 ZIP 包
- 配置 **环境变量**：

| 变量名 | 示例值 | 说明 |
|--------|--------|------|
| `AI_API_KEY` | `sk-xxxxxxxxxxxxx` | 通义千问 API Key |
| `AI_API_BASE` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | API 地址 |
| `AI_MODEL` | `qwen-plus` | 模型名称 |
| `REDIS_HOST` | `r-xxxxxx.redis.rds.aliyuncs.com` | Redis 内网地址（可选） |
| `REDIS_PORT` | `6379` | Redis 端口 |
| `REDIS_PASSWORD` | `your_password` | Redis 密码 |
| `CACHE_TTL` | `3600` | 缓存超时（秒） |

- 创建 HTTP 触发器，认证方式选择 **无需认证**，获得公网访问 URL（类似 `https://xxxxx.cn-hangzhou.fcapp.run`）。

#### 4. 安装依赖（若 ZIP 中未包含）
- 在函数详情页打开 **WebIDE**，进入终端，执行：
  ```bash
  pip install -r requirements.txt -t . --force-reinstall --no-cache-dir
📖 使用说明
打开前端页面（GitHub Pages 地址）。

点击 上传简历，选择一份 PDF 格式的简历文件。

（可选）在 岗位需求描述 文本框中输入招聘要求，支持任意自然语言描述。

点击 开始解析与匹配。

页面将显示：

✅ 基本信息：姓名、电话、邮箱、地址等。

✅ 教育经历：分条展示学校、专业、学位、起止年份。

✅ 项目经历：分条展示项目名称、时间、技术栈标签和描述。

✅ 匹配度评分：综合评分、技能匹配率、经验匹配度（若填写了岗位描述）。

再次提交相同简历和岗位描述时，结果将直接来自缓存（响应更快）。
🧪 本地开发
克隆项目并进入 backend 目录：

bash
git clone https://github.com/你的用户名/resume-matcher.git
cd resume-matcher/backend
创建虚拟环境并安装依赖：

bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
在 backend 目录下创建 .env 文件，填入必要的环境变量（参照上述表格）。

启动后端：

bash
python app.py
打开 front/index.html 即可本地测试（需自行解决跨域，或使用 Live Server）。

📄 许可
本项目仅用于学习与交流，使用通义千问 API 请遵守阿里云相关服务条款。
简历数据仅用于解析与匹配，不会持久化存储（缓存可配置清除）。
