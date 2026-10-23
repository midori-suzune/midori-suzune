import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import update_anime


def item(media_id):
    return {"updatedAt": media_id, "media": {
        "id": media_id,
        "title": {"english": f"Title {media_id}"},
        "siteUrl": f"https://anilist.co/anime/{media_id}",
    }}


class AnimeBlockTest(unittest.TestCase):
    def test_four_most_recent_cards_and_youtube_cards_survive_update(self):
        anime = [item(index) for index in range(1, 6)]
        manga = [item(index) for index in (6, 7)]
        with tempfile.TemporaryDirectory() as directory:
            readme = Path(directory) / "README.md"
            assets = Path(directory) / "assets"
            with patch.object(update_anime, "create_card", return_value=b"card"):
                block, _ = update_anime.render_block(anime, manga)
                readme.write_text(block.replace(
                    "<!-- BEGIN YOUTUBE-CARDS -->\n<!-- END YOUTUBE-CARDS -->",
                    "<!-- BEGIN YOUTUBE-CARDS -->\n<a href=\"https://youtube.com/watch?v=1\">Video</a>\n<!-- END YOUTUBE-CARDS -->",
                ))
                with patch.object(update_anime, "README", readme), \
                     patch.object(update_anime, "ASSETS", assets), \
                     patch.object(update_anime, "fetch_items", return_value=(anime, manga)):
                    update_anime.main()

            updated = readme.read_text()
            anime_rows = updated.split('<p align="center">\n')[1].split("\n</p>")[0].split("\n<br />\n")
            self.assertEqual(len(anime_rows), 1)
            self.assertEqual(anime_rows[0].count('<img src="assets/'), 4)
            self.assertIn('assets/manga/7.png', anime_rows[0])
            self.assertNotIn('assets/anime/3.png', anime_rows[0])
            self.assertIn('<a href="https://youtube.com/watch?v=1">Video</a>', updated)


if __name__ == "__main__":
    unittest.main()
