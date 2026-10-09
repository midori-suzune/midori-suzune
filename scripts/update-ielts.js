#!/usr/bin/env node

const fs = require("node:fs/promises");
const path = require("node:path");
const {
  listMarkdownFiles,
  countVocabEntries,
  gitCommitInfo,
  dateFromTimestamp,
  formatDate,
  replaceTaggedSection: replaceSection,
} = require("./update-daily-reading.js");

const START_TAG = "<!-- YOUPASS:START -->";
const END_TAG = "<!-- YOUPASS:END -->";
const SOURCES = [
  { name: "Reading", directory: "Review Reading Test" },
  { name: "Listening", directory: "Review Listening Test" },
];
const SUPPORT_FILES = new Set(["Revision Note.md", "IELTS_READING_ANALYSIS_PATTERN.md"]);

function activityLimit() {
  const limit = Number(process.env.IELTS_ACTIVITY_LIMIT || 4);
  return Number.isFinite(limit) && limit >= 1 ? Math.floor(limit) : 4;
}

async function loadReviewActivity(sourceRoot) {
  const groups = await Promise.all(SOURCES.map(async (source) => {
    const directory = path.join(sourceRoot, source.directory);
    const files = await listMarkdownFiles(directory);
    return Promise.all(files.filter((file) => !SUPPORT_FILES.has(path.basename(file))).map(async (file) => {
      const commit = gitCommitInfo(file, sourceRoot);
      const stat = await fs.stat(file);
      const timestamp = commit.timestamp || Math.floor(stat.mtimeMs / 1000);
      return {
        date: formatDate(commit.timestamp ? commit.date : dateFromTimestamp(timestamp)),
        skill: source.name,
        title: path.basename(file, path.extname(file)),
        vocab: countVocabEntries(await fs.readFile(file, "utf8")),
        timestamp,
        file: path.relative(sourceRoot, file),
      };
    }));
  }));
  return groups.flat()
    .sort((left, right) => right.timestamp - left.timestamp || left.file.localeCompare(right.file))
    .slice(0, activityLimit());
}

function fitEnd(value, width) {
  const text = String(value);
  return text.length > width ? text.slice(0, width - 1) + "…" : text.padEnd(width);
}

function formatActivity(items) {
  const lines = ["📋 Recent Activity", ""];
  if (items.length === 0) {
    return [...lines, "No activity yet."].join("\n");
  }
  const row = (date, skill, title, vocab) => [
    fitEnd(date, 9),
    fitEnd(skill, 12),
    fitEnd(title, 52),
    String(vocab).padStart(10),
  ].join("   ").trimEnd();
  lines.push(row("Date", "Skill", "Title", "New Vocab"), "─".repeat(100));
  items.forEach((item, index) => {
    if (index > 0) lines.push("");
    lines.push(row(item.date, item.skill, item.title, `${item.vocab} ${item.vocab === 1 ? "word" : "words"}`));
  });
  return lines.join("\n");
}

function replaceTaggedSection(readme, content) {
  return replaceSection(readme, content, START_TAG, END_TAG);
}

async function updateReadme() {
  const readmePath = path.resolve(process.env.README_PATH || "README.md");
  const sourceRoot = path.resolve(process.env.IELTS_REVIEW_PATH || "practice-english-daily");
  const items = await loadReviewActivity(sourceRoot);
  const content = ["```text", formatActivity(items), "```"].join("\n");
  const readme = await fs.readFile(readmePath, "utf8");
  const nextReadme = replaceTaggedSection(readme, content);
  if (nextReadme === readme) {
    console.log("Recent Activity is already up to date.");
    return;
  }
  await fs.writeFile(readmePath, nextReadme);
  console.log("Updated Recent Activity from review Markdown files.");
}

if (process.argv.includes("--help") || process.argv.includes("-h")) {
  console.log("Usage: node scripts/update-ielts.js\n\nIELTS_REVIEW_PATH: Practice-English-Daily repository path (default: practice-english-daily).\nIELTS_ACTIVITY_LIMIT: Number of recent rows (default: 4).\nREADME_PATH: README file path (default: README.md).\nDAILY_READING_TIME_ZONE: Time zone for commit dates (default: Asia/Ho_Chi_Minh).");
} else if (require.main === module) {
  updateReadme().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}

module.exports = { loadReviewActivity, formatActivity, replaceTaggedSection };
