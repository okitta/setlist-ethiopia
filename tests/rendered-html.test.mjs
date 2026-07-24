import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

test("ships the Zema Archive experience and production build", async () => {
  const [page, app, layout, css, hosting] = await Promise.all([
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/zema-app.tsx", root), "utf8"),
    readFile(new URL("app/layout.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
    readFile(new URL(".openai/hosting.json", root), "utf8"),
  ]);

  await access(new URL("dist/server/index.js", root));
  assert.match(page, /ZemaApp/);
  assert.match(app, /Every stage has a story/);
  assert.match(app, /Add a performance/);
  assert.match(app, /I was there/);
  assert.match(layout, /Zema Archive/);
  assert.match(css, /@media \(max-width: 640px\)/);
  assert.match(hosting, /"d1": "DB"/);
  assert.doesNotMatch(`${page}${layout}`, /codex-preview|SkeletonPreview/);
});
