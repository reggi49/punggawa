"""Test suite for CMS Notifier tool and Dongeng Notification Node."""
import unittest
from unittest.mock import MagicMock, patch

from orchestrator.tools.cms_notifier import trigger_post_notification
from orchestrator.graphs.dongeng_pipeline import trigger_notification_node


class TestCmsNotifier(unittest.TestCase):
    def test_invalid_post_id(self):
        # ID string alfabet / kosong tidak boleh memicu HTTP request
        res1 = trigger_post_notification("")
        self.assertFalse(res1["success"])
        self.assertIn("Invalid post_id", res1["error"])

        res2 = trigger_post_notification("dQw4w9WgXcQ")  # YouTube ID, bukan database ID
        self.assertFalse(res2["success"])
        self.assertIn("Invalid post_id", res2["error"])

    @patch("requests.get")
    def test_successful_notification_dispatch_302(self, mock_get):
        # Laravel sendnotification returns redirect (302) or 200 after redirect
        mock_resp = MagicMock()
        mock_resp.status_code = 302
        mock_resp.url = "https://bogorstore.com/agoose/posts"
        mock_get.return_value = mock_resp

        res = trigger_post_notification(1106)
        self.assertTrue(res["success"])
        self.assertEqual(res["post_id"], 1106)
        self.assertEqual(res["mode"], "smart")
        self.assertEqual(res["status_code"], 302)
        mock_get.assert_called_once()
        called_url = mock_get.call_args[0][0]
        self.assertIn("/posts/sendnotification/1106", called_url)
        called_params = mock_get.call_args[1].get("params")
        self.assertEqual(called_params, {"mode": "smart"})

    @patch("requests.get")
    def test_smart_anti_collision_parameters(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://bogorstore.com/agoose/posts"
        mock_get.return_value = mock_resp

        # Test delay mode
        res_delay = trigger_post_notification(1106, mode="delay", delay_minutes=60)
        self.assertTrue(res_delay["success"])
        self.assertEqual(mock_get.call_args[1]["params"], {"mode": "delay", "delay": 60})

        # Test specific time mode
        res_specific = trigger_post_notification(1106, mode="specific", schedule_time="19:30")
        self.assertTrue(res_specific["success"])
        self.assertEqual(mock_get.call_args[1]["params"], {"mode": "specific", "time": "19:30"})

    @patch("requests.get")
    def test_cms_server_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_get.return_value = mock_resp

        res = trigger_post_notification(99999)
        self.assertFalse(res["success"])
        self.assertEqual(res["status_code"], 500)
        self.assertIn("HTTP 500", res["error"])

    def test_node_guards_skip_on_failed_state(self):
        state = {
            "task_id": "test-1",
            "status": "failed",
            "is_notified": False,
            "cms_post_result": {"data": {"id": 1106}},
        }
        res = trigger_notification_node(state)
        self.assertFalse(res.get("is_notified"))

    def test_node_guards_skip_on_dry_run(self):
        state = {
            "task_id": "test-2",
            "status": "processing",
            "is_notified": False,
            "input_data": {"dry_run": True},
            "cms_post_result": {"status": "dry-run", "id": "dQw4w9WgXcQ"},
        }
        res = trigger_notification_node(state)
        self.assertFalse(res.get("is_notified"))
        self.assertEqual(res.get("notification_status"), "skipped_dry_run")

    def test_node_guards_skip_on_non_numeric_id(self):
        state = {
            "task_id": "test-3",
            "status": "processing",
            "is_notified": False,
            "input_data": {},
            "cms_post_result": {"id": "youtube_id_only"},
        }
        res = trigger_notification_node(state)
        self.assertFalse(res.get("is_notified"))
        self.assertEqual(res.get("notification_status"), "skipped_invalid_id")

    @patch("orchestrator.graphs.dongeng_pipeline.trigger_post_notification")
    def test_node_success_with_valid_post_id(self, mock_trigger):
        mock_trigger.return_value = {
            "success": True,
            "post_id": 1106,
            "status_code": 302,
            "message": "Push notification job dispatched",
        }
        state = {
            "task_id": "test-4",
            "status": "processing",
            "is_notified": False,
            "input_data": {},
            "cms_post_result": {
                "status": "success",
                "message": "Post berhasil dibuat via API",
                "data": {"id": 1106, "title": "Kancil dan Buaya"},
            },
            "curation_result": {"title": "Kancil dan Buaya"},
        }
        res = trigger_notification_node(state)
        self.assertTrue(res.get("is_notified"))
        self.assertEqual(res.get("notification_status"), "scheduled")
        mock_trigger.assert_called_once_with(
            post_id=1106,
            mode="smart",
            delay_minutes=None,
            schedule_time=None,
        )


if __name__ == "__main__":
    unittest.main()
