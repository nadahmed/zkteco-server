import unittest

class TestConnection(unittest.TestCase):
    def test_sum(self):
        assert sum([1, 2, 3]) == 6, "Should be 6"

    def test_sum_tuple(self):
        assert sum((1, 2, 3)) == 6, "Should be 6"

# if __name__ == "__main__":
#     unittest.main()