#!/usr/bin/env node

const fs = require("node:fs/promises");
const path = require("node:path");

const START_TAG = "<!-- OPENQUIZ_STATS:START -->";
const END_TAG = "<!-- OPENQUIZ_STATS:END -->";

function isMondayInVietnam(date = new Date()) {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    weekday: "short",
  }).format(date) === "Mon";
}

function resetOpenQuizStats(readme, isMonday) {
  const start = readme.indexOf(START_TAG);
  const end = readme.indexOf(END_TAG, start + START_TAG.length);
  if (start === -1 || end === -1) {
    throw new Error("Missing OPENQUIZ_STATS markers in README.");
  }

  const section = readme.slice(start + START_TAG.length, end);
  const studyBlock = /```text\r?\n⏱️ OpenQuiz Study Time\r?\n[\s\S]*?\r?\n```/;
  if (!studyBlock.test(section)) {
    throw new Error("Missing OpenQuiz Study Time block in README.");
  }

  const updatedSection = section.replace(studyBlock, (block) => {
    const todayLine = /^([ \t]*Today[ \t]+)[^\r\n]+$/m;
    const weekLine = /^([ \t]*This Week[ \t]+)[^\r\n]+$/m;
    if (!todayLine.test(block) || !weekLine.test(block)) {
      throw new Error("Missing Today or This Week in OpenQuiz Study Time block.");
    }

    const resetToday = block.replace(todayLine, (_, prefix) => `${prefix}0 mins`);
    return isMonday ? resetToday.replace(weekLine, (_, prefix) => `${prefix}0 mins`) : resetToday;
  });

  return readme.slice(0, start + START_TAG.length) + updatedSection + readme.slice(end);
}

async function main() {
  const readmePath = path.resolve(process.env.README_PATH || path.join(__dirname, "..", "README.md"));
  const readme = await fs.readFile(readmePath, "utf8");
  const updated = resetOpenQuizStats(readme, isMondayInVietnam());
  if (updated === readme) {
    console.log("OpenQuiz study time is already reset.");
    return;
  }

  await fs.writeFile(readmePath, updated);
  console.log("Reset OpenQuiz Today (and This Week on Monday).");
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}

module.exports = { isMondayInVietnam, resetOpenQuizStats };
