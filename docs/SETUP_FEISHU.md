# 飞书接入配置指南

本 CLI 用**自建应用**的 `tenant_access_token` 访问你的多维表格。跟着下面 5 步走一遍即可。

## 1. 创建自建应用
1. 打开飞书开放平台开发者后台：https://open.feishu.cn/app （海外 Lark：https://open.larksuite.com/app）
2. 「创建企业自建应用」，填名称（如 `Prompt2Feishu`）。
3. 进入应用后，在「凭证与基础信息」里拿到 **App ID** 和 **App Secret** —— 填进 `.env` 的
   `FEISHU_APP_ID` / `FEISHU_APP_SECRET`。

## 2. 开通权限（Scopes）
在「权限管理」里搜索并添加以下权限，然后保存：
- `bitable:app`（读写多维表格）—— 写入记录必需
- 云文档/媒体上传相关权限（上传附件必需）。搜索 “drive” / “media” / “上传”，
  勾选允许**上传文件到云空间**的权限（如 `drive:drive`）。
- 读取多维表格元数据/字段的权限（通常随 `bitable:app` 一并具备）。

> 若某次调用报权限错误（code 类似 `99991672`/`1254302` 等），基本都是这里少勾了对应
> scope，或应用未发布/未审批。补齐后重新发布即可。

## 3. 发布并启用应用
在「版本管理与发布」创建一个版本并发布；企业内需要管理员审批的，等审批通过。
应用处于「已启用」状态才能调接口。

## 4. 把应用加为多维表格的协作者（最容易漏）
应用有了权限，还必须被授权访问**这一张具体的表**：
1. 打开你的多维表格，点右上角「…」或「分享」。
2. 添加协作者时搜索你的**应用名**（自建应用会以成员形式出现），给它「可编辑」权限。
   - 若搜不到应用，可改用「添加文档应用」/「更多 → 添加应用」入口（不同版本入口略有差异）。

没有这一步，即使 scope 齐全，接口也会返回「无权限访问该 App」。

## 5. 拿到 app_token 和 table_id
打开多维表格，看浏览器地址栏，URL 形如：

```
https://xxxx.feishu.cn/base/BASCxxxxxxxxxxxxxxxxxx?table=tblXXXXXXXXXXXX&view=vewYYYY
```

- `/base/` 后面那段 = **FEISHU_APP_TOKEN**（`BASC...` 或 `bascn...`）
- `table=` 后面那段 = **FEISHU_TABLE_ID**（`tbl...`）

把两者填进 `.env`。

## 6. 验证
```bash
pip install -r requirements.txt
cp .env.example .env      # 然后编辑 .env 填入上面四个值
python feishu_cli.py test
```
`test` 成功会打印表名和字段列表。再跑 `python feishu_cli.py list-fields` 核对
`config/field_map.json` 里的列名是否与你表里的真实列名一致（不一致就改映射文件）。

## 常见问题
- **附件传上去了但列里不显示**：确认目标列类型是「附件」，且 `field_map.json` 里该字段
  `type` 为 `attachment`；图片用 `parent_type=bitable_image`，视频用 `bitable_file`
  （CLI 会按文件 MIME 自动判断）。
- **单选「分类」写入报错**：写入值必须是该单选字段里**已存在的选项名**，否则先在表里
  建好选项，或留空。
- **海外 Lark 租户**：在 `.env` 设 `FEISHU_BASE_URL=https://open.larksuite.com`。
