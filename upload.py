#!/usr/bin/env python3
"""Upload TikTok videos via autotok (requests + offline signer).

No browser touches TikTok: all HTTP goes through requests (proxy-aware),
signing runs in an offline Chromium page. The session comes from a
TikTok-only cookies.txt export - see README.md. Never commit that file.
Usage:
  python upload.py --cookies cookies-tiktok-only.txt --video clip.mp4 --caption clip.txt
  python upload.py --cookies cookies-tiktok-only.txt --clips-dir clips --nums 02 03 --gap-minutes 10
Caption files: first line = title, second line = hashtags (or one line with both).
"""
import argparse, sys, time
from pathlib import Path

def load_cookies(path):
    out = {}
    for line in Path(path).read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        s = line[len("#HttpOnly_"):] if line.startswith("#HttpOnly_") else line
        if s.startswith("#"):
            continue
        p = s.split("\t")
        if len(p) >= 7:
            out[p[5]] = p[6]
    return out

def make_client(cookies_path):
    c = load_cookies(cookies_path)
    if "sessionid" not in c:
        raise SystemExit("no sessionid in cookies file - export fresh TikTok-only cookies (see README.md)")
    from autotok import settings
    from autotok.uploader import Client
    client = Client.from_session_id(c["sessionid"], datacenter=c.get("tt-target-idc"),
                                    user_agent=settings.DEFAULT_USER_AGENT, proxy=False)
    print(f"session check: {client.check_session()}", flush=True)
    if not client.check_session():
        raise SystemExit("session rejected by TikTok - export fresh cookies and retry")
    return client

def upload_one(client, video, caption):
    print(f"uploading {Path(video).name} :: {caption!r}", flush=True)
    res = client.upload(str(video), caption, visibility=0)
    line = f"OK video_id={res.video_id} creation_id={res.creation_id}"
    print(line, flush=True)
    print(f"  -> https://www.tiktok.com/video/{res.video_id}", flush=True)
    with open("upload.log", "a", encoding="utf-8") as f:
        f.write(f"{Path(video).name}: {line}\n")
    return res

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cookies", default="cookies-tiktok-only.txt")
    ap.add_argument("--video", default="")
    ap.add_argument("--caption", default="")
    ap.add_argument("--clips-dir", default="")
    ap.add_argument("--nums", nargs="*", default=[])
    ap.add_argument("--gap-minutes", type=int, default=10)
    args = ap.parse_args()
    client = make_client(args.cookies)
    if args.video:
        cap = Path(args.caption).read_text(encoding="utf-8").strip() if args.caption else ""
        if not cap:
            raise SystemExit("--caption is required (a .txt file with the title + hashtags)")
        upload_one(client, args.video, cap)
        return 0
    if args.clips_dir and args.nums:
        d = Path(args.clips_dir)
        for i, num in enumerate(args.nums):
            video = d / f"ducky-reloaded-gta6-{num}.mp4"
            txt = d / f"ducky-reloaded-gta6-{num}.txt"
            if not video.exists():
                # generic fallback: any clip named <num>.mp4 / <num>.txt
                video = d / f"{num}.mp4"
                txt = d / f"{num}.txt"
            cap = txt.read_text(encoding="utf-8").strip()
            try:
                upload_one(client, video, cap)
            except Exception as e:
                print(f"[{num}] FAILED: {type(e).__name__}: {e}", flush=True)
                return 1
            if i < len(args.nums) - 1:
                print(f"Waiting {args.gap_minutes} min before next clip...", flush=True)
                time.sleep(args.gap_minutes * 60)
        print("All done.")
        return 0
    ap.print_help()
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
