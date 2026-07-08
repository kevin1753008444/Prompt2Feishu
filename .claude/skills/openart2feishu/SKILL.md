---
name: openart2feishu
description: 用 OpenArt 生成图片/视频，并在用户要求时把生成结果连同参考图与 prompt 一起写入飞书多维表格。当用户给出 prompt（可含参考图）想用 OpenArt 生成、或说“把这个结果存进多维表格/记录下来”时使用。
---

# OpenArt 生成 → 飞书多维表格

用 OpenArt MCP 生成图/视频，然后（在用户确认时）把 **结果 + 参考图 + prompt** 回填到飞书表。
写入走本仓库的 `feishu_cli.py`，附件支持直接传 URL。

## A. 生成阶段（OpenArt MCP）

1. 读需求：用户给的 prompt（中/英均可）+ 可选参考图。
2. 选模型/模式：`openart_model_list` 挑合适模型；有参考图用 `image2image`（图）或
   `image2video/element2video`（视频），纯文字用 `text2image/text2video`。
3. `openart_model_form_get(model, mode)` 拿参数 schema，再调
   `openart_generate_image` / `openart_generate_video`。
4. **本环境是 CLI 文本宿主**：generate 返回 `historyId` 后，调
   `openart_creation_wait(historyId)` 直到完成（视频可能要多次 wait）。
5. 从完成结果里取出**结果媒体的 URL**（图片/视频直链），记下来备用。

> 参考图来源：若用户提供的是可访问的**图片 URL**，可直接作为 OpenArt 的
> `visualReferences[].url`，也可直接写进飞书附件。若用户是在会话里贴的本地图片，
> 先落到 `scratch/` 再用。

## B. 回填阶段（在用户明确要求时才写）

用户说“存进多维表格 / 记录一下”后：

1. 组织字段：`标题`（一句话概括）、`提示词-英文`/`提示词-中文`（本次生成用的 prompt，
   缺侧翻译补全）、`分类`（如“生成/镜头”，需为已有选项，否则留空）、`备注`
   （模型名、参数、来源等）。
2. 附件：
   - 生成结果 → 写进 `相关图片`（图）或 `相关视频`（视频）；
   - 参考图 → 也写进 `相关图片`（同一列可放多张，多次 `--media 相关图片=...`）。
3. 调 CLI（附件可直接给 URL）：
   ```bash
   python feishu_cli.py add-record \
     --data '{"标题":"...","提示词-英文":"...","提示词-中文":"...","备注":"OpenArt <model> 生成"}' \
     --media 相关图片=<结果图URL> \
     --media 相关图片=<参考图URL或本地路径>
   ```
   视频结果用 `--media 相关视频=<结果视频URL>`。
4. 回报创建的 `record_id` 与写入字段。

## 注意
- **容器出口策略**：`feishu_cli.py` 下载附件 URL 是在容器内发起的，受网络白名单限制。
  若 OpenArt 结果域名未放行会下载失败——把该域名加进环境 Network access 的 Allowed
  domains 即可（与 `open.feishu.cn` 同理）。飞书 API 走 `open.feishu.cn`（已放行）。
- 大视频：飞书 `medias/upload_all` 有大小上限，超限需分片上传（后续可在 CLI 里补分片流程）。
- 只在用户明确要“存/记录”时才写表；生成与写入是两步，别自动写。
