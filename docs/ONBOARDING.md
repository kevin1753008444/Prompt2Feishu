# 开箱配置 Onboarding（分享给他人也照此做一遍）

本插件要打通三方：**Claude Code / Codex（agent）+ 飞书多维表格（CLI）+ OpenArt（MCP）**。
第一次用需要配好下面几项；配完就长期有效，之后手机/电脑任意会话直接用。

## 1. 环境网络白名单（Network access）
云会话默认只允许部分域名，本插件要直连的域名需手动放行：
启动云会话处点云图标 → 编辑环境 → **Network access** 选 **Custom** → **Allowed domains** 逐行加：

```
open.feishu.cn        # 飞书 API（写记录 + 上传附件）；海外 Lark 用 open.larksuite.com
cdn.openart.ai        # OpenArt 生成结果所在，回填飞书时要下载
catbox.moe            # 默认参考图图床（免注册）；若只用 GitHub 兜底则可不加
files.catbox.moe      # catbox 直链域名
```
并勾选 **“Also include default list of common package managers”**（保留默认，含 GitHub、
`raw.githubusercontent.com`、pip 等）。`raw.githubusercontent.com` 用于把粘贴的参考图发布成
公网 URL 喂给 OpenArt，已在默认列表里，无需另加。

## 2. 环境变量（飞书凭据）
在同一环境配置的 **Environment variables** 里加（这样每个新会话自带、无需 `.env`）：
```
FEISHU_APP_ID=cli_xxxxxxxx
FEISHU_APP_SECRET=xxxxxxxx
FEISHU_APP_TOKEN=<多维表格 URL 里 /base/ 后那段>
FEISHU_TABLE_ID=<URL 里 table= 后那段>
```
飞书应用怎么建、权限怎么开、如何把应用加为表格协作者：见 [SETUP_FEISHU.md](SETUP_FEISHU.md)。

## 3. GitHub App（用于推代码/发布参考图 URL）
到 https://github.com/apps/claude **Install** 到目标仓库（仅“Authorize 登录”不够，
Install 后才有 contents 写权限，push 才不 403）。

## 4. OpenArt 连接器
在会话里启用 **OpenArt** MCP 连接器（连接器是按会话/例程启用的）。首次可能要在
claude.ai 里授权 OpenArt 账号。

## 5. 减少每次的 Allow 弹窗
本仓库已带 `.claude/settings.json`，预先放行了 OpenArt 工具与本插件的 CLI/脚本命令，
常规操作不再逐次弹窗。若仍遇到新命令的弹窗，可把它追加进该文件的 `permissions.allow`。
> 注：像“允许云端访问 keychain”这类**系统级凭据弹窗**由平台控制，可能仍需首次手动确认一次，
> 不在仓库设置的可控范围内。

## 默认行为约定（重要，所有使用者请知悉）
- **prompt 一字不改**：默认直接使用你输入的 prompt 原文，**不优化、不扩写、不润色、不改语言**。
  只有当你**明确说**"帮我优化/扩写/翻译 prompt"时才修改。写入飞书时原文照存。
- **参考图直接粘贴**：参考图直接粘在对话里即可（无需上传卡片），插件会自动按**粘贴顺序**
  提取并发布成公网 URL 喂给 OpenArt。顺序即你粘贴的先后。
- **生成与写表分两步**：生成后先给你看结果；只有你明确说"存进多维表格"才写入。

## 参考图图床（默认外部免注册，GitHub 兜底）
参考图需要一个**临时公网 URL**（够 OpenArt 生成 + 飞书回填下载即可，之后可失效）。默认用
免注册图床 **catbox.moe**（无账号、无损存储），所以白名单需加一行 `catbox.moe`（见上）。
没有该域名或它不可用时，自动回退到 GitHub raw（需已装 GitHub App）。切换见
`tools/publish_refs.py --host catbox|github`。

## 自检
```
pip install -r requirements.txt
python feishu_cli.py test          # 飞书鉴权 + 读字段
python feishu_cli.py list-fields   # 核对 config/field_map.json
```
两步通过即代表飞书侧就绪；OpenArt 侧用一次生成验证即可。
