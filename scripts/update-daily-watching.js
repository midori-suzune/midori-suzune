#!/usr/bin/env node

const fs = require("node:fs/promises");
const path = require("node:path");
const {
  countDailyLearningFiles,
  formatDailyLearning,
  loadDailyLearningData,
  normalizeEntries,
  replaceTaggedSection,
} = require("./update-daily-reading.js");

const START_TAG = "<!-- DAILY_WATCHING:START -->";
const END_TAG = "<!-- DAILY_WATCHING:END -->";
const DEFAULT_DATA_PATH = "assets/daily-watching.json";

function formatDailyWatching(data, videoCount) {
  const seen = new Set();
  const entries = normalizeEntries(data).filter((entry) => {
    const title = entry.article.normalize("NFKC").trim().replace(/\s+/g, " ").toLowerCase();
    if (seen.has(title)) {
      return false;
    }
    seen.add(title);
    return true;
  });
  return formatDailyLearning(entries, "📺 Daily Watching", "Title", videoCount, "videos");
}

async function updateReadme() {
  const readmePath = path.resolve(process.env.README_PATH || "README.md");
  const dataPath = path.resolve(process.env.DAILY_WATCHING_PATH || DEFAULT_DATA_PATH);
  const data = await loadDailyLearningData(dataPath, process.env.DAILY_WATCHING_FILE);
  const videoCount = await countDailyLearningFiles(dataPath, process.env.DAILY_WATCHING_FILE);
  const readme = await fs.readFile(readmePath, "utf8");
  const nextReadme = replaceTaggedSection(
    readme,
    formatDailyWatching(data, videoCount),
    START_TAG,
    END_TAG,
  );

  if (nextReadme === readme) {
    console.log("Daily Watching is already up to date.");
    return;
  }

  await fs.writeFile(readmePath, nextReadme);
  console.log(`Updated Daily Watching in ${path.relative(process.cwd(), readmePath) || readmePath}.`);
}

if (require.main === module) {
  updateReadme().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}

module.exports = { formatDailyWatching };
