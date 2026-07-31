import { NextResponse } from "next/server";
import { readFileSync } from "node:fs";
import { join } from "node:path";

// Extract the @version from the userscript file served at /echo360-connector.user.js
function readUserscriptVersion(): string | null {
  try {
    const src = readFileSync(
      join(process.cwd(), "public", "echo360-connector.user.js"),
      "utf-8",
    );
    const match = src.match(/^\/\/\s+@version\s+(\S+)/m);
    return match ? match[1] : null;
  } catch {
    return null;
  }
}

export function GET(): NextResponse {
  const version = readUserscriptVersion();
  if (!version) {
    return NextResponse.json({ error: "version not found" }, { status: 500 });
  }
  return NextResponse.json({ version });
}
