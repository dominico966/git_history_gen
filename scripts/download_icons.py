import os
import urllib.request

ICONS = [
    {"id": "20906", "size": 100, "name": "logo_git_20906_100.png"},
    {"id": "33279", "size": 80,  "name": "avatar_commit_33279_80.png"},
    {"id": "1476",  "size": 64,  "name": "icon_db_1476_64.png"},
    {"id": "33279", "size": 64,  "name": "icon_commit_33279_64.png"},
    {"id": "102261","size": 64,  "name": "icon_users_102261_64.png"},
    {"id": "417",   "size": 64,  "name": "icon_bug_417_64.png"},
    # 추가 아이콘 (헤더 링크 등)
    {"id": "1476",  "size": 32,  "name": "icon_db_1476_32.png"},
    {"id": "12599", "size": 32,  "name": "icon_github_12599_32.png"},
    # 에이전트(봇) 아바타 아이콘 (Icons8 nolan 스타일)
    {"id": "XiSP6YsZ9SZ0", "size": 80, "name": "avatar_agent_icons8_nolan_80.png"},
]

BASE_URL = "https://img.icons8.com/"


def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def download_icon(icon, out_dir):
    url = f"{BASE_URL}?id={icon['id']}&format=png&size={icon['size']}"
    out_path = os.path.join(out_dir, icon['name'])

    try:
        print(f"Downloading {url} -> {out_path}")
        urllib.request.urlretrieve(url, out_path)
        if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
            raise RuntimeError("Downloaded file is empty")
        print(f"✓ Saved: {out_path}")
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        raise


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(project_root, 'public', 'icons')
    ensure_dir(out_dir)

    for icon in ICONS:
        download_icon(icon, out_dir)

    print("All icons downloaded to:", out_dir)


if __name__ == "__main__":
    main()
