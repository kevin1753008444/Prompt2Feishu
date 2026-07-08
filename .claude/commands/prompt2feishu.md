---
description: 把 prompt 截图/文本抽取成结构化字段并写入飞书多维表格
---

请对我接下来提供的 prompt 素材（截图或文本，可能附带参考图）执行 `prompt2feishu` skill 的流程：
识别并抽取出「标题、分类、提示词-英文、提示词-中文、评分、备注、链接」字段，
先列给我确认，确认后用 `feishu_cli.py add-record` 写入飞书多维表格，并回报 record_id。

$ARGUMENTS
