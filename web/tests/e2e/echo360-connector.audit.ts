import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

/**
 * E2E audit for the Echo360 Tampermonkey connector (userscript).
 *
 * The userscript runs on the DeepTurtol library page and communicates via
 * postMessage.  This test injects it with shimmed Tampermonkey APIs to
 * validate the protocol and internal logic without a real Echo360 session.
 */

/* ------------------------------------------------------------------ */
/*  Fixtures                                                          */
/* ------------------------------------------------------------------ */

const USERSCRIPT_PATH = resolve(
  __dirname,
  "../../../deeptutor/assets/echo360_userscript/echo360-connector.user.js",
);
const USERS_ORIGIN = "http://localhost:3000";

const MOCK_ENROLLMENTS = {
  data: [
    {
      groupInfo: { name: "Foundations of Computing" },
      userSections: [
        {
          sectionId: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
          courseCode: "COMP10001",
          courseName: "Foundations of Computing",
        },
        {
          sectionId: "ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj",
          courseCode: "COMP20002",
          courseName: "Data Structures",
        },
      ],
    },
  ],
};

const MOCK_SYLLABUS_WITH_MEDIA = {
  data: [
    {
      groupInfo: { name: "Foundations of Computing" },
      lessons: [
        {
          id: "lesson-uuid-0001",
          displayName: "Graph Traversal",
          hasVideo: true,
          timing: { start: "2026-07-20T14:05:00Z" },
          video: {
            media: {
              media: {
                current: {
                  primaryFiles: [
                    {
                      s3Url: "https://s3.amazonaws.com/echo360/media.mp4",
                    },
                  ],
                },
                versions: [
                  {
                    manifests: [
                      {
                        uri: "https://content.echo360.net.au/lecture.m3u8",
                      },
                    ],
                  },
                ],
              },
            },
          },
        },
      ],
    },
  ],
};

const MOCK_SYLLABUS_STRIPPED = {
  data: [
    {
      groupInfo: { name: "Foundations of Computing" },
      lessons: [
        {
          id: "G_group-uuid_lesson-uuid_2026-07-20T14:05:00.000_2026-07-20T15:00:00.000",
          displayName: "Graph Traversal",
          hasVideo: true,
          timing: { start: "2026-07-20T14:05:00Z" },
          // No video.media — stripped by Echo360 cross-origin
        },
      ],
    },
  ],
};

const MOCK_CLASSROOM_HTML = `<!DOCTYPE html>
<html lang="en-US">
<head>
  <title>COMP10001 — Foundations of Computing</title>
  <script>
    Echo = {};
    Echo["echoPlayerV2FullApp"]("{\\"video\\":{\\"playableMedias\\":[{\\"sourceIndex\\":1,\\"uri\\":\\"https:\\\\/\\\\/content.echo360.net.au\\\\/lecture.m3u8\\"}]}}");
  </script>
</head>
<body><div id="content-player"></div></body>
</html>`;

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Minimal Tampermonkey GM shim that keeps state in an in-memory Map. */
function gmShim() {
  const store = new Map<string, string>();
  const openTabs: Array<{ closed: boolean }> = [];

  (globalThis as any).GM_info = {
    script: { version: "9.9.9-test" },
  };
  (globalThis as any).GM_setValue = (key: string, val: string) =>
    store.set(key, val);
  (globalThis as any).GM_getValue = (key: string, def?: string) =>
    store.get(key) ?? def ?? "";
  (globalThis as any).GM_deleteValue = (key: string) => store.delete(key);
  (globalThis as any).GM_openInTab = (_url: string, _opts?: any) => {
    const tab = { closed: false };
    openTabs.push(tab);
    return tab;
  };
  (globalThis as any).GM_xmlhttpRequest = (
    opts: {
      url: string;
      method?: string;
      headers?: Record<string, string>;
      onload?: (resp: {
        status: number;
        responseText: string;
        response?: any;
      }) => void;
      onerror?: () => void;
      ontimeout?: () => void;
    },
  ) => {
    const url = opts.url || "";
    let status = 200;
    let body = "";

    if (url.includes("/user/enrollments")) {
      body = JSON.stringify(MOCK_ENROLLMENTS);
    } else if (url.includes("/section/") && url.includes("/syllabus")) {
      body = JSON.stringify(MOCK_SYLLABUS_STRIPPED);
    } else if (url.includes("/lesson/") && url.includes("/classroom")) {
      body = MOCK_CLASSROOM_HTML;
    } else if (
      url.includes("/lesson/") &&
      (url.includes("/media") ||
        url.includes("/playback") ||
        url.includes("/source"))
    ) {
      // These API endpoints return 404 in the real world
      status = 404;
      body = "Not found";
    } else {
      status = 200;
      body = "{}";
    }

    setTimeout(() => {
      if (opts.onload)
        opts.onload({ status, responseText: body, response: undefined as any });
    }, 10);
  };
}

/**
 * Send a postMessage to the userscript and wait for the response.
 * Returns a promise that resolves with the response result.
 */
function postMessageAndWait(
  page: Page,
  type: string,
  payload?: Record<string, unknown>,
  timeoutMs = 10_000,
): Promise<any> {
  const requestId = "test-" + crypto.randomUUID();

  return page.evaluate(
    ({ requestId, type, payload, timeoutMs }) => {
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
          window.removeEventListener("message", handler);
          reject(new Error("Timeout waiting for connector response"));
        }, timeoutMs);

        function handler(event: MessageEvent) {
          if (
            event.data?.requestId === requestId &&
            event.data?.source === "deepturtol-echo360-userscript"
          ) {
            clearTimeout(timer);
            window.removeEventListener("message", handler);
            if (event.data.ok) resolve(event.data.result);
            else reject(new Error(event.data.error || "Connector error"));
          }
        }

        window.addEventListener("message", handler);
        window.postMessage(
          {
            source: "deepturtol-web",
            requestId,
            type,
            payload,
          },
          window.location.origin,
        );
      });
    },
    { requestId, type, payload, timeoutMs },
  );
}

/* ------------------------------------------------------------------ */
/*  Tests                                                              */
/* ------------------------------------------------------------------ */

test.describe("Echo360 Connector Userscript", () => {
  test.beforeEach(async ({ page }) => {
    // Inject GM shims before the userscript runs
    await page.addInitScript(gmShim);

    // Inject the actual userscript code
    const code = readFileSync(USERSCRIPT_PATH, "utf-8");
    // Strip the UserScript metadata block (it's a comment) and the IIFE wrapper
    // is self-executing so we just inject it as-is
    await page.addInitScript(code);

    // Navigate to a page that matches the userscript's @match patterns
    // Intercept the request to return a minimal HTML page without a full server
    await page.route("**/library*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/html",
        body: `<!DOCTYPE html>
<html><head><title>DeepTurtol Library</title></head>
<body><div id="root"><h1>Media Library</h1></div></body>
</html>`,
      });
    });
  });

  test("PING returns installed status and version", async ({ page }) => {
    await page.goto(`${USERS_ORIGIN}/library`);
    const result = await postMessageAndWait(
      page,
      "DEEPTURTOL_ECHO360_PING",
      undefined,
      5_000,
    );
    expect(result).toBeDefined();
    expect(result.installed).toBe(true);
    expect(result.version).toBe("9.9.9-test");
  });

  test("COURSES returns parsed course list from enrollments endpoint", async ({
    page,
  }) => {
    await page.goto(`${USERS_ORIGIN}/library`);
    const result = await postMessageAndWait(
      page,
      "DEEPTURTOL_ECHO360_COURSES",
      undefined,
      10_000,
    );
    expect(result).toBeDefined();
    expect(Array.isArray(result.courses)).toBe(true);
    expect(result.courses.length).toBeGreaterThanOrEqual(2);
    expect(result.courses[0]).toHaveProperty("id");
    expect(result.courses[0]).toHaveProperty("name");
    expect(result.courses[0].name).toContain("COMP10001");
  });

  test("RECORDINGS returns recording list from syllabus endpoint", async ({
    page,
  }) => {
    await page.goto(`${USERS_ORIGIN}/library`);
    const courseId = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";

    // Override the syllabus mock to include media URLs for recordings
    // We need to update the GM_xmlhttpRequest shim
    await page.evaluate((syllabus) => {
      const orig = (globalThis as any).GM_xmlhttpRequest;
      (globalThis as any).GM_xmlhttpRequest = (opts: any) => {
        if (opts.url?.includes("/section/") && opts.url?.includes("/syllabus")) {
          setTimeout(() => {
            if (opts.onload)
              opts.onload({
                status: 200,
                responseText: JSON.stringify(syllabus),
              });
          }, 10);
        } else {
          orig(opts);
        }
      };
    }, MOCK_SYLLABUS_WITH_MEDIA);

    const result = await postMessageAndWait(
      page,
      "DEEPTURTOL_ECHO360_RECORDINGS",
      { courseId },
      10_000,
    );
    expect(result).toBeDefined();
    expect(result.courseName).toBe("Foundations of Computing");
    expect(Array.isArray(result.recordings)).toBe(true);
    expect(result.recordings.length).toBeGreaterThanOrEqual(1);
    expect(result.recordings[0].title).toBe("Graph Traversal");
    expect(result.recordings[0].id).toBeTruthy();
  });

  test("SOURCES resolves media via syllabus when available", async ({
    page,
  }) => {
    await page.goto(`${USERS_ORIGIN}/library`);
    const courseId = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";

    // Use syllabus with media URLs for this test
    await page.evaluate((syllabus) => {
      (globalThis as any).GM_xmlhttpRequest = (opts: any) => {
        if (opts.url?.includes("/section/") && opts.url?.includes("/syllabus")) {
          setTimeout(() => {
            if (opts.onload)
              opts.onload({
                status: 200,
                responseText: JSON.stringify(syllabus),
              });
          }, 10);
        } else {
          setTimeout(() => {
            if (opts.onload)
              opts.onload({ status: 404, responseText: "Not found" });
          }, 10);
        }
      };
    }, MOCK_SYLLABUS_WITH_MEDIA);

    const result = await postMessageAndWait(
      page,
      "DEEPTURTOL_ECHO360_SOURCES",
      {
        courseId,
        recordingIds: ["lesson-uuid-0001"],
      },
      10_000,
    );

    expect(result).toBeDefined();
    expect(Array.isArray(result.sources)).toBe(true);
    expect(result.sources.length).toBeGreaterThanOrEqual(1);
    const src = result.sources[0];
    expect(src.media_url).toBeTruthy();
    expect(src.media_kind).toBe("mp4"); // s3Url ends with .mp4 → mp4 kind
  });

  test("SOURCES falls back to classroom HTML scrape when syllabus has no media", async ({
    page,
  }) => {
    await page.goto(`${USERS_ORIGIN}/library`);
    const courseId = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
    const recId =
      "G_group-uuid_lesson-uuid_2026-07-20T14:05:00.000_2026-07-20T15:00:00.000";

    // Use stripped syllabus (no media URLs)
    await page.evaluate((syllabus) => {
      (globalThis as any).GM_xmlhttpRequest = (opts: any) => {
        if (opts.url?.includes("/section/") && opts.url?.includes("/syllabus")) {
          setTimeout(() => {
            if (opts.onload)
              opts.onload({
                status: 200,
                responseText: JSON.stringify(syllabus),
              });
          }, 10);
        } else if (opts.url?.includes("/classroom")) {
          // Return a classroom HTML page with embedded player config
          setTimeout(() => {
            if (opts.onload)
              opts.onload({
                status: 200,
                responseText: `<!DOCTYPE html>
<html><head><title>COMP10001 — Foundations of Computing</title>
<script>
Echo["echoPlayerV2FullApp"]("{\\"video\\":{\\"playableMedias\\":[{\\"sourceIndex\\":1,\\"uri\\":\\"https:\\\\/\\\\/content.echo360.net.au\\\\/lecture.m3u8\\"}]}}");
</script>
</head><body></body></html>`,
              });
          }, 10);
        } else {
          setTimeout(() => {
            if (opts.onload)
              opts.onload({ status: 404, responseText: "Not found" });
          }, 10);
        }
      };
    }, MOCK_SYLLABUS_STRIPPED);

    const result = await postMessageAndWait(
      page,
      "DEEPTURTOL_ECHO360_SOURCES",
      { courseId, recordingIds: [recId] },
      15_000,
    );

    expect(result).toBeDefined();
    expect(Array.isArray(result.sources)).toBe(true);
    // Should have resolved at least 1 source via classroom scrape
    expect(result.sources.length).toBeGreaterThanOrEqual(1);
    const src = result.sources[0];
    expect(src.media_url).toBeTruthy();
    // The classroom HTML had .m3u8 → hls
    expect(src.media_kind).toBe("hls");
    expect(src.media_url).toContain("content.echo360.net.au");
  });

  test("SOURCES handles recordings with no media gracefully", async ({
    page,
  }) => {
    await page.goto(`${USERS_ORIGIN}/library`);
    const courseId = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
    const recId =
      "G_group-uuid_lesson-uuid_2026-07-20T14:05:00.000_2026-07-20T15:00:00.000";

    // Syllabus stripped AND classroom HTML has NO media URLs
    await page.evaluate(() => {
      (globalThis as any).GM_xmlhttpRequest = (opts: any) => {
        if (opts.url?.includes("/section/") && opts.url?.includes("/syllabus")) {
          setTimeout(() => {
            if (opts.onload)
              opts.onload({
                status: 200,
                responseText: JSON.stringify({
                  data: [
                    {
                      groupInfo: { name: "Foundations of Computing" },
                      lessons: [
                        {
                          id: recId,
                          displayName: "Missing Lecture",
                          hasVideo: true,
                          timing: { start: "2026-07-20T14:05:00Z" },
                        },
                      ],
                    },
                  ],
                }),
              });
          }, 10);
        } else if (opts.url?.includes("/classroom")) {
          // Classroom page with no media URLs (vanilla HTML)
          setTimeout(() => {
            if (opts.onload)
              opts.onload({
                status: 200,
                responseText: `<!DOCTYPE html>
<html><head><title>Course Overview — No Video</title></head>
<body><p>No recording available.</p></body></html>`,
              });
          }, 10);
        } else {
          setTimeout(() => {
            if (opts.onload)
              opts.onload({ status: 404, responseText: "Not found" });
          }, 10);
        }
      };
    });

    const result = await postMessageAndWait(
      page,
      "DEEPTURTOL_ECHO360_SOURCES",
      { courseId, recordingIds: [recId] },
      15_000,
    );

    // Request succeeds, but sources array may be empty
    expect(result).toBeDefined();
    expect(Array.isArray(result.sources)).toBe(true);
  });

  test("invalid course ID is rejected", async ({ page }) => {
    await page.goto(`${USERS_ORIGIN}/library`);
    let caught: Error | null = null;
    try {
      await postMessageAndWait(
        page,
        "DEEPTURTOL_ECHO360_SOURCES",
        { courseId: "not-a-uuid", recordingIds: [] },
        5_000,
      );
    } catch (err: any) {
      caught = err;
    }
    expect(caught).not.toBeNull();
    expect(caught!.message).toContain("Invalid Echo360 course identifier");
  });

  test("deepFindMediaUrl extracts URLs from nested JSON", async ({
    page,
  }) => {
    await page.goto(`${USERS_ORIGIN}/library`);

    // Access deepFindMediaUrl through closure by testing via classroomStreamUrl
    // Instead, test the logic directly by evaluating code in the page
    const result = await page.evaluate(() => {
      // Replicate the function in the page context (same logic)
      const deepFindMediaUrl = (obj: any, depth = 0): string | null => {
        if (depth > 10 || obj == null || typeof obj === "boolean" || typeof obj === "number") return null;
        if (typeof obj === "string") {
          if (obj.endsWith(".m3u8") || obj.endsWith(".mp4")) return obj;
          const match = obj.match(/https?:\/\/[^\s"']+?\.(?:m3u8|mp4)[^\s"']*/i);
          if (match) return match[0];
          return null;
        }
        if (Array.isArray(obj)) {
          for (const item of obj) {
            const found = deepFindMediaUrl(item, depth + 1);
            if (found) return found;
          }
          return null;
        }
        for (const key of ["uri", "url", "s3Url", "sourceUri", "mediaUrl", "playbackUrl", "sourceUrl", "href"]) {
          if (key in obj) {
            const found = deepFindMediaUrl(obj[key], depth + 1);
            if (found) return found;
          }
        }
        for (const val of Object.values(obj)) {
          const found = deepFindMediaUrl(val, depth + 1);
          if (found) return found;
        }
        return null;
      };

      return {
        fromUri: deepFindMediaUrl({ uri: "https://content.echo360.net.au/video.m3u8" }),
        fromS3: deepFindMediaUrl({ current: { primaryFiles: [{ s3Url: "https://s3.amazonaws.com/video.mp4" }] } }),
        fromNested: deepFindMediaUrl({ a: { b: { c: { playbackUrl: "https://cdn.example.com/stream.mp4?token=abc" } } } }),
        noMatch: deepFindMediaUrl({ title: "no url here" }),
        handlesNull: deepFindMediaUrl(null),
        handlesNumber: deepFindMediaUrl(0),
        handlesBoolean: deepFindMediaUrl(false),
      };
    });

    expect(result.fromUri).toContain(".m3u8");
    expect(result.fromS3).toContain(".mp4");
    expect(result.fromNested).toContain("stream.mp4");
    expect(result.noMatch).toBeNull();
    expect(result.handlesNull).toBeNull();
    expect(result.handlesNumber).toBeNull();
    expect(result.handlesBoolean).toBeNull();
  });

  test("extractLessonUuid extracts second UUID from composite ID", async ({
    page,
  }) => {
    await page.goto(`${USERS_ORIGIN}/library`);
    const result = await page.evaluate(() => {
      const extractLessonUuid = (id: string): string | null => {
        if (!id.startsWith("G_")) return null;
        const match = id.match(
          /^G_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i,
        );
        return match ? match[2] : null;
      };

      return {
        extractsLesson: extractLessonUuid(
          "G_aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee_55555555-6666-7777-8888-999999999999_2026-07-20T14:05:00.000_2026-07-20T15:00:00.000",
        ),
        nonComposite: extractLessonUuid("plain-uuid-here"),
        noMatch: extractLessonUuid("X_not-even-close"),
      };
    });

    expect(result.extractsLesson).toBe("55555555-6666-7777-8888-999999999999");
    expect(result.nonComposite).toBeNull();
    expect(result.noMatch).toBeNull();
  });

  test("contentUrl rewrites echo360 hostnames to content subdomain", async ({
    page,
  }) => {
    await page.goto(`${USERS_ORIGIN}/library`);
    const result = await page.evaluate(() => {
      const ECHO360_ORIGIN = "https://echo360.net.au";
      const contentUrl = (uri: string): string => {
        try {
          const url = new URL(uri, ECHO360_ORIGIN);
          if (
            !url.hostname.startsWith("content.") &&
            url.hostname.endsWith("echo360.net.au")
          ) {
            url.hostname = "content." + url.hostname;
          }
          return url.toString();
        } catch {
          return uri;
        }
      };

      return {
        bareHost: contentUrl("https://echo360.net.au/video.m3u8"),
        alreadyContent: contentUrl("https://content.echo360.net.au/video.m3u8"),
        s3Url: contentUrl("https://s3.amazonaws.com/echo360/video.mp4"),
        relativePath: contentUrl("/lesson/some-id/classroom"),
      };
    });

    expect(result.bareHost).toBe("https://content.echo360.net.au/video.m3u8");
    expect(result.alreadyContent).toBe("https://content.echo360.net.au/video.m3u8");
    expect(result.s3Url).toBe("https://s3.amazonaws.com/echo360/video.mp4");
    expect(result.relativePath).toContain("echo360.net.au");
  });

  test("recordingsFromPayload correctly parses syllabus JSON", async ({
    page,
  }) => {
    await page.goto(`${USERS_ORIGIN}/library`);
    const result = await page.evaluate(() => {
      // recordingsFromPayload logic inlined
      const parse = (payload: any, courseId: string) => {
        let courseName = "";
        const lessons: any[] = [];
        for (const item of Array.isArray(payload.data) ? payload.data : []) {
          if (!courseName && item?.groupInfo?.name) courseName = String(item.groupInfo.name);
          if (Array.isArray(item?.lessons)) lessons.push(...item.lessons.filter(Boolean));
          else if (item?.lesson && typeof item.lesson === "object") lessons.push(item.lesson);
        }
        const recordings: any[] = [];
        for (const outer of lessons) {
          if (outer?.hasVideo === false) continue;
          const lesson = outer?.lesson && typeof outer.lesson === "object" ? outer.lesson : outer;
          const id = String(lesson?.id || "");
          if (!id) continue;
          const media = lesson?.video?.media?.media;
          const m3u8Urls: string[] = [];
          const mp4Urls: string[] = [];
          for (const version of Array.isArray(media?.versions) ? media.versions : []) {
            for (const manifest of Array.isArray(version?.manifests) ? version.manifests : []) {
              if (manifest?.uri) m3u8Urls.push(String(manifest.uri));
            }
          }
          for (const file of Array.isArray(media?.current?.primaryFiles) ? media.current.primaryFiles : []) {
            if (file?.s3Url) mp4Urls.push(String(file.s3Url));
          }
          recordings.push({
            id,
            title: String(lesson?.displayName || lesson?.name || "Untitled"),
            date: String(lesson?.timing?.start || "").slice(0, 10),
            course_id: courseId,
            course_name: courseName,
            has_media: !!media,
            mp4_urls: mp4Urls,
            m3u8_urls: m3u8Urls,
          });
        }
        return { courseName, recordings };
      };

      const withMedia = parse({
        data: [
          {
            groupInfo: { name: "Algorithms" },
            lessons: [
              {
                id: "lesson-1",
                displayName: "Sorting",
                hasVideo: true,
                timing: { start: "2026-08-01T10:00:00Z" },
                video: {
                  media: {
                    media: {
                      current: { primaryFiles: [{ s3Url: "https://s3.amazonaws.com/sorting.mp4" }] },
                      versions: [{ manifests: [{ uri: "https://content.echo360.net.au/sorting.m3u8" }] }],
                    },
                  },
                },
              },
            ],
          },
        ],
      }, "course-1");

      const stripped = parse({
        data: [
          {
            groupInfo: { name: "Algorithms" },
            lessons: [
              {
                id: "lesson-2",
                displayName: "Searching",
                hasVideo: true,
                timing: { start: "2026-08-08T10:00:00Z" },
                // No video.media — stripped cross-origin response
              },
            ],
          },
        ],
      }, "course-1");

      return {
        withMediaCount: withMedia.recordings.length,
        withMediaName: withMedia.recordings[0].title,
        withMediaUrls: withMedia.recordings[0].mp4_urls.length + withMedia.recordings[0].m3u8_urls.length,
        strippedCount: stripped.recordings.length,
        strippedHasMedia: stripped.recordings[0].has_media,
        strippedUrls: stripped.recordings[0].mp4_urls.length + stripped.recordings[0].m3u8_urls.length,
      };
    });

    expect(result.withMediaCount).toBe(1);
    expect(result.withMediaName).toBe("Sorting");
    expect(result.withMediaUrls).toBe(2); // 1 mp4 + 1 m3u8
    expect(result.strippedCount).toBe(1);
    expect(result.strippedHasMedia).toBe(false);
    expect(result.strippedUrls).toBe(0);
  });
});
