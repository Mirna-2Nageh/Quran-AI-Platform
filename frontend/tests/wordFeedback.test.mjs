import assert from "node:assert/strict";
import { test } from "node:test";
import { buildWordFeedback, tokenizeExpectedWords } from "../src/features/recitation/utils/wordFeedback.ts";

function alignment(expectedCount, matchedCount, issues = [], recognizedCount = expectedCount) {
  return {
    expected_word_count: expectedCount,
    recognized_word_count: recognizedCount,
    matched_word_count: matchedCount,
    issues,
  };
}

test("all matching words", () => {
  const result = buildWordFeedback("بسم الله الرحمن", alignment(3, 3));
  assert.deepEqual(result.words.map((word) => word.status), [
    "matched", "matched", "matched",
  ]);
  assert.equal(result.matchPercentage, 100);
  assert.equal(result.canHighlight, true);
});

test("substituted word", () => {
  const result = buildWordFeedback("بسم الله", alignment(2, 1, [{
    operation: "substitution",
    expected_word: "الله",
    recognized_word: "الرحمن",
    expected_index: 1,
    recognized_index: 1,
  }]));
  assert.equal(result.words[1].status, "substituted");
  assert.equal(result.words[1].recognizedWord, "الرحمن");
});

test("missing word", () => {
  const result = buildWordFeedback("بسم الله الرحمن", alignment(3, 2, [{
    operation: "deletion",
    expected_word: "الله",
    recognized_word: null,
    expected_index: 1,
    recognized_index: null,
  }], 2));
  assert.equal(result.words[1].status, "missing");
});

test("extra recognized word", () => {
  const result = buildWordFeedback("بسم الله", alignment(2, 2, [{
    operation: "insertion",
    expected_word: null,
    recognized_word: "الرحمن",
    expected_index: null,
    recognized_index: 2,
  }], 3));
  assert.deepEqual(result.extraWords, [{
    word: "الرحمن",
    recognizedIndex: 2,
  }]);
});

test("standalone Quranic punctuation does not shift indices", () => {
  assert.deepEqual(
    tokenizeExpectedWords("بسم ۝ الله ﴿ الرحمن"),
    ["بسم", "الله", "الرحمن"],
  );
});

test("Arabic diacritics preserve word indices", () => {
  const result = buildWordFeedback(
    "بِسْمِ اللَّهِ",
    alignment(2, 2),
  );

  assert.equal(result.canHighlight, true);
  assert.deepEqual(
    result.words.map((word) => word.word),
    ["بِسْمِ", "اللَّهِ"],
  );
});

test("repeated words use alignment indices, not word matching", () => {
  const result = buildWordFeedback(
    "بسم الله الله الرحمن",
    alignment(4, 3, [{
      operation: "deletion",
      expected_word: "الله",
      recognized_word: null,
      expected_index: 2,
      recognized_index: null,
    }], 3),
  );

  assert.deepEqual(
    result.words.map((word) => word.status),
    ["matched", "matched", "missing", "matched"],
  );
});

test("disables highlighting when token counts differ", () => {
  const result = buildWordFeedback(
    "بسم الله الرحمن",
    alignment(2, 1),
  );

  assert.equal(result.canHighlight, false);
});

test("disables highlighting when issue index points to wrong word", () => {
  const result = buildWordFeedback(
    "بسم الله الرحمن",
    alignment(3, 2, [{
      operation: "deletion",
      expected_word: "الله",
      recognized_word: null,
      expected_index: 2,
      recognized_index: null,
    }], 2),
  );

  assert.equal(result.canHighlight, false);
  assert.deepEqual(
    result.words.map((word) => word.status),
    ["matched", "matched", "matched"],
  );
});

test("preserves extra words when highlighting is disabled", () => {
  const result = buildWordFeedback(
    "بسم الله الرحمن",
    alignment(2, 1, [{
      operation: "insertion",
      expected_word: null,
      recognized_word: "زيادة",
      expected_index: null,
      recognized_index: 1,
    }], 3),
  );

  assert.equal(result.canHighlight, false);
  assert.deepEqual(result.extraWords, [{
    word: "زيادة",
    recognizedIndex: 1,
  }]);
});

test("alignment indices continue across multiple ayahs", () => {
  const ayah1 = "بسم الله";
  const ayah2 = "الرحمن الرحيم";
  const expectedText = [ayah1, ayah2].join(" ");

  const result = buildWordFeedback(
    expectedText,
    alignment(4, 3, [{
      operation: "deletion",
      expected_word: "الرحمن",
      recognized_word: null,
      expected_index: 2,
      recognized_index: null,
    }], 3),
  );

  const secondAyahOffset = tokenizeExpectedWords(ayah1).length;

  assert.equal(secondAyahOffset, 2);
  assert.equal(result.canHighlight, true);
  assert.equal(result.words[secondAyahOffset].word, "الرحمن");
  assert.equal(result.words[secondAyahOffset].status, "missing");
  assert.equal(result.words[1].status, "matched");
});

test("Quranic punctuation and spaces preserve multi-ayah indices", () => {
  const ayah1 = "بِسْمِ   ۝   اللَّهِ";
  const ayah2 = "﴿ الرَّحْمَٰنِ الرَّحِيمِ";
  const expectedText = [ayah1, ayah2].join(" ");

  const result = buildWordFeedback(
    expectedText,
    alignment(4, 3, [{
      operation: "substitution",
      expected_word: "الرَّحْمَٰنِ",
      recognized_word: "الرحيم",
      expected_index: 2,
      recognized_index: 2,
    }]),
  );

  assert.equal(result.canHighlight, true);
  assert.deepEqual(
    result.words.map((word) => word.status),
    ["matched", "matched", "substituted", "matched"],
  );
});
