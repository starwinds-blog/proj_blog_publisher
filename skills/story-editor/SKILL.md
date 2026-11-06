---
name: story-editor
description: 자유 형식 스토리/메모를 원문 의미를 보존하며 Hugo Markdown + YAML Front Matter 초안으로 편집합니다.
---

# Story Editor Skill

## 목적
`stories/raw/`의 자유 형식 텍스트/Markdown을 읽어 문법·맞춤법·문단 구조를 정돈하고, 글의 성격에 맞는 템플릿(`essay`, `experience`, `technical-note`, `review`)과 Hugo Front Matter를 적용하여 `stories/drafts/<slug>.md`를 생성합니다.

## 필수 편집 규칙
1. **원문 불변:** `stories/raw/` 파일은 절대 수정하지 않는다.
2. **화자 및 의미 유지:** 작성자의 1인칭 시점, 감정, 유보적 표현("아마도", "느꼈다")을 단정적 사실로 왜곡하지 않는다.
3. **허위 사실 생성 금지:** 원문에 없는 수치, 날짜, 외부 링크, 인용을 추가하지 않는다. 확인이 필요한 항목은 `[검증 필요]`로 표시하고 별도 `suggestions` 배열에 기록한다.
4. **코드 블록 보호:** ```` ``` ```` 내부의 코드, 명령어, 설정값, 들여쓰기는 일절 변경하지 않는다.
5. **기계적 소제목 남발 금지:** 짧은 서사형 글(`essay`)은 무리하게 H2/H3로 쪼개지 않고 자연스러운 문단 호흡을 유지한다.

## 실행 도구 연계
- CLI: `python3 scripts/story_editor.py --input stories/raw/<filename> --template auto`
- 생성 산출물:
  - `stories/drafts/<slug>.md` (`draft: true` 기본값)
  - `stories/drafts/<slug>.review.json` (변경 요약, unified diff, fact-check 항목, 제안 사항)
