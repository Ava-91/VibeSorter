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


test("desktop shell keeps results in-window and restores cancellation controls", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const html = fs.readFileSync(path.join(__dirname, "../desktop-ui/index.html"), "utf8");
  assert.match(html, /id="results-frame"/);
  assert.match(html, /src="progress.js"/);
  assert.doesNotMatch(html, /window\.location\.href/);
  assert.match(html, /cancel\.disabled = false/);
  assert.match(html, /analysis-diagnostic/);
});


test("desktop shell awaits all event subscriptions before enabling actions", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const html = fs.readFileSync(path.join(__dirname, "../desktop-ui/index.html"), "utf8");
  assert.match(html, /const listenersReady = Promise\.all\(\[/);
  assert.match(html, /listenersReady\.then\(\(unlisten\)/);
  assert.match(html, /choose\.disabled = false/);
  for (const event of ["analysis-output", "analysis-diagnostic", "analysis-error", "analysis-failed", "analysis-cancelled", "analysis-finished"]) {
    assert.ok(html.includes('listen("' + event + '"'));
  }
});

test("desktop shell restores Browse results after cancelled or failed runs", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const html = fs.readFileSync(path.join(__dirname, "../desktop-ui/index.html"), "utf8");
  assert.match(html, /if \(!running\) browse\.classList\.toggle\("hidden", !browserUrl\)/);
  for (const event of ["analysis-error", "analysis-failed", "analysis-cancelled"]) {
    const start = html.indexOf('listen("' + event + '"');
    assert.notEqual(start, -1);
    assert.ok(html.indexOf("setRunning(false)", start) > start);
  }
});


test("desktop shell event lifecycle keeps existing results reachable", async () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const vm = require("node:vm");
  const html = fs.readFileSync(path.join(__dirname, "../desktop-ui/index.html"), "utf8");
  const marker = html.indexOf("const tauri = window.__TAURI__;");
  const scriptStart = html.lastIndexOf("<script", marker);
  const scriptEnd = html.indexOf("</script>", marker);
  const source = html.slice(html.indexOf(">", scriptStart) + 1, scriptEnd);
  assert.ok(source, "desktop controller script should exist");

  function makeElement(id, initiallyHidden = false) {
    const classes = new Set(initiallyHidden ? ["hidden"] : []);
    const handlers = {};
    return {
      id,
      disabled: id === "choose" || id === "analyze",
      hidden: id === "results-shell",
      textContent: "",
      src: "",
      handlers,
      classList: {
        add(name) { classes.add(name); },
        remove(name) { classes.delete(name); },
        contains(name) { return classes.has(name); },
        toggle(name, force) {
          const next = force === undefined ? !classes.has(name) : Boolean(force);
          if (next) classes.add(name); else classes.delete(name);
          return next;
        },
      },
      addEventListener(type, callback) { handlers[type] = callback; },
    };
  }

  const elements = Object.fromEntries([
    "choose", "analyze", "cancel", "path", "status", "browse",
    "results-shell", "results-frame", "hide-results",
  ].map((id) => [id, makeElement(id, id === "cancel" || id === "browse")]));
  const main = makeElement("main");
  const eventHandlers = {};
  const invokes = [];
  const window = {
    __TAURI__: {
      core: {
        async invoke(command) {
          invokes.push(command);
          if (command === "choose_folder") return "/test/library";
          if (command === "start_backend") return "http://127.0.0.1:43210";
          return undefined;
        },
      },
      event: {
        async listen(name, callback) {
          eventHandlers[name] = callback;
          return () => { delete eventHandlers[name]; };
        },
      },
    },
    VibeSorterProgress: {
      createLineParser() { return { push() {}, flush() {} }; },
    },
    addEventListener() {},
  };
  const document = {
    getElementById(id) { return elements[id]; },
    querySelector(selector) { return selector === "main" ? main : null; },
  };

  vm.runInNewContext(source, { window, document, console, Date, JSON, Promise });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(elements.choose.disabled, false, "folder selection unlocks after listeners resolve");
  assert.ok(eventHandlers["analysis-output"], "analysis output listener is installed before interaction");

  await elements.choose.handlers.click();
  assert.equal(elements.analyze.disabled, false);
  await elements.analyze.handlers.click();
  assert.equal(invokes.includes("index_folder"), true);
  assert.equal(elements.browse.classList.contains("hidden"), true);

  eventHandlers["analysis-finished"]({ payload: 0 });
  assert.equal(elements.browse.classList.contains("hidden"), false);

  await elements.analyze.handlers.click();
  eventHandlers["analysis-cancelled"]({});
  assert.equal(elements.browse.classList.contains("hidden"), false, "cancelled rerun keeps prior results accessible");

  await elements.analyze.handlers.click();
  eventHandlers["analysis-failed"]({ payload: 2 });
  assert.equal(elements.browse.classList.contains("hidden"), false, "failed rerun keeps prior results accessible");
});
