# AI Story-to-Blog Publisher (`proj_blog_publisher`)

사용자의 자유 형식 스토리/메모를 원문 의미를 보존하며 블로그 게시글(Hugo Markdown + YAML Front Matter)로 편집·검토하고, 명시적 승인 후 **Hugo + GitHub Pages**로 자동 발행하는 로컬 우선 워크플로 및 **통합 Web Dashboard(`app/`)**입니다.

---

## 1. 주요 기능

1. **통합 Web Dashboard (`app/`)**:
   - `/mnt/c/Users/User/proj_brain_for_home/app` 아키텍처(FastAPI + SQLAlchemy SQLite + React 19 + Vite + Tailwind CSS v4) 기반 통합 UI.
   - **대시보드 홈 (`OverviewPage`)**: `raw -> draft -> approved -> staged -> published` 단계별 통계, 로컬 환경 점검 결과, 최근 실행 로그 확인.
   - **스토리 입력 & 초안 스튜디오 (`StoryStudioPage`)**: 웹에서 자유 형식 메모를 입력하면 `stories/raw/`에 원문을 보존(Read-only)하고, 선택한 템플릿(`essay`, `experience`, `technical-note`, `review`, `auto`)에 맞춰 초안 및 편집 요약을 생성.
   - **Diff 검토 & 승인 게이트 (`ReviewGatePage`)**: 원문 대비 Unified Diff 비교, Front Matter/코드블록/링크/민감정보(API 키·토큰·내부 IP) 검증 신호등 확인 후 명시적 승인(`draft: false`).
   - **발행 센터 & 배포 설정 (`PublishCenterPage`)**: Allowlist 기반 `site/content/posts/` 스테이징, Dry-run 시뮬레이션, 명시적 원격 Git Push 승인 게이트, GitHub Actions/URL 배포 상태 확인.
2. **표준 라이브러리 기반 CLI 파이프라인 (`scripts/`)**:
   - `gh` CLI 없이도 표준 `git` 명령어와 Python `urllib` 기반 GitHub REST API 조회로 전체 배포/검증 동작.
   - 코드 블록(```` ``` ````) 내부 텍스트·들여쓰기·명령어 100% 보존.

---

## 2. 디렉토리 구조

```text
proj_blog_publisher/
├── AGENTS.md                        # 에이전트 편집/발행 운영 규칙
├── README.md
├── requirements-dashboard.txt       # FastAPI 대시보드 의존성
├── deploy/run_dashboard.sh          # 통합 웹 대시보드 실행 스크립트 (기본 포트: 8500)
├── config/
│   ├── editorial-policy.yaml        # 원문 보존·금지 행위·프라이버시 정규식 정책
│   ├── templates.yaml               # 4종 템플릿(essay, experience, technical-note, review)
│   └── publishing.example.yaml      # 블로그 및 GitHub Pages 배포 설정 예시
├── stories/
│   ├── raw/                         # 원본 스토리 보관 (Read-only, 공개 배포 제외)
│   ├── drafts/                      # 편집 초안(.md) 및 Diff/검토 리포트(.review.json)
│   ├── approved/                    # 승인 완료된 게시물 (draft: false)
│   └── records/publications.json    # 발행 이력, 커밋 SHA, URL 매핑
├── skills/                          # story-editor, content-reviewer, blog-publisher 스킬 정의
├── scripts/
│   ├── check_env.py                 # 로컬 도구 및 설정 진단
│   ├── story_editor.py              # 원문 -> 초안 변환 및 Diff 생성
│   ├── validate_post.py             # 메타데이터·코드블록·이미지·민감정보 검증
│   ├── prepare_publish.py           # 승인, allowlist 복사, Hugo 빌드, Git push
│   └── publication_status.py        # GitHub Actions 및 실제 URL 접근 상태 확인
├── app/
│   ├── backend/                     # FastAPI + SQLite 백엔드 (/api/overview, /api/blog/*)
│   └── web/                         # React 19 + Vite + Tailwind CSS v4 프론트엔드
├── site/                            # 공개 배포 대상 Hugo 사이트 및 .github/workflows/hugo.yml
└── tests/test_pipeline.py           # 단위 및 대시보드 API 통합 테스트
```

---

## 3. 실행 및 사용 방법

### A. 통합 웹 대시보드 실행 (권장)

```bash
chmod +x deploy/run_dashboard.sh
./deploy/run_dashboard.sh
```
- 브라우저에서 **`http://localhost:8500`** 접속
- 프론트엔드 수정 시 재빌드:
  ```bash
  cd app/web
  npm run build
  ```

### B. CLI 파이프라인 직접 실행

```bash
# 1. 환경 점검
python3 scripts/check_env.py

# 2. 원문으로부터 초안 및 Diff 리포트 생성
python3 scripts/story_editor.py --input stories/raw/first-test-story.md --template auto

# 3. 초안 품질 및 보안 검증
python3 scripts/validate_post.py --file stories/drafts/first-test-story.md --raw stories/raw/first-test-story.md

# 4. 승인 및 Dry-run 발행 시뮬레이션
python3 scripts/prepare_publish.py --slug first-test-story --approve --dry-run

# 5. 로컬 Hugo 사이트(site/content/posts/) 반영
python3 scripts/prepare_publish.py --slug first-test-story --approve --stage

# 6. 명시적 승인 후 원격 GitHub 저장소 Push
python3 scripts/prepare_publish.py --slug first-test-story --publish --confirm-public-push

# 7. 배포 및 URL 상태 확인
python3 scripts/publication_status.py --slug first-test-story --check-remote
```

### C. 로컬 Hugo 미리보기 (Hugo 설치 시)

```bash
hugo server -D --source site
```

### D. 자동화 테스트 실행

```bash
/mnt/c/Users/User/proj_cdc_mig/.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 4. 안전 및 프라이버시 주의사항

- **공개 저장소 주의:** GitHub Pages 공개 저장소에 push된 게시물은 인터넷 및 검색 엔진에 노출될 수 있습니다.
- **원본 격리:** `stories/raw/`, `stories/drafts/`, `.env`, `var/`는 공개 사이트 경로(`site/content/posts/`)로 복사되지 않으며, allowlist를 통과하고 승인(`approved`)된 글만 반영됩니다.
