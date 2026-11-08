import sys
import types
import unittest
from unittest.mock import Mock, patch

from image_refpack.resolution import LSResolutionSelector


class Tensor:
    def __init__(self, shape):
        self.shape = shape
        self.ndim = len(shape)


class ResolutionSelectorTests(unittest.TestCase):
    def setUp(self):
        context = patch.dict(sys.modules, {"torch": types.SimpleNamespace(Tensor=Tensor)})
        context.start()
        self.addCleanup(context.stop)

    def test_resolution_selector_original_dimensions(self):
        node = LSResolutionSelector()
        for count in (1, 3):
            self.assertEqual(node.select("1:1 (Square)", 16.0, 32, True,
                Tensor((count, 713, 1237, 3)))["result"], (1248, 704))
        self.assertEqual(node.select("1:1 (Square)", 16.0, 8, True,
            Tensor((1, 713, 1237, 3)))["result"], (1240, 712))
        self.assertEqual(node.select("1:1 (Square)", 16.0, 32, True,
            Tensor((1, 704, 1248, 3)))["result"], (1248, 704))
        self.assertEqual(node.select("1:1 (Square)", 16.0, 32, True,
            Tensor((1, 1, 1, 3)))["result"], (32, 32))
        for image in (None, "bad", Tensor((0, 713, 1237, 3)), Tensor((1, 0, 1237, 3))):
            with self.subTest(image=image), self.assertRaisesRegex(ValueError, "non-empty IMAGE"):
                node.select("1:1 (Square)", 1.0, 8, True, image)

    def test_resolution_selector_delegates_to_native(self):
        execute = Mock(return_value=(3552, 4736))
        native = types.SimpleNamespace(ResolutionSelector=types.SimpleNamespace(execute=execute))
        with patch.dict(sys.modules, {"comfy_extras.nodes_resolution": native}):
            for image in (None, Tensor((1, 713, 1237, 3))):
                result = LSResolutionSelector().select("3:4 (Portrait Standard)", 16.0, 32, False, image)
                self.assertEqual(result["result"], (3552, 4736))
                self.assertEqual(result["ui"], {"width": [3552], "height": [4736]})
                execute.assert_called_with("3:4 (Portrait Standard)", 16.0, 32)

