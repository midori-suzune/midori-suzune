import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import update_anime


def item(media_id):
    return {"media": {
        "id": media_id,
        "title": {"english": f"Title {media_id}"},
        "siteUrl": f"https://anilist.co/anime/{media_id}",
    }}


class AnimeBlockTest(unittest.TestCase):
    def test_four_cards_per_row_and_youtube_cards_survive_update(self):
        anime = [item(index) for index in range(1, 6)]
        with tempfile.TemporaryDirectory() as directory:
            readme = Path(directory) / "README.md"
            assets = Path(directory) / "assets"
            with patch.object(update_anime, "create_card", return_value=b"card"):
                block, _ = update_anime.render_block(anime, [])
                readme.write_text(block.replace(
                    "<!-- BEGIN YOUTUBE-CARDS -->\n<!-- END YOUTUBE-CARDS -->",
                    "<!-- BEGIN YOUTUBE-CARDS -->\n<a href=\"https://youtube.com/watch?v=1\">Video</a>\n<!-- END YOUTUBE-CARDS -->",
                ))
                with patch.object(update_anime, "README", readme), \
                     patch.object(update_anime, "ASSETS", assets), \
                     patch.object(update_anime, "fetch_items", return_value=(anime, [])):
                    update_anime.main()

            updated = readme.read_text()
            anime_rows = updated.split('<p align="center">\n')[1].split("\n</p>")[0].split("\n<br />\n")
            self.assertEqual([row.count('<img src="assets/anime/') for row in anime_rows], [4, 1])
            self.assertEqual(updated.count('width="160"'), 5)
            self.assertIn('<a href="https://youtube.com/watch?v=1">Video</a>', updated)


if __name__ == "__main__":
    unittest.main()
