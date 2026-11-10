# 웹툰 서재

망검회귀와 잿빛 서약을 세로 스크롤로 읽는 정적 웹툰 뷰어입니다. 서버 없이 GitHub Pages나 로컬 정적 서버에서 동작합니다.

- 공개 주소: https://tax911.github.io/webtoon/
- 저장소: https://github.com/tax911/webtoon

## 새 회차 추가하는 방법

1. 원고 이미지를 `/workspace/webtoon/<작품폴더>/epNNN/` 에 컷 순서대로 넣습니다.
   - 예: `/workspace/webtoon/manggeom-hoegwi/ep002/01.jpg`, `02.jpg`, …
   - 시안만 있을 때는 `ep001_concepts/` 처럼 `_concepts` 접미사를 쓰면 ‘시안’으로 표시됩니다.
   - 같은 회차에 본편 폴더(`ep001`)와 시안 폴더가 함께 있으면 본편을 우선합니다.
2. 제목과 소개는 `/workspace/webtoon/<작품폴더>/series.json` 의 `episodes` 항목에 적습니다.
3. 사이트 폴더에서 빌드합니다.

```bash
python3 /workspace/webtoon-site/build.py
```

4. 공개 사이트에 반영하려면:

```bash
/workspace/webtoon-site/publish.sh
```

원본 이미지는 읽어서 복사만 하며, 웹툰봇 원본 파일은 수정하거나 지우지 않습니다.
