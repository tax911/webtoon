#!/usr/bin/env bash
# Rebuild the static site from /workspace/webtoon and push to GitHub Pages.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

python3 "$ROOT/build.py"

if [ ! -d "$ROOT/.git" ]; then
  echo "이 폴더에 git 저장소가 없습니다. 처음에는 게시 설정을 먼저 해야 합니다." >&2
  exit 1
fi

git add -A
if git diff --cached --quiet; then
  echo "새로 올릴 변경이 없습니다."
  git status -sb
  exit 0
fi

MESSAGE="${1:-Update webtoon site $(date '+%Y-%m-%d %H:%M')}"
git commit -m "$MESSAGE"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
git push -u origin "$BRANCH"
echo "올렸습니다. 1~2분 뒤 https://tax911.github.io/webtoon/ 에서 확인할 수 있습니다."
