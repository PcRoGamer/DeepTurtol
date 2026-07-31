/**
 * Narrow WebUI boundary for the Tampermonkey Echo360 connector.
 *
 * The browser userscript executes requests in an already-signed-in Echo360
 * page. This module receives only its non-secret results; it never has access
 * to browser cookies or the Echo360 iframe's DOM.
 */
const WEB_SOURCE = "deepturtol-web";
const CONNECTOR_SOURCE = "deepturtol-echo360-userscript";

type ConnectorReply<T> = {
  source: typeof CONNECTOR_SOURCE;
  requestId: string;
  ok: boolean;
  result?: T;
  error?: string;
};

export type Echo360Course = { id: string; name: string; url: string };
export type Echo360Recording = {
  id: string;
  title: string;
  date: string;
  course_id: string;
  course_name: string;
  has_media: boolean;
};
export type Echo360Source = {
  id: string;
  title: string;
  date: string;
  course_id: string;
  course_name: string;
  media_url: string;
  media_kind: "mp4" | "hls";
};

type RequestType =
  | "DEEPTURTOL_ECHO360_PING"
  | "DEEPTURTOL_ECHO360_OPEN_LMS"
  | "DEEPTURTOL_ECHO360_CLOSE_LMS"
  | "DEEPTURTOL_ECHO360_COURSES"
  | "DEEPTURTOL_ECHO360_RECORDINGS"
  | "DEEPTURTOL_ECHO360_SOURCES";

function connectorRequest<T>(
  type: RequestType,
  payload?: Record<string, unknown>,
  timeoutMs = 20_000,
): Promise<T> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("The Echo360 connector is available only in the WebUI."));
  }
  const requestId = crypto.randomUUID();
  return new Promise<T>((resolve, reject) => {
    const timer = window.setTimeout(() => {
      window.removeEventListener("message", onMessage);
      reject(new Error("The Echo360 connector did not respond. Open Echo360 through UniMelb LMS, then try again."));
    }, timeoutMs);
    function onMessage(event: MessageEvent<ConnectorReply<T>>) {
      if (
        event.origin !== window.location.origin ||
        event.data?.source !== CONNECTOR_SOURCE ||
        event.data.requestId !== requestId
      ) {
        return;
      }
      window.clearTimeout(timer);
      window.removeEventListener("message", onMessage);
      if (event.data.ok && event.data.result) resolve(event.data.result);
      else reject(new Error(event.data.error || "The Echo360 connector could not complete that request."));
    }
    window.addEventListener("message", onMessage);
    window.postMessage({ source: WEB_SOURCE, requestId, type, payload }, window.location.origin);
  });
}

export type ConnectorInfo = { installed: boolean; version?: string };

export async function hasEcho360Connector(): Promise<boolean> {
  try {
    const result = await connectorRequest<ConnectorInfo>(
      "DEEPTURTOL_ECHO360_PING",
      undefined,
      2_500,
    );
    return result.installed === true;
  } catch {
    return false;
  }
}

export async function getConnectorInfo(): Promise<ConnectorInfo | null> {
  try {
    return await connectorRequest<ConnectorInfo>(
      "DEEPTURTOL_ECHO360_PING",
      undefined,
      2_500,
    );
  } catch {
    return null;
  }
}

export async function getExpectedConnectorVersion(): Promise<string | null> {
  try {
    const res = await fetch("/echo360-connector-version");
    if (!res.ok) return null;
    const data = await res.json();
    return typeof data.version === "string" ? data.version : null;
  } catch {
    return null;
  }
}

export function openEcho360ThroughLms(): Promise<{ message: string }> {
  return connectorRequest("DEEPTURTOL_ECHO360_OPEN_LMS");
}

export function closeLmsTab(): Promise<{ closed: boolean }> {
  return connectorRequest("DEEPTURTOL_ECHO360_CLOSE_LMS", undefined, 5_000);
}

export function listEcho360Courses(): Promise<{ courses: Echo360Course[] }> {
  // Long timeout: the Echo360 tab may need to load through LMS SSO first.
  return connectorRequest("DEEPTURTOL_ECHO360_COURSES", undefined, 60_000);
}

export function listEcho360Recordings(
  courseId: string,
): Promise<{ courseName: string; recordings: Echo360Recording[] }> {
  return connectorRequest("DEEPTURTOL_ECHO360_RECORDINGS", { courseId }, 60_000);
}

export function resolveEcho360Sources(
  courseId: string,
  recordingIds: string[],
): Promise<{ sources: Echo360Source[] }> {
  return connectorRequest("DEEPTURTOL_ECHO360_SOURCES", { courseId, recordingIds }, 60_000);
}
