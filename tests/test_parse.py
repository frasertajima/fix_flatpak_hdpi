import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from flatpak_hidpi import parse_mutter_scale

# Trimmed from a real GetCurrentState reply (laptop panel at 1.67x).
ONE = "(uint32 12, [...], [(0, 0, 1.6666666269302368, uint32 0, true, [('eDP-1', 'LGD', '0x06aa', '0x00000000')], {})], {})"
TWO = ("[(0, 0, 2.0, uint32 0, false, [('DP-1', 'A', 'B', 'C')], {}), "
       "(3840, 0, 1.25, uint32 0, true, [('eDP-1', 'LGD', '0x06aa', '0x0')], {})]")

class T(unittest.TestCase):
    def test_single(self): self.assertAlmostEqual(parse_mutter_scale(ONE), 1.66667, places=4)
    def test_primary_wins(self): self.assertEqual(parse_mutter_scale(TWO), 1.25)
    def test_garbage(self): self.assertIsNone(parse_mutter_scale("nonsense"))

if __name__ == "__main__":
    unittest.main()
