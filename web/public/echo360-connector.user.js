// ==UserScript==
// @name         DeepTurtol Echo360 Connector
// @namespace    http://localhost:3000/
// @version      1.9.0
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
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_deleteValue
// @connect      echo360.net.au
// @connect      content.echo360.net.au
// @connect      canvas.lms.unimelb.edu.au
// @run-at       document-start
// ==/UserScript==

/*
 * This is deliberately a browser-side operator, not a cookie bridge.
 *
 * DUAL-MODE architecture:
 *
 * 1) Library-page mode (localhost:3000): Echo360 metadata (courses,
 *    recordings) is fetched via GM_xmlhttpRequest, which includes Echo360
 *    session cookies.  For media URLs, the cross-origin syllabus endpoint
 *    often returns a stripped response — so we fall back to mode 2.
 *
 * 2) Echo360-tab mode (echo360.net.au): A background Echo360 tab fetches the
 *    same syllabus endpoint via same-origin fetch(), which Echo360's server
 *    treats as a first-party request and returns the full response including
 *    HLS/MP4 URLs.  Communication uses GM_setValue/GM_getValue.
 *
 * The script never reads, serialises, or sends a browser cookie to any server
 * outside the user's direct browser session.
 */
(() => {
  "use strict";
  /* Debug trace: accumulates messages, included in error replies. */
  var _trace = [];
  var trace = function (msg) { _trace.push(msg); };
  var traceFlush = function () {
    var lines = _trace.slice();
    _trace.length = 0;
    return lines.join(" | ");
  };

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
      const xhrOpts = {
          method: options.method || "GET",
          url: `${ECHO360_ORIGIN}${path}`,
          headers: {
            Accept: "application/json, text/html, */*",
            // Helps Echo360 treat this closer to a same-origin request.
            Referer: `${ECHO360_ORIGIN}/`,
            ...options.headers,
          },
          withCredentials: true,
          timeout: options.timeout ?? 30_000,
      };
      if (options.followRedirects !== undefined) {
        xhrOpts.followRedirects = options.followRedirects;
      }
      GM_xmlhttpRequest(Object.assign(xhrOpts, {
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
      }));
    });

  /** Convenience: fetch JSON from Echo360. */
  const echoJson = async (path) => {
    const response = await echoFetch(path, {
      headers: { Accept: "application/json" },
    });
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
    const response = await echoFetch(path, {
      headers: { Accept: "text/html" },
    });
    return response.responseText;
  };

  /** Fetch a URL and return the final URL after redirects (for download links).
   *  Echo360 `/media/download/{id}/{file}?lessonId={compositeId}` returns a
   *  303 redirect to a signed S3 URL; this helper follows it and returns the
   *  signed URL. */
  const echoRedirectUrl = async (path) => {
    const response = await echoFetch(path, { followRedirects: true });
    return response.finalUrl || "";
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

  /** Classify a media URL into its kind for the backend API. */
  const mediaKind = (url) => {
    if (!url) return "hls";
    if (/\.(?:mp4|webm|mov)$/i.test(url)) return "mp4";
    if (/\.(?:mp3|aac|wav|ogg|m4a|flac)$/i.test(url)) return "mp3";
    return "hls";
  };

  /** Extract the lesson UUID from a composite Echo360 recording ID
   *  (format: G_{group}_{lesson}_{start}_{end}). */
  const lessonUuidFromId = (id) => {
    if (!id || typeof id !== "string") return null;
    const m = id.match(/^G_[^_]+_([^_]+)/);
    return m ? m[1] : null;
  };

  /** Probe the Echo360 download endpoint for a longer-lived content URL.
   *  The download endpoint returns a 303 → signed S3 URL (valid for hours),
   *  which the backend can later fetch with FFmpeg.  Uses HEAD to avoid
   *  downloading the full media body. */
  const tryDownloadUrl = async (mediaId, lessonId) => {
    if (!mediaId || !lessonId) return null;
    const encLessonId = encodeURIComponent(lessonId);
    // Try audio first (smallest redirect), then progressive video qualities.
    const qualities = ["audio.mp3", "sd2.mp4", "sd1.mp4", "hd1.mp4"];
    for (const quality of qualities) {
      const path = "/media/download/" + encodeURIComponent(mediaId) + "/" + quality + "?lessonId=" + encLessonId;
      try {
        const resp = await echoFetch(path, {
          method: "HEAD",
          followRedirects: true,
          timeout: 15_000,
        });
        if (resp.finalUrl && /https?:\/\/content\./.test(resp.finalUrl)) {
          trace("tryDownloadUrl(" + quality + ") → " + resp.finalUrl.slice(0, 100));
          return resp.finalUrl;
        }
      } catch (e) {
        trace("tryDownloadUrl(" + quality + "): " + e.message);
      }
    }
    return null;
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
      trace("recording " + id + ": mp4=" + mp4Urls.length + " m3u8=" + m3u8Urls.length + " hasMedia=" + !!media);
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
        media_id: media?.id || "",
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
   *  media URL (.m3u8, .mp4, .mp3, .aac, .wav).  Returns the first match or null. */
  const deepFindMediaUrl = (obj, depth = 0) => {
    if (depth > 10 || obj == null || typeof obj === "boolean" || typeof obj === "number") return null;
    if (typeof obj === "string") {
      if (/\.(?:m3u8|mp4|mp3|aac|wav|ogg)$/i.test(obj))
        return contentUrl(obj);
      if (/\.(?:m3u8|mp4|mp3|aac)/i.test(obj)) {
        // It might be a full URL with query params
        const match = obj.match(
          /https?:\/\/[^\s"']+?\.(?:m3u8|mp4|mp3|aac|wav|ogg)[^\s"']*/i,
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

  /** Extract the individual lesson UUID from a composite Echo360 ID.
   *  Composite format: G_{groupUUID}_{lessonUUID}_{start}_{end}
   *  Returns the lesson UUID or null if the ID isn't composite. */
  const extractLessonUuid = (id) => {
    if (!id.startsWith("G_")) return null;
    // G_<group>_<lesson>_<timestamps...>
    // The second UUID in the sequence is the lesson UUID.
    const match = id.match(
      /^G_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i,
    );
    return match ? match[2] : null;
  };

  const classroomStreamUrl = async (recordingId, recording) => {
    const encId = encodeURIComponent(recordingId);
    const lessonUuid = extractLessonUuid(recordingId);
    const encUuid = lessonUuid
      ? encodeURIComponent(lessonUuid)
      : null;
    const mediaId = recording?.media_id || lessonUuid || "";
    const encMediaId = mediaId ? encodeURIComponent(mediaId) : null;

    /* ---- 1) Try known Echo360 lesson media API endpoints ---- */
    trace("classroomStreamUrl(" + recordingId + "): uuid=" + (lessonUuid || "(none)") + " mediaId=" + mediaId.slice(0, 12));
    const apiPaths = [];
    // Try with full composite ID
    for (const tmpl of [
      "/{0}/media",
      "/api/{0}/playback",
      "/{0}/source",
      "/{0}",
      "/api/{0}",
      "/api/v1/lessons/{0}",
      "/api/v2/lessons/{0}",
      "/api/v2/{0}",
      "/{0}/player",
      "/{0}/resource",
    ]) {
      apiPaths.push(tmpl.replace("{0}", "lesson/" + encId));
      // Also try with just the lesson UUID
      if (encUuid)
        apiPaths.push(tmpl.replace("{0}", "lesson/" + encUuid));
    }
    // Also try `/media/download/{mediaId}/{quality}?lessonId={compositeId}`
    // which returns a 303 → signed S3 URL (works for both video and audio)
    if (encMediaId) {
      for (const quality of ["hd1.mp4", "sd1.mp4", "sd2.mp4", "audio.mp3"]) {
        apiPaths.push(
          "/media/download/" + encMediaId + "/" + quality + "?lessonId=" + encId,
        );
        // Also try with lesson UUID as mediaId fallback
        if (encUuid && encUuid !== encMediaId) {
          apiPaths.push(
            "/media/download/" + encUuid + "/" + quality + "?lessonId=" + encId,
          );
        }
      }
    }
    // Finally the classroom page URL (always with full ID)
    apiPaths.push("/lesson/" + encId + "/classroom");

    const tried = new Set();
    for (const apiPath of apiPaths) {
      if (tried.has(apiPath)) continue;
      tried.add(apiPath);
      try {
        const body = await echoJson(apiPath);
        const found = deepFindMediaUrl(body);
        if (found) {
          trace("API " + apiPath + " → FOUND: " + found);
          return found;
        }
        trace("API " + apiPath + " → JSON OK but no media URL");
      } catch (err) {
            trace("API " + apiPath + " → " + err.message);
      }
    }

    /* ---- 2) Try download endpoint (303 → signed URL) ---- */
    // If none of the JSON endpoints worked, try the download endpoint
    // with followRedirects to capture the signed content URL directly.
    if (encMediaId) {
      for (const quality of ["hd1.mp4", "sd1.mp4", "sd2.mp4", "audio.mp3"]) {
        const dlPath = "/media/download/" + encMediaId + "/" + quality + "?lessonId=" + encId;
        try {
          const signedUrl = await echoRedirectUrl(dlPath);
          if (signedUrl && /https?:\/\/content\./.test(signedUrl)) {
            trace("Download " + dlPath + " → " + signedUrl.slice(0, 100));
            return signedUrl;
          }
        } catch (err) {
          trace("Download " + dlPath + " → " + err.message);
        }
        // Fallback: try with lesson UUID as mediaId
        if (encUuid && encUuid !== encMediaId) {
          const dlPath2 = "/media/download/" + encUuid + "/" + quality + "?lessonId=" + encId;
          try {
            const signedUrl = await echoRedirectUrl(dlPath2);
            if (signedUrl && /https?:\/\/content\./.test(signedUrl)) {
              trace("Download " + dlPath2 + " → " + signedUrl.slice(0, 100));
              return signedUrl;
            }
          } catch (err) {
            trace("Download " + dlPath2 + " → " + err.message);
          }
        }
      }
    }

    /* ---- 3) Scrape the classroom page HTML for embedded URLs ---- */
    trace("Download endpoints exhausted — fetching classroom HTML");
    let page;
    try {
      page = await echoHtml(`/lesson/${encId}/classroom`);
    } catch (err) {
      trace("echoHtml failed: " + err.message);
      throw new Error("Echo360 has no playable media for this lecture. (HTML fetch: " + err.message + ")");
    }
    trace("classroom HTML: " + page.length + " chars, starts: " + page.slice(0, 300));
    const pageReplaced = page.replace(/\\\//g, "/");

    /* ---- Helper: collect URLs matching a pattern ---- */
    const findUrls = (pattern, options = {}) => {
      const matches = [...pageReplaced.matchAll(pattern)]
        .map((m) => m[1] || m[0])
        .filter((url) => {
          if (url.startsWith("http")) return true;
          if (url.startsWith("//")) return true;
          return false;
        })
        .map((url) => (url.startsWith("//") ? "https:" + url : url));
      if (options.unique) return [...new Set(matches)];
      return matches;
    };

    // a) Echo player config (various patterns)
    const playerPatterns = [
      /Echo\["echoPlayerV2FullApp"\]\("(.+?)"\)/,
      /Echo\s*=\s*Echo\s*\|\|\s*\{\};\s*Echo\["echoPlayerV2FullApp"\]\("(.+?)"\)/,
      /"echoPlayerV2FullApp"\s*,\s*"([^"]+)"\s*\)/,
    ];
    for (const playerPattern of playerPatterns) {
      const pgMatch = page.match(playerPattern);
      if (pgMatch) {
        try {
          let rawJson = pgMatch[1];
          rawJson = rawJson.replace(/\\"/g, '"').replace(/\\\\/g, "\\");
          const player = JSON.parse(rawJson);
          // Try various known player config paths
          const candidates = [
            player?.video?.playableMedias,
            player?.playableMedias,
            player?.media?.playableMedias,
            player?.video?.media,
            player?.sources,
            player?.media,
          ];
          for (const list of candidates) {
            const items = Array.isArray(list) ? list : [];
            for (const item of items) {
              if (item?.uri) return contentUrl(String(item.uri));
              if (item?.src) return contentUrl(String(item.src));
            }
          }
          // Also check for direct uri/src on the player
          if (player?.uri) return contentUrl(String(player.uri));
          if (player?.src) return contentUrl(String(player.src));
          // Some configs have a single media object
          if (player?.video?.media?.uri)
            return contentUrl(String(player.video.media.uri));
          if (player?.video?.sourceUri)
            return contentUrl(String(player.video.sourceUri));
        } catch {
          /* fall through */
        }
      }
    }

    // b) Search for embedded JSON blobs (__INITIAL_STATE__ etc)
    const jsonBlobs = page.match(
      /(?:window\.__INITIAL_STATE__|window\.__DATA__|__NEXT_DATA__|window\.__PRELOADED_STATE__)\s*=\s*(\{.+?\});/gs,
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

    // c) Search for JSON-LD or script type="application/json"
    const scriptJsons = page.match(
      /<script[^>]+type=["']application\/json["'][^>]*>([\s\S]*?)<\/script>/gi,
    );
    if (scriptJsons) {
      for (const tag of scriptJsons) {
        try {
          const content = tag.replace(/<script[^>]*>([\s\S]*)<\/script>/i, "$1");
          const data = JSON.parse(content);
          const found = deepFindMediaUrl(data);
          if (found) return found;
        } catch {
          /* try next */
        }
      }
    }

    // d) Collect ALL streaming/media URLs from page (non-unique)
    const allUrls = findUrls(
      /https?:\/\/[^"'\s,<>]+?\.(?:m3u8|mp4|mp3|aac|wav|ogg)(?:[^"'\s,<>]*)?/gi,
      { unique: true },
    );

    // e) Also look for content.echo360.net.au URLs (even without .m3u8/.mp4)
    const contentUrls = findUrls(
      /https?:\/\/[^"'\s,<>]*content[^"'\s,<>]*echo360[^"'\s,<>]+\/[^"'\s,<>"]+/gi,
      { unique: true },
    );

    // f) Brute-force m3u8 URLs in page — prefer av.m3u8 (adaptive video)
    const m3u8Candidates = allUrls.filter((u) => u.includes(".m3u8"));
    const av = m3u8Candidates.filter((u) => u.includes("av.m3u8"));
    if (av.length > 0) return av.sort()[av.length - 1];
    if (m3u8Candidates.length > 0)
      return m3u8Candidates[m3u8Candidates.length - 1];

    // g) Brute-force mp4 URLs in page — prefer HD
    const mp4Candidates = allUrls.filter((u) => u.includes(".mp4"));
    const hdMp4 = mp4Candidates.filter((u) => /hd/i.test(u));
    if (hdMp4.length > 0) return hdMp4[0];
    if (mp4Candidates.length > 0) return mp4Candidates[0];

    // h) Audio URLs (.mp3 / .aac)
    const audioCandidates = allUrls.filter(
      (u) => /\.(?:mp3|aac|wav|ogg)/i.test(u),
    );
    if (audioCandidates.length > 0) return audioCandidates[0];

    // j) Any content.echo360 URL (fallback server-side validation will check)
    if (contentUrls.length > 0) return contentUrls[0];

    // k) Check if the page is actually a course page (not a lecture page)
    const pageTitle = page.match(/<title>([^<]*)<\/title>/i);
    const pageIsCourse =
      pageTitle &&
      !pageTitle[1].includes("Lesson") &&
      !pageTitle[1].includes("Lecture") &&
      !pageTitle[1].includes("Video") &&
      !pageTitle[1].includes("Media");

    const foundUrlsSummary =
      (m3u8Candidates.length > 0 ? "m3u8:" + m3u8Candidates.join(", ") : "") +
      (m3u8Candidates.length > 0 && mp4Candidates.length > 0 ? "; " : "") +
      (mp4Candidates.length > 0 ? "mp4:" + mp4Candidates.join(", ") : "") +
      (audioCandidates.length > 0 ? (m3u8Candidates.length > 0 || mp4Candidates.length > 0 ? "; " : "") + "audio:" + audioCandidates.join(", ") : "") +
      (contentUrls.length > 0
        ? (m3u8Candidates.length > 0 || mp4Candidates.length > 0 || audioCandidates.length > 0 ? "; " : "") +
          "content:" + contentUrls.join(", ")
        : "");

    throw new Error(
      "Echo360 has no playable media for this lecture." +
        (pageIsCourse ? " (classroom page shows course overview, not a lecture)" : "") +
        (foundUrlsSummary ? " Found URLs but none match expected patterns: " + foundUrlsSummary : ""),
    );
  };

  /*
   * Cross-tab Echo360 request/response protocol.
   *
   * When the syllabus JSON (fetched from localhost via GM_xmlhttpRequest)
   * lacks media URLs, we ask an echo360.net.au tab to fetch the same endpoint
   * same-origin, which returns the full response.
   *
   * WIRE FORMAT (GM storage — JSON strings):
   *   dt_echo360_request = { requestId, courseId, recordingIds }
   *   dt_echo360_response_{requestId} = { ok, sources?: [...], error?: "..." }
   */

  const ECHO_TAB_POLL_MS = 800;
  const ECHO_TAB_TIMEOUT_MS = 60_000;
  // The Echo360 tab navigates through classroom pages (up to ~36s each),
  // so the timeout must account for multiple recordings.
  const echoTabTimeoutMs = (recordingCount) =>
    Math.max(ECHO_TAB_TIMEOUT_MS, recordingCount * 60_000);

  /** Send a SOURCES request to an Echo360 tab via GM storage and wait.
   *
   *  @param {string} courseId
   *  @param {object[]} recordings  — recordings missing media from syllabus
   *  @param {object}  [echoTab]    — optional pre-opened tab (best-effort close on timeout)
   */
  const echoTabSources = async (courseId, recordings, echoTab) => {
    const requestId =
      "dt_" + Date.now() + "_" + Math.random().toString(36).slice(2, 8);
    GM_setValue(
      "dt_echo360_request",
      JSON.stringify({
        requestId,
        courseId,
        recordingIds: recordings.map((r) => r.id),
        recordings: recordings.map((r) => ({
          id: r.id,
          title: r.title,
          date: r.date,
        })),
      }),
    );

    const timeoutMs = echoTabTimeoutMs(recordings.length);
    const startTime = Date.now();
    while (Date.now() - startTime < timeoutMs) {
      const raw = GM_getValue(`dt_echo360_response_${requestId}`);
      if (raw) {
        GM_deleteValue(`dt_echo360_response_${requestId}`);
        const result = JSON.parse(raw);
        if (!result.ok)
          throw new Error(
            result.error || "Echo360 cross-tab request failed",
          );
        return result.sources;
      }
      // Also check if an already-open Echo360 tab posted a message
      await new Promise((r) => setTimeout(r, ECHO_TAB_POLL_MS));
    }

    // Timeout — clean up and throw.
    try { if (echoTab) echoTab.close(); } catch { /* best effort */ }
    GM_deleteValue(`dt_echo360_response_${requestId}`);
    throw new Error(
      "Echo360 tab did not respond in time. " +
        "Make sure you have an echo360.net.au tab open and are signed in.",
    );
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

        // Pre-open an Echo360 tab *synchronously* (within user-action
        // context) so Tampermonkey's GM_openInTab does not get blocked.
        // We will use it below only if the syllabus JSON (fetched
        // cross-origin) lacks media URLs.
        const needsCrossTab =
          type === "DEEPTURTOL_ECHO360_SOURCES" &&
          Array.isArray(payload?.recordingIds) &&
          payload.recordingIds.length > 0;
        let echoTab = null;
        let usedEchoTab = false;
        if (needsCrossTab) {
          echoTab = GM_openInTab("https://echo360.net.au/user/enrollments", {
            active: false,
            insert: true,
            setParent: true,
          });
        }

        /* ---- Fetch syllabus (first await — everything above was sync) ---- */
        let courseName = "";
        let recordings = [];
        let syllabusFailed = false;
        try {
          const body = await echoJson(
            `/section/${encodeURIComponent(courseId)}/syllabus`,
          );
          const result = recordingsFromPayload(body, courseId);
          courseName = result.courseName;
          recordings = result.recordings;
        } catch (err) {
          syllabusFailed = true;
          trace(
            "syllabus JSON failed (" +
              err.message +
              ") — will try Echo360 tab",
          );
        }

        if (type === "DEEPTURTOL_ECHO360_RECORDINGS") {
          if (echoTab) try { echoTab.close(); } catch {}
          replyToWeb(requestId, true, { courseName, recordings });
          return;
        }

        // SOURCES: resolve selected recordings to downloadable URLs
        const requested = new Set(
          Array.isArray(payload?.recordingIds)
            ? payload.recordingIds
            : [],
        );

        // Build the set of recordings we need to resolve.
        // When the syllabus JSON succeeded, use its recordings data.
        // Otherwise build minimal recording objects from request metadata
        // or plain IDs — the Echo360 tab can still resolve them.
        let selected;
        if (!syllabusFailed && recordings.length > 0) {
          selected = recordings.filter((r) => requested.has(r.id));
        } else {
          const payloadRecs = payload?.recordings || {};
          selected = [...requested].map((id) => ({
            id,
            title: payloadRecs[id]?.title || "",
            date: payloadRecs[id]?.date || "",
            course_id: courseId,
            course_name: courseName,
            mp4_urls: [],
            m3u8_urls: [],
            media_id: "",
          }));
        }

        // First pass — media already in the syllabus JSON
        const sources = [];
        const needsTab = [];
        for (const rec of selected) {
          const fromSyllabus = rec.mp4_urls[0] || rec.m3u8_urls[0] || "";
          if (fromSyllabus) {
            trace("source " + rec.id + " (" + rec.title + "): from syllabus");
            sources.push({
              id: rec.id,
              title: rec.title,
              date: rec.date,
              course_id: rec.course_id,
              course_name: rec.course_name || courseName,
              media_url: fromSyllabus,
              media_kind: mediaKind(fromSyllabus),
            });
          } else {
            needsTab.push(rec);
          }
        }

        // Second pass — use an Echo360 tab (same-origin) for recordings
        // whose media URLs the cross-origin syllabus did not include.
        if (needsTab.length > 0) {
          usedEchoTab = true;
          trace(
            "syllabus has no media for " +
              needsTab.length +
              " recordings — trying Echo360 tab",
          );
          /** Try HTML scraping as a last resort for a recording. */
          const tryScrape = async (rec) => {
            try {
              const media_url = await classroomStreamUrl(rec.id, rec);
              trace("source " + rec.id + " (" + rec.title + "): from HTML scrape");
              sources.push({
                id: rec.id,
                title: rec.title,
                date: rec.date,
                course_id: rec.course_id,
                course_name: rec.course_name || courseName,
                media_url,
                media_kind: mediaKind(media_url),
              });
            } catch (scrapeErr) {
              trace("scrape failed for " + rec.id + ": " + scrapeErr.message);
            }
          };

          try {
            trace(
              "requesting Echo360 tab for " +
                needsTab.length +
                " recordings: " +
                needsTab.map((r) => r.id.slice(0, 20)).join(", "),
            );
            const tabSources = await echoTabSources(
              courseId,
              needsTab,
              echoTab,
            );
            trace(
              "Echo360 tab returned " + tabSources.length + "/" + needsTab.length + " sources",
            );
            // Add whatever the tab resolved
            const tabIds = new Set(tabSources.map((s) => s.id));
            for (const s of tabSources) {
              // Tab sources may be missing metadata — look up from needsTab
              const rec = needsTab.find((r) => r.id === s.id) || {};
              // The Echo360 tab extracts the video src (often a short-lived CDN
              // URL that expires in minutes). Try the download endpoint (HEAD)
              // for a longer-lived S3 signed URL (valid for hours), so the
              // backend can later fetch it with FFmpeg.
              let mediaUrl = s.media_url || "";
              const dlMediaId = lessonUuidFromId(s.id);
              if (dlMediaId) {
                const longLivedUrl = await tryDownloadUrl(dlMediaId, s.id);
                if (longLivedUrl) {
                  trace("source " + s.id + " (" + (s.title || rec.title || "(untitled)") + "): upgraded to download URL");
                  mediaUrl = longLivedUrl;
                }
              }
              if (!mediaUrl) {
                trace("source " + s.id + " (" + (s.title || rec.title || "(untitled)") + "): from Echo360 tab → (no URL)");
              } else {
                trace(
                  "source " + s.id + " (" + (s.title || rec.title || "(untitled)") + "): from Echo360 tab → " +
                    mediaUrl.slice(0, 80),
                );
              }
              sources.push({
                id: s.id,
                title: s.title || rec.title || "",
                date: s.date || rec.date || "",
                course_id: courseId,
                course_name: courseName,
                media_url: mediaUrl,
                media_kind: mediaKind(mediaUrl),
              });
            }
            // Any recordings still unresolved → HTML scrape fallback
            const stillMissing = needsTab.filter((r) => !tabIds.has(r.id));
            if (stillMissing.length > 0) {
              trace(
                "Echo360 tab missing " +
                  stillMissing.length +
                  "/" + needsTab.length +
                  " recordings — falling back to HTML scrape",
              );
            }
            for (const rec of stillMissing) {
              await tryScrape(rec);
            }
          } catch (tabErr) {
            trace("Echo360 tab failed: " + tabErr.message);
            // Last resort — try classroomStreamUrl for each.
            for (const rec of needsTab) {
              await tryScrape(rec);
            }
          }
        }

        // Close the tab if we opened it but didn't end up needing it.
        if (!usedEchoTab && echoTab) {
          try { if (!echoTab.closed) echoTab.close(); } catch {}
        }

        trace(
          "SOURCES resolved: " + sources.length + "/" + selected.length +
            " recordings (" +
            sources.filter((s) => s.media_url).length + " with media)",
        );

        replyToWeb(requestId, true, { sources });
        return;
      }

      throw new Error("Unsupported Echo360 connector request.");
    } catch (error) {
      var traceInfo = traceFlush();
      replyToWeb(
        requestId,
        false,
        undefined,
        (error instanceof Error ? error.message : "The Echo360 connector failed.") +
          (traceInfo ? " [DEBUG: " + traceInfo + "]" : ""),
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
    // (GM_closeTab would close the library page so we rely on
    //  the Echo360 tab's own window.close() after processing.)
  };

  if (isLibrary()) {
    log("Connector script loaded on library page");
    window.addEventListener("message", async (event) => {
      if (
        event.origin !== location.origin ||
        event.data?.source !== WEB_SOURCE ||
        typeof event.data?.requestId !== "string"
      )
        return;

      const { requestId, type, payload } = event.data;
      log("Received " + type + " requestId=" + requestId.slice(0, 8));

      if (type === "DEEPTURTOL_ECHO360_PING") {
        replyToWeb(requestId, true, {
          installed: true,
          version: String(GM_info.script.version || ""),
        });
        log("Replied to PING");
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
        log("Replied to OPEN_LMS");
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

  /* ---- Echo360-tab handler — classroom page navigation for media URLs ---- */
  if (isEcho()) {
    log("Connector script loaded on Echo360 tab: " + location.hostname);
    /* Helper: flush trace into GM storage for debugging. */
    const saveTrace = (msg) => {
      var t = GM_getValue("dt_echo360_trace", "");
      GM_setValue("dt_echo360_trace", t + "[" + Date.now() + "] " + msg + "\n");
    };

    /* If we are on a classroom page AND have a batch-processing state stored,
     * wait for the video element, extract the URL, and either navigate to
     * the next recording or finalise. */
    const lessonMatch = location.pathname.match(/\/lesson\/([^/?]+)/);
    const processingRaw = GM_getValue("dt_echo360_processing");

    // If we have processing state but are NOT on a lesson page (e.g. redirect
    // from /lesson/{id}/classroom to / or /home), the processing is stuck.
    // Clear it so the polling loop can recover on the next request cycle.
    if (processingRaw && !lessonMatch) {
      saveTrace("stale processing state on non-lesson page — clearing");
      GM_deleteValue("dt_echo360_processing");
      // Also write an empty response so the library page doesn't wait forever.
      try {
        var stale = JSON.parse(processingRaw);
        if (stale.requestId) {
          GM_setValue(
            "dt_echo360_response_" + stale.requestId,
            JSON.stringify({ ok: true, sources: stale.sources || [] }),
          );
        }
      } catch (_) { /* ignore parse errors */ }
    }

    if (lessonMatch && processingRaw) {
      const state = JSON.parse(processingRaw);
      const idx = state.nextIndex;

      if (idx < state.recordingIds.length && !state.done) {
        saveTrace("classroom loaded, idx=" + idx + " waiting for video…");
        let attempts = 0;
        const CHECK_MS = 1200;
        const MAX_ATTEMPTS = 30;  // ~36 s total per recording

        const iv = setInterval(() => {
          attempts++;
          // Try via content-player > video (echo360‑downloader's approach)
          const player = document.getElementById("content-player");
          const video = player
            ? player.querySelector("video")
            : document.querySelector("video");
          const src = video ? (video.getAttribute("src") || video.src || "") : "";

          // Fallback: brute-force media URLs in rendered page text
          const pageText = document.body?.innerText || "";
          const mediaFallback = pageText.match(
            /https?:\/\/[^\s"]+\.(?:m3u8|mp4|mp3|aac|wav|ogg)[^\s"]*/i,
          );

          const mediaUrl = src || (mediaFallback ? mediaFallback[0] : "");

          if (mediaUrl || attempts >= MAX_ATTEMPTS) {
            clearInterval(iv);
            if (mediaUrl) {
              const recId = state.recordingIds[idx];
              const recMeta = state.meta?.[recId] || {};
              saveTrace("idx=" + idx + " → found: " + mediaUrl.slice(0, 100));
              state.sources.push({
                id: recId,
                title: recMeta.title || "",
                date: recMeta.date || "",
                media_url: mediaUrl,
                media_kind: mediaKind(mediaUrl),
              });
            } else {
              saveTrace("idx=" + idx + " → no media found after timeout");
            }

            state.nextIndex++;
            if (state.nextIndex >= state.recordingIds.length || state.done) {
              // Complete
              state.done = true;
              saveTrace(
                "all " + state.sources.length + "/" +
                  state.recordingIds.length + " resolved",
              );
              GM_setValue(
                "dt_echo360_response_" + state.requestId,
                JSON.stringify({ ok: true, sources: state.sources }),
              );
              GM_deleteValue("dt_echo360_processing");
              // Close the tab — we're done.
              try { window.close(); } catch {}
            } else {
              GM_setValue("dt_echo360_processing", JSON.stringify(state));
              saveTrace("navigating to idx=" + state.nextIndex);
              location.href =
                location.origin + "/lesson/" +
                encodeURIComponent(state.recordingIds[state.nextIndex]) +
                "/classroom";
            }
          }
        }, CHECK_MS);
      }
    } else {
      /* Not on a classroom page (or no active processing state) —
       * poll for incoming requests. */
      const poll = () => {
        if (GM_getValue("dt_echo360_processing")) return;
        const raw = GM_getValue("dt_echo360_request");
        if (!raw) return;
        GM_deleteValue("dt_echo360_request");

        try {
          const request = JSON.parse(raw);
          saveTrace("received request " + request.requestId);
          // Build a lookup of recording metadata (title/date) from the request
          const meta = {};
          if (Array.isArray(request.recordings)) {
            for (const r of request.recordings) meta[r.id] = r;
          }
          GM_setValue(
            "dt_echo360_processing",
            JSON.stringify({
              requestId: request.requestId,
              recordingIds: request.recordingIds,
              meta,  // passed through so response sources include title/date
              nextIndex: 0,
              sources: [],
              done: false,
            }),
          );
          saveTrace("navigating to first classroom page");
          location.href =
            location.origin + "/lesson/" +
            encodeURIComponent(request.recordingIds[0]) +
            "/classroom";
        } catch {}
      };

      // Also check immediately for an orphaned processing state from a
      // previous navigation that didn't complete.
      const orphanRaw = GM_getValue("dt_echo360_processing");
      if (orphanRaw) {
        const orphan = JSON.parse(orphanRaw);
        if (orphan.nextIndex < orphan.recordingIds.length && !orphan.done) {
          saveTrace("orphaned processing — resuming idx=" + orphan.nextIndex);
          location.href =
            location.origin + "/lesson/" +
            encodeURIComponent(orphan.recordingIds[orphan.nextIndex]) +
            "/classroom";
        } else if (!orphan.done) {
          // All done but not marked — mark done
          GM_setValue(
            "dt_echo360_response_" + orphan.requestId,
            JSON.stringify({ ok: true, sources: orphan.sources }),
          );
          GM_deleteValue("dt_echo360_processing");
        }
      }

      poll();
      setInterval(poll, 3000);
    }
  }
})();
