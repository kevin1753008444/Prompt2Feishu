# 使用说明

Prompt2Feishu 是一个 **Claude Code 项目/插件**（技能 `/prompt2feishu` + `feishu_cli.py` +
OpenArt MCP 配置）。它跑在 Claude 的云端会话里，**手机端和 PC 端行为完全一致**——你打开的
是同一个云会话。

## 一、一次性准备（配好后长期有效）

在**环境配置**里（启动云会话时点云图标 → 编辑环境）设好两样东西：

1. **网络访问**：Network access 选 **Custom**，Allowed domains 加一行 `open.feishu.cn`
   （海外 Lark 再加 `open.larksuite.com`），并勾选保留默认包管理器列表。
2. **环境变量**（让每个新会话都自带飞书凭据，无需 `.env`）：
   ```
   FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
   FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   FEISHU_APP_TOKEN=QGFsbIh4MayB7vsjCjicZ8Trneb
   FEISHU_TABLE_ID=tbl4ViTShcnBmrW2
   ```
   `feishu_cli.py` 优先读真实环境变量，所以设好后开箱即用。

> GitHub 推送：需要在 https://github.com/apps/claude 把 Claude 的 GitHub App **安装**到
> `Prompt2Feishu` 仓库（仅「授权登录」不够，安装后才有写入/推送权限）。

## 二、日常使用（Prompt → 飞书）

1. 打开 **Claude Code**（网页 claude.ai/code，或手机 App 的 Code 部分），
   新建/进入一个绑定 **`Prompt2Feishu`** 仓库的会话。
2. 把刷到的 prompt **截图或文本粘进对话**，然后：
   - 直接说「把这个记录到我的多维表格」，或
   - 输入斜杠命令 **`/prompt2feishu`**。
3. Claude 会识别、抽取出结构化字段（标题 / 分类 / 提示词-英文 / 提示词-中文 / 评分 /
   备注 / 链接），**先列给你确认**。
4. 你确认（或让它改）后，它调用 `feishu_cli.py` 写入你的「提示词文档」表，并回报 record_id。
5. 如果这张图本身是你想存的**参考图**，告诉它「把这张图也存进相关图片」，它会一并上传到
   附件列。

就是这样——跟聊天一样，无需碰命令行。

## 三、字段说明（按你表的真实结构）

| 逻辑字段 | 表内列 | 类型 | 说明 |
|---|---|---|---|
| 标题 | 标题1 | 文本 | 一句话概括用途 |
| 分类 | 分类 | 单选 | 需为已存在选项（如「镜头」）；新选项建议先在表里建好 |
| 提示词-英文 | 提示词-英文 | 文本 | 英文正文 |
| 提示词-中文 | 提示词-中文 | 文本 | 中文正文（缺哪侧会翻译补全）|
| 评分 | 评分 | **多选** | 只有你明确给出时才填 |
| 备注 | 备注 | 文本 | 来源、注意事项等 |
| 相关图片 | 相关图片 | 附件 | `--media 相关图片=路径` 上传 |
| 相关视频 | 相关视频 | 附件 | `--media 相关视频=路径` 上传 |
| 链接 | 链接 | URL | 原始出处链接 |

> 若以后改了表结构，跑 `python feishu_cli.py list-fields` 核对，并同步改
> `config/field_map.json`。

## 四、手动用 CLI（可选，排查用）

```bash
python feishu_cli.py test          # 连通性自检
python feishu_cli.py list-fields   # 查看字段与类型
python feishu_cli.py add-record --dry-run --data '{"标题":"x"}'   # 不联网预览
python feishu_cli.py add-record --data '{"标题":"x","链接":"https://..."}'
python feishu_cli.py add-record --data '{"标题":"参考镜头"}' --media 相关图片=scratch/a.png
```

## 五、路线图

- ✅ 阶段一：Prompt → 飞书（已完成，联调通过）
- ⏳ 阶段二：OpenArt → 飞书（用 OpenArt MCP 生成图/视频，一键把结果 + prompt + 参考图
  回填多维表格）。使用时需在会话里启用 **OpenArt** 连接器（MCP 连接器是按会话启用的）。
