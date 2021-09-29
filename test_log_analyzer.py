from unittest import TestCase
import unittest


class TryTesting(TestCase):

    def test_always_passes(self):
        self.assertTrue(True)

    def test_always_fails(self):
        self.assertTrue(False)


if __name__ == '__main__':
    unittest.main()
