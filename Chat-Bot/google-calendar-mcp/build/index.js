#!/usr/bin/env node


// src/index.ts
import { fileURLToPath } from "url";

// src/server.ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { McpError as McpError3, ErrorCode as ErrorCode3 } from "@modelcontextprotocol/sdk/types.js";

// src/auth/client.ts
import { OAuth2Client } from "google-auth-library";
function validateEnvironmentVariables() {
  const requiredVars = ["GCALENDAR_ACCESS_TOKEN", "GCALENDAR_REFRESH_TOKEN"];
  const missing = requiredVars.filter((varName) => !process.env[varName]);
  if (missing.length > 0) {
    throw new Error(`Missing required environment variables: ${missing.join(", ")}`);
  }
  console.error("\u2705 Google Calendar environment variables validated successfully");
}
async function initializeOAuth2Client() {
  try {
    const accessToken = process.env.GCALENDAR_ACCESS_TOKEN;
    const refreshToken = process.env.GCALENDAR_REFRESH_TOKEN;
    validateEnvironmentVariables();
    console.error("Creating OAuth2 client with environment tokens...");
    const oAuth2Client = new OAuth2Client();
    oAuth2Client.setCredentials({
      access_token: accessToken,
      refresh_token: refreshToken,
      token_type: "Bearer",
      scope: [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events"
      ].join(" ")
    });
    console.error("OAuth2 client configured successfully with environment tokens.");
    return oAuth2Client;
  } catch (error) {
    console.error("Failed to authorize with environment tokens:", error);
    throw new Error(`Google Calendar authentication failed: ${error instanceof Error ? error.message : "Unknown error"}`);
  }
}

// src/tools/registry.ts
import { z } from "zod";
import { zodToJsonSchema } from "zod-to-json-schema";

// src/handlers/core/BaseToolHandler.ts
import { McpError, ErrorCode } from "@modelcontextprotocol/sdk/types.js";
import { GaxiosError } from "gaxios";
import { google } from "googleapis";
var BaseToolHandler = class {
  handleGoogleApiError(error) {
    if (error instanceof GaxiosError) {
      const status = error.response?.status;
      const errorData = error.response?.data;
      if (errorData?.error === "invalid_grant") {
        throw new McpError(
          ErrorCode.InvalidRequest,
          "Authentication token is invalid or expired. Please re-run the authentication process (e.g., `npm run auth`)."
        );
      }
      if (status === 403) {
        throw new McpError(
          ErrorCode.InvalidRequest,
          `Access denied: ${errorData?.error?.message || "Insufficient permissions"}`
        );
      }
      if (status === 404) {
        throw new McpError(
          ErrorCode.InvalidRequest,
          `Resource not found: ${errorData?.error?.message || "The requested calendar or event does not exist"}`
        );
      }
      if (status === 429) {
        throw new McpError(
          ErrorCode.InternalError,
          "Rate limit exceeded. Please try again later."
        );
      }
      if (status && status >= 500) {
        throw new McpError(
          ErrorCode.InternalError,
          `Google API server error: ${errorData?.error?.message || error.message}`
        );
      }
      throw new McpError(
        ErrorCode.InvalidRequest,
        `Google API error: ${errorData?.error?.message || error.message}`
      );
    }
    if (error instanceof Error) {
      throw new McpError(
        ErrorCode.InternalError,
        `Internal error: ${error.message}`
      );
    }
    throw new McpError(
      ErrorCode.InternalError,
      "An unknown error occurred"
    );
  }
  getCalendar(auth) {
    return google.calendar({
      version: "v3",
      auth,
      timeout: 3e3
      // 3 second timeout for API calls
    });
  }
  async withTimeout(promise, timeoutMs = 3e4) {
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error(`Operation timed out after ${timeoutMs}ms`)), timeoutMs);
    });
    return Promise.race([promise, timeoutPromise]);
  }
  /**
   * Gets calendar details including default timezone
   * @param client OAuth2Client
   * @param calendarId Calendar ID to fetch details for
   * @returns Calendar details with timezone
   */
  async getCalendarDetails(client, calendarId) {
    try {
      const calendar = this.getCalendar(client);
      const response = await calendar.calendarList.get({ calendarId });
      if (!response.data) {
        throw new Error(`Calendar ${calendarId} not found`);
      }
      return response.data;
    } catch (error) {
      throw this.handleGoogleApiError(error);
    }
  }
  /**
   * Gets the default timezone for a calendar, falling back to UTC if not available
   * @param client OAuth2Client
   * @param calendarId Calendar ID
   * @returns Timezone string (IANA format)
   */
  async getCalendarTimezone(client, calendarId) {
    try {
      const calendarDetails = await this.getCalendarDetails(client, calendarId);
      return calendarDetails.timeZone || "UTC";
    } catch (error) {
      return "UTC";
    }
  }
};

// src/handlers/core/ListCalendarsHandler.ts
var ListCalendarsHandler = class extends BaseToolHandler {
  async runTool(_, oauth2Client) {
    const calendars = await this.listCalendars(oauth2Client);
    return {
      content: [{
        type: "text",
        // This MUST be a string literal
        text: this.formatCalendarList(calendars)
      }]
    };
  }
  async listCalendars(client) {
    try {
      const calendar = this.getCalendar(client);
      const response = await calendar.calendarList.list();
      return response.data.items || [];
    } catch (error) {
      throw this.handleGoogleApiError(error);
    }
  }
  /**
   * Formats a list of calendars into a user-friendly string with detailed information.
   */
  formatCalendarList(calendars) {
    return calendars.map((cal) => {
      const name = this.sanitizeString(cal.summaryOverride || cal.summary || "Untitled");
      const id = this.sanitizeString(cal.id || "no-id");
      const timezone = this.sanitizeString(cal.timeZone || "Unknown");
      const kind = this.sanitizeString(cal.kind || "Unknown");
      const accessRole = this.sanitizeString(cal.accessRole || "Unknown");
      const isPrimary = cal.primary ? " (PRIMARY)" : "";
      const isSelected = cal.selected !== false ? "Yes" : "No";
      const isHidden = cal.hidden ? "Yes" : "No";
      const backgroundColor = this.sanitizeString(cal.backgroundColor || "Default");
      let description = "";
      if (cal.description) {
        const sanitizedDesc = this.sanitizeString(cal.description);
        description = sanitizedDesc.length > 100 ? `
  Description: ${sanitizedDesc.substring(0, 100)}...` : `
  Description: ${sanitizedDesc}`;
      }
      let defaultReminders = "None";
      if (cal.defaultReminders && cal.defaultReminders.length > 0) {
        defaultReminders = cal.defaultReminders.map((reminder) => {
          const method = this.sanitizeString(reminder.method || "unknown");
          const minutes = reminder.minutes || 0;
          return `${method} (${minutes}min before)`;
        }).join(", ");
      }
      return `${name}${isPrimary} (${id})
  Timezone: ${timezone}
  Kind: ${kind}
  Access Role: ${accessRole}
  Selected: ${isSelected}
  Hidden: ${isHidden}
  Background Color: ${backgroundColor}
  Default Reminders: ${defaultReminders}${description}`;
    }).join("\n\n");
  }
  /**
   * Sanitizes a string to prevent crashes by removing problematic characters
   */
  sanitizeString(str) {
    if (!str) return "";
    return str.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, "").replace(/[\uFFFE\uFFFF]/g, "").substring(0, 500).trim();
  }
};

// src/handlers/utils.ts
function generateEventUrl(calendarId, eventId) {
  const encodedCalendarId = encodeURIComponent(calendarId);
  const encodedEventId = encodeURIComponent(eventId);
  return `https://calendar.google.com/calendar/event?eid=${encodedEventId}&cid=${encodedCalendarId}`;
}
function getEventUrl(event, calendarId) {
  if (event.htmlLink) {
    return event.htmlLink;
  } else if (calendarId && event.id) {
    return generateEventUrl(calendarId, event.id);
  }
  return null;
}
function formatDateTime(dateTime, date, timeZone) {
  if (!dateTime && !date) return "unspecified";
  try {
    const dt = dateTime || date;
    if (!dt) return "unspecified";
    const parsedDate = new Date(dt);
    if (isNaN(parsedDate.getTime())) return dt;
    if (date && !dateTime) {
      return parsedDate.toLocaleDateString("en-US", {
        weekday: "short",
        year: "numeric",
        month: "short",
        day: "numeric"
      });
    }
    const options = {
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short"
    };
    if (timeZone) {
      options.timeZone = timeZone;
    }
    return parsedDate.toLocaleString("en-US", options);
  } catch (error) {
    return dateTime || date || "unspecified";
  }
}
function formatAttendees(attendees) {
  if (!attendees || attendees.length === 0) return "";
  const formatted = attendees.map((attendee) => {
    const email = attendee.email || "unknown";
    const name = attendee.displayName || email;
    const status = attendee.responseStatus || "unknown";
    const statusText = {
      "accepted": "accepted",
      "declined": "declined",
      "tentative": "tentative",
      "needsAction": "pending"
    }[status] || "unknown";
    return `${name} (${statusText})`;
  }).join(", ");
  return `
Guests: ${formatted}`;
}
function formatEventWithDetails(event, calendarId) {
  const title = event.summary ? `Event: ${event.summary}` : "Untitled Event";
  const eventId = event.id ? `
Event ID: ${event.id}` : "";
  const description = event.description ? `
Description: ${event.description}` : "";
  const location = event.location ? `
Location: ${event.location}` : "";
  const startTime = formatDateTime(event.start?.dateTime, event.start?.date, event.start?.timeZone || void 0);
  const endTime = formatDateTime(event.end?.dateTime, event.end?.date, event.end?.timeZone || void 0);
  let timeInfo;
  if (event.start?.date) {
    if (event.start.date === event.end?.date) {
      timeInfo = `
Date: ${startTime}`;
    } else {
      const endDate = event.end?.date ? new Date(event.end.date) : null;
      if (endDate) {
        endDate.setDate(endDate.getDate() - 1);
        const adjustedEndTime = endDate.toLocaleDateString("en-US", {
          weekday: "short",
          year: "numeric",
          month: "short",
          day: "numeric"
        });
        timeInfo = `
Start Date: ${startTime}
End Date: ${adjustedEndTime}`;
      } else {
        timeInfo = `
Start Date: ${startTime}`;
      }
    }
  } else {
    timeInfo = `
Start: ${startTime}
End: ${endTime}`;
  }
  const attendeeInfo = formatAttendees(event.attendees);
  const eventUrl = getEventUrl(event, calendarId);
  const urlInfo = eventUrl ? `
View: ${eventUrl}` : "";
  return `${title}${eventId}${description}${timeInfo}${location}${attendeeInfo}${urlInfo}`;
}

// src/handlers/core/BatchRequestHandler.ts
var BatchRequestError = class extends Error {
  constructor(message, errors, partial = false) {
    super(message);
    this.errors = errors;
    this.partial = partial;
    this.name = "BatchRequestError";
  }
};
var BatchRequestHandler = class {
  // 1 second
  constructor(auth) {
    this.auth = auth;
    this.boundary = "batch_boundary_" + Date.now();
  }
  batchEndpoint = "https://www.googleapis.com/batch/calendar/v3";
  boundary;
  maxRetries = 3;
  baseDelay = 1e3;
  async executeBatch(requests) {
    if (requests.length === 0) {
      return [];
    }
    if (requests.length > 50) {
      throw new Error("Batch requests cannot exceed 50 requests per batch");
    }
    return this.executeBatchWithRetry(requests, 0);
  }
  async executeBatchWithRetry(requests, attempt) {
    try {
      const batchBody = this.createBatchBody(requests);
      const token = await this.auth.getAccessToken();
      const response = await fetch(this.batchEndpoint, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token.token}`,
          "Content-Type": `multipart/mixed; boundary=${this.boundary}`
        },
        body: batchBody
      });
      const responseText = await response.text();
      if (response.status === 429 && attempt < this.maxRetries) {
        const retryAfter = response.headers.get("Retry-After");
        const delay = retryAfter ? parseInt(retryAfter) * 1e3 : this.baseDelay * Math.pow(2, attempt);
        process.stderr.write(`Rate limited, retrying after ${delay}ms (attempt ${attempt + 1}/${this.maxRetries})
`);
        await this.sleep(delay);
        return this.executeBatchWithRetry(requests, attempt + 1);
      }
      if (!response.ok) {
        throw new BatchRequestError(
          `Batch request failed: ${response.status} ${response.statusText}`,
          [{
            statusCode: response.status,
            message: `HTTP ${response.status}: ${response.statusText}`,
            details: responseText
          }]
        );
      }
      return this.parseBatchResponse(responseText);
    } catch (error) {
      if (error instanceof BatchRequestError) {
        throw error;
      }
      if (attempt < this.maxRetries && this.isRetryableError(error)) {
        const delay = this.baseDelay * Math.pow(2, attempt);
        process.stderr.write(`Network error, retrying after ${delay}ms (attempt ${attempt + 1}/${this.maxRetries}): ${error instanceof Error ? error.message : "Unknown error"}
`);
        await this.sleep(delay);
        return this.executeBatchWithRetry(requests, attempt + 1);
      }
      throw new BatchRequestError(
        `Failed to execute batch request: ${error instanceof Error ? error.message : "Unknown error"}`,
        [{
          statusCode: 0,
          message: error instanceof Error ? error.message : "Unknown error",
          details: error
        }]
      );
    }
  }
  isRetryableError(error) {
    if (error instanceof Error) {
      const message = error.message.toLowerCase();
      return message.includes("network") || message.includes("timeout") || message.includes("econnreset") || message.includes("enotfound");
    }
    return false;
  }
  sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
  createBatchBody(requests) {
    return requests.map((req, index) => {
      const parts = [
        `--${this.boundary}`,
        `Content-Type: application/http`,
        `Content-ID: <item${index + 1}>`,
        "",
        `${req.method} ${req.path} HTTP/1.1`
      ];
      if (req.headers) {
        Object.entries(req.headers).forEach(([key, value]) => {
          parts.push(`${key}: ${value}`);
        });
      }
      if (req.body) {
        parts.push("Content-Type: application/json");
        parts.push("");
        parts.push(JSON.stringify(req.body));
      }
      return parts.join("\r\n");
    }).join("\r\n\r\n") + `\r
--${this.boundary}--`;
  }
  parseBatchResponse(responseText) {
    const lines = responseText.split(/\r?\n/);
    let boundary = null;
    for (let i = 0; i < Math.min(10, lines.length); i++) {
      const line = lines[i];
      if (line.toLowerCase().includes("content-type:") && line.includes("boundary=")) {
        const boundaryMatch = line.match(/boundary=([^\s\r\n;]+)/);
        if (boundaryMatch) {
          boundary = boundaryMatch[1];
          break;
        }
      }
    }
    if (!boundary) {
      const boundaryMatch = responseText.match(/--([a-zA-Z0-9_-]+)/);
      if (boundaryMatch) {
        boundary = boundaryMatch[1];
      }
    }
    if (!boundary) {
      throw new Error("Could not find boundary in batch response");
    }
    const parts = responseText.split(`--${boundary}`);
    const responses = [];
    for (let i = 1; i < parts.length; i++) {
      const part = parts[i];
      if (part.trim() === "" || part.trim() === "--" || part.trim().startsWith("--")) continue;
      const response = this.parseResponsePart(part);
      if (response) {
        responses.push(response);
      }
    }
    return responses;
  }
  parseResponsePart(part) {
    const lines = part.split(/\r?\n/);
    let httpLineIndex = -1;
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].startsWith("HTTP/1.1")) {
        httpLineIndex = i;
        break;
      }
    }
    if (httpLineIndex === -1) return null;
    const httpLine = lines[httpLineIndex];
    const statusMatch = httpLine.match(/HTTP\/1\.1 (\d+)/);
    if (!statusMatch) return null;
    const statusCode = parseInt(statusMatch[1]);
    const headers = {};
    let bodyStartIndex = httpLineIndex + 1;
    for (let i = httpLineIndex + 1; i < lines.length; i++) {
      const line = lines[i];
      if (line.trim() === "") {
        bodyStartIndex = i + 1;
        break;
      }
      const colonIndex = line.indexOf(":");
      if (colonIndex > 0) {
        const key = line.substring(0, colonIndex).trim();
        const value = line.substring(colonIndex + 1).trim();
        headers[key] = value;
      }
    }
    let body = null;
    if (bodyStartIndex < lines.length) {
      const bodyLines = [];
      for (let i = bodyStartIndex; i < lines.length; i++) {
        bodyLines.push(lines[i]);
      }
      while (bodyLines.length > 0 && bodyLines[bodyLines.length - 1].trim() === "") {
        bodyLines.pop();
      }
      if (bodyLines.length > 0) {
        const bodyText = bodyLines.join("\n");
        if (bodyText.trim()) {
          try {
            body = JSON.parse(bodyText);
          } catch {
            body = bodyText;
          }
        }
      }
    }
    return {
      statusCode,
      headers,
      body
    };
  }
};

// src/handlers/utils/datetime.ts
function hasTimezoneInDatetime(datetime) {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$/.test(datetime);
}
function convertToRFC3339(datetime, fallbackTimezone) {
  if (hasTimezoneInDatetime(datetime)) {
    return datetime;
  } else {
    try {
      const date = new Date(datetime);
      const options = {
        timeZone: fallbackTimezone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        timeZoneName: "longOffset"
      };
      const formatter = new Intl.DateTimeFormat("sv-SE", options);
      const parts = formatter.formatToParts(date);
      const year = parts.find((p) => p.type === "year")?.value;
      const month = parts.find((p) => p.type === "month")?.value;
      const day = parts.find((p) => p.type === "day")?.value;
      const hour = parts.find((p) => p.type === "hour")?.value;
      const minute = parts.find((p) => p.type === "minute")?.value;
      const second = parts.find((p) => p.type === "second")?.value;
      const timeZoneName = parts.find((p) => p.type === "timeZoneName")?.value;
      if (year && month && day && hour && minute && second && timeZoneName) {
        const offsetMatch = timeZoneName.match(/GMT([+-]\d{2}:\d{2})/);
        const offset = offsetMatch ? offsetMatch[1] : "Z";
        return `${year}-${month}-${day}T${hour}:${minute}:${second}${offset}`;
      }
    } catch (error) {
      return datetime + "Z";
    }
    return datetime + "Z";
  }
}
function createTimeObject(datetime, fallbackTimezone) {
  if (hasTimezoneInDatetime(datetime)) {
    return { dateTime: datetime };
  } else {
    return { dateTime: datetime, timeZone: fallbackTimezone };
  }
}

// src/handlers/core/ListEventsHandler.ts
var ListEventsHandler = class extends BaseToolHandler {
  async runTool(args, oauth2Client) {
    const validArgs = args;
    const calendarIds = Array.isArray(validArgs.calendarId) ? validArgs.calendarId : [validArgs.calendarId];
    const allEvents = await this.fetchEvents(oauth2Client, calendarIds, {
      timeMin: validArgs.timeMin,
      timeMax: validArgs.timeMax,
      timeZone: validArgs.timeZone
    });
    if (allEvents.length === 0) {
      return {
        content: [{
          type: "text",
          text: `No events found in ${calendarIds.length} calendar(s).`
        }]
      };
    }
    let text = calendarIds.length === 1 ? `Found ${allEvents.length} event(s):

` : `Found ${allEvents.length} event(s) across ${calendarIds.length} calendars:

`;
    if (calendarIds.length === 1) {
      allEvents.forEach((event, index) => {
        const eventDetails = formatEventWithDetails(event, event.calendarId);
        text += `${index + 1}. ${eventDetails}

`;
      });
    } else {
      const grouped = this.groupEventsByCalendar(allEvents);
      for (const [calendarId, events] of Object.entries(grouped)) {
        text += `Calendar: ${calendarId}

`;
        events.forEach((event, index) => {
          const eventDetails = formatEventWithDetails(event, event.calendarId);
          text += `${index + 1}. ${eventDetails}

`;
        });
        text += "\n";
      }
    }
    return {
      content: [{
        type: "text",
        text: text.trim()
      }]
    };
  }
  async fetchEvents(client, calendarIds, options) {
    if (calendarIds.length === 1) {
      return this.fetchSingleCalendarEvents(client, calendarIds[0], options);
    }
    return this.fetchMultipleCalendarEvents(client, calendarIds, options);
  }
  async fetchSingleCalendarEvents(client, calendarId, options) {
    try {
      const calendar = this.getCalendar(client);
      let timeMin = options.timeMin;
      let timeMax = options.timeMax;
      if (timeMin || timeMax) {
        const timezone = options.timeZone || await this.getCalendarTimezone(client, calendarId);
        timeMin = timeMin ? convertToRFC3339(timeMin, timezone) : void 0;
        timeMax = timeMax ? convertToRFC3339(timeMax, timezone) : void 0;
      }
      const response = await calendar.events.list({
        calendarId,
        timeMin,
        timeMax,
        singleEvents: true,
        orderBy: "startTime"
      });
      return (response.data.items || []).map((event) => ({
        ...event,
        calendarId
      }));
    } catch (error) {
      throw this.handleGoogleApiError(error);
    }
  }
  async fetchMultipleCalendarEvents(client, calendarIds, options) {
    const batchHandler = new BatchRequestHandler(client);
    const requests = await Promise.all(calendarIds.map(async (calendarId) => ({
      method: "GET",
      path: await this.buildEventsPath(client, calendarId, options)
    })));
    const responses = await batchHandler.executeBatch(requests);
    const { events, errors } = this.processBatchResponses(responses, calendarIds);
    if (errors.length > 0) {
      process.stderr.write(`Some calendars had errors: ${errors.map((e) => `${e.calendarId}: ${e.error}`).join(", ")}
`);
    }
    return this.sortEventsByStartTime(events);
  }
  async buildEventsPath(client, calendarId, options) {
    let timeMin = options.timeMin;
    let timeMax = options.timeMax;
    if (timeMin || timeMax) {
      const timezone = options.timeZone || await this.getCalendarTimezone(client, calendarId);
      timeMin = timeMin ? convertToRFC3339(timeMin, timezone) : void 0;
      timeMax = timeMax ? convertToRFC3339(timeMax, timezone) : void 0;
    }
    const params = new URLSearchParams({
      singleEvents: "true",
      orderBy: "startTime",
      ...timeMin && { timeMin },
      ...timeMax && { timeMax }
    });
    return `/calendar/v3/calendars/${encodeURIComponent(calendarId)}/events?${params.toString()}`;
  }
  processBatchResponses(responses, calendarIds) {
    const events = [];
    const errors = [];
    responses.forEach((response, index) => {
      const calendarId = calendarIds[index];
      if (response.statusCode === 200 && response.body?.items) {
        const calendarEvents = response.body.items.map((event) => ({
          ...event,
          calendarId
        }));
        events.push(...calendarEvents);
      } else {
        const errorMessage = response.body?.error?.message || response.body?.message || `HTTP ${response.statusCode}`;
        errors.push({ calendarId, error: errorMessage });
      }
    });
    return { events, errors };
  }
  sortEventsByStartTime(events) {
    return events.sort((a, b) => {
      const aStart = a.start?.dateTime || a.start?.date || "";
      const bStart = b.start?.dateTime || b.start?.date || "";
      return aStart.localeCompare(bStart);
    });
  }
  groupEventsByCalendar(events) {
    return events.reduce((acc, event) => {
      const calId = event.calendarId;
      if (!acc[calId]) acc[calId] = [];
      acc[calId].push(event);
      return acc;
    }, {});
  }
};

// src/handlers/core/SearchEventsHandler.ts
var SearchEventsHandler = class extends BaseToolHandler {
  async runTool(args, oauth2Client) {
    const validArgs = args;
    const events = await this.searchEvents(oauth2Client, validArgs);
    if (events.length === 0) {
      return {
        content: [{
          type: "text",
          text: "No events found matching your search criteria."
        }]
      };
    }
    let text = `Found ${events.length} event(s) matching your search:

`;
    events.forEach((event, index) => {
      const eventDetails = formatEventWithDetails(event, validArgs.calendarId);
      text += `${index + 1}. ${eventDetails}

`;
    });
    return {
      content: [{
        type: "text",
        text: text.trim()
      }]
    };
  }
  async searchEvents(client, args) {
    try {
      const calendar = this.getCalendar(client);
      const timezone = args.timeZone || await this.getCalendarTimezone(client, args.calendarId);
      const timeMin = convertToRFC3339(args.timeMin, timezone);
      const timeMax = convertToRFC3339(args.timeMax, timezone);
      const response = await calendar.events.list({
        calendarId: args.calendarId,
        q: args.query,
        timeMin,
        timeMax,
        singleEvents: true,
        orderBy: "startTime"
      });
      return response.data.items || [];
    } catch (error) {
      throw this.handleGoogleApiError(error);
    }
  }
};

// src/handlers/core/ListColorsHandler.ts
var ListColorsHandler = class extends BaseToolHandler {
  async runTool(_, oauth2Client) {
    const colors = await this.listColors(oauth2Client);
    return {
      content: [{
        type: "text",
        text: `Available event colors:
${this.formatColorList(colors)}`
      }]
    };
  }
  async listColors(client) {
    try {
      const calendar = this.getCalendar(client);
      const response = await calendar.colors.get();
      if (!response.data) throw new Error("Failed to retrieve colors");
      return response.data;
    } catch (error) {
      throw this.handleGoogleApiError(error);
    }
  }
  /**
   * Formats the color information into a user-friendly string.
   */
  formatColorList(colors) {
    const eventColors = colors.event || {};
    return Object.entries(eventColors).map(([id, colorInfo]) => `Color ID: ${id} - ${colorInfo.background} (background) / ${colorInfo.foreground} (foreground)`).join("\n");
  }
};

// src/handlers/core/CreateEventHandler.ts
var CreateEventHandler = class extends BaseToolHandler {
  async runTool(args, oauth2Client) {
    const validArgs = args;
    const event = await this.createEvent(oauth2Client, validArgs);
    const eventDetails = formatEventWithDetails(event, validArgs.calendarId);
    const text = `Event created successfully!

${eventDetails}`;
    return {
      content: [{
        type: "text",
        text
      }]
    };
  }
  async createEvent(client, args) {
    try {
      const calendar = this.getCalendar(client);
      const timezone = args.timeZone || await this.getCalendarTimezone(client, args.calendarId);
      const requestBody = {
        summary: args.summary,
        description: args.description,
        start: createTimeObject(args.start, timezone),
        end: createTimeObject(args.end, timezone),
        attendees: args.attendees,
        location: args.location,
        colorId: args.colorId,
        reminders: args.reminders,
        recurrence: args.recurrence
      };
      const response = await calendar.events.insert({
        calendarId: args.calendarId,
        requestBody
      });
      if (!response.data) throw new Error("Failed to create event, no data returned");
      return response.data;
    } catch (error) {
      throw this.handleGoogleApiError(error);
    }
  }
};

// src/handlers/core/RecurringEventHelpers.ts
var RecurringEventHelpers = class {
  calendar;
  constructor(calendar) {
    this.calendar = calendar;
  }
  /**
   * Get the calendar instance
   */
  getCalendar() {
    return this.calendar;
  }
  /**
   * Detects if an event is recurring or single
   */
  async detectEventType(eventId, calendarId) {
    const response = await this.calendar.events.get({
      calendarId,
      eventId
    });
    const event = response.data;
    return event.recurrence && event.recurrence.length > 0 ? "recurring" : "single";
  }
  /**
   * Formats an instance ID for single instance updates
   */
  formatInstanceId(eventId, originalStartTime) {
    const utcDate = new Date(originalStartTime);
    const basicTimeFormat = utcDate.toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";
    return `${eventId}_${basicTimeFormat}`;
  }
  /**
   * Calculates the UNTIL date for future instance updates
   */
  calculateUntilDate(futureStartDate) {
    const futureDate = new Date(futureStartDate);
    const untilDate = new Date(futureDate.getTime() - 864e5);
    return untilDate.toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";
  }
  /**
   * Calculates end time based on original duration
   */
  calculateEndTime(newStartTime, originalEvent) {
    const newStart = new Date(newStartTime);
    const originalStart = new Date(originalEvent.start.dateTime);
    const originalEnd = new Date(originalEvent.end.dateTime);
    const duration = originalEnd.getTime() - originalStart.getTime();
    return new Date(newStart.getTime() + duration).toISOString();
  }
  /**
   * Updates recurrence rule with UNTIL clause
   */
  updateRecurrenceWithUntil(recurrence, untilDate) {
    if (!recurrence || recurrence.length === 0) {
      throw new Error("No recurrence rule found");
    }
    const updatedRecurrence = [];
    let foundRRule = false;
    for (const rule of recurrence) {
      if (rule.startsWith("RRULE:")) {
        foundRRule = true;
        const updatedRule = rule.replace(/;UNTIL=\d{8}T\d{6}Z/g, "").replace(/;COUNT=\d+/g, "") + `;UNTIL=${untilDate}`;
        updatedRecurrence.push(updatedRule);
      } else {
        updatedRecurrence.push(rule);
      }
    }
    if (!foundRRule) {
      throw new Error("No RRULE found in recurrence rules");
    }
    return updatedRecurrence;
  }
  /**
   * Cleans event fields for new event creation
   */
  cleanEventForDuplication(event) {
    const cleanedEvent = { ...event };
    delete cleanedEvent.id;
    delete cleanedEvent.etag;
    delete cleanedEvent.iCalUID;
    delete cleanedEvent.created;
    delete cleanedEvent.updated;
    delete cleanedEvent.htmlLink;
    delete cleanedEvent.hangoutLink;
    return cleanedEvent;
  }
  /**
   * Builds request body for event updates
   */
  buildUpdateRequestBody(args, defaultTimeZone) {
    const requestBody = {};
    if (args.summary !== void 0 && args.summary !== null) requestBody.summary = args.summary;
    if (args.description !== void 0 && args.description !== null) requestBody.description = args.description;
    if (args.location !== void 0 && args.location !== null) requestBody.location = args.location;
    if (args.colorId !== void 0 && args.colorId !== null) requestBody.colorId = args.colorId;
    if (args.attendees !== void 0 && args.attendees !== null) requestBody.attendees = args.attendees;
    if (args.reminders !== void 0 && args.reminders !== null) requestBody.reminders = args.reminders;
    if (args.recurrence !== void 0 && args.recurrence !== null) requestBody.recurrence = args.recurrence;
    let timeChanged = false;
    const effectiveTimeZone = args.timeZone || defaultTimeZone;
    if (args.start !== void 0 && args.start !== null) {
      requestBody.start = { dateTime: args.start, timeZone: effectiveTimeZone };
      timeChanged = true;
    }
    if (args.end !== void 0 && args.end !== null) {
      requestBody.end = { dateTime: args.end, timeZone: effectiveTimeZone };
      timeChanged = true;
    }
    if (timeChanged || !args.start && !args.end && effectiveTimeZone) {
      if (!requestBody.start) requestBody.start = {};
      if (!requestBody.end) requestBody.end = {};
      if (!requestBody.start.timeZone) requestBody.start.timeZone = effectiveTimeZone;
      if (!requestBody.end.timeZone) requestBody.end.timeZone = effectiveTimeZone;
    }
    return requestBody;
  }
};
var RecurringEventError = class extends Error {
  code;
  constructor(message, code) {
    super(message);
    this.name = "RecurringEventError";
    this.code = code;
  }
};
var RECURRING_EVENT_ERRORS = {
  INVALID_SCOPE: "INVALID_MODIFICATION_SCOPE",
  MISSING_ORIGINAL_TIME: "MISSING_ORIGINAL_START_TIME",
  MISSING_FUTURE_DATE: "MISSING_FUTURE_START_DATE",
  PAST_FUTURE_DATE: "FUTURE_DATE_IN_PAST",
  NON_RECURRING_SCOPE: "SCOPE_NOT_APPLICABLE_TO_SINGLE_EVENT"
};

// src/handlers/core/UpdateEventHandler.ts
var UpdateEventHandler = class extends BaseToolHandler {
  async runTool(args, oauth2Client) {
    const validArgs = args;
    const event = await this.updateEventWithScope(oauth2Client, validArgs);
    const eventDetails = formatEventWithDetails(event, validArgs.calendarId);
    const text = `Event updated successfully!

${eventDetails}`;
    return {
      content: [{
        type: "text",
        text
      }]
    };
  }
  async updateEventWithScope(client, args) {
    try {
      const calendar = this.getCalendar(client);
      const helpers = new RecurringEventHelpers(calendar);
      const defaultTimeZone = await this.getCalendarTimezone(client, args.calendarId);
      const eventType = await helpers.detectEventType(args.eventId, args.calendarId);
      if (args.modificationScope && args.modificationScope !== "all" && eventType !== "recurring") {
        throw new RecurringEventError(
          'Scope other than "all" only applies to recurring events',
          RECURRING_EVENT_ERRORS.NON_RECURRING_SCOPE
        );
      }
      switch (args.modificationScope) {
        case "thisEventOnly":
          return this.updateSingleInstance(helpers, args, defaultTimeZone);
        case "all":
        case void 0:
          return this.updateAllInstances(helpers, args, defaultTimeZone);
        case "thisAndFollowing":
          return this.updateFutureInstances(helpers, args, defaultTimeZone);
        default:
          throw new RecurringEventError(
            `Invalid modification scope: ${args.modificationScope}`,
            RECURRING_EVENT_ERRORS.INVALID_SCOPE
          );
      }
    } catch (error) {
      if (error instanceof RecurringEventError) {
        throw error;
      }
      throw this.handleGoogleApiError(error);
    }
  }
  async updateSingleInstance(helpers, args, defaultTimeZone) {
    if (!args.originalStartTime) {
      throw new RecurringEventError(
        "originalStartTime is required for single instance updates",
        RECURRING_EVENT_ERRORS.MISSING_ORIGINAL_TIME
      );
    }
    const calendar = helpers.getCalendar();
    const instanceId = helpers.formatInstanceId(args.eventId, args.originalStartTime);
    const response = await calendar.events.patch({
      calendarId: args.calendarId,
      eventId: instanceId,
      requestBody: helpers.buildUpdateRequestBody(args, defaultTimeZone)
    });
    if (!response.data) throw new Error("Failed to update event instance");
    return response.data;
  }
  async updateAllInstances(helpers, args, defaultTimeZone) {
    const calendar = helpers.getCalendar();
    const response = await calendar.events.patch({
      calendarId: args.calendarId,
      eventId: args.eventId,
      requestBody: helpers.buildUpdateRequestBody(args, defaultTimeZone)
    });
    if (!response.data) throw new Error("Failed to update event");
    return response.data;
  }
  async updateFutureInstances(helpers, args, defaultTimeZone) {
    if (!args.futureStartDate) {
      throw new RecurringEventError(
        "futureStartDate is required for future instance updates",
        RECURRING_EVENT_ERRORS.MISSING_FUTURE_DATE
      );
    }
    const calendar = helpers.getCalendar();
    const effectiveTimeZone = args.timeZone || defaultTimeZone;
    const originalResponse = await calendar.events.get({
      calendarId: args.calendarId,
      eventId: args.eventId
    });
    const originalEvent = originalResponse.data;
    if (!originalEvent.recurrence) {
      throw new Error("Event does not have recurrence rules");
    }
    const untilDate = helpers.calculateUntilDate(args.futureStartDate);
    const updatedRecurrence = helpers.updateRecurrenceWithUntil(originalEvent.recurrence, untilDate);
    await calendar.events.patch({
      calendarId: args.calendarId,
      eventId: args.eventId,
      requestBody: { recurrence: updatedRecurrence }
    });
    const requestBody = helpers.buildUpdateRequestBody(args, defaultTimeZone);
    let endTime = args.end;
    if (args.start || args.futureStartDate) {
      const newStartTime = args.start || args.futureStartDate;
      endTime = endTime || helpers.calculateEndTime(newStartTime, originalEvent);
    }
    const newEvent = {
      ...helpers.cleanEventForDuplication(originalEvent),
      ...requestBody,
      start: {
        dateTime: args.start || args.futureStartDate,
        timeZone: effectiveTimeZone
      },
      end: {
        dateTime: endTime,
        timeZone: effectiveTimeZone
      }
    };
    const response = await calendar.events.insert({
      calendarId: args.calendarId,
      requestBody: newEvent
    });
    if (!response.data) throw new Error("Failed to create new recurring event");
    return response.data;
  }
};

// src/handlers/core/DeleteEventHandler.ts
var DeleteEventHandler = class extends BaseToolHandler {
  async runTool(args, oauth2Client) {
    const validArgs = args;
    await this.deleteEvent(oauth2Client, validArgs);
    return {
      content: [{
        type: "text",
        text: "Event deleted successfully"
      }]
    };
  }
  async deleteEvent(client, args) {
    try {
      const calendar = this.getCalendar(client);
      await calendar.events.delete({
        calendarId: args.calendarId,
        eventId: args.eventId,
        sendUpdates: args.sendUpdates
      });
    } catch (error) {
      throw this.handleGoogleApiError(error);
    }
  }
};

// src/handlers/core/FreeBusyEventHandler.ts
var FreeBusyEventHandler = class extends BaseToolHandler {
  async runTool(args, oauth2Client) {
    const validArgs = args;
    if (!this.isLessThanThreeMonths(validArgs.timeMin, validArgs.timeMax)) {
      return {
        content: [{
          type: "text",
          text: "The time gap between timeMin and timeMax must be less than 3 months"
        }]
      };
    }
    const result = await this.queryFreeBusy(oauth2Client, validArgs);
    const summaryText = this.generateAvailabilitySummary(result);
    return {
      content: [{
        type: "text",
        text: summaryText
      }]
    };
  }
  async queryFreeBusy(client, args) {
    try {
      const calendar = this.getCalendar(client);
      const response = await calendar.freebusy.query({
        requestBody: {
          timeMin: args.timeMin,
          timeMax: args.timeMax,
          timeZone: args.timeZone,
          groupExpansionMax: args.groupExpansionMax,
          calendarExpansionMax: args.calendarExpansionMax,
          items: args.calendars
        }
      });
      return response.data;
    } catch (error) {
      throw this.handleGoogleApiError(error);
    }
  }
  isLessThanThreeMonths(timeMin, timeMax) {
    const minDate = new Date(timeMin);
    const maxDate = new Date(timeMax);
    const diffInMilliseconds = maxDate.getTime() - minDate.getTime();
    const threeMonthsInMilliseconds = 3 * 30 * 24 * 60 * 60 * 1e3;
    return diffInMilliseconds <= threeMonthsInMilliseconds;
  }
  generateAvailabilitySummary(response) {
    return Object.entries(response.calendars).map(([email, calendarInfo]) => {
      if (calendarInfo.errors?.some((error) => error.reason === "notFound")) {
        return `Cannot check availability for ${email} (account not found)
`;
      }
      if (calendarInfo.busy.length === 0) {
        return `${email} is available during ${response.timeMin} to ${response.timeMax}, please schedule calendar to ${email} if you want 
`;
      }
      const busyTimes = calendarInfo.busy.map((slot) => `- From ${slot.start} to ${slot.end}`).join("\n");
      return `${email} is busy during:
${busyTimes}
`;
    }).join("\n").trim();
  }
};

// src/handlers/core/GetCurrentTimeHandler.ts
import { McpError as McpError2, ErrorCode as ErrorCode2 } from "@modelcontextprotocol/sdk/types.js";
var GetCurrentTimeHandler = class extends BaseToolHandler {
  async runTool(args, _oauth2Client) {
    const validArgs = args;
    const now = /* @__PURE__ */ new Date();
    const requestedTimeZone = validArgs.timeZone;
    const systemTimeZone = this.getSystemTimeZone();
    let result;
    if (requestedTimeZone) {
      if (!this.isValidTimeZone(requestedTimeZone)) {
        throw new McpError2(
          ErrorCode2.InvalidRequest,
          `Invalid timezone: ${requestedTimeZone}. Use IANA timezone format like 'America/Los_Angeles' or 'UTC'.`
        );
      }
      result = {
        currentTime: {
          utc: now.toISOString(),
          timestamp: now.getTime(),
          requestedTimeZone: {
            timeZone: requestedTimeZone,
            rfc3339: this.formatDateInTimeZone(now, requestedTimeZone),
            humanReadable: this.formatHumanReadable(now, requestedTimeZone),
            offset: this.getTimezoneOffset(now, requestedTimeZone)
          }
        }
      };
    } else {
      result = {
        currentTime: {
          utc: now.toISOString(),
          timestamp: now.getTime(),
          systemTimeZone: {
            timeZone: systemTimeZone,
            rfc3339: this.formatDateInTimeZone(now, systemTimeZone),
            humanReadable: this.formatHumanReadable(now, systemTimeZone),
            offset: this.getTimezoneOffset(now, systemTimeZone)
          },
          note: "System timezone shown. For HTTP mode, specify timeZone parameter for user's local time."
        }
      };
    }
    return {
      content: [{
        type: "text",
        text: JSON.stringify(result, null, 2)
      }]
    };
  }
  getSystemTimeZone() {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch {
      return "UTC";
    }
  }
  isValidTimeZone(timeZone) {
    try {
      Intl.DateTimeFormat(void 0, { timeZone });
      return true;
    } catch {
      return false;
    }
  }
  formatDateInTimeZone(date, timeZone) {
    const offset = this.getTimezoneOffset(date, timeZone);
    const isoString = date.toISOString().replace(/\.\d{3}Z$/, "");
    return isoString + offset;
  }
  formatHumanReadable(date, timeZone) {
    const formatter = new Intl.DateTimeFormat("en-US", {
      timeZone,
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      timeZoneName: "long"
    });
    return formatter.format(date);
  }
  getTimezoneOffset(_date, timeZone) {
    try {
      const offsetMinutes = this.getTimezoneOffsetMinutes(timeZone);
      if (offsetMinutes === 0) {
        return "Z";
      }
      const offsetHours = Math.floor(Math.abs(offsetMinutes) / 60);
      const offsetMins = Math.abs(offsetMinutes) % 60;
      const sign = offsetMinutes >= 0 ? "+" : "-";
      return `${sign}${offsetHours.toString().padStart(2, "0")}:${offsetMins.toString().padStart(2, "0")}`;
    } catch {
      return "Z";
    }
  }
  getTimezoneOffsetMinutes(timeZone) {
    const date = /* @__PURE__ */ new Date();
    const targetTimeString = new Intl.DateTimeFormat("sv-SE", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    }).format(date);
    const utcTimeString = new Intl.DateTimeFormat("sv-SE", {
      timeZone: "UTC",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    }).format(date);
    const targetTime = (/* @__PURE__ */ new Date(targetTimeString.replace(" ", "T") + "Z")).getTime();
    const utcTimeParsed = (/* @__PURE__ */ new Date(utcTimeString.replace(" ", "T") + "Z")).getTime();
    return (targetTime - utcTimeParsed) / (1e3 * 60);
  }
};

// src/tools/registry.ts
var ToolSchemas = {
  "list-calendars": z.object({}),
  "list-events": z.object({
    calendarId: z.string().describe(
      `ID of the calendar(s) to list events from. Accepts either a single calendar ID string or an array of calendar IDs (passed as JSON string like '["cal1", "cal2"]')`
    ),
    timeMin: z.string().refine((val) => {
      const withTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$/.test(val);
      const withoutTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(val);
      return withTimezone || withoutTimezone;
    }, "Must be ISO 8601 format: '2026-01-01T00:00:00'").describe("Start time boundary. Preferred: '2024-01-01T00:00:00' (uses timeZone parameter or calendar timezone). Also accepts: '2024-01-01T00:00:00Z' or '2024-01-01T00:00:00-08:00'.").optional(),
    timeMax: z.string().refine((val) => {
      const withTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$/.test(val);
      const withoutTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(val);
      return withTimezone || withoutTimezone;
    }, "Must be ISO 8601 format: '2026-01-01T00:00:00'").describe("End time boundary. Preferred: '2024-01-01T23:59:59' (uses timeZone parameter or calendar timezone). Also accepts: '2024-01-01T23:59:59Z' or '2024-01-01T23:59:59-08:00'.").optional(),
    timeZone: z.string().optional().describe(
      "Timezone as IANA Time Zone Database name (e.g., America/Los_Angeles). Takes priority over calendar's default timezone. Only used for timezone-naive datetime strings."
    )
  }),
  "search-events": z.object({
    calendarId: z.string().describe("ID of the calendar (use 'primary' for the main calendar)"),
    query: z.string().describe(
      "Free text search query (searches summary, description, location, attendees, etc.)"
    ),
    timeMin: z.string().refine((val) => {
      const withTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$/.test(val);
      const withoutTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(val);
      return withTimezone || withoutTimezone;
    }, "Must be ISO 8601 format: '2026-01-01T00:00:00'").describe("Start time boundary. Preferred: '2024-01-01T00:00:00' (uses timeZone parameter or calendar timezone). Also accepts: '2024-01-01T00:00:00Z' or '2024-01-01T00:00:00-08:00'."),
    timeMax: z.string().refine((val) => {
      const withTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$/.test(val);
      const withoutTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(val);
      return withTimezone || withoutTimezone;
    }, "Must be ISO 8601 format: '2026-01-01T00:00:00'").describe("End time boundary. Preferred: '2024-01-01T23:59:59' (uses timeZone parameter or calendar timezone). Also accepts: '2024-01-01T23:59:59Z' or '2024-01-01T23:59:59-08:00'."),
    timeZone: z.string().optional().describe(
      "Timezone as IANA Time Zone Database name (e.g., America/Los_Angeles). Takes priority over calendar's default timezone. Only used for timezone-naive datetime strings."
    )
  }),
  "list-colors": z.object({}),
  "create-event": z.object({
    calendarId: z.string().describe("ID of the calendar (use 'primary' for the main calendar)"),
    summary: z.string().describe("Title of the event"),
    description: z.string().optional().describe("Description/notes for the event"),
    start: z.string().refine((val) => {
      const withTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$/.test(val);
      const withoutTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(val);
      return withTimezone || withoutTimezone;
    }, "Must be ISO 8601 format: '2026-01-01T00:00:00'").describe("Event start time: '2024-01-01T10:00:00'"),
    end: z.string().refine((val) => {
      const withTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$/.test(val);
      const withoutTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(val);
      return withTimezone || withoutTimezone;
    }, "Must be ISO 8601 format: '2026-01-01T00:00:00'").describe("Event end time: '2024-01-01T11:00:00'"),
    timeZone: z.string().optional().describe(
      "Timezone as IANA Time Zone Database name (e.g., America/Los_Angeles). Takes priority over calendar's default timezone. Only used for timezone-naive datetime strings."
    ),
    location: z.string().optional().describe("Location of the event"),
    attendees: z.array(z.object({
      email: z.string().email().describe("Email address of the attendee")
    })).optional().describe("List of attendee email addresses"),
    colorId: z.string().optional().describe(
      "Color ID for the event (use list-colors to see available IDs)"
    ),
    reminders: z.object({
      useDefault: z.boolean().describe("Whether to use the default reminders"),
      overrides: z.array(z.object({
        method: z.enum(["email", "popup"]).default("popup").describe("Reminder method"),
        minutes: z.number().describe("Minutes before the event to trigger the reminder")
      }).partial({ method: true })).optional().describe("Custom reminders")
    }).describe("Reminder settings for the event").optional(),
    recurrence: z.array(z.string()).optional().describe(
      'Recurrence rules in RFC5545 format (e.g., ["RRULE:FREQ=WEEKLY;COUNT=5"])'
    )
  }),
  "update-event": z.object({
    calendarId: z.string().describe("ID of the calendar (use 'primary' for the main calendar)"),
    eventId: z.string().describe("ID of the event to update"),
    summary: z.string().optional().describe("Updated title of the event"),
    description: z.string().optional().describe("Updated description/notes"),
    start: z.string().refine((val) => {
      const withTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$/.test(val);
      const withoutTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(val);
      return withTimezone || withoutTimezone;
    }, "Must be ISO 8601 format: '2026-01-01T00:00:00'").describe("Updated start time: '2024-01-01T10:00:00'").optional(),
    end: z.string().refine((val) => {
      const withTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$/.test(val);
      const withoutTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(val);
      return withTimezone || withoutTimezone;
    }, "Must be ISO 8601 format: '2026-01-01T00:00:00'").describe("Updated end time: '2024-01-01T11:00:00'").optional(),
    timeZone: z.string().optional().describe("Updated timezone as IANA Time Zone Database name. If not provided, uses the calendar's default timezone."),
    location: z.string().optional().describe("Updated location"),
    attendees: z.array(z.object({
      email: z.string().email().describe("Email address of the attendee")
    })).optional().describe("Updated attendee list"),
    colorId: z.string().optional().describe("Updated color ID"),
    reminders: z.object({
      useDefault: z.boolean().describe("Whether to use the default reminders"),
      overrides: z.array(z.object({
        method: z.enum(["email", "popup"]).default("popup").describe("Reminder method"),
        minutes: z.number().describe("Minutes before the event to trigger the reminder")
      }).partial({ method: true })).optional().describe("Custom reminders")
    }).describe("Reminder settings for the event").optional(),
    recurrence: z.array(z.string()).optional().describe("Updated recurrence rules"),
    sendUpdates: z.enum(["all", "externalOnly", "none"]).default("all").describe(
      "Whether to send update notifications"
    ),
    modificationScope: z.enum(["thisAndFollowing", "all", "thisEventOnly"]).optional().describe(
      "Scope for recurring event modifications"
    ),
    originalStartTime: z.string().refine((val) => {
      const withTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$/.test(val);
      const withoutTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(val);
      return withTimezone || withoutTimezone;
    }, "Must be ISO 8601 format: '2026-01-01T00:00:00'").describe("Original start time in the ISO 8601 format '2024-01-01T10:00:00'").optional(),
    futureStartDate: z.string().refine((val) => {
      const withTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$/.test(val);
      const withoutTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(val);
      return withTimezone || withoutTimezone;
    }, "Must be ISO 8601 format: '2026-01-01T00:00:00'").describe("Start date for future instances in the ISO 8601 format '2024-01-01T10:00:00'").optional()
  }).refine(
    (data) => {
      if (data.modificationScope === "thisEventOnly" && !data.originalStartTime) {
        return false;
      }
      return true;
    },
    {
      message: "originalStartTime is required when modificationScope is 'thisEventOnly'",
      path: ["originalStartTime"]
    }
  ).refine(
    (data) => {
      if (data.modificationScope === "thisAndFollowing" && !data.futureStartDate) {
        return false;
      }
      return true;
    },
    {
      message: "futureStartDate is required when modificationScope is 'thisAndFollowing'",
      path: ["futureStartDate"]
    }
  ).refine(
    (data) => {
      if (data.futureStartDate) {
        const futureDate = new Date(data.futureStartDate);
        const now = /* @__PURE__ */ new Date();
        return futureDate > now;
      }
      return true;
    },
    {
      message: "futureStartDate must be in the future",
      path: ["futureStartDate"]
    }
  ),
  "delete-event": z.object({
    calendarId: z.string().describe("ID of the calendar (use 'primary' for the main calendar)"),
    eventId: z.string().describe("ID of the event to delete"),
    sendUpdates: z.enum(["all", "externalOnly", "none"]).default("all").describe(
      "Whether to send cancellation notifications"
    )
  }),
  "get-freebusy": z.object({
    calendars: z.array(z.object({
      id: z.string().describe("ID of the calendar (use 'primary' for the main calendar)")
    })).describe(
      "List of calendars and/or groups to query for free/busy information"
    ),
    timeMin: z.string().refine((val) => {
      const withTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$/.test(val);
      const withoutTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(val);
      return withTimezone || withoutTimezone;
    }, "Must be ISO 8601 format: '2026-01-01T00:00:00'").describe("Start time boundary. Preferred: '2024-01-01T00:00:00' (uses timeZone parameter or calendar timezone). Also accepts: '2024-01-01T00:00:00Z' or '2024-01-01T00:00:00-08:00'."),
    timeMax: z.string().refine((val) => {
      const withTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$/.test(val);
      const withoutTimezone = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(val);
      return withTimezone || withoutTimezone;
    }, "Must be ISO 8601 format: '2026-01-01T00:00:00'").describe("End time boundary. Preferred: '2024-01-01T23:59:59' (uses timeZone parameter or calendar timezone). Also accepts: '2024-01-01T23:59:59Z' or '2024-01-01T23:59:59-08:00'."),
    timeZone: z.string().optional().describe("Timezone for the query"),
    groupExpansionMax: z.number().int().max(100).optional().describe(
      "Maximum number of calendars to expand per group (max 100)"
    ),
    calendarExpansionMax: z.number().int().max(50).optional().describe(
      "Maximum number of calendars to expand (max 50)"
    )
  }),
  "get-current-time": z.object({
    timeZone: z.string().optional().describe(
      "Optional IANA timezone (e.g., 'America/Los_Angeles', 'Europe/London', 'UTC'). If not provided, returns UTC time and system timezone for reference."
    )
  })
};
var ToolRegistry = class {
  static extractSchemaShape(schema) {
    const schemaAny = schema;
    if (schemaAny._def && schemaAny._def.typeName === "ZodEffects") {
      return this.extractSchemaShape(schemaAny._def.schema);
    }
    if ("shape" in schemaAny) {
      return schemaAny.shape;
    }
    if (schemaAny._def && schemaAny._def.schema) {
      return this.extractSchemaShape(schemaAny._def.schema);
    }
    return schemaAny._def?.schema?.shape || schemaAny.shape;
  }
  static tools = [
    {
      name: "list-calendars",
      description: "List all available calendars",
      schema: ToolSchemas["list-calendars"],
      handler: ListCalendarsHandler
    },
    {
      name: "list-events",
      description: "List events from one or more calendars.",
      schema: ToolSchemas["list-events"],
      handler: ListEventsHandler,
      handlerFunction: async (args) => {
        let processedCalendarId = args.calendarId;
        if (typeof args.calendarId === "string" && args.calendarId.trim().startsWith("[") && args.calendarId.trim().endsWith("]")) {
          try {
            const parsed = JSON.parse(args.calendarId);
            if (Array.isArray(parsed) && parsed.every((id) => typeof id === "string" && id.length > 0)) {
              if (parsed.length === 0) {
                throw new Error("At least one calendar ID is required");
              }
              if (parsed.length > 50) {
                throw new Error("Maximum 50 calendars allowed per request");
              }
              if (new Set(parsed).size !== parsed.length) {
                throw new Error("Duplicate calendar IDs are not allowed");
              }
              processedCalendarId = parsed;
            } else {
              throw new Error("JSON string must contain an array of non-empty strings");
            }
          } catch (error) {
            throw new Error(
              `Invalid JSON format for calendarId: ${error instanceof Error ? error.message : "Unknown parsing error"}`
            );
          }
        }
        if (Array.isArray(processedCalendarId)) {
          if (processedCalendarId.length === 0) {
            throw new Error("At least one calendar ID is required");
          }
          if (processedCalendarId.length > 50) {
            throw new Error("Maximum 50 calendars allowed per request");
          }
          if (!processedCalendarId.every((id) => typeof id === "string" && id.length > 0)) {
            throw new Error("All calendar IDs must be non-empty strings");
          }
          if (new Set(processedCalendarId).size !== processedCalendarId.length) {
            throw new Error("Duplicate calendar IDs are not allowed");
          }
        }
        return { calendarId: processedCalendarId, timeMin: args.timeMin, timeMax: args.timeMax };
      }
    },
    {
      name: "search-events",
      description: "Search for events in a calendar by text query.",
      schema: ToolSchemas["search-events"],
      handler: SearchEventsHandler
    },
    {
      name: "list-colors",
      description: "List available color IDs and their meanings for calendar events",
      schema: ToolSchemas["list-colors"],
      handler: ListColorsHandler
    },
    {
      name: "create-event",
      description: "Create a new calendar event.",
      schema: ToolSchemas["create-event"],
      handler: CreateEventHandler
    },
    {
      name: "update-event",
      description: "Update an existing calendar event with recurring event modification scope support.",
      schema: ToolSchemas["update-event"],
      handler: UpdateEventHandler
    },
    {
      name: "delete-event",
      description: "Delete a calendar event.",
      schema: ToolSchemas["delete-event"],
      handler: DeleteEventHandler
    },
    {
      name: "get-freebusy",
      description: "Query free/busy information for calendars. Note: Time range is limited to a maximum of 3 months between timeMin and timeMax.",
      schema: ToolSchemas["get-freebusy"],
      handler: FreeBusyEventHandler
    },
    {
      name: "get-current-time",
      description: "Get current system time and timezone information.",
      schema: ToolSchemas["get-current-time"],
      handler: GetCurrentTimeHandler
    }
  ];
  static getToolsWithSchemas() {
    return this.tools.map((tool) => {
      const jsonSchema = zodToJsonSchema(tool.schema);
      return {
        name: tool.name,
        description: tool.description,
        inputSchema: jsonSchema
      };
    });
  }
  static async registerAll(server, executeWithHandler) {
    for (const tool of this.tools) {
      server.registerTool(
        tool.name,
        {
          description: tool.description,
          inputSchema: this.extractSchemaShape(tool.schema)
        },
        async (args) => {
          const validatedArgs = tool.schema.parse(args);
          const processedArgs = tool.handlerFunction ? await tool.handlerFunction(validatedArgs) : validatedArgs;
          const handler = new tool.handler();
          return executeWithHandler(handler, processedArgs);
        }
      );
    }
  }
};

// src/transports/stdio.ts
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
var StdioTransportHandler = class {
  server;
  constructor(server) {
    this.server = server;
  }
  async connect() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
  }
};

// src/transports/http.ts
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import http from "http";
var HttpTransportHandler = class {
  server;
  config;
  constructor(server, config = {}) {
    this.server = server;
    this.config = config;
  }
  async connect() {
    const port = this.config.port || 3e3;
    const host = this.config.host || "127.0.0.1";
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: void 0
      // Stateless mode - allows multiple initializations
    });
    await this.server.connect(transport);
    const httpServer = http.createServer(async (req, res) => {
      const origin = req.headers.origin;
      const allowedOrigins = [
        "http://localhost",
        "http://127.0.0.1",
        "https://localhost",
        "https://127.0.0.1"
      ];
      if (origin && !allowedOrigins.some((allowed) => origin.startsWith(allowed))) {
        res.writeHead(403, { "Content-Type": "application/json" });
        res.end(JSON.stringify({
          error: "Forbidden: Invalid origin",
          message: "Origin header validation failed"
        }));
        return;
      }
      const contentLength = parseInt(req.headers["content-length"] || "0", 10);
      const maxRequestSize = 10 * 1024 * 1024;
      if (contentLength > maxRequestSize) {
        res.writeHead(413, { "Content-Type": "application/json" });
        res.end(JSON.stringify({
          error: "Payload Too Large",
          message: "Request size exceeds maximum allowed size"
        }));
        return;
      }
      res.setHeader("Access-Control-Allow-Origin", "*");
      res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
      res.setHeader("Access-Control-Allow-Headers", "Content-Type, mcp-session-id");
      if (req.method === "OPTIONS") {
        res.writeHead(200);
        res.end();
        return;
      }
      if (req.method === "POST" || req.method === "GET") {
        const acceptHeader = req.headers.accept;
        if (acceptHeader && !acceptHeader.includes("application/json") && !acceptHeader.includes("text/event-stream") && !acceptHeader.includes("*/*")) {
          res.writeHead(406, { "Content-Type": "application/json" });
          res.end(JSON.stringify({
            error: "Not Acceptable",
            message: "Accept header must include application/json or text/event-stream"
          }));
          return;
        }
      }
      if (req.method === "GET" && req.url === "/health") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({
          status: "healthy",
          server: "google-calendar-mcp",
          version: "1.3.0",
          timestamp: (/* @__PURE__ */ new Date()).toISOString()
        }));
        return;
      }
      try {
        await transport.handleRequest(req, res);
      } catch (error) {
        process.stderr.write(`Error handling request: ${error instanceof Error ? error.message : error}
`);
        if (!res.headersSent) {
          res.writeHead(500, { "Content-Type": "application/json" });
          res.end(JSON.stringify({
            jsonrpc: "2.0",
            error: {
              code: -32603,
              message: "Internal server error"
            },
            id: null
          }));
        }
      }
    });
    httpServer.listen(port, host, () => {
      process.stderr.write(`Google Calendar MCP Server listening on http://${host}:${port}
`);
    });
  }
};

// src/server.ts
var GoogleCalendarMcpServer = class {
  server;
  oauth2Client;
  config;
  constructor(config) {
    this.config = config;
    this.server = new McpServer({
      name: "google-calendar",
      version: "1.3.0"
    });
  }
  async initialize() {
    this.oauth2Client = await initializeOAuth2Client();
    this.registerTools();
    this.setupGracefulShutdown();
  }
  registerTools() {
    ToolRegistry.registerAll(this.server, this.executeWithHandler.bind(this));
  }
  async ensureAuthenticated() {
    try {
      const { google: google2 } = await import("googleapis");
      const calendar = google2.calendar({ version: "v3", auth: this.oauth2Client });
      await calendar.calendarList.list({ maxResults: 1 });
    } catch (error) {
      console.error("Authentication test failed:", error);
      throw new McpError3(
        ErrorCode3.InvalidRequest,
        "Authentication failed. Please check your GCALENDAR_ACCESS_TOKEN and GCALENDAR_REFRESH_TOKEN environment variables."
      );
    }
  }
  async executeWithHandler(handler, args) {
    await this.ensureAuthenticated();
    const result = await handler.runTool(args, this.oauth2Client);
    return result;
  }
  async start() {
    switch (this.config.transport.type) {
      case "stdio":
        const stdioHandler = new StdioTransportHandler(this.server);
        await stdioHandler.connect();
        break;
      case "http":
        const httpConfig = {
          port: this.config.transport.port,
          host: this.config.transport.host
        };
        const httpHandler = new HttpTransportHandler(this.server, httpConfig);
        await httpHandler.connect();
        break;
      default:
        throw new Error(`Unsupported transport type: ${this.config.transport.type}`);
    }
  }
  setupGracefulShutdown() {
    const cleanup = async () => {
      try {
        this.server.close();
        process.exit(0);
      } catch (error) {
        process.stderr.write(`Error during cleanup: ${error instanceof Error ? error.message : error}
`);
        process.exit(1);
      }
    };
    process.on("SIGINT", cleanup);
    process.on("SIGTERM", cleanup);
  }
  // Expose server for testing
  getServer() {
    return this.server;
  }
};

// src/config/TransportConfig.ts
function parseArgs(args) {
  const config = {
    transport: {
      type: process.env.TRANSPORT || "stdio",
      port: process.env.PORT ? parseInt(process.env.PORT, 10) : 3e3,
      host: process.env.HOST || "127.0.0.1"
    },
    debug: process.env.DEBUG === "true" || false
  };
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    switch (arg) {
      case "--transport":
        const transport = args[++i];
        if (transport === "stdio" || transport === "http") {
          config.transport.type = transport;
        }
        break;
      case "--port":
        config.transport.port = parseInt(args[++i], 10);
        break;
      case "--host":
        config.transport.host = args[++i];
        break;
      case "--debug":
        config.debug = true;
        break;
      case "--help":
        process.stderr.write(`
Google Calendar MCP Server

Usage: node build/index.js [options]

Options:
  --transport <type>        Transport type: stdio (default) | http
  --port <number>          Port for HTTP transport (default: 3000)
  --host <string>          Host for HTTP transport (default: 127.0.0.1)
  --debug                  Enable debug logging
  --help                   Show this help message

Environment Variables:
  TRANSPORT               Transport type: stdio | http
  PORT                   Port for HTTP transport
  HOST                   Host for HTTP transport
  DEBUG                  Enable debug logging (true/false)

Examples:
  node build/index.js                              # stdio (local use)
  node build/index.js --transport http --port 3000 # HTTP server
  PORT=3000 TRANSPORT=http node build/index.js     # Using env vars
        `);
        process.exit(0);
    }
  }
  return config;
}

// src/index.ts
import { readFileSync } from "fs";
import { join, dirname } from "path";
var __filename = fileURLToPath(import.meta.url);
var __dirname = dirname(__filename);
var packageJsonPath = join(__dirname, "..", "package.json");
var packageJson = JSON.parse(readFileSync(packageJsonPath, "utf-8"));
var VERSION = packageJson.version;
async function main() {
  try {
    const config = parseArgs(process.argv.slice(2));
    const server = new GoogleCalendarMcpServer(config);
    await server.initialize();
    await server.start();
  } catch (error) {
    process.stderr.write(`Failed to start server: ${error instanceof Error ? error.message : error}
`);
    process.exit(1);
  }
}
function showHelp() {
  process.stdout.write(`
Google Calendar MCP Server v${VERSION} (Token-Based Authentication)

Usage:
  npx @cocal/google-calendar-mcp [command]

Commands:
  start    Start the MCP server (default)
  version  Show version information
  help     Show this help message

Examples:
  npx @cocal/google-calendar-mcp start
  npx @cocal/google-calendar-mcp version
  npx @cocal/google-calendar-mcp

Required Environment Variables:
  GCALENDAR_ACCESS_TOKEN     Google Calendar access token
  GCALENDAR_REFRESH_TOKEN    Google Calendar refresh token

Required Google API Scopes:
  - https://www.googleapis.com/auth/calendar
  - https://www.googleapis.com/auth/calendar.events

Note: This server uses token-based authentication. You must provide valid
Google Calendar API tokens with the required scopes via environment variables.
`);
}
function showVersion() {
  process.stdout.write(`Google Calendar MCP Server v${VERSION} (Token-Based)
`);
}
function parseCliArgs() {
  const args = process.argv.slice(2);
  let command2;
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--version" || arg === "-v" || arg === "--help" || arg === "-h") {
      command2 = arg;
      continue;
    }
    if (arg === "--transport" || arg === "--port" || arg === "--host") {
      i++;
      continue;
    }
    if (arg === "--debug") {
      continue;
    }
    if (!command2 && !arg.startsWith("--")) {
      command2 = arg;
      continue;
    }
  }
  return { command: command2 };
}
var { command } = parseCliArgs();
switch (command) {
  case "auth":
    process.stderr.write(`Authentication command is no longer supported.
`);
    process.stderr.write(`This server now uses token-based authentication via environment variables.
`);
    process.stderr.write(`Please set GCALENDAR_ACCESS_TOKEN and GCALENDAR_REFRESH_TOKEN environment variables.
`);
    process.exit(1);
    break;
  case "start":
  case void 0:
    main().catch((error) => {
      process.stderr.write(`Failed to start server: ${error}
`);
      process.exit(1);
    });
    break;
  case "version":
  case "--version":
  case "-v":
    showVersion();
    break;
  case "help":
  case "--help":
  case "-h":
    showHelp();
    break;
  default:
    process.stderr.write(`Unknown command: ${command}
`);
    showHelp();
    process.exit(1);
}
export {
  main
};
//# sourceMappingURL=index.js.map
