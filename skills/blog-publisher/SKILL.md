---
name: blog-publisher
description: 승인된 게시물만 Hugo 사이트로 allowlist 복사하고 로컬 빌드 및 명시적 승인 기반 Git 배포/상태 확인을 수행합니다.
---

# Blog Publisher Skill

## 목적
사용자가 명시적으로 승인한 글(`stories/approved/<slug>.md`)만 공개 Hugo 디렉토리(`site/content/posts/<slug>.md`)로 복사하고, 로컬 빌드 검증 및 Git 푸시, GitHub Actions 배포 상태 및 최종 URL 확인을 수행합니다.

## 안전 가드레일
1. **Allowlist 발행:** `stories/raw/`, `stories/drafts/`, `.env`, `var/` 등은 절대 `site/`로 복사하지 않는다. 오직 승인된 게시물과 허용된 정적 이미지만 반영한다.
2. **Dry-run 기본값:** `--publish --confirm-public-push`가 명시되지 않으면 원격 저장소에 push하지 않는다.
3. **중복 발행 방지:** 동일한 `slug`가 이미 존재할 경우 `--upsert`(수정 발행) 옵션 없이는 덮어쓰기를 차단한다.
4. **정직한 배포 상태 기록:** Git push 직후에는 `pushed` 또는 `pending_verification`으로 기록하며, 실제 GitHub Actions 성공 및 URL HTTP 200 응답이 확인된 경우에만 `published` 상태를 부여한다.

## 실행 도구 연계
- 발행 준비/실행: `python3 scripts/prepare_publish.py --slug <slug> --approve --dry-run`
- 상태 확인: `python3 scripts/publication_status.py --slug <slug> --check-remote`
