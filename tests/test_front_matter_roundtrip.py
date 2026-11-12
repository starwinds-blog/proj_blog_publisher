"""Repeated dashboard save/approval must not grow string escape sequences."""
import unittest
from scripts.pipeline_core import build_markdown_post, parse_front_matter


class FrontMatterRoundtripTests(unittest.TestCase):
    def test_repeated_save_and_approval_preserve_description(self):
        description = '첫 줄\n둘째 줄\t"인용"과 C:\\notes\\file, 문자 그대로의 \\n'
        metadata = {'title': '제목', 'description': description}
        body = '```shell\nprintf "hello\\n"\n```'
        for _ in range(20):
            markdown = build_markdown_post(metadata, body)
            metadata, parsed_body, errors = parse_front_matter(markdown)
            self.assertEqual(errors, [])
            self.assertEqual(metadata['description'], description)
            self.assertEqual(parsed_body.strip(), body)

    def test_single_quoted_yaml_keeps_literal_backslashes(self):
        metadata, _, errors = parse_front_matter("---\ntitle: 'It''s literal \\n'\n---\nBody\n")
        self.assertEqual(errors, [])
        self.assertEqual(metadata['title'], "It's literal \\n")
