#!/usr/bin/env python3
"""Prompt2Feishu CLI.

一个封装飞书开放平台 OpenAPI 的轻量 CLI：鉴权、读表字段、上传媒体、写入记录。
Claude Code 和 Codex 都可以直接 `python feishu_cli.py ...` 调用。

需要的环境变量（见 .env.example）：
  FEISHU_APP_ID, FEISHU_APP_SECRET   —— 飞书自建应用凭据
  FEISHU_APP_TOKEN, FEISHU_TABLE_ID  —— 目标多维表格的定位信息
可选：FEISHU_BASE_URL（默认 https://open.feishu.cn，海外租户用 https://open.larksuite.com）

所有命令都把结果以 JSON 打印到 stdout，出错时以非 0 退出码结束。
"""
import argparse
import json
import mimetypes
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
except ImportError:  # pragma: no cover - 友好提示
    sys.stderr.write("缺少依赖 requests，请先运行: pip install -r requirements.txt\n")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent
FIELD_MAP_PATH = ROOT / "config" / "field_map.json"


def _load_env_file() -> None:
    """极简 .env 加载：不覆盖已存在的真实环境变量。"""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _require_env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise SystemExit(f"缺少环境变量 {name}（请在 .env 或环境中设置）")
    return val


def base_url() -> str:
    return os.environ.get("FEISHU_BASE_URL", "https://open.feishu.cn").rstrip("/")


def load_field_map() -> dict:
    if not FIELD_MAP_PATH.exists():
        raise SystemExit(f"找不到字段映射文件: {FIELD_MAP_PATH}")
    return json.loads(FIELD_MAP_PATH.read_text(encoding="utf-8"))


class Feishu:
    def __init__(self):
        self.app_id = _require_env("FEISHU_APP_ID")
        self.app_secret = _require_env("FEISHU_APP_SECRET")
        self._token = None
        self.session = requests.Session()

    # ---- 鉴权 ----
    def token(self) -> str:
        if self._token:
            return self._token
        url = f"{base_url()}/open-apis/auth/v3/tenant_access_token/internal"
        resp = self.session.post(
            url,
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise SystemExit(f"获取 tenant_access_token 失败: {json.dumps(data, ensure_ascii=False)}")
        self._token = data["tenant_access_token"]
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token()}"}

    def _api(self, method: str, path: str, **kwargs) -> dict:
        url = f"{base_url()}{path}"
        headers = kwargs.pop("headers", {})
        headers.update(self._headers())
        resp = self.session.request(method, url, headers=headers, timeout=60, **kwargs)
        try:
            data = resp.json()
        except ValueError:
            raise SystemExit(f"接口返回非 JSON（HTTP {resp.status_code}）: {resp.text[:500]}")
        if data.get("code") not in (0, None):
            raise SystemExit(f"接口 {path} 报错: {json.dumps(data, ensure_ascii=False)}")
        return data

    # ---- 多维表格 ----
    def list_fields(self, app_token: str, table_id: str) -> list:
        path = f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        data = self._api("GET", path, params={"page_size": 100})
        return data.get("data", {}).get("items", [])

    def table_meta(self, app_token: str) -> dict:
        path = f"/open-apis/bitable/v1/apps/{app_token}"
        return self._api("GET", path).get("data", {})

    def _download_url(self, url: str) -> Path:
        """把 http(s) URL 下载到临时文件，扩展名尽量按 Content-Type 推断。

        注意：下载在容器内发起，受环境出口策略限制。若目标域名未放行会连不上，
        需在环境网络策略里把该域名加入白名单（与 open.feishu.cn 同理）。
        """
        resp = self.session.get(url, stream=True, timeout=120)
        if resp.status_code != 200:
            raise SystemExit(f"下载 URL 失败（HTTP {resp.status_code}）: {url}")
        # 先取 URL 里的文件名/扩展名，缺失再按 Content-Type 补
        name = Path(urlparse(url).path).name or "download"
        if "." not in name:
            ext = mimetypes.guess_extension((resp.headers.get("Content-Type") or "").split(";")[0].strip())
            if ext:
                name += ext
        tmp_dir = Path(tempfile.mkdtemp(prefix="p2f_"))
        dest = tmp_dir / name
        with dest.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                if chunk:
                    fh.write(chunk)
        return dest

    def upload_media(self, file_path: str, app_token: str, parent_type: str = None) -> str:
        # 支持本地路径或 http(s) URL（URL 先下载到临时文件）
        if str(file_path).startswith(("http://", "https://")):
            p = self._download_url(file_path)
        else:
            p = Path(file_path)
        if not p.exists():
            raise SystemExit(f"文件不存在: {file_path}")
        if parent_type is None:
            parent_type = _parent_type_for(p.name)
        size = p.stat().st_size
        path = "/open-apis/drive/v1/medias/upload_all"
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        with p.open("rb") as fh:
            files = {
                "file_name": (None, p.name),
                "parent_type": (None, parent_type),
                "parent_node": (None, app_token),
                "size": (None, str(size)),
                "file": (p.name, fh, mime),
            }
            data = self._api("POST", path, files=files)
        return data.get("data", {}).get("file_token", "")

    def create_record(self, app_token: str, table_id: str, fields: dict) -> dict:
        path = f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        data = self._api("POST", path, json={"fields": fields})
        return data.get("data", {}).get("record", {})

    def update_record(self, app_token: str, table_id: str, record_id: str, fields: dict) -> dict:
        path = f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
        data = self._api("PUT", path, json={"fields": fields})
        return data.get("data", {}).get("record", {})


# 视频文件的附件父类型
def _parent_type_for(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or ""
    return "bitable_file" if mime.startswith("video/") else "bitable_image"


def build_fields(client, app_token, logical_data: dict, media: list, field_map: dict) -> dict:
    """把逻辑字段名 + 值转换成飞书 create 记录所需的 {列名: 值} 结构。"""
    out = {}
    for logical, value in logical_data.items():
        if logical not in field_map:
            raise SystemExit(f"字段 '{logical}' 不在 field_map.json 中，请先补充映射。")
        spec = field_map[logical]
        column, ftype = spec["column"], spec["type"]
        out[column] = _coerce(ftype, value)

    for logical, file_path in media:
        if logical not in field_map:
            raise SystemExit(f"附件字段 '{logical}' 不在 field_map.json 中。")
        spec = field_map[logical]
        if spec["type"] != "attachment":
            raise SystemExit(f"字段 '{logical}' 不是附件类型，无法用 --media 上传。")
        token = client.upload_media(file_path, app_token)  # parent_type 自动判断
        out.setdefault(spec["column"], [])
        out[spec["column"]].append({"file_token": token})
    return out


def _coerce(ftype: str, value):
    if ftype in ("text", "single_select"):
        return str(value)
    if ftype == "multi_select":
        return value if isinstance(value, list) else [str(value)]
    if ftype == "number":
        return float(value) if isinstance(value, str) else value
    if ftype == "url":
        if isinstance(value, dict):
            return value
        return {"link": str(value), "text": str(value)}
    if ftype == "attachment":
        # 允许直接传 file_token 列表
        if isinstance(value, list):
            return [v if isinstance(v, dict) else {"file_token": v} for v in value]
        return [{"file_token": str(value)}]
    return value


# ---------------- 子命令 ----------------
def cmd_test(args):
    client = Feishu()
    app_token = _require_env("FEISHU_APP_TOKEN")
    table_id = _require_env("FEISHU_TABLE_ID")
    meta = client.table_meta(app_token)
    fields = client.list_fields(app_token, table_id)
    print(json.dumps({
        "ok": True,
        "app": meta.get("app", {}).get("name"),
        "table_id": table_id,
        "field_count": len(fields),
        "fields": [f.get("field_name") for f in fields],
    }, ensure_ascii=False, indent=2))


def cmd_list_fields(args):
    client = Feishu()
    app_token = _require_env("FEISHU_APP_TOKEN")
    table_id = _require_env("FEISHU_TABLE_ID")
    fields = client.list_fields(app_token, table_id)
    print(json.dumps(fields, ensure_ascii=False, indent=2))


def cmd_upload_media(args):
    client = Feishu()
    app_token = _require_env("FEISHU_APP_TOKEN")
    # args.parent_type 为 None 时，upload_media 会在（下载后）按 MIME 自动判断
    token = client.upload_media(args.path, app_token, args.parent_type)
    print(json.dumps({"file_token": token}, ensure_ascii=False))


def _parse_media_args(media_list):
    """把 ['相关图片=a.png', '相关图片=b.png'] 解析成 [(字段, 路径), ...]（保序、可重复）。

    用 list 而非 dict：同一字段多次出现代表往同一附件列放多张图，dict 会互相覆盖。
    """
    result = []
    for item in media_list or []:
        if "=" not in item:
            raise SystemExit(f"--media 参数格式应为 字段=路径，收到: {item}")
        key, _, path = item.partition("=")
        result.append((key.strip(), path.strip()))
    return result


def cmd_add_record(args):
    field_map = load_field_map()
    try:
        logical_data = json.loads(args.data) if args.data else {}
    except json.JSONDecodeError as e:
        raise SystemExit(f"--data 不是合法 JSON: {e}")
    media = _parse_media_args(args.media)

    if args.dry_run:
        # 不联网：只做映射与类型转换的展示（附件仅列出待上传文件）
        preview = {}
        for logical, value in logical_data.items():
            if logical not in field_map:
                raise SystemExit(f"字段 '{logical}' 不在 field_map.json 中。")
            spec = field_map[logical]
            preview[spec["column"]] = _coerce(spec["type"], value)
        print(json.dumps({
            "dry_run": True,
            "fields": preview,
            "pending_media_uploads": [{"field": k, "path": v} for k, v in media],
        }, ensure_ascii=False, indent=2))
        return

    client = Feishu()
    app_token = _require_env("FEISHU_APP_TOKEN")
    table_id = _require_env("FEISHU_TABLE_ID")
    fields = build_fields(client, app_token, logical_data, media, field_map)
    record = client.create_record(app_token, table_id, fields)
    print(json.dumps({
        "ok": True,
        "record_id": record.get("record_id"),
        "fields_written": list(fields.keys()),
    }, ensure_ascii=False, indent=2))


def cmd_update_record(args):
    field_map = load_field_map()
    try:
        logical_data = json.loads(args.data) if args.data else {}
    except json.JSONDecodeError as e:
        raise SystemExit(f"--data 不是合法 JSON: {e}")
    media = _parse_media_args(args.media)

    client = Feishu()
    app_token = _require_env("FEISHU_APP_TOKEN")
    table_id = _require_env("FEISHU_TABLE_ID")
    fields = build_fields(client, app_token, logical_data, media, field_map)
    record = client.update_record(app_token, table_id, args.record_id, fields)
    print(json.dumps({
        "ok": True,
        "record_id": record.get("record_id") or args.record_id,
        "fields_written": list(fields.keys()),
    }, ensure_ascii=False, indent=2))


def main():
    _load_env_file()
    parser = argparse.ArgumentParser(description="Prompt2Feishu —— 飞书多维表格 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("test", help="连通性自检：鉴权 + 读取目标表字段").set_defaults(func=cmd_test)
    sub.add_parser("list-fields", help="列出目标表所有字段及类型").set_defaults(func=cmd_list_fields)

    p_up = sub.add_parser("upload-media", help="上传本地文件或 http(s) URL 的图片/视频，返回 file_token")
    p_up.add_argument("path", help="本地文件路径，或 http(s) URL（会先下载再上传）")
    p_up.add_argument("--parent-type", dest="parent_type", default=None,
                      help="bitable_image（默认，图片）或 bitable_file（视频/其它）")
    p_up.set_defaults(func=cmd_upload_media)

    p_add = sub.add_parser("add-record", help="写入一条记录（可选附件上传）")
    p_add.add_argument("--data", required=True,
                       help='逻辑字段 JSON，如 \'{"标题":"...","提示词-英文":"..."}\'')
    p_add.add_argument("--media", action="append", default=[],
                       help="附件：字段=本地路径或URL，可重复。"
                            "如 --media 相关图片=a.png 或 --media 相关图片=https://.../out.png")
    p_add.add_argument("--dry-run", action="store_true",
                       help="不联网，仅打印映射后的字段结构（用于自检）")
    p_add.set_defaults(func=cmd_add_record)

    p_upd = sub.add_parser("update-record",
                           help="更新已有记录（附件列会被新列表整体替换，需传齐所有想保留的图）")
    p_upd.add_argument("--record-id", required=True, help="要更新的 record_id")
    p_upd.add_argument("--data", default="{}",
                       help='逻辑字段 JSON（只改这些字段）；不改字段可传 {}')
    p_upd.add_argument("--media", action="append", default=[],
                       help="附件：字段=本地路径或URL，可重复。整列会被替换为这些图。")
    p_upd.set_defaults(func=cmd_update_record)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
