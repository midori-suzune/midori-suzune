#!/usr/bin/env node

const fs = require("node:fs/promises");
const path = require("node:path");

// Keep these thresholds in sync with widget_dicord/axios.js.
const RANKS = [
  { min: 0, name: "Luyện Khí", color: "64748b" },
  { min: 500, name: "Trúc Cơ", color: "22c55e" },
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
  const labelWidth = 58;
  const rankWidth = Math.max(100, rank.name.length * 9 + 24);
  const width = labelWidth + rankWidth;
  const rankCenter = labelWidth + rankWidth / 2;

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="28" role="img" aria-label="Rank: ${rank.name}">
  <title>Rank: ${rank.name} — ${masteredWords} mastered words</title>
  <clipPath id="rounded"><rect width="${width}" height="28" rx="5"/></clipPath>
  <g clip-path="url(#rounded)">
    <rect width="${labelWidth}" height="28" fill="#334155"/>
    <rect x="${labelWidth}" width="${rankWidth}" height="28" fill="#${rank.color}"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,DejaVu Sans,sans-serif" font-size="12">
    <text x="${labelWidth / 2}" y="18">RANK</text>
    <text x="${rankCenter}" y="18" font-weight="bold">${rank.name}</text>
  </g>
</svg>
`;
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
  const badgePath = path.join(root, "assets", "rank.svg");
  const badge = renderBadge(masteredWords);
  const previous = await fs.readFile(badgePath, "utf8").catch((error) => {
    if (error.code === "ENOENT") return "";
    throw error;
  });
  if (badge === previous) {
    console.log("Rank badge is already up to date.");
    return;
  }
  await fs.mkdir(path.dirname(badgePath), { recursive: true });
  await fs.writeFile(badgePath, badge);
  console.log(`Updated rank badge: ${getRank(masteredWords).name} (${masteredWords} words).`);
}

if (require.main === module) {
  updateBadge().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}

module.exports = { getRank, renderBadge };
