/* Shared incremental parser for newline-delimited backend progress events. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.VibeSorterProgress = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  function createLineParser(onLine) {
    let buffer = "";
    return {
      push(chunk) {
        buffer += String(chunk == null ? "" : chunk);
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() || "";
        for (const line of lines) onLine(line);
      },
      flush() {
        if (buffer.length) onLine(buffer);
        buffer = "";
      }
    };
  }
  return { createLineParser };
});
