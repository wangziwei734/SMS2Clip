import sys
import threading
import unittest
import uuid

from SMS2Clip.single_instance import ManagerInstance


@unittest.skipUnless(sys.platform == "win32", "Windows named events only")
class ManagerInstanceTests(unittest.TestCase):
    def test_second_instance_activates_the_first_manager(self):
        suffix = uuid.uuid4().hex
        mutex_name = f"Local\\SMS2Clip.Test.{suffix}"
        event_name = f"Local\\SMS2Clip.Test.{suffix}.Activate"
        first = ManagerInstance(mutex_name=mutex_name, event_name=event_name)
        second = None
        try:
            self.assertFalse(first.already_running)
            second = ManagerInstance(mutex_name=mutex_name, event_name=event_name)
            self.assertTrue(second.already_running)

            activated = threading.Event()
            first.wait_for_activation(activated.set)
            self.assertTrue(second.signal_existing())
            self.assertTrue(activated.wait(2))
        finally:
            if second is not None:
                second.close()
            first.close()


if __name__ == "__main__":
    unittest.main()
