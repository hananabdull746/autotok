#!/usr/bin/env python3
"""Test a TikTok session + the offline autotok signer, without uploading.
Usage: python test_session.py --cookies cookies-tiktok-only.txt
Never prints cookie values.
"""
import argparse
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cookies", default="cookies-tiktok-only.txt")
    args = ap.parse_args()
    c = {}
    for line in Path(args.cookies).read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        s = line[len("#HttpOnly_"):] if line.startswith("#HttpOnly_") else line
        if s.startswith("#"):
            continue
        p = s.split("\t")
        if len(p) >= 7:
            c[p[5]] = p[6]
    print(f"cookies loaded: {len(c)} names; sessionid present: {'sessionid' in c}; "
          f"tt-target-idc present: {'tt-target-idc' in c}; msToken present: {'msToken' in c}")
    if "sessionid" not in c:
        print("NO sessionid - cannot test")
        return 2
    from autotok import settings
    from autotok.uploader import Client
    from autotok.signer import Signer
    ua = settings.DEFAULT_USER_AGENT
    client = Client.from_session_id(c["sessionid"], datacenter=c.get("tt-target-idc"),
                                    user_agent=ua, proxy=False)
    print(f"check_session: {client.check_session()}")
    if not client.check_session():
        print("Session rejected by TikTok upload/auth - export fresh cookies.")
        return 1
    print("Testing offline signer...")
    with Signer(ua, proxy=None, timeout=60) as signer:
        sig = signer.sign("https://www.tiktok.com/api/v1/web/project/post/?app_name=tiktok_web&channel=tiktok_web&device_platform=web&aid=1988&msToken=test")
        print(f"signer OK: signature len={len(sig.signature)} x_bogus len={len(sig.x_bogus)} verify_fp present={bool(sig.verify_fp)}")
    print("ALL TESTS PASSED - ready to upload")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
