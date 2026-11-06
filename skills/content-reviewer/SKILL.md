---
name: content-reviewer
description: 편집된 블로그 초안의 의미 보존, Front Matter 무결성, 코드블록 균형, 링크/이미지 경로, 민감정보 포함 여부를 검증합니다.
---

# Content Reviewer Skill

## 목적
`stories/drafts/<slug>.md`가 공개 블로그에 게시되기 전에 품질 및 보안 가드레일을 통과하는지 검증하고 사용자 승인 게이트에 리포트를 제공합니다.

## 검증 체크리스트
1. **Front Matter 필수 필드:** `title`, `date`, `draft`, `description`, `tags`, `categories`, `slug` 존재 및 유효성 확인.
2. **Markdown 안정성:** 펜스 코드 블록(```` ``` ````) 개수의 짝 일치 여부, 빈 링크(`[]()`), 로컬 이미지(`static/images/` 대응) 누락 확인.
3. **원문 대비 보존 검증:** 원문의 코드 블록이 손상 없이 보존되었는지 대조.
4. **프라이버시/보안 스캔:** API 키(`sk-`, `ghp_`, `AKIA`), 개인키 블록, 비밀번호 할당문, 사내 내부 IP/도메인, 전화번호 패턴 검출 시 에러/경고 발생.
5. **변경 가시화:** 원문 대비 라인 단위 Diff 및 변경 요약(문단 정리, 맞춤법 교정, 템플릿 구조화) 제공.

## 실행 도구 연계
- CLI: `python3 scripts/validate_post.py --file stories/drafts/<slug>.md --raw stories/raw/<raw_file>`
