#!/usr/bin/env node

const fs = require("node:fs/promises");
const path = require("node:path");

// Keep these thresholds in sync with widget_dicord/axios.js.
const RANKS = [
  { min: 0, name: "Luyện Khí", color: "64748b" },
  { min: 500, name: "Trúc Cơ", color: "10b981" },
  { min: 1200, name: "Kim Đan", color: "eab308" },
  { min: 2100, name: "Nguyên Anh", color: "f97316" },
  { min: 3100, name: "Bán Thần", color: "ef4444" },
  { min: 4200, name: "Chân Thần", color: "a855f7" },
  { min: 5400, name: "Bán Bộ Phi Thăng", color: "6366f1" },
  { min: 6700, name: "Bán Tiên", color: "ec4899" },
  { min: 7500, name: "Chân Tiên", color: "06b6d4" },
];

function getRank(masteredWords) {
  return [...RANKS].reverse().find((rank) => masteredWords >= rank.min) || RANKS[0];
}

function renderBadge(masteredWords) {
  const rank = getRank(masteredWords);
  const name = encodeURIComponent(rank.name.replace(/ /g, "_"));
  return `<img src="https://img.shields.io/badge/${name}-${rank.color}?style=flat" alt="${rank.name}" />`;
}

function replaceBadge(readme, masteredWords) {
  const pattern = /<!-- VOCAB_RANK:START -->[\s\S]*?<!-- VOCAB_RANK:END -->/;
  if (!pattern.test(readme)) {
    throw new Error("Missing VOCAB_RANK markers in README.");
  }
  return readme.replace(pattern, `<!-- VOCAB_RANK:START -->\n${renderBadge(masteredWords)}\n<!-- VOCAB_RANK:END -->`);
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
    console.log("Rank badge is already up to date.");
    return;
  }
  await fs.writeFile(readmePath, nextReadme);
  console.log(`Updated rank badge: ${getRank(masteredWords).name} (${masteredWords} words).`);
}

if (require.main === module) {
  updateBadge().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}

module.exports = { getRank, renderBadge, replaceBadge };
