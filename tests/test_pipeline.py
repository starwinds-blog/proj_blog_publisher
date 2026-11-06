"""Comprehensive unit & integration tests for AI Story-to-Blog Publisher (CLI + FastAPI Dashboard)."""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import scripts.pipeline_core as core
from app.backend.main import app
from scripts.prepare_publish import approve_post, prepare_and_publish
from scripts.story_editor import create_draft_from_raw
from scripts.validate_post import validate_markdown_file


class TestBlogPublisherPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="blog_pub_test_"))
        self.raw_dir = self.temp_dir / "stories" / "raw"
        self.drafts_dir = self.temp_dir / "stories" / "drafts"
        self.approved_dir = self.temp_dir / "stories" / "approved"
        self.records_dir = self.temp_dir / "stories" / "records"
        self.site_dir = self.temp_dir / "site"
        self.site_posts_dir = self.site_dir / "content" / "posts"
        self.site_images_dir = self.site_dir / "static" / "images"
        self.config_dir = self.temp_dir / "config"

        for d in (
            self.raw_dir,
            self.drafts_dir,
            self.approved_dir,
            self.records_dir,
            self.site_posts_dir,
            self.site_images_dir,
            self.config_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

        # Patch paths across modules
        self.patches = [
            patch("scripts.pipeline_core.PROJECT_ROOT", self.temp_dir),
            patch("scripts.pipeline_core.CONFIG_DIR", self.config_dir),
            patch("scripts.pipeline_core.RAW_DIR", self.raw_dir),
            patch("scripts.pipeline_core.DRAFTS_DIR", self.drafts_dir),
            patch("scripts.pipeline_core.APPROVED_DIR", self.approved_dir),
            patch("scripts.pipeline_core.RECORDS_DIR", self.records_dir),
            patch("scripts.pipeline_core.SITE_DIR", self.site_dir),
            patch("scripts.pipeline_core.SITE_POSTS_DIR", self.site_posts_dir),
            patch("scripts.pipeline_core.SITE_IMAGES_DIR", self.site_images_dir),
            patch("scripts.pipeline_core.PUBLICATIONS_FILE", self.records_dir / "publications.json"),
            patch("scripts.story_editor.RAW_DIR", self.raw_dir),
            patch("scripts.story_editor.DRAFTS_DIR", self.drafts_dir),
            patch("scripts.validate_post.PROJECT_ROOT", self.temp_dir),
            patch("scripts.validate_post.SITE_DIR", self.site_dir),
            patch("scripts.validate_post.SITE_IMAGES_DIR", self.site_images_dir),
            patch("scripts.prepare_publish.PROJECT_ROOT", self.temp_dir),
            patch("scripts.prepare_publish.RAW_DIR", self.raw_dir),
            patch("scripts.prepare_publish.DRAFTS_DIR", self.drafts_dir),
            patch("scripts.prepare_publish.APPROVED_DIR", self.approved_dir),
            patch("scripts.prepare_publish.SITE_DIR", self.site_dir),
            patch("scripts.prepare_publish.SITE_POSTS_DIR", self.site_posts_dir),
            patch("app.backend.services.blog_service.PROJECT_ROOT", self.temp_dir),
            patch("app.backend.services.blog_service.RAW_DIR", self.raw_dir),
            patch("app.backend.services.blog_service.DRAFTS_DIR", self.drafts_dir),
            patch("app.backend.services.blog_service.APPROVED_DIR", self.approved_dir),
            patch("app.backend.services.blog_service.SITE_POSTS_DIR", self.site_posts_dir),
            patch("app.backend.api.blog.PROJECT_ROOT", self.temp_dir),
            patch("app.backend.api.blog.DRAFTS_DIR", self.drafts_dir),
            patch("app.backend.api.blog.APPROVED_DIR", self.approved_dir),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self) -> None:
        for p in reversed(self.patches):
            p.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_1_korean_and_codeblock_preservation(self) -> None:
        """1. 한글 본문 교정 시 원본 불변 및 코드 블록 내부 텍스트 100% 보존 검증."""
        raw_content = (
            "# 기술 노트 테스트\n\n"
            "설정이 잘 안되서 몇일 동안 고민했다. 할수있는 방법을 찾았다.\n\n"
            "```bash\n"
            "# 코드 블록 내부의 '되서', '할수있'는 절대 바뀌면 안됨\n"
            "echo \"되서 할수있다\"\n"
            "```\n"
        )
        raw_file = self.raw_dir / "tech-code-test.md"
        raw_file.write_text(raw_content, encoding="utf-8")

        report = create_draft_from_raw(raw_file, template="technical-note", slug_override="tech-code-test")
        draft_file = self.drafts_dir / "tech-code-test.md"

        # Original raw file must remain untouched
        self.assertEqual(raw_file.read_text(encoding="utf-8"), raw_content)

        draft_text = draft_file.read_text(encoding="utf-8")
        # Prose outside code block is polished
        self.assertIn("안되어서 며칠 동안", draft_text)
        self.assertIn("할 수 있는", draft_text)
        # Code block inside is untouched
        self.assertIn('echo "되서 할수있다"', draft_text)

        val = validate_markdown_file(draft_file, raw_file)
        self.assertTrue(val["valid"], f"Expected valid draft, got errors: {val['errors']}")
        self.assertTrue(val["checks"]["raw_code_preserved"])

    def test_2_missing_image_and_secret_blocking(self) -> None:
        """2. 로컬 이미지 누락 및 API 키/토큰 포함 시 검증 실패 및 승인 차단 확인."""
        raw_content = (
            "# 보안 및 이미지 테스트\n\n"
            "아래 이미지는 존재하지 않습니다.\n"
            "![다이어그램](images/non-existent.png)\n\n"
            "실수로 토큰을 적었습니다: ghp_1234567890abcdefghijklmnopqrstuv\n"
        )
        raw_file = self.raw_dir / "secret-post.md"
        raw_file.write_text(raw_content, encoding="utf-8")

        create_draft_from_raw(raw_file, slug_override="secret-post")
        draft_file = self.drafts_dir / "secret-post.md"

        val = validate_markdown_file(draft_file, raw_file)
        self.assertFalse(val["valid"])
        self.assertFalse(val["checks"]["links_and_images_valid"])
        self.assertFalse(val["checks"]["no_secrets_found"])

        # Approval must be blocked
        app_res = approve_post("secret-post")
        self.assertFalse(app_res["ok"])
        self.assertFalse((self.approved_dir / "secret-post.md").exists())

    def test_3_dry_run_duplicate_slug_and_explicit_push_gate(self) -> None:
        """3. Dry-run 시 site/ 미반영, 중복 slug 방지, 명시적 원격 push 승인 게이트 검증."""
        raw_file = self.raw_dir / "safe-story.md"
        raw_file.write_text("# 짧은 회고 메모\n\n오늘 하루를 돌아보며 남기는 짧은 글이다.\n", encoding="utf-8")
        create_draft_from_raw(raw_file, slug_override="safe-story")

        # Step A: Approve + Dry-run -> approved file created, but site/content/posts/ not written
        res_dry = prepare_and_publish("safe-story", approve=True, dry_run=True)
        self.assertTrue(res_dry["ok"])
        self.assertTrue((self.approved_dir / "safe-story.md").exists())
        self.assertFalse((self.site_posts_dir / "safe-story.md").exists())

        # Step B: Stage for real -> copied to site/content/posts/safe-story.md
        res_stage = prepare_and_publish("safe-story", approve=False, dry_run=False)
        self.assertTrue(res_stage["ok"])
        self.assertTrue((self.site_posts_dir / "safe-story.md").exists())

        # Step C: Re-running identical content skips duplicate gracefully
        res_dup_same = prepare_and_publish("safe-story", approve=False, dry_run=False, upsert=False)
        self.assertTrue(res_dup_same["ok"])
        self.assertTrue(res_dup_same.get("duplicate_skipped"))

        # Step D: Modified content with same slug without --upsert is blocked
        app_file = self.approved_dir / "safe-story.md"
        app_file.write_text(app_file.read_text(encoding="utf-8") + "\n추가 문단입니다.\n", encoding="utf-8")
        res_dup_diff = prepare_and_publish("safe-story", approve=False, dry_run=False, upsert=False)
        self.assertFalse(res_dup_diff["ok"])
        self.assertIn("동일한 slug", res_dup_diff.get("error", ""))

        # Step E: Remote publish without confirm_public_push is blocked
        res_unconfirmed = prepare_and_publish(
            "safe-story",
            approve=False,
            dry_run=False,
            upsert=True,
            publish_remote=True,
            confirm_public_push=False,
        )
        self.assertFalse(res_unconfirmed["ok"])
        self.assertIn("confirm-public-push", res_unconfirmed.get("error", ""))

    def test_4_dashboard_api_end_to_end(self) -> None:
        """4. 대시보드 API를 통한 스토리 입력 -> 초안 생성 -> 승인 -> 스테이징 E2E 테스트."""
        client = TestClient(app)

        # Create story via API
        create_resp = client.post(
            "/api/blog/stories",
            json={
                "raw_text": "# 대시보드에서 작성한 첫 글\n\n웹 UI에서 스토리를 입력하면 자동으로 초안이 만들어지니 편하다.",
                "slug": "dashboard-e2e-post",
                "template": "essay",
                "tags": ["대시보드", "테스트"],
            },
        )
        self.assertEqual(create_resp.status_code, 200)
        payload = create_resp.json()
        self.assertEqual(payload["summary"]["slug"], "dashboard-e2e-post")
        self.assertTrue((self.raw_dir / "dashboard-e2e-post.md").exists())
        self.assertTrue((self.drafts_dir / "dashboard-e2e-post.md").exists())

        # Approve via API
        app_resp = client.post("/api/blog/stories/dashboard-e2e-post/approve")
        self.assertEqual(app_resp.status_code, 200)
        self.assertTrue((self.approved_dir / "dashboard-e2e-post.md").exists())

        # Stage via Publish API
        pub_resp = client.post(
            "/api/blog/stories/dashboard-e2e-post/publish",
            json={
                "approve": True,
                "dry_run": False,
                "upsert": True,
                "publish_remote": False,
                "confirm_public_push": False,
            },
        )
        self.assertEqual(pub_resp.status_code, 200)
        pub_data = pub_resp.json()
        self.assertTrue(pub_data["ok"])
        self.assertEqual(pub_data["status"], "staged")
        self.assertTrue((self.site_posts_dir / "dashboard-e2e-post.md").exists())


if __name__ == "__main__":
    unittest.main()
