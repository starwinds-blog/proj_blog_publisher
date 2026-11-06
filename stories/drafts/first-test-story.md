---
title: "[테스트 샘플] 로컬 우선 AI 블로그 퍼블리셔 시작하기"
date: 2026-11-06T16:37:16+09:00
draft: false
description: "이 글은 AI Story-to-Blog Publisher 워크플로를 검증하기 위한 명백한 테스트 콘텐츠입니다. 외부에 공개되어도 무방한 샘플 데이터로 작성되었습니다."
tags: ["자동화", "AI", "개발노트", "회고", "리뷰"]
categories: ["experience"]
slug: "first-test-story"
---

## 배경과 상황

이 글은 AI Story-to-Blog Publisher 워크플로를 검증하기 위한 명백한 테스트 콘텐츠입니다. 외부에 공개되어도 무방한 샘플 데이터로 작성되었습니다.

## 진행 과정

평소에 떠오르는 생각이나 기술 검토 메모를 자유 형식으로 적어두면 나중에 다시 정리하기가 쉽지 않았다. 맞춤법이 틀리거나 문단이 길어지면 블로그에 올리기 전에 손이 많이 가서 작성을 미루게 되어서 아쉬웠다.

이번에는 원본 텍스트 파일을 `stories/raw/`에 그대로 보존하면서, 편집 규칙에 따라 Front Matter와 문단 호흡만 다듬어 주는 로컬 파이프라인과 대시보드를 구성했다.

아래처럼 코드 블록 안의 명령어나 들여쓰기는 교정 대상에서 제외하고 그대로 보존할 수 있다.

```bash
python3 scripts/check_env.py
python3 scripts/story_editor.py --input stories/raw/first-test-story.md --template experience
python3 scripts/validate_post.py --file stories/drafts/first-test-story.md --raw stories/raw/first-test-story.md
```

## 결과 및 배운 점

어쨌든 가장 중요한 원칙은 AI가 내 문체를 멋대로 덮어쓰거나 없는 사실을 지어내지 않도록 승인 게이트를 두는 것이다. 앞으로 메모가 쌓일 때마다 가볍게 초안을 만들고 대시보드에서 Diff를 비교한 뒤 발행해 볼 생각이다.
