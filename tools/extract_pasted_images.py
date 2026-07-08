#!/usr/bin/env python3
"""从当前 Claude Code 会话记录里提取用户「粘贴在对话里的图片」，按顺序存成文件。

解决的问题：在 Claude Code 里粘贴的图片不会落到磁盘，但会以 base64 存在会话
transcript（~/.claude/projects/<proj>/<session>.jsonl）里。本脚本把它们按**原始顺序**
取出来存成文件，供后续上传 OpenArt / 写入飞书使用——这样用户无需再用上传卡片。

用法：
  python tools/extract_pasted_images.py                # 取「最近一个含图 user 轮次」的所有图
  python tools/extract_pasted_images.py --last 2       # 取全局最近 2 张（跨轮次，保序）
  python tools/extract_pasted_images.py --turn -1      # 指定倒数第 1 个含图轮次
  python tools/extract_pasted_images.py --out scratch/paste

输出：把文件写成 01.ext、02.ext…（保序），并打印 JSON: {"files":[...]}。
"""
import argparse
import base64
import glob
import json
import os
import sys
from pathlib import Path

EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}


def find_transcript() -> Path:
    """定位当前会话 transcript：~/.claude/projects 下最新修改的 .jsonl。"""
    root = Path.home() / ".claude" / "projects"
    candidates = glob.glob(str(root / "**" / "*.jsonl"), recursive=True)
    if not candidates:
        raise SystemExit("找不到会话 transcript（~/.claude/projects/**/*.jsonl）")
    return Path(max(candidates, key=lambda p: os.path.getmtime(p)))


def _images_in_content(content):
    """从一个 message.content 里抽出 base64 图片，返回 [(media_type, data)]（保序）。"""
    out = []
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict) and b.get("type") == "image":
                src = b.get("source", {})
                if isinstance(src, dict) and src.get("type") == "base64" and src.get("data"):
                    out.append((src.get("media_type", "image/png"), src["data"]))
    return out


def collect_user_turns(transcript: Path):
    """返回按时间顺序的含图 user 轮次列表：[[(media_type,data),...], ...]"""
    turns = []
    with transcript.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = rec.get("message") if isinstance(rec.get("message"), dict) else rec
            if not isinstance(msg, dict) or msg.get("role") != "user":
                continue
            imgs = _images_in_content(msg.get("content"))
            if imgs:
                turns.append(imgs)
    return turns


def main():
    ap = argparse.ArgumentParser(description="提取对话中粘贴的图片（保序）")
    ap.add_argument("--transcript", default=None, help="指定 transcript 路径（默认自动定位最新会话）")
    ap.add_argument("--last", type=int, default=None, help="取全局最近 N 张（跨轮次，保序）")
    ap.add_argument("--turn", type=int, default=-1,
                    help="取第几个含图 user 轮次（默认 -1=最近）；--last 优先")
    ap.add_argument("--out", default="scratch/paste", help="输出目录（默认 scratch/paste）")
    args = ap.parse_args()

    transcript = Path(args.transcript) if args.transcript else find_transcript()
    turns = collect_user_turns(transcript)
    if not turns:
        raise SystemExit("会话里没有找到粘贴的图片。")

    if args.last is not None:
        flat = [img for turn in turns for img in turn]  # 保序展开
        selected = flat[-args.last:]
    else:
        selected = turns[args.turn]

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    # 清掉旧的编号文件，避免与上一次混淆
    for old in out_dir.glob("[0-9][0-9].*"):
        old.unlink()

    files = []
    for i, (mtype, data) in enumerate(selected, start=1):
        ext = EXT.get(mtype, ".png")
        dest = out_dir / f"{i:02d}{ext}"
        dest.write_bytes(base64.b64decode(data))
        files.append(str(dest))

    print(json.dumps({
        "transcript": str(transcript),
        "count": len(files),
        "files": files,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
