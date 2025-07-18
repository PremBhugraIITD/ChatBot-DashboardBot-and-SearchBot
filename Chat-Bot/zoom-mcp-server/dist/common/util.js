import { getUserAgent } from "universal-user-agent";
import { VERSION } from "./version.js";
import { createZoomError } from "./error.js";
import { getAccessToken } from "./auth.js";
export async function parseResponseBody(response) {
    const contentType = response.headers.get("content-type");
    if (contentType?.includes("application/json")) {
        return response.json();
    }
    return response.text();
}
const USER_AGENT = `zoom-mcp-server/v${VERSION} ${getUserAgent()}`;
export async function zoomRequest(url, options = {}) {
    const token = (await getAccessToken()).access_token;
    const headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        Authorization: `Bearer ${token}`,
        ...options.headers,
    };
    const response = await fetch(url, {
        method: options.method || "GET",
        headers,
        body: options.body ? JSON.stringify(options.body) : undefined,
    });
    const responseBody = await parseResponseBody(response);
    if (!response.ok) {
        throw createZoomError(response.status, responseBody);
    }
    return responseBody;
}
