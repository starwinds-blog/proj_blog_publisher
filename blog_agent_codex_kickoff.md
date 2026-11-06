# AI Story-to-Blog Publisher — Codex CLI 프로젝트 착수 컨텍스트

> 작성일: 2026-11-06  
> 실행 주체: Codex CLI (로컬 개발 에이전트)  
> 목표: 사용자의 자유 형식 스토리/메모를 읽기 좋은 블로그 글로 편집하고, 승인 후 Hugo + GitHub Pages에 자동 발행하는 로컬 우선 워크플로 구축

## 0. Codex에게 전달하는 작업 요청

당신은 이 작업 디렉토리의 소프트웨어 엔지니어이자 프로젝트 코디네이터입니다. 아래 요구사항을 검토하고 실제 실행 가능한 MVP를 설계·구현하십시오. 먼저 로컬 환경과 기존 파일을 탐색하고, 부족한 선행조건을 구분하십시오. **기술적 세부 사항은 합리적으로 결정하되, 외부에 공개되는 저장소 생성·최초 발행·기존 파일 삭제·비용 발생 작업은 사용자 승인을 받으십시오.** 구현 가능하고 안전한 부분은 계획만 세우지 말고 작업 디렉토리에 실제로 생성·테스트하십시오.

- 최초 응답에 환경 점검 결과, 권장 아키텍처, 사람에게 필요한 입력/승인, 구현 순서를 간결히 제시할 것.
- 계정·GitHub username·도메인·저장소가 아직 없다고 가정하며, **임의로 이름/계정/URL을 만들어 사용하지 말 것**.
- 가급적 Python 표준 라이브러리 기반 도구와 Hugo 정식 CLI 사용. 추가 의존성은 이유를 명시.
- MVP는 로컬에서 시작할 수 있어야 하고, GitHub 인증 전에도 샘플 콘텐츠의 편집·미리보기·검증을 재현할 수 있어야 함.
- Codex의 자연어 편집 기능은 스킬/프롬프트로 정의하고, 글 검증·상태 전환·발행 등 반복 가능해야 하는 과정은 스크립트로 구현.

## 1. 배경과 목표

사용자가 TXT/Markdown 또는 자유 형식 자연어로 경험담, 생각, 기술적인 검토 메모를 작성하면 AI Agent(Codex CLI)가 다음을 수행한다.

1. 문법·맞춤법·가독성 개선, 문단 분리, 들여쓰기·Markdown 형식 정리.
2. 글의 성격에 맞는 템플릿 적용(에세이/회고, 경험 공유, 기술 노트, 리뷰).
3. 제목·요약·소제목·태그·URL slug와 Hugo Front Matter 생성.
4. 원문 대비 의미 보존 검증, 변경 요약 및 검토용 Diff 생성.
5. 로컬 Hugo 미리보기 제공.
6. 사용자의 명시적 승인 후 Git/GitHub Actions를 통해 GitHub Pages에 발행.
7. 배포 상태 및 실제 접근 가능한 글의 URL 기록.

블로그 편집과 발행 수단을 분리해 향후 WordPress 등 다른 발행 어댑터 추가가 가능하도록 한다. 다만 **MVP 발행 대상은 Hugo + GitHub Pages 한 가지**로 한정한다.

### 성공 기준

- 초기 자유 형식 스토리 1건으로 `raw -> draft -> approved -> published` 흐름을 시연할 수 있다.
- 편집 이전 원문을 변경하지 않고 보존한다.
- 한글 본문, 코드 블록, 인용, 표, 이미지 경로, 링크가 깨지지 않는다.
- 승인 없이 Public 저장소로 push/배포하지 않는다.
- 재실행할 때 같은 문서가 중복 발행되지 않는다.
- Actions 빌드 실패 시 성공이라고 보고하지 않는다.
- 콘텐츠 오류·미설정 계정·인증 실패·네트워크 실패를 사용자에게 명확히 알린다.

## 2. 기본 기술 스택 및 의사결정

| 레이어 | 기본 선택 | 비고 |
|---|---|---|
| Agent | Codex CLI + `AGENTS.md` + 로컬 스킬/지침 | 편집 규칙은 버전 관리 |
| 콘텐츠 입력 | UTF-8 TXT/Markdown | 자유 형식 입력 허용 |
| 원본 보관 | 로컬 `stories/raw/` | 공개 저장소에 push 금지 |
| 결과 포맷 | Markdown + YAML Front Matter | Hugo 호환 |
| 정적 사이트 | Hugo Extended | 실제 테마 요구사항에 따라 버전 고정 |
| 테마 | PaperMod 우선 검토 | 라이선스·버전 호환성 확인 후 선택 |
| 배포 | GitHub Actions 공식 Hugo Pages workflow | GitHub Pages source는 GitHub Actions |
| 저장소 | Public GitHub Pages 저장소 | GitHub Free 가정, 공개 콘텐츠만 포함 |
| 인증 | 개발자 로컬 `gh auth login` | credential/token 파일에 저장 금지 |
| 품질 검증 | 로컬 검사 스크립트, `hugo --minify`, CI | 배포 전 검증 |

### 저장소 구성 권장

**권장안: 로컬 작업/원본 디렉토리와 공개 Hugo 저장소를 명확히 분리한다.** 초기에는 아래처럼 두 디렉토리를 사용하고, 필요하다면 나중에 Private 저장소를 추가한다.

```text
ai-blog-workspace/                  # 로컬 전용; GitHub 공개 저장소 아님
├── AGENTS.md
├── README.md
├── config/
│   ├── editorial-policy.yaml
│   ├── templates.yaml
│   └── publishing.example.yaml
├── stories/
│   ├── raw/                     # 절대 Public repo에 커밋하지 않음
│   ├── drafts/
│   ├── approved/
│   └── records/                 # 발행 이력, 최종 URL, 원본-게시물 매핑
├── skills/
│   ├── story-editor/SKILL.md
│   ├── content-reviewer/SKILL.md
│   └── blog-publisher/SKILL.md
├── scripts/
│   ├── check_env.py
│   ├── validate_post.py
│   ├── prepare_publish.py
│   └── publication_status.py
├── tests/
└── site/                        # Hugo Git repo: 공개 콘텐츠/테마/Actions만
    ├── hugo.toml
    ├── content/posts/
    ├── static/images/
    ├── layouts/
    ├── themes/ 또는 hugo module
    └── .github/workflows/hugo.yml
```

- `site/`는 별도 Git 저장소로 관리하거나 독립 디렉토리로 분리할 것. nested Git 혼동을 피하고, 루트 작업 디렉토리를 통째로 Public push하지 않도록 보호할 것.
- 원본·초안·비밀정보·토큰·개인적인 내부 메모가 `site/`로 복사되지 않도록 **allowlist 기반 발행**을 구현할 것.
- `site/public/`, `site/resources/` 등 생성 산출물의 Git 처리 방식은 공식 Hugo 지침에 맞춰 `.gitignore`에 반영할 것. 특히 `public/`은 커밋하지 않는다.
- 기본 사이트 주소는 username이 확정되면 `https://<username>.github.io/`로 생성. 프로젝트형 저장소를 쓰는 경우 baseURL과 상대 경로를 구분하여 처리.

## 3. 콘텐츠 파이프라인/상태 모델

```text
[입력 파일 raw]
     |
     v
[AI 편집 + 템플릿 선택] --> [draft.md + 변경내역/검토 요약]
     |
     v
[품질 검증 / 민감정보 스캔 / 로컬 Hugo preview]
     |
     v
[사용자 승인 게이트] -- 거절/수정 --> [draft 재작업]
     |
     v
[approved 콘텐츠만 site/content/posts 로 복사]
     |
     v
[로컬 Hugo build + Git 검증]
     |
     v
[사용자 승인된 GitHub push / PR merge]
     |
     v
[GitHub Actions 배포 상태 확인]
     |
     v
[실제 URL 확인 + published 기록]
```

- MVP에서 권장 발행 흐름은 `draft 브랜치 -> Pull Request -> 사용자 리뷰/merge -> Actions 배포`.
- GitHub PR 이전의 로컬 승인과 GitHub PR 승인 중 하나로 단순화할 수 있으나, **어느 단계가 최종 공개 승인인지 명확하게** 해야 한다.
- 단독 개인 블로그의 첫 MVP에서는 `명시적 CLI 승인 -> main push` 간편 모드를 선택 가능하게 하되 기본값은 `dry-run` 및 비공개 상태.
- `published` 상태는 push 직후가 아니라 Actions 배포 성공과 사이트 URL 접근 확인 후에 부여.
- 네트워크 접근이 없으면 `pending_verification`으로 기록.
- 파일명/slug 중복, 재발행과 수정 발행(upsert), 롤백 전략을 마련.

## 4. AI 편집 정책 (가장 중요)

원문은 '고칠 자료'가 아니라 작성자의 생각을 표현한 1차 자료다. AI가 문체를 일방적으로 덮어쓰거나 본래 취지를 바꾸지 않도록 한다.

### 반드시 지킬 규칙

1. **원문 보존:** 원본 파일은 read-only 취급, 편집본은 새로운 파일.
2. **의미/화자 보존:** 작성자의 관점·감정·불확실성·고유 표현을 유지하고 과장·단정하지 않기.
3. **허위 정보 금지:** 경험·날짜·통계·인용·출처·링크를 새로 지어내지 않기. 확인이 필요한 내용은 `[검증 필요]`와 함께 검토 사항에 표시.
4. **변경 가시화:** 교정/문단 재구성/표현 변경/사실 보완을 분리하여 변경 요약을 제공.
5. **적정 수준 편집:** 지나친 SEO 최적화, 클릭 유도 제목, 의미 없는 서론·결론을 자동 삽입하지 않음.
6. **Markdown 안정성:** 코드 블록 내 텍스트·들여쓰기·JSON/YAML·Shell 명령어를 문장 교정 대상으로 삼지 않음.
7. **프라이버시:** 인명·주소·사내 정보·API key·토큰·비공개 URL 등이 포함되면 자동 발행 차단 및 사용자 확인.
8. **이미지/저작권:** 사용 권리가 확인되지 않은 외부 이미지 자동 수집 및 게시 금지. 글에 없는 자료를 임의 추가하지 않기.
9. **언어:** 한국어를 기본으로 하되 기술 용어 및 영어 코드 식별자는 보존.
10. **원문과 일치하지 않는 AI 추론:** 본문에 자연스럽게 끼워 넣지 말고 별도의 `suggestions`에 제시.

### 콘텐츠 유형별 템플릿

- `essay`: 도입/핵심 이야기/생각의 변화 또는 여운. 지나친 섹션 분할 지양.
- `experience`: 배경/상황/행동/결과/배운 점. 사건의 실제 순서 유지.
- `technical-note`: 문제/환경/검토 과정/대안/결론/재현 또는 참고 링크.
- `review`: 대상/검토 기준/경험/장단점/종합 의견.

글 유형을 자동 추천하되 사용자가 명시하면 그 설정을 우선. 글이 짧거나 서사형인 경우 H2/H3를 기계적으로 늘리지 않는다.

### Front Matter 예시

```yaml
---
title: "첫 번째 글의 제목"
date: 2026-11-06T00:00:00+09:00
draft: true
description: "짧은 글 소개"
tags: ["경험", "생각"]
categories: ["essay"]
slug: "first-story"
---
```

- 날짜는 사용자가 정하거나 발행 시점에 설정하며, 기존 과거 글의 날짜를 마음대로 바꾸지 말 것.
- 승인 전에는 `draft: true`; Hugo의 빌드/게시 옵션과 실제 배포 산출물 간 일관성 검증.
- 한국어 slug 처리는 기본적으로 영문 수동 지정 또는 일관된 변환 전략을 선택.

## 5. 기능 범위

### P0: 반드시 구현할 MVP

- 환경 점검(`git`, `gh`, `hugo`, `codex`, Git remote, OS).
- Hugo 프로젝트 및 테마 초기화, 로컬 `hugo server -D` 미리보기.
- 자유 형식 스토리를 편집본 Markdown + Front Matter로 만드는 Codex 작업 지침.
- 원본/편집본 Diff 및 편집 요약 리포트.
- 게시물 메타데이터·링크·이미지 참조·Markdown 코드블록·보안 문자열 검증.
- `dry-run` 모드, 명시적 publish 승인, 중복 발행 방지.
- 공식 권장 GitHub Actions Hugo Pages workflow 기반 빌드 및 배포.
- 발행 이력(원본 경로, post id/slug, Git commit SHA, URL, 날짜, 상태).
- 테스트와 README(로컬 실행, 글 생성, 검토, 발행, 오류 해결).

### P1: MVP 이후

- 사진 최적화/alt 텍스트, OG 이미지, RSS, sitemap, SEO 메타데이터.
- 예약 발행(별도 Scheduler/Action 조건 설계 필요).
- 여러 글 일괄 처리와 재시도 큐.
- 콘텐츠 검색/태그 체계, 관련 글 추천.
- PR 코멘트 기반 승인, 게시물 수정 자동화.
- 추가 CMS 발행 어댑터.

### 의도적으로 제외

- 웹 기반 편집 대시보드, 자체 인증 서버, 데이터베이스, 댓글 시스템, 유료 도메인 자동 구매, 자동 외부 자료 수집, 무승인 완전 자동 공개 발행.

## 6. Codex가 수행할 단계별 실행 계획

### Phase 0 — 사전 조사·환경 진단

1. 작업 디렉토리의 파일, Git 상태, 설치된 CLI와 버전 확인.
2. GitHub 계정/인증 유무를 `gh auth status`로 확인(토큰 내용 출력 금지).
3. `site/` 저장소가 이미 있는지, 사용자 site(`username.github.io`)인지 project site인지 구분.
4. 필요한 사람 작업을 체크리스트로 반환. **계정 로그인/브라우저 인증을 임의로 우회하지 않는다.**
5. 공식 Hugo Pages 가이드에 맞춰 현재 유효한 workflow/action 버전 확인.

### Phase 1 — 로컬 MVP 스캐폴드

1. `README.md`, `AGENTS.md`, 편집 정책/템플릿 파일 및 스킬 생성.
2. `site/`에 Hugo + PaperMod를 구성하고 테마 라이선스 및 의존성을 기록.
3. 한글 샘플 글 1개 제공(공개해도 되는 **명백한 테스트 콘텐츠**임을 표시).
4. `hugo server -D`로 로컬 결과 테스트, `hugo --minify`로 프로덕션 빌드 테스트.
5. 명령어 인터페이스는 단순하게. 예: `python scripts/check_env.py`, `python scripts/validate_post.py --file ...`, `python scripts/prepare_publish.py --slug ... --dry-run`.

### Phase 2 — AI 편집/검토 자동화

1. 사용자가 `stories/raw/`에 TXT/MD 파일을 저장하면 Codex가 편집 지침에 따라 `stories/drafts/`의 글 생성.
2. 원문과 비교해 변경 요약 및 사실 확인 항목 도출.
3. 메타데이터와 본문 lint 및 로컬 미리보기.
4. 승인된 글만 `stories/approved/`로 상태 이동/복사.
5. 편집 작업에 필요한 Codex CLI 호출이 자동화 가능한지 환경별로 검증하고, 비대화형 실행 여부는 실제 버전/옵션에 근거해 결정.

### Phase 3 — GitHub Pages 배포

1. 사용자가 GitHub 계정 및 공개 저장소 이름을 제공/승인한 뒤 remote 연결.
2. `.github/workflows/hugo.yml` 작성. 공식 예제를 기준으로 `contents: read`, `pages: write`, `id-token: write`와 GitHub Pages 배포 단계를 포함.
3. GitHub Repository Settings > Pages에서 Source를 **GitHub Actions**로 설정/확인.
4. 최초 공개 배포는 사용자 승인 후 진행. 실제 URL과 workflow 성공 상태 검증.
5. 자동 발행은 이후 승인 절차에 따라 PR merge 또는 명시적 push로 동작.

### Phase 4 — 검증/완료 보고

1. 테스트 케이스 실행: 한글, 짧은 메모, 기술 코드블록, 이미지 누락, 중복 slug, 비밀정보 발견, 빌드 실패, 인증 실패, 재실행.
2. 사용자가 복제·재설치 후 재현할 수 있도록 README 완성.
3. 실제 테스트 결과와 미완료 사항을 구별해 기록.
4. 최종 산출물: 디렉토리 구조, 실행 방법, 샘플 입출력, 운영 가이드, 배포 URL(실제로 생성된 경우에만).

## 7. 안전/보안/운영 가드레일

- Public repo로 push하는 것은 외부 공개 작업임. 승인 없는 원격 push 금지.
- GitHub 토큰, OAuth 자격증명, 로컬 사용자 프로필/환경변수 값을 로그나 문서에 노출하지 말 것.
- `.env`, 토큰, 원문, 내부 문서, drafts 및 발행 이력을 공개 repo에 포함하지 말 것.
- GitHub Actions는 최소 권한 사용, 출처 불명의 Action/테마 설치 주의, 버전 고정 권장.
- 사용자 승인 없이 유료 서비스 신청·도메인 등록·외부 API 과금 호출 금지.
- 발행 URL이 실제 접근 가능한지 확인하기 전 '배포 완료'라고 선언하지 말 것.
- 사이트의 검색 엔진 노출 가능성과 GitHub의 공개 저장소 특성을 README에 경고할 것.
- GitHub Pages 호스팅과 Actions 사용 제한·약관을 최신 공식 문서로 점검.

## 8. 사람에게 요청해야 할 입력 및 승인

### 필수

- [ ] 개인 GitHub 계정(기존 계정 사용 가능).
- [ ] 로컬 `gh auth login`으로 GitHub 인증(또는 기존 인증 확인).
- [ ] 공개 블로그 운영에 대한 동의.
- [ ] 블로그 username 및 repo 이름 결정: 사용자 사이트 권장 `<username>.github.io`.
- [ ] 사이트 제목/소개 등 최소 메타데이터. 미정이면 placeholder로 로컬 개발 진행.
- [ ] 최초 테스트 글 공개 승인 및 최초 remote push 승인.

### 선택

- [ ] 개인 도메인(기본 `github.io` 사용 시 불필요).
- [ ] 글의 실명/필명 여부, 공개 가능한 주제 범위.
- [ ] 테마 디자인(기본 PaperMod), 색상/메뉴, 프로필 이미지.
- [ ] PR 승인 방식 또는 로컬 publish 승인 방식 선택.

> **계정이 없어도 Phase 1~2는 먼저 구현 가능**. GitHub 사이트의 실제 공개 배포는 계정/인증/저장소 및 사용자 승인 후에만 수행.

## 9. Codex가 사용자에게 보고할 내용의 형식

초기 분석을 마친 뒤 아래 내용을 요약해 보고하십시오.

1. **검사 결과:** git/gh/hugo/codex 버전과 설치 필요 여부.
2. **권장 결정:** 계정형 site vs project site, 테마 선택, 승인 방식 및 근거.
3. **구현한 것:** 실제 생성 파일/테스트 결과.
4. **다음 작업:** Codex가 바로 진행할 작업.
5. **사람이 할 일:** 로그인/승인/설정 UI 조작을 구분한 체크리스트.
6. **현재 blocker:** 없으면 '없음'으로 명시.

## 10. 참고 공식 문서

- Hugo: Deploy to GitHub Pages — https://gohugo.io/host-and-deploy/deploy-to-github-pages/
- GitHub: Hugo Pages starter workflow — https://github.com/actions/starter-workflows/blob/main/pages/hugo.yml
- GitHub Docs: Create a GitHub Pages site — https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- GitHub Docs: GitHub CLI authentication — https://docs.github.com/en/github-cli/github-cli/authenticating-with-github-cli
- GitHub CLI manual — https://cli.github.com/manual/gh_auth_login
- Hugo PaperMod theme — https://github.com/adityatelange/hugo-PaperMod

---

## 11. 시작 지시문 (Codex에게 그대로 전달)

> 위 문서를 프로젝트의 구현 요구사항으로 사용하라. 우선 Phase 0 환경 진단 후 Phase 1~2의 **로컬에서 검증 가능한 최소 구현**을 진행하라. 사용자가 아직 제공하지 않은 GitHub 계정·repo 이름 등은 임의로 가정하지 말고 설정값으로 분리하라. GitHub에 공개되는 작업은 반드시 사람의 명시적인 승인을 받은 뒤 실행하라. 구현이 끝나면 프로젝트 파일 목록, 테스트 로그 요약, 로컬 미리보기 명령, 실제 발행까지 남은 준비사항을 보고하라.
