#!/usr/bin/env node

const fs = require("node:fs/promises");
const path = require("node:path");

async function formatWakaBadges() {
  const readmePath = path.resolve(process.env.README_PATH || "README.md");
  const readme = await fs.readFile(readmePath, "utf8");
  const start = "<!--START_SECTION:waka-->";
  const end = "<!--END_SECTION:waka-->";
  const startIndex = readme.indexOf(start);
  const endIndex = readme.indexOf(end, startIndex + start.length);
  if (startIndex === -1 || endIndex === -1) {
    throw new Error("Missing WakaTime section markers in README.");
  }

  const section = readme.slice(startIndex + start.length, endIndex);
  const badges = /^(!\[Code Time\]\([^\r\n]+\))\r?\n(?:[ \t]*\r?\n)*(!\[AI Code Time\]\([^\r\n]+\))/m;
  const formatted = section.replace(badges, "$1 $2");
  if (formatted !== section) {
    await fs.writeFile(readmePath, readme.slice(0, startIndex + start.length) + formatted + readme.slice(endIndex));
    console.log("Aligned WakaTime badges on one line.");
  }
}

if (require.main === module) {
  formatWakaBadges().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}

module.exports = { formatWakaBadges };
