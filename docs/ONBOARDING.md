# 开箱配置 Onboarding（分享给他人也照此做一遍）

本插件要打通三方：**Claude Code / Codex（agent）+ 飞书多维表格（CLI）+ OpenArt（MCP）**。
第一次用需要配好下面几项；配完就长期有效，之后手机/电脑任意会话直接用。

## 1. 环境网络白名单（Network access）
云会话默认只允许部分域名，本插件要直连的域名需手动放行：
启动云会话处点云图标 → 编辑环境 → **Network access** 选 **Custom** → **Allowed domains** 逐行加：

```
open.feishu.cn        # 飞书 API（写记录 + 上传附件）；海外 Lark 用 open.larksuite.com
cdn.openart.ai        # OpenArt 生成结果所在，回填飞书时要下载
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

## 自检
```
pip install -r requirements.txt
python feishu_cli.py test          # 飞书鉴权 + 读字段
python feishu_cli.py list-fields   # 核对 config/field_map.json
```
两步通过即代表飞书侧就绪；OpenArt 侧用一次生成验证即可。
