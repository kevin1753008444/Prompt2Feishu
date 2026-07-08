---
description: 用 OpenArt 生成图片/视频，按需把结果+参考图+prompt 写入飞书多维表格
---

请按 `openart2feishu` skill 执行：用 OpenArt MCP 根据我给的 prompt（及可选参考图）生成图片/视频；
生成后先把结果给我看。等我说“存进多维表格/记录一下”时，再用 `feishu_cli.py add-record`
把「结果媒体 + 参考图 + 中英 prompt」写入飞书表，并回报 record_id。

$ARGUMENTS
