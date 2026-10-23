from io import BytesIO
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from scripts import update_youtube


CARDS = '''<a href="https://www.youtube.com/watch?v=1VQNMDSzWpE">
<picture><img src="https://ytcards.demolab.com/?id=1VQNMDSzWpE&amp;duration=362" alt="A title &amp; more"></picture>
</a>
<a href="https://www.youtube.com/watch?v=-IVhkLjGDEA">
<picture><img src="https://ytcards.demolab.com/?id=-IVhkLjGDEA&amp;duration=17376" alt="Another video"></picture>
</a>'''


class YouTubeCardsTest(unittest.TestCase):
    def test_playlist_output_and_portrait_images(self):
        image = Image.new("RGB", (320, 180), "#ef4444")
        jpeg = BytesIO()
        image.save(jpeg, format="JPEG")
        with tempfile.TemporaryDirectory() as directory:
            readme = Path(directory) / "README.md"
            assets = Path(directory) / "assets" / "youtube"
            readme.write_text(
                "<!--ANIME_START-->\n<p align=\"center\">\n"
                f"{update_youtube.START}\nOld cards\n{update_youtube.END}\n"
                "</p>\n<!--ANIME_END-->"
            )
            with patch.object(update_youtube, "README", readme), \
                 patch.object(update_youtube, "ASSETS", assets), \
                 patch.object(update_youtube, "get_views", return_value={"1VQNMDSzWpE": 198300}), \
                 patch.object(update_youtube.urllib.request, "urlopen", side_effect=lambda *args, **kwargs: BytesIO(jpeg.getvalue())), \
                 patch.dict(update_youtube.os.environ, {"YOUTUBE_CARDS": CARDS}):
                update_youtube.main()
                first = readme.read_text()
                update_youtube.main()
                self.assertEqual(readme.read_text(), first)

            self.assertIn('alt="A title &amp; more"', first)
            self.assertEqual(first.count('width="160" height="224"'), 2)
            self.assertEqual(first.count(update_youtube.START), 1)
            self.assertIn("<!--ANIME_START-->", first)
            for video_id in ("1VQNMDSzWpE", "-IVhkLjGDEA"):
                with Image.open(assets / f"{video_id}.png") as card:
                    self.assertEqual(card.size, (320, 448))

    def test_empty_or_invalid_playlist_does_not_replace_cards(self):
        with self.assertRaises(ValueError):
            update_youtube.get_videos("")
        with self.assertRaises(ValueError):
            update_youtube.get_videos('<a href="https://example.com/?v=1VQNMDSzWpE">Not YouTube</a>')


if __name__ == "__main__":
    unittest.main()
