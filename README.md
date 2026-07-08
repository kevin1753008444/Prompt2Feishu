# Prompt2Feishu

把刷到的**生图/生视频 prompt**（截图或长文本）快速交给 Claude Code / Codex，
自动识别、抽取成干净的结构化信息，一键写入你的**飞书多维表格**；
并可（第二阶段）接入 **OpenArt** 直接生成，把好的结果回填到同一张表。

## 为什么这么设计（MCP 还是 CLI？）

- **飞书 → 用自定义 CLI。** 官方飞书 MCP（`@larksuiteoapi/lark-mcp`）**不支持文件/媒体
  上传**，写不了「相关图片 / 相关视频」附件列，而这正是本需求的核心。所以飞书这一侧用一个
  轻量 Python CLI（`feishu_cli.py`）直接封装飞书 OpenAPI，既能写记录、又能传图/传视频，
  Claude Code 和 Codex 都能直接调。
- **OpenArt → 用现成 MCP。** OpenArt 已提供 MCP，直接接入即可（生图/生视频、查历史等）。

一个仓库同时打通：**agent（Claude Code / Codex）+ 飞书（CLI）+ OpenArt（MCP）**。

## 目录结构

```
feishu_cli.py                    # 核心 CLI：鉴权 / 读字段 / 上传媒体 / 写记录
config/field_map.json            # 逻辑字段 -> 表内真实列名 的映射（按需修改）
docs/SETUP_FEISHU.md             # 飞书接入分步指南（创建应用、权限、拿 token）
.env.example                     # 需要的四个环境变量
.claude/skills/prompt2feishu/    # Claude Code skill：截图/文本 -> 结构化字段 -> 写入
.claude/commands/prompt2feishu.md# /prompt2feishu 斜杠命令
.mcp.json                        # OpenArt MCP 配置（便于移植接入）
```

## 快速开始

1. 安装依赖并配置飞书凭据（详见 [docs/SETUP_FEISHU.md](docs/SETUP_FEISHU.md)）：
   ```bash
   pip install -r requirements.txt
   cp .env.example .env    # 填入 App ID/Secret、app_token、table_id
   python feishu_cli.py test          # 连通性自检
   python feishu_cli.py list-fields   # 核对字段映射
   ```
2. 在 Claude Code 里，粘贴一张 prompt 截图或文本，运行 `/prompt2feishu`，
   确认抽取结果后即写入多维表格。

## CLI 用法

```bash
# 连通性自检（打印表名 + 字段列表）
python feishu_cli.py test

# 列出目标表所有字段与类型
python feishu_cli.py list-fields

# 不联网预览映射结果（自检字段结构）
python feishu_cli.py add-record --dry-run \
  --data '{"标题":"苹果广告电影感镜头","分类":"镜头","提示词-英文":"Shot with ARRI Alexa 35...","提示词-中文":"苹果广告美学，电影感微冷..."}'

# 正式写入一条记录
python feishu_cli.py add-record \
  --data '{"标题":"苹果广告电影感镜头","提示词-英文":"...","提示词-中文":"...","链接":"https://x.com/..."}'

# 带附件写入（图片进「相关图片」，视频进「相关视频」）
python feishu_cli.py add-record \
  --data '{"标题":"参考镜头"}' \
  --media 相关图片=scratch/ref1.png \
  --media 相关视频=scratch/clip.mp4

# 只上传一个媒体、拿 file_token
python feishu_cli.py upload-media scratch/ref1.png
```

## 路线图

- [x] **阶段一：Prompt → 飞书**（截图/文本识别抽取 + 写记录 + 附件上传）
- [x] **阶段二：OpenArt → 飞书**（用 OpenArt MCP 生成，按需把结果图/视频 + prompt + 参考图
      回填多维表格；`feishu_cli.py` 的 `--media` 已支持直接传 URL；命令 `/openart2feishu`）
- [ ] 阶段三（可选）：解析 X / YouTube / Instagram 链接里的 prompt 与媒体

> 附件可传 URL：`python feishu_cli.py add-record --data '{"标题":"x"}' --media 相关图片=https://.../out.png`
> （容器内下载受网络白名单限制；若 OpenArt 结果域名未放行，加进环境 Allowed domains 即可。）

## 安全

`.env` 已被 `.gitignore` 忽略，密钥不会进仓库。请勿把 App Secret 写入代码或提交历史。
