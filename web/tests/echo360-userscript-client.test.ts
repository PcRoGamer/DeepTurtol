import test from "node:test";
import assert from "node:assert/strict";
// Workaround: remove the .audit test from the tsconfig path
// by importing only what we need for Node tests.

/**
 * Tests for the WebUI-side Echo360 connector client (echo360-userscript.ts).
 *
 * The connector uses postMessage to communicate with the Tampermonkey userscript.
 * In Node.js (no window), the module gracefully degrades.
 */

test("echo360-userscript module: hasEcho360Connector returns false in non-browser env", async () => {
  const { hasEcho360Connector } = await import("../lib/echo360-userscript");
  assert.equal(await hasEcho360Connector(), false);
});

test("echo360-userscript module: getConnectorInfo returns null in non-browser env", async () => {
  const { getConnectorInfo } = await import("../lib/echo360-userscript");
  assert.equal(await getConnectorInfo(), null);
});

test("echo360-userscript module: getExpectedConnectorVersion returns null when server unreachable", async () => {
  const { getExpectedConnectorVersion } = await import(
    "../lib/echo360-userscript"
  );
  // No server running in test — fetch will fail → null
  assert.equal(await getExpectedConnectorVersion(), null);
});

test("echo360-userscript module: source and web constants are consistent", async () => {
  // Import the module (it defines WEB_SOURCE and CONNECTOR_SOURCE at module scope)
  // We can't access private constants, but we verify the exports work
  const mod = await import("../lib/echo360-userscript");
  assert.ok(typeof mod.hasEcho360Connector === "function");
  assert.ok(typeof mod.getConnectorInfo === "function");
  assert.ok(typeof mod.listEcho360Courses === "function");
  assert.ok(typeof mod.listEcho360Recordings === "function");
  assert.ok(typeof mod.resolveEcho360Sources === "function");
  assert.ok(typeof mod.openEcho360ThroughLms === "function");
  assert.ok(typeof mod.closeLmsTab === "function");
});

test("echo360-userscript module: all functions reject gracefully in node", async () => {
  const mod = await import("../lib/echo360-userscript");
  const results = await Promise.allSettled([
    mod.listEcho360Courses(),
    mod.openEcho360ThroughLms(),
    mod.closeLmsTab(),
  ]);
  for (const r of results) {
    assert.equal(r.status, "rejected");
  }
});
