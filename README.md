# autotok — TikTok uploader that works on a VM

A small wrapper around [makiisthenes/TiktokAutoUploader](https://github.com/makiisthenes/TiktokAutoUploader) (`autotok` 2.1.0) that uploads TikTok videos from a Linux VM with **no browser touching TikTok**.

## Why this exists

Browser-based uploaders (Playwright / Selenium driving `tiktok.com`) fail on many sandboxed VMs: the browser can't get through the egress proxy (`ERR_TUNNEL_CONNECTION_FAILED` on every site, while `curl` works fine).

`autotok` fixes that by design:

- **Upload = plain HTTP `requests`** — same transport as `curl`, proxy-aware, so it works where a browser can't.
- **Signing = offline Chromium page** — TikTok's `X-Bogus` / `_signature` are computed in a headless Chromium page that never touches the network. No Node.js needed.
- **Login = your existing session** — import a `sessionid` + `tt-target-idc` from your own browser cookies. No interactive login, no password in code.

Built and tested 2026-11-19 on a CPU-only Linux VM: session check passed, signer passed, and a real clip published to TikTok on the first try.

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# Playwright Chromium is only used offline, for signing:
.venv/bin/playwright install chromium
```

Python 3.12+.

## Cookies — read this first

Export cookies from the browser where you're signed in to TikTok, **TikTok only**:

1. In Chrome, signed in to TikTok, open `tiktok.com`.
2. Extension "Get cookies.txt LOCALLY" → Export. That file contains cookies for *every* site — filter it to TikTok only before using it here.
3. Save the filtered file as `cookies-tiktok-only.txt` next to the scripts. It contains a live `sessionid`: **it is a full login. Never commit it, never share it, delete it when done.** It is in `.gitignore` for exactly that reason.

```bash
# filter an all-sites export down to TikTok only (example, Python):
python3 - << 'PY'
from pathlib import Path
src, dst = Path("cookies.txt"), Path("cookies-tiktok-only.txt")
kept = []
for line in src.read_text(errors="ignore").splitlines():
    s = line[len("#HttpOnly_"):] if line.startswith("#HttpOnly_") else line
    parts = s.split("\t")
    if len(parts) >= 7 and parts[0].strip() in (".tiktok.com", "www.tiktok.com", ".www.tiktok.com", "tiktok.com"):
        kept.append(line)
dst.write_text("\n".join(kept) + "\n")
print(f"kept {len(kept)} TikTok cookies")
PY
chmod 600 cookies-tiktok-only.txt
```

## Test the session + signer

```bash
.venv/bin/python test_session.py --cookies cookies-tiktok-only.txt
```

Expected output:

```
cookies loaded: 34 names; sessionid present: True; tt-target-idc present: True
check_session: True
signer OK: signature len=47 x_bogus len=28
ALL TESTS PASSED - ready to upload
```

If `check_session` is `False`, the session expired — export fresh cookies.

## Upload

Single clip, caption from a text file (first line = title, second line = hashtags):

```bash
.venv/bin/python upload.py --cookies cookies-tiktok-only.txt \
  --video clips/my-clip.mp4 --caption clips/my-clip.txt
```

Batch, one clip every 10 minutes (TikTok-friendly spacing), stopping on the first failure:

```bash
.venv/bin/python upload.py --cookies cookies-tiktok-only.txt \
  --clips-dir clips --nums 02 03 04 05 --gap-minutes 10
```

Each success prints the video URL, e.g. `https://www.tiktok.com/@yourhandle/video/<video_id>`, and appends it to `upload.log`.

## Files

- `upload.py` — upload one clip, or a batch with a gap between posts.
- `test_session.py` — checks the session against TikTok's upload/auth endpoint and tests the offline signer, without uploading anything.
- `requirements.txt` — `autotok[youtube]`.

## Notes / risks

- This drives your own logged-in session. Automated uploading may violate TikTok's Terms of Service — use it on your own account, at your own risk.
- `autotok` is AGPL-3.0 (see its repo). This wrapper is MIT; if you redistribute `autotok` itself, its licence applies.
- TikTok changes its web API and signing from time to time. If `check_session` passes but publishing fails, the signer or upload flow probably needs updating against the current `autotok` release first.
