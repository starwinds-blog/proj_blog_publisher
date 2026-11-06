# AI Story-to-Blog Publisher — Agent Operating Instructions (AGENTS.md)

이 저장소는 사용자의 자유 형식 스토리/메모를 블로그 글로 편집·검토하고, 명시적 승인 후 Hugo + GitHub Pages로 발행하는 로컬 우선 워크플로 및 통합 Web Dashboard(`app/`)를 포함합니다.

## 1. 핵심 원칙 (절대 규칙)

1. **원문 보존 (Read-only Raw):**
   - `stories/raw/`에 저장된 원본 파일은 절대 덮어쓰거나 삭제하지 않는다.
   - 편집 결과물은 항상 `stories/drafts/<slug>.md`와 변경 리포트(`stories/drafts/<slug>.review.json`)로 별도 생성한다.
2. **의미·화자 보존 및 허위 정보 금지:**
   - 작성자의 1인칭 시점, 어조, 감정, 불확실성을 유지하며 과장하거나 단정하지 않는다.
   - 원문에 없는 날짜, 수치, 통계, 인용, 외부 링크, 이미지를 임의로 지어내지 않는다.
   - 사실 확인이 필요한 부분은 `[검증 필요]` 태그로 표시하고 `suggestions` 목록으로 분리한다.
3. **코드 블록 및 기술 식별자 보호:**
   - 펜스 코드 블록(```` ``` ````) 내부의 텍스트, 들여쓰기, JSON/YAML/Shell 명령어는 자연어 교정 대상에서 제외한다.
4. **프라이버시 및 민감정보 차단:**
   - API 키, 토큰, 비밀번호, 이메일, 전화번호, 사내 비공개 URL 등이 감지되면 자동 승인을 차단한다.
5. **명시적 승인 게이트 (Human-in-the-Loop):**
   - 사용자 승인(`approve`) 전에는 `stories/approved/` 또는 `site/content/posts/`로 복사하지 않는다.
   - 원격 GitHub 저장소로의 `git push`는 반드시 사용자의 명시적 승인(`--publish --confirm-public-push` 또는 대시보드 Publish 승인)이 있을 때만 수행한다.
   - 기본 실행 모드는 항상 `--dry-run`이다.

## 2. 디렉토리 역할

- `stories/raw/`: 사용자 입력 원문 (절대 공개 배포 금지)
- `stories/drafts/`: 편집 초안(`.md`) 및 변경 요약/Diff 리포트(`.review.json`)
- `stories/approved/`: 승인 완료된 게시물 (`draft: false`)
- `stories/records/`: 발행 이력(`publications.json`) 및 상태 추적
- `config/`: 편집 정책(`editorial-policy.yaml`), 템플릿(`templates.yaml`), 배포 설정(`publishing.example.yaml`)
- `scripts/`: CLI 및 대시보드 백엔드가 공유하는 결정론적 파이프라인 스크립트
- `site/`: 공개 배포용 Hugo 사이트 (`content/posts/`, `hugo.toml`, `.github/workflows/hugo.yml`)
- `app/`: FastAPI 백엔드(`app/backend`) + React 19 프론트엔드(`app/web`) 통합 대시보드

## 3. 표준 명령어

- 환경 점검: `python3 scripts/check_env.py`
- 초안 생성: `python3 scripts/story_editor.py --input stories/raw/<file> --template auto`
- 게시물 검증: `python3 scripts/validate_post.py --file stories/drafts/<slug>.md --raw stories/raw/<file>`
- 승인 및 발행 준비 (Dry-run): `python3 scripts/prepare_publish.py --slug <slug> --approve --dry-run`
- 발행 상태 확인: `python3 scripts/publication_status.py --slug <slug>`
- 통합 대시보드 실행: `./deploy/run_dashboard.sh`
