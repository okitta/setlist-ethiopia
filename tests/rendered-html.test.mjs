import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

test("ships the Vercel-compatible Zema Archive experience", async () => {
  const [page, app, layout, css, packageJson, schema, envExample] = await Promise.all([
    readFile(new URL("app/page.tsx", root), "utf8"),
    readFile(new URL("app/zema-app.tsx", root), "utf8"),
    readFile(new URL("app/layout.tsx", root), "utf8"),
    readFile(new URL("app/globals.css", root), "utf8"),
    readFile(new URL("package.json", root), "utf8"),
    readFile(new URL("db/schema.ts", root), "utf8"),
    readFile(new URL(".env.example", root), "utf8"),
  ]);

  await access(new URL(".next/BUILD_ID", root));
  assert.match(page, /ZemaApp/);
  assert.match(app, /Every stage has a story/);
  assert.match(app, /Add a performance/);
  assert.match(app, /I was there/);
  assert.match(layout, /Zema Archive/);
  assert.match(css, /@media \(max-width: 640px\)/);
  assert.match(packageJson, /"build": "next build --webpack"/);
  assert.match(schema, /pgTable/);
  assert.match(envExample, /NEXT_PUBLIC_SUPABASE_URL/);
  assert.doesNotMatch(packageJson, /vinext|wrangler|cloudflare/);
});
