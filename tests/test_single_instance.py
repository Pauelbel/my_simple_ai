import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop_assistant.core.single_instance import acquire_instance_lock


class SingleInstanceTests(unittest.TestCase):
    def test_second_lock_is_rejected_until_first_is_released(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            with patch("desktop_assistant.core.single_instance.app_data_dir", return_value=data_dir):
                first = acquire_instance_lock()
                self.assertIsNotNone(first)
                self.addCleanup(first.unlock)
                self.assertIsNone(acquire_instance_lock())

                first.unlock()
                after_release = acquire_instance_lock()
                self.assertIsNotNone(after_release)
                self.addCleanup(after_release.unlock)


if __name__ == "__main__":
    unittest.main()
