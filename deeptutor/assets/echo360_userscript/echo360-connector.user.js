// ==UserScript==
// @name         DeepTurtol Echo360 Connector
// @namespace    http://localhost:3000/
// @version      1.3.0
// @description  Lets DeepTurtol request selected Echo360 data from this already-signed-in browser, without reading or copying cookies.
// @match        http://localhost:3000/library*
// @match        http://127.0.0.1:3000/library*
// @match        http://localhost:3782/library*
// @match        http://127.0.0.1:3782/library*
// @match        *://localhost:3000/library*
// @match        *://127.0.0.1:3000/library*
// @match        *://localhost:3782/library*
// @match        *://127.0.0.1:3782/library*
// @match        https://echo360.net.au/*
// @match        https://*.echo360.net.au/*
// @match        https://canvas.lms.unimelb.edu.au/courses/241246/external_tools/4090*
// @grant        GM_info
// @grant        GM_xmlhttpRequest
// @grant        GM_openInTab
// @connect      echo360.net.au
// @connect      canvas.lms.unimelb.edu.au
// @run-at       document-start
// ==/UserScript==

/*
 * This is deliberately a browser-side operator, not a cookie bridge.
 *
 * Echo360 API calls are made from the library page using GM_xmlhttpRequest,
 * which includes Echo360 session cookies (from a prior visit to echo360.net.au
 * via the Canvas LTI launch).  The script returns only course metadata and
 * selected media source URLs to the local DeepTurtol page.  It never reads,
 * serialises, or sends a browser cookie to any server.
 *
 * The Echo360-tab handler (isEcho) no longer exists — all requests are
 * fulfilled directly from the DeepTurtol library page.
 */
(() => {
  "use strict";
  const log = typeof console !== "undefined"
    ? console.log.bind(console, "[DT-Echo]")
    : () => {};

  const WEB_SOURCE = "deepturtol-web";
  const CONNECTOR_SOURCE = "deepturtol-echo360-userscript";
  const LMS_LAUNCH_URL =
    "https://canvas.lms.unimelb.edu.au/courses/241246/external_tools/4090";
  const ECHO360_ORIGIN = "https://echo360.net.au";
  const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  const isLibrary = () =>
    ["localhost", "127.0.0.1"].includes(location.hostname) &&
    ["3000", "3782"].includes(location.port) &&
    location.pathname.startsWith("/library");
  const isEcho = () =>
    location.hostname === "echo360.net.au" ||
    location.hostname.endsWith(".echo360.net.au");

  const replyToWeb = (requestId, ok, result, error = "") => {
    window.postMessage(
      { source: CONNECTOR_SOURCE, requestId, ok, result, error },
      location.origin,
    );
  };

  /** Promisified GM_xmlhttpRequest for Echo360 endpoints. */
  const echoFetch = (path, options = {}) =>
    new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
          method: options.method || "GET",
          url: `${ECHO360_ORIGIN}${path}`,
          headers: {
            Accept: "application/json, text/html, */*",
            "X-Requested-With": "XMLHttpRequest",
            ...options.headers,
          },
          withCredentials: true,
          timeout: options.timeout ?? 30_000,
        onload: (response) => {
          if (response.status >= 200 && response.status < 300) {
            resolve(response);
          } else if (response.status === 401 || response.status === 403) {
            reject(
              new Error(
                "Echo360 needs a fresh UniMelb sign-in. Open the LMS launch, then try again.",
              ),
            );
          } else {
            reject(
              new Error(
                `Echo360 returned HTTP ${response.status} for ${path}.`,
              ),
            );
          }
        },
        onerror: () =>
          reject(new Error(`Could not reach Echo360 for ${path}.`)),
        ontimeout: () =>
          reject(
            new Error(
              "Echo360 did not respond in time. Are you signed in through UniMelb LMS?",
            ),
          ),
      });
    });

  /** Convenience: fetch JSON from Echo360. */
  const echoJson = async (path) => {
    const response = await echoFetch(path);
    try {
      const body = JSON.parse(response.responseText);
      if (!body || typeof body !== "object")
        throw new Error("Unexpected response from Echo360.");
      return body;
    } catch (cause) {
      throw new Error(
        cause instanceof SyntaxError
          ? "Echo360 returned non-JSON data."
          : cause.message,
      );
    }
  };

  /** Fetch HTML page from Echo360 (for stream extraction). */
  const echoHtml = async (path) => {
    // Omit X-Requested-With so Echo360 serves the full page, not an AJAX fragment.
    const response = await echoFetch(path, {
      headers: { Accept: "text/html", "X-Requested-With": "" },
    });
    return response.responseText;
  };

  const contentUrl = (uri) => {
    try {
      const url = new URL(uri, ECHO360_ORIGIN);
      if (
        !url.hostname.startsWith("content.") &&
        url.hostname.endsWith("echo360.net.au")
      ) {
        url.hostname = `content.${url.hostname}`;
      }
      return url.toString();
    } catch {
      return uri;
    }
  };

  const coursesFromPayload = (payload) => {
    const seen = new Set();
    const courses = [];
    for (const group of Array.isArray(payload.data) ? payload.data : []) {
      for (const section of Array.isArray(group?.userSections)
        ? group.userSections
        : []) {
        const id = String(section?.sectionId || "");
        if (!UUID.test(id) || seen.has(id)) continue;
        seen.add(id);
        const code = String(section.courseCode || "").trim();
        const label = String(
          section.courseName ||
            section.sectionName ||
            code ||
            id.slice(0, 8),
        ).trim();
        courses.push({
          id,
          name:
            code && !label.toLowerCase().includes(code.toLowerCase())
              ? `${code} — ${label}`
              : label,
          url: `https://echo360.net.au/section/${id}`,
        });
      }
    }
    return courses.sort((left, right) =>
      left.name.localeCompare(right.name),
    );
  };

  const recordingsFromPayload = (payload, courseId) => {
    let courseName = "";
    const lessons = [];
    for (const item of Array.isArray(payload.data) ? payload.data : []) {
      if (!courseName && item?.groupInfo?.name)
        courseName = String(item.groupInfo.name);
      if (Array.isArray(item?.lessons))
        lessons.push(...item.lessons.filter(Boolean));
      else if (item?.lesson && typeof item.lesson === "object")
        lessons.push(item.lesson);
    }
    const recordings = [];
    for (const outer of lessons) {
      if (outer?.hasVideo === false) continue;
      const lesson =
        outer?.lesson && typeof outer.lesson === "object"
          ? outer.lesson
          : outer;
      const id = String(lesson?.id || "");
      if (!id) continue;
      const timing =
        lesson?.timing && typeof lesson.timing === "object"
          ? lesson.timing
          : {};
      const media = lesson?.video?.media?.media;
      const m3u8Urls = [];
      const mp4Urls = [];
      for (const version of Array.isArray(media?.versions)
        ? media.versions
        : []) {
        for (const manifest of Array.isArray(version?.manifests)
          ? version.manifests
          : []) {
          if (manifest?.uri) m3u8Urls.push(contentUrl(String(manifest.uri)));
        }
      }
      for (const file of Array.isArray(media?.current?.primaryFiles)
        ? media.current.primaryFiles
        : []) {
        if (file?.s3Url) mp4Urls.push(String(file.s3Url));
      }
      log(`recording ${id}: mp4=${mp4Urls.length} m3u8=${m3u8Urls.length} hasMedia=${!!media}`);
      recordings.push({
        id,
        title: String(
          lesson?.displayName || lesson?.name || "Untitled lecture",
        ),
        date: String(
          timing.start ||
            outer?.captureStartedAt ||
            lesson?.createdAt ||
            "",
        ).slice(0, 10),
        course_id: courseId,
        course_name: courseName,
        has_media: true,
        mp4_urls: mp4Urls,
        m3u8_urls: m3u8Urls,
      });
    }
    return {
      courseName,
      recordings: recordings.sort((left, right) =>
        `${right.date}${right.title}`.localeCompare(
          `${left.date}${left.title}`,
        ),
      ),
    };
  };

  /** Recursively search a parsed JSON object for any value that looks like a
   *  streaming URL (.m3u8 or .mp4).  Returns the first match or null. */
  const deepFindMediaUrl = (obj, depth = 0) => {
    if (depth > 10 || obj == null || typeof obj === "boolean") return null;
    if (typeof obj === "string") {
      if (obj.endsWith(".m3u8") || obj.endsWith(".mp4"))
        return contentUrl(obj);
      if (obj.includes("m3u8") || obj.includes(".mp4")) {
        // It might be a full URL with query params
        const match = obj.match(
          /https?:\/\/[^\s"']+?\.(?:m3u8|mp4)[^\s"']*/i,
        );
        if (match) return contentUrl(match[0]);
      }
      return null;
    }
    if (Array.isArray(obj)) {
      for (const item of obj) {
        const found = deepFindMediaUrl(item, depth + 1);
        if (found) return found;
      }
      return null;
    }
    // Plain object
    for (const key of ["uri", "url", "s3Url", "sourceUri", "mediaUrl",
      "playbackUrl", "sourceUrl", "href"]) {
      if (key in obj) {
        const found = deepFindMediaUrl(obj[key], depth + 1);
        if (found) return found;
      }
    }
    // Fallback: search all values
    for (const val of Object.values(obj)) {
      const found = deepFindMediaUrl(val, depth + 1);
      if (found) return found;
    }
    return null;
  };

  const classroomStreamUrl = async (recordingId) => {
    const encId = encodeURIComponent(recordingId);

    /* ---- 1) Try known Echo360 lesson media API endpoints ---- */
    log(`classroomStreamUrl(${recordingId}) — trying 8 API endpoints`);
    for (const apiPath of [
      `/lesson/${encId}/media`,
      `/api/lesson/${encId}/playback`,
      `/lesson/${encId}/source`,
      `/lesson/${encId}`,
      `/api/lesson/${encId}`,
      `/api/v1/lessons/${encId}`,
      `/api/v2/lessons/${encId}`,
      `/lesson/${encId}/classroom`,
    ]) {
      try {
        const body = await echoJson(apiPath);
        const found = deepFindMediaUrl(body);
        if (found) {
          log(`API ${apiPath} → FOUND: ${found}`);
          return found;
        }
        log(`API ${apiPath} → JSON OK but no media URL`);
      } catch (err) {
            log(`API ${apiPath} → ${err.message}`);
      }
    }

    /* ---- 2) Scrape the classroom page HTML for embedded URLs ---- */
    log(`API endpoints exhausted — fetching classroom HTML`);
    let page;
    try {
      page = await echoHtml(`/lesson/${encId}/classroom`);
    } catch (err) {
      log(`echoHtml failed: ${err.message}`);
      throw new Error(`Echo360 has no playable media for this lecture. (HTML fetch: ${err.message})`);
    }
    log(`classroom HTML: ${page.length} chars, starts: ${page.slice(0, 300)}`);
    const pageReplaced = page.replace(/\\\//g, "/");

    /* ---- Helper: collect URLs matching a pattern ---- */
    const findUrls = (pattern) =>
      [...pageReplaced.matchAll(pattern)]
        .map((m) => m[1] || m[0])
        .filter((url) => url.startsWith("http"));

    // a) Echo player config
    const pgMatch = page.match(
      /Echo\["echoPlayerV2FullApp"\]\("(.+?)"\)/,
    );
    if (pgMatch) {
      try {
        const player = JSON.parse(JSON.parse(`"${pgMatch[1]}"`));
        const playable = player?.video?.playableMedias;
        for (const index of [1, 2, 0]) {
          const found = Array.isArray(playable)
            ? playable.find(
                (item) => item?.sourceIndex === index && item?.uri,
              )
            : null;
          if (found?.uri) return contentUrl(String(found.uri));
        }
      } catch {
        /* fall through */
      }
    }

    // b) Search for embedded JSON blobs (__INITIAL_STATE__ etc)
    const jsonBlobs = page.match(
      /(?:window\.__INITIAL_STATE__|window\.__DATA__|__NEXT_DATA__)\s*=\s*(\{.+?\});/gs,
    );
    if (jsonBlobs) {
      for (const blob of jsonBlobs) {
        try {
          const eqIdx = blob.indexOf("=");
          const data = JSON.parse(blob.slice(eqIdx + 1).replace(/;$/, ""));
          const found = deepFindMediaUrl(data);
          if (found) return found;
        } catch {
          /* try next blob */
        }
      }
    }

    // c) Brute-force m3u8 URLs in page
    const m3u8Candidates = findUrls(
      /https?:\/\/[^"'\s,<]+\.m3u8[^"'\s,<"]*/gi,
    );
    const av = m3u8Candidates.filter((u) => u.includes("av.m3u8"));
    if (av.length > 0) return av.sort()[av.length - 1];
    if (m3u8Candidates.length > 0)
      return m3u8Candidates[m3u8Candidates.length - 1];

    // d) Brute-force mp4 URLs in page
    const mp4Candidates = findUrls(
      /https?:\/\/[^"'\s,<]+\.mp4[^"'\s,<"]*/gi,
    );
    const hdMp4 = mp4Candidates.filter((u) => /hd/i.test(u));
    if (hdMp4.length > 0) return hdMp4[0];
    if (mp4Candidates.length > 0) return mp4Candidates[0];

    // e) Any content.echo360 URL
    const contentUrls = findUrls(
      /https?:\/\/content\.[^"'\s,<]+\/[^"'\s,<"]+/gi,
    );
    if (contentUrls.length > 0) return contentUrls[0];

    throw new Error("Echo360 has no playable media for this lecture.");
  };

  /* ---- Request handler — runs directly on the library page ---- */

  const handleRequest = async (requestId, type, payload) => {
    try {
      if (type === "DEEPTURTOL_ECHO360_COURSES") {
        const body = await echoJson("/user/enrollments");
        replyToWeb(requestId, true, { courses: coursesFromPayload(body) });
        return;
      }

      if (
        type === "DEEPTURTOL_ECHO360_RECORDINGS" ||
        type === "DEEPTURTOL_ECHO360_SOURCES"
      ) {
        const courseId = String(payload?.courseId || "");
        if (!UUID.test(courseId))
          throw new Error("Invalid Echo360 course identifier.");
        const body = await echoJson(
          `/section/${encodeURIComponent(courseId)}/syllabus`,
        );
        const { courseName, recordings } = recordingsFromPayload(
          body,
          courseId,
        );
        if (type === "DEEPTURTOL_ECHO360_RECORDINGS") {
          replyToWeb(requestId, true, { courseName, recordings });
          return;
        }
        // SOURCES: resolve selected recordings to downloadable URLs
        const requested = new Set(
          Array.isArray(payload?.recordingIds)
            ? payload.recordingIds
            : [],
        );
        const selected = recordings.filter((r) => requested.has(r.id));
        const sources = await Promise.all(
          selected.map(async (recording) => {
            const fromSyllabus = recording.mp4_urls[0] || recording.m3u8_urls[0] || "";
            const media_url = fromSyllabus || (await classroomStreamUrl(recording.id));
            log(`source ${recording.id} (${recording.title}): ${fromSyllabus ? "from syllabus" : "from classroomStreamUrl"} → ${media_url.slice(0, 80)}`);
            return {
              id: recording.id,
              title: recording.title,
              date: recording.date,
              course_id: recording.course_id,
              course_name: recording.course_name || courseName,
              media_url,
              media_kind: media_url.endsWith(".mp4") ? "mp4" : "hls",
            };
          }),
        );
        replyToWeb(requestId, true, { sources });
        return;
      }

      throw new Error("Unsupported Echo360 connector request.");
    } catch (error) {
      replyToWeb(
        requestId,
        false,
        undefined,
        error instanceof Error
          ? error.message
          : "The Echo360 connector failed.",
      );
    }
  };

  /* ---- Set up listeners on the DeepTurtol library page ---- */

  /* ---- Track the LMS tab so we can close it on demand ---- */
  let lmsTab = null;
  const closeLmsTab = () => {
    if (lmsTab && !lmsTab.closed) {
      try { lmsTab.close(); } catch { /* some TM versions lack close() */ }
      lmsTab = null;
    }
    // Safety: close any echo360.net.au tabs opened by this script
    try { GM_closeTab(); } catch { /* GM_closeTab may not exist */ }
  };

  if (isLibrary()) {
    window.addEventListener("message", async (event) => {
      if (
        event.origin !== location.origin ||
        event.data?.source !== WEB_SOURCE ||
        typeof event.data?.requestId !== "string"
      )
        return;

      const { requestId, type, payload } = event.data;

      if (type === "DEEPTURTOL_ECHO360_PING") {
        replyToWeb(requestId, true, {
          installed: true,
          version: String(GM_info.script.version || ""),
        });
        return;
      }

      if (type === "DEEPTURTOL_ECHO360_OPEN_LMS") {
        lmsTab = GM_openInTab(LMS_LAUNCH_URL, {
          active: true,
          insert: true,
          setParent: true,
        });
        // Fallback: close after 30s even if no close signal arrives.
        setTimeout(() => closeLmsTab(), 30_000);
        replyToWeb(requestId, true, {
          state: "signin_required",
          message:
            "Opened UniMelb Canvas. Complete the sign-in in the new tab, then return here.",
        });
        return;
      }

      if (type === "DEEPTURTOL_ECHO360_CLOSE_LMS") {
        closeLmsTab();
        replyToWeb(requestId, true, { closed: true });
        return;
      }

      if (
        [
          "DEEPTURTOL_ECHO360_COURSES",
          "DEEPTURTOL_ECHO360_RECORDINGS",
          "DEEPTURTOL_ECHO360_SOURCES",
        ].includes(type)
      ) {
        await handleRequest(requestId, type, payload);
        // If this was a SOURCES request that succeeded → LMS tab is done.
        if (type === "DEEPTURTOL_ECHO360_SOURCES") closeLmsTab();
      }
    });
  }

  /* ---- Echo360-tab handler (legacy — no longer used for requests) ---- */
  if (isEcho()) {
    // The script still runs here so the user knows it's installed, but all
    // API requests now originate from the library page via GM_xmlhttpRequest.
  }
})();
