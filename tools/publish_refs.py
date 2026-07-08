#!/usr/bin/env python3
"""一步到位：把「对话里粘贴的参考图」按顺序发布成公网 URL，喂给 OpenArt。

流程（全自动，无需上传卡片、无需人工核对顺序）：
  1. 从会话 transcript 提取用户最近粘贴的图片（保序）——复用 extract_pasted_images。
  2. 存到 scratch/paste/01.ext、02.ext…（编号即粘贴顺序）。
  3. 上传到图床，得到公网 URL：
     - host=catbox（默认）：免注册匿名图床 catbox.moe，无损、直链、无账号。
     - host=github：提交到当前工作分支 assets/refs/，用 commit SHA 拼 raw URL（需装 GitHub App）。
     - host=auto（推荐）：先试 catbox，失败自动回退 github。
  4. 打印 JSON：{"host":..,"refs":[{"index":1,"url":..,"media_type":..}, ...]}，
     顺序即粘贴顺序，直接作为 OpenArt visualReferences[].url 使用。

用法：
  python tools/publish_refs.py --last 2                 # 最近 2 张，默认 host=auto
  python tools/publish_refs.py --host catbox --last 2
  python tools/publish_refs.py --host github

顺序保证：编号来自 transcript 里的粘贴顺序，脚本层面即确定，无需再用视觉逐张核对。
说明：这些 URL 只需短暂存活（够 OpenArt 生成 + 飞书回填下载即可），之后失效不影响已写入飞书的附件。
"""
import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    sys.stderr.write("缺少依赖 requests，请先 pip install -r requirements.txt\n")
    sys.exit(2)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_pasted_images import find_transcript, collect_user_turns, EXT  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PASTE_DIR = ROOT / "scratch" / "paste"
REFS_DIR = ROOT / "assets" / "refs"
CATBOX_API = "https://catbox.moe/user/api.php"


def _git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def extract(last, turn):
    turns = collect_user_turns(find_transcript())
    if not turns:
        raise SystemExit("会话里没有找到粘贴的图片。")
    if last is not None:
        selected = [img for t in turns for img in t][-last:]
    else:
        selected = turns[turn]
    PASTE_DIR.mkdir(parents=True, exist_ok=True)
    for old in PASTE_DIR.glob("[0-9][0-9].*"):
        old.unlink()
    files = []
    for i, (mtype, data) in enumerate(selected, start=1):
        dest = PASTE_DIR / f"{i:02d}{EXT.get(mtype, '.png')}"
        dest.write_bytes(base64.b64decode(data))
        files.append((dest, mtype))
    return files


def upload_catbox(path: Path) -> str:
    with path.open("rb") as fh:
        resp = requests.post(
            CATBOX_API,
            data={"reqtype": "fileupload"},
            files={"fileToUpload": (path.name, fh)},
            timeout=120,
        )
    resp.raise_for_status()
    url = resp.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"catbox 返回异常: {url[:200]}")
    return url


def publish_github(files):
    REFS_DIR.mkdir(parents=True, exist_ok=True)
    for old in REFS_DIR.glob("[0-9][0-9].*"):
        old.unlink()
    rel = []
    for dest, _ in files:
        target = REFS_DIR / dest.name
        target.write_bytes(dest.read_bytes())
        rel.append(f"assets/refs/{dest.name}")
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    _git("add", *rel)
    try:
        _git("commit", "-m", f"chore: publish {len(rel)} 参考图 -> assets/refs")
    except subprocess.CalledProcessError:
        pass
    subprocess.run(["git", "push", "origin", branch], cwd=ROOT, check=True,
                   capture_output=True, text=True)
    sha = _git("rev-parse", "HEAD")
    url = _git("config", "--get", "remote.origin.url")
    tail = url.rstrip("/").replace(".git", "")
    repo = "/".join(tail.replace(":", "/").split("/")[-2:])
    return [f"https://raw.githubusercontent.com/{repo}/{sha}/{p}" for p in rel]


def main():
    ap = argparse.ArgumentParser(description="把对话粘贴的参考图发布成公网 URL")
    ap.add_argument("--host", choices=["auto", "catbox", "github"], default="auto")
    ap.add_argument("--last", type=int, default=None, help="取全局最近 N 张（保序）")
    ap.add_argument("--turn", type=int, default=-1, help="取第几个含图轮次（默认最近）")
    args = ap.parse_args()

    files = extract(args.last, args.turn)

    urls = None
    used = None
    if args.host in ("auto", "catbox"):
        try:
            urls = [upload_catbox(dest) for dest, _ in files]
            used = "catbox"
        except Exception as e:  # noqa: BLE001
            if args.host == "catbox":
                raise SystemExit(f"catbox 上传失败：{e}\n（需在环境白名单放行 catbox.moe）")
            sys.stderr.write(f"catbox 失败，回退 github：{e}\n")
    if urls is None:
        urls = publish_github(files)
        used = "github"

    refs = [{"index": i + 1, "media_type": files[i][1], "url": urls[i]}
            for i in range(len(files))]
    print(json.dumps({"host": used, "count": len(refs), "refs": refs},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
