const test = require("node:test");
const assert = require("node:assert/strict");
const { createLineParser } = require("../desktop-ui/progress.js");

test("parses LF-delimited progress events", () => {
  const lines = [];
  const parser = createLineParser((line) => lines.push(line));
  parser.push('{"type":"progress","phase":"scan"}\n{"type":"progress","phase":"complete"}\n');
  assert.deepEqual(lines, ['{"type":"progress","phase":"scan"}', '{"type":"progress","phase":"complete"}']);
});

test("parses CRLF and chunks split across delimiters", () => {
  const lines = [];
  const parser = createLineParser((line) => lines.push(line));
  parser.push('{"type":"progress","phase":"scan"}\r');
  parser.push('\n{"type":"progress","phase":"analyze"}\r\n');
  assert.deepEqual(lines, ['{"type":"progress","phase":"scan"}', '{"type":"progress","phase":"analyze"}']);
});

test("flushes a final event without a trailing newline", () => {
  const lines = [];
  const parser = createLineParser((line) => lines.push(line));
  parser.push('{"type":"progress","phase":"complete"}');
  assert.deepEqual(lines, []);
  parser.flush();
  assert.deepEqual(lines, ['{"type":"progress","phase":"complete"}']);
});

test("does not lose a line when chunks split JSON content", () => {
  const lines = [];
  const parser = createLineParser((line) => lines.push(line));
  parser.push('{"type":"prog');
  parser.push('ress","phase":"scan"}\n');
  assert.deepEqual(lines, ['{"type":"progress","phase":"scan"}']);
});
