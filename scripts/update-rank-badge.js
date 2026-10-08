#!/usr/bin/env node

const fs = require("node:fs/promises");
const path = require("node:path");

// Keep these thresholds in sync with widget_dicord/axios.js.
const RANKS = [
  { min: 0, name: "Luyện Khí" },
  { min: 500, name: "Trúc Cơ" },
  { min: 1200, name: "Kim Đan" },
  { min: 2100, name: "Nguyên Anh" },
  { min: 3100, name: "Bán Thần" },
  { min: 4200, name: "Chân Thần" },
  { min: 5400, name: "Bán Bộ Phi Thăng" },
  { min: 6700, name: "Bán Tiên" },
  { min: 7500, name: "Chân Tiên" },
];

function getRank(masteredWords) {
  return [...RANKS].reverse().find((rank) => masteredWords >= rank.min) || RANKS[0];
}

function renderProgress(masteredWords) {
  const rank = getRank(masteredWords);
  const nextRank = RANKS[RANKS.indexOf(rank) + 1];
  if (!nextRank) {
    return ["```text", `${rank.name}  ${"⣿".repeat(30)}  100.00%  (${masteredWords} words) — Đã đạt rank cao nhất`, "```"].join("\n");
  }

  const percent = Math.max(0, Math.min(100, masteredWords / nextRank.min * 100));
  const filled = Math.round(percent / 100 * 30);
  const bar = "⣿".repeat(filled) + "⣀".repeat(30 - filled);
  return ["```text", `${rank.name} → ${nextRank.name}  ${bar}  ${percent.toFixed(2)}%  (${masteredWords} / ${nextRank.min})`, "```"].join("\n");
}

function replaceBadge(readme, masteredWords) {
  const pattern = /<!-- VOCAB_RANK:START -->[\s\S]*?<!-- VOCAB_RANK:END -->/;
  if (!pattern.test(readme)) {
    throw new Error("Missing VOCAB_RANK markers in README.");
  }
  return readme.replace(pattern, `<!-- VOCAB_RANK:START -->\n${renderProgress(masteredWords)}\n<!-- VOCAB_RANK:END -->`);
}

async function updateBadge() {
  const root = path.resolve(__dirname, "..");
  const readmePath = path.resolve(process.env.README_PATH || path.join(root, "README.md"));
  const readme = await fs.readFile(readmePath, "utf8");
  const section = readme.match(/<!-- OPENQUIZ_STATS:START -->([\s\S]*?)<!-- OPENQUIZ_STATS:END -->/);
  const match = section?.[1].match(/Mastered:\s*(\d+)\s*words/i);
  if (!match) {
    throw new Error("Missing Mastered word count in OPENQUIZ_STATS section.");
  }

  const masteredWords = Number(match[1]);
  const nextReadme = replaceBadge(readme, masteredWords);
  if (nextReadme === readme) {
    console.log("Rank progress is already up to date.");
    return;
  }
  await fs.writeFile(readmePath, nextReadme);
  console.log(`Updated rank progress: ${getRank(masteredWords).name} (${masteredWords} words).`);
}

if (require.main === module) {
  updateBadge().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}

module.exports = { getRank, renderProgress, replaceBadge };
