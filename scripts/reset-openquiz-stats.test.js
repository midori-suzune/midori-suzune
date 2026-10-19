const assert = require("node:assert/strict");
const { test } = require("node:test");
const { isMondayInVietnam, resetOpenQuizStats } = require("./reset-openquiz-stats.js");

const readme = `Before
<!-- OPENQUIZ_STATS:START -->
Mastered: 715 words

\`\`\`text
⏱️ OpenQuiz Study Time

Today        2 hrs 14 mins    100 words

This Week    7 hrs 51 mins    189 words

Total        7 hrs 51 mins
\`\`\`

\`\`\`text
📅 OpenQuiz Activity
26.10.18    Sunday       2 hrs 14 mins    100 words
\`\`\`
<!-- OPENQUIZ_STATS:END -->
After Today        unchanged
`;

test("resets only Today on other days", () => {
  const result = resetOpenQuizStats(readme, false);
  assert.match(result, /Today        0 mins\s+0 words/);
  assert.match(result, /This Week    7 hrs 51 mins    189 words/);
  assert.match(result, /Total        7 hrs 51 mins/);
  assert.match(result, /26\.10\.18    Sunday       2 hrs 14 mins    100 words/);
  assert.match(result, /After Today        unchanged/);
  assert.equal(resetOpenQuizStats(result, false), result);
});

test("resets Today and This Week on Monday in Vietnam", () => {
  const result = resetOpenQuizStats(readme, true);
  assert.match(result, /Today        0 mins\s+0 words/);
  assert.match(result, /This Week    0 mins\s+0 words/);
  assert.match(result, /Total        7 hrs 51 mins/);
  assert.equal(isMondayInVietnam(new Date("2026-10-18T23:00:00Z")), true);
  assert.equal(isMondayInVietnam(new Date("2026-10-17T23:00:00Z")), false);
});

test("fails safely when the study block is missing", () => {
  assert.throws(() => resetOpenQuizStats("<!-- OPENQUIZ_STATS:START -->\n<!-- OPENQUIZ_STATS:END -->", true));
});

test("adds zero words when resetting legacy time-only lines", () => {
  const legacy = readme.replace("Today        2 hrs 14 mins    100 words", "Today        2 hrs 14 mins")
    .replace("This Week    7 hrs 51 mins    189 words", "This Week    7 hrs 51 mins");
  const result = resetOpenQuizStats(legacy, true);
  assert.match(result, /Today        0 mins\s+0 words/);
  assert.match(result, /This Week    0 mins\s+0 words/);
});
