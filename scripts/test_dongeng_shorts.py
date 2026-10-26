"""Unit tests for YouTube Shorts / Stories pipeline integration in Dongeng."""
import unittest
from unittest.mock import MagicMock, patch

from orchestrator.tools.dongeng_publisher import (
    DongengPublishError,
    post_story_to_cms,
)
from orchestrator.graphs.dongeng_pipeline import (
    complete_node,
    curate_video_node,
    ingest_node,
    publish_node,
    sop_validator_node,
    thumbnail_portrait_node,
    trigger_notification_node,
)


class TestDongengShortsPipeline(unittest.TestCase):
    def test_post_story_to_cms_dry_run(self):
        res = post_story_to_cms(
            channel_id="UCtest123",
            title="Kancil Lucu #Shorts",
            video_id="dQw4w9WgXcQ",
            dry_run=True,
        )
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("status"), "dry-run")
        self.assertEqual(res.get("id"), "dQw4w9WgXcQ")
        self.assertEqual(res.get("channel_id"), "UCtest123")

    @patch("httpx.Client.post")
    def test_post_story_to_cms_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "status": "success",
            "message": "Story / Short berhasil ditambahkan!",
            "data": {
                "id": 99,
                "channel_id": "UCtest123",
                "title": "Kancil Lucu #Shorts",
                "videoId": "dQw4w9WgXcQ",
                "published": 1,
            },
        }
        mock_post.return_value = mock_resp

        res = post_story_to_cms(
            channel_id="UCtest123",
            title="Kancil Lucu #Shorts",
            video_id="dQw4w9WgXcQ",
            dry_run=False,
        )
        self.assertTrue(res.get("success"))
        self.assertEqual(res["data"]["id"], 99)

    @patch("httpx.Client.post")
    def test_post_story_to_cms_http_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 405
        mock_resp.text = "Method Not Allowed"
        mock_post.return_value = mock_resp

        with self.assertRaises(DongengPublishError):
            post_story_to_cms(
                channel_id="UCtest123",
                title="Kancil Lucu #Shorts",
                video_id="dQw4w9WgXcQ",
                dry_run=False,
            )

    @patch("orchestrator.graphs.dongeng_pipeline.get_youtube_metadata")
    @patch("orchestrator.graphs.dongeng_pipeline.is_short_video")
    def test_ingest_node_detects_shorts(self, mock_is_short, mock_meta):
        mock_meta.return_value = {
            "title": "Kancil dan Harimau Lucu #Shorts",
            "channel_id": "UCtest123",
            "duration_seconds": 45,
        }
        mock_is_short.return_value = True

        state = {
            "task_id": "task-short-1",
            "video_id": "dQw4w9WgXcQ",
            "input_data": {},
        }
        res = ingest_node(state)
        self.assertEqual(res.get("status"), "processing")
        self.assertTrue(res.get("is_short"))

    def test_curate_video_node_bypasses_category_for_shorts(self):
        state = {
            "task_id": "task-short-2",
            "video_id": "dQw4w9WgXcQ",
            "is_short": True,
            "video_metadata": {
                "title": "Kancil Lucu #Shorts",
                "channel_id": "UCtest123",
            },
        }
        res = curate_video_node(state)
        curation = res.get("curation_result", {})
        self.assertFalse(curation.get("skip"))
        self.assertEqual(curation.get("category_id"), "stories")
        self.assertEqual(curation.get("title"), "Kancil Lucu #Shorts")

    def test_thumbnail_portrait_node_bypassed_for_shorts(self):
        state = {
            "task_id": "task-short-3",
            "video_id": "dQw4w9WgXcQ",
            "is_short": True,
            "curation_result": {"title": "Kancil Lucu #Shorts"},
        }
        res = thumbnail_portrait_node(state)
        self.assertIsNone(res.get("thumbnail_path"))

    def test_sop_validator_node_shorts_validation(self):
        # Valid shorts
        state_valid = {
            "task_id": "task-short-4",
            "video_id": "dQw4w9WgXcQ",
            "is_short": True,
            "video_metadata": {"channel_id": "UCtest123"},
            "curation_result": {"title": "Kancil Lucu #Shorts"},
            "thumbnail_path": None,
        }
        res_valid = sop_validator_node(state_valid)
        self.assertIsNone(res_valid.get("error"))

        # Invalid shorts (missing channel_id)
        state_invalid = {
            "task_id": "task-short-5",
            "video_id": "dQw4w9WgXcQ",
            "is_short": True,
            "video_metadata": {"channel_id": ""},
            "curation_result": {"title": "Kancil Lucu #Shorts"},
            "thumbnail_path": None,
        }
        res_invalid = sop_validator_node(state_invalid)
        self.assertEqual(res_invalid.get("status"), "failed")
        self.assertIn("channel_id kosong", res_invalid.get("error"))

    @patch("orchestrator.graphs.dongeng_pipeline.post_story_to_cms")
    @patch("orchestrator.graphs.dongeng_pipeline.post_to_cms")
    def test_publish_node_routes_to_post_story(self, mock_post_regular, mock_post_story):
        mock_post_story.return_value = {
            "success": True,
            "status": "success",
            "data": {"id": 101},
        }

        state = {
            "task_id": "task-short-6",
            "video_id": "dQw4w9WgXcQ",
            "is_short": True,
            "video_metadata": {"channel_id": "UCtest123"},
            "curation_result": {"title": "Kancil Lucu #Shorts"},
            "input_data": {"dry_run": False},
        }
        res = publish_node(state)
        self.assertEqual(res.get("status"), "processing")
        mock_post_story.assert_called_once()
        mock_post_regular.assert_not_called()

    def test_trigger_notification_bypassed_for_shorts(self):
        state = {
            "task_id": "task-short-7",
            "video_id": "dQw4w9WgXcQ",
            "is_short": True,
            "status": "processing",
            "is_notified": False,
            "cms_post_result": {"data": {"id": 101}},
        }
        res = trigger_notification_node(state)
        self.assertFalse(res.get("is_notified"))
        self.assertEqual(res.get("notification_status"), "skipped_shorts")

    def test_complete_node_summary_for_shorts(self):
        state = {
            "task_id": "task-short-8",
            "video_id": "dQw4w9WgXcQ",
            "is_short": True,
            "status": "completed",
            "curation_result": {"title": "Kancil Lucu #Shorts"},
            "cms_post_result": {"data": {"id": 101}},
        }
        res = complete_node(state)
        self.assertEqual(res.get("status"), "completed")
        summary = res["result"]["summary"]
        self.assertIn("SHORTS/STORY", summary)


if __name__ == "__main__":
    unittest.main()

