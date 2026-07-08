#!/usr/bin/env python3
"""一步到位：把「对话里粘贴的参考图」按顺序发布成公网 raw URL，喂给 OpenArt。

流程（全自动，无需上传卡片、无需人工核对顺序）：
  1. 从会话 transcript 提取用户最近粘贴的图片（保序）——复用 extract_pasted_images。
  2. 复制到 assets/refs/01.ext、02.ext…（编号即顺序）。
  3. git add/commit/push 到当前工作分支。
  4. 用 commit SHA 拼出 raw.githubusercontent.com 公网 URL（稳定、公开、已在白名单）。
  5. 打印 JSON：{"refs":[{"index":1,"url":...,"media_type":...}, ...]}，
     顺序即粘贴顺序，直接作为 OpenArt visualReferences[].url 使用。

用法：
  python tools/publish_refs.py --last 2          # 最近 2 张
  python tools/publish_refs.py                   # 最近一个含图轮次的所有图
  python tools/publish_refs.py --repo kevin1753008444/Prompt2Feishu

顺序保证：编号来自 transcript 里的粘贴顺序，脚本层面即确定，无需再用视觉逐张核对。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_pasted_images import find_transcript, collect_user_turns, EXT  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REFS_DIR = ROOT / "assets" / "refs"


def _git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser(description="把对话粘贴的参考图发布成公网 URL")
    ap.add_argument("--last", type=int, default=None, help="取全局最近 N 张（保序）")
    ap.add_argument("--turn", type=int, default=-1, help="取第几个含图轮次（默认最近）")
    ap.add_argument("--repo", default=None,
                    help="owner/repo，用于拼 raw URL；默认从 git remote 推断")
    ap.add_argument("--no-push", action="store_true", help="只提交不推送（调试用）")
    args = ap.parse_args()

    turns = collect_user_turns(find_transcript())
    if not turns:
        raise SystemExit("会话里没有找到粘贴的图片。")
    if args.last is not None:
        selected = [img for t in turns for img in t][-args.last:]
    else:
        selected = turns[args.turn]

    REFS_DIR.mkdir(parents=True, exist_ok=True)
    for old in REFS_DIR.glob("[0-9][0-9].*"):
        old.unlink()

    import base64
    rel_paths, metas = [], []
    for i, (mtype, data) in enumerate(selected, start=1):
        ext = EXT.get(mtype, ".png")
        dest = REFS_DIR / f"{i:02d}{ext}"
        dest.write_bytes(base64.b64decode(data))
        rel_paths.append(f"assets/refs/{i:02d}{ext}")
        metas.append(mtype)

    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    _git("add", *rel_paths)
    # 允许「无改动」时不失败（同一批图重复发布）
    try:
        _git("commit", "-m", f"chore: publish {len(rel_paths)} 参考图 -> assets/refs")
    except subprocess.CalledProcessError:
        pass
    if not args.no_push:
        subprocess.run(["git", "push", "origin", branch], cwd=ROOT, check=True,
                       capture_output=True, text=True)
    sha = _git("rev-parse", "HEAD")

    repo = args.repo
    if not repo:
        url = _git("config", "--get", "remote.origin.url")
        # 从 .../git/<owner>/<repo> 或 git@github.com:owner/repo.git 里抠 owner/repo
        tail = url.rstrip("/").replace(".git", "")
        parts = tail.replace(":", "/").split("/")
        repo = "/".join(parts[-2:])

    refs = [{
        "index": i + 1,
        "media_type": metas[i],
        "url": f"https://raw.githubusercontent.com/{repo}/{sha}/{rel_paths[i]}",
    } for i in range(len(rel_paths))]

    print(json.dumps({"repo": repo, "sha": sha, "count": len(refs), "refs": refs},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
