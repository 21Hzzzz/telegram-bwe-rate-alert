import unittest

from rate_monitor import BurstDetector


class BurstDetectorTests(unittest.TestCase):
    def test_fifth_message_in_minute_triggers(self):
        detector = BurstDetector()
        results = [detector.record(timestamp) for timestamp in (0, 5, 10, 15, 59)]
        self.assertEqual(results, [False, False, False, False, True])

    def test_four_messages_do_not_trigger(self):
        detector = BurstDetector()
        self.assertFalse(any(detector.record(timestamp) for timestamp in (0, 5, 10, 15)))

    def test_burst_alerts_only_once(self):
        detector = BurstDetector()
        for timestamp in (0, 1, 2, 3):
            self.assertFalse(detector.record(timestamp))
        self.assertTrue(detector.record(4))
        self.assertFalse(detector.record(5))
        self.assertFalse(detector.record(30))

    def test_new_burst_after_window_expires(self):
        detector = BurstDetector()
        for timestamp in (0, 1, 2, 3):
            detector.record(timestamp)
        self.assertTrue(detector.record(4))
        self.assertFalse(detector.record(65))
        for timestamp in (66, 67, 68):
            self.assertFalse(detector.record(timestamp))
        self.assertTrue(detector.record(69))

    def test_window_boundary_is_exclusive(self):
        detector = BurstDetector()
        for timestamp in (0, 1, 2, 3):
            detector.record(timestamp)
        self.assertFalse(detector.record(60))


if __name__ == "__main__":
    unittest.main()
