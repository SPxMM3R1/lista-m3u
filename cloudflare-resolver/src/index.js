const BROWSER_USER_AGENT =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";
const TVN_LIVE_PAGE = "https://live.tvn.cl/";
const TVN_DEFAULT_ID = "57a498c4d7b86d600e5461cb";
const MEGANOTICIAS_LIVE_PAGE =
  "https://www.meganoticias.cl/senal-en-vivo/meganoticias/";
const MEGANOTICIAS_DEFAULT_ID = "561430ae330428c223687e1e";
const MEGAMEDIA_API_URL = "https://api.mega.cl/api/v1/mdstrm";
const MEGA_MASTER_URL =
  "https://tr.live.clarovtrcdn.vtrplay.com/megahdchi/vxfmt=dp/" +
  "playlist.m3u8?device_profile=STB_HLS_VCAS_LIVE_HD";
const MEGANOTICIAS_PROXY_PATH = "/meganoticias-proxy.m3u8";
const MEGANOTICIAS_YOUTUBE_PATH = "/meganoticias-youtube.m3u8";
const MEGANOTICIAS_YOUTUBE_CHANNEL_LIVE =
  "https://www.youtube.com/channel/UCkccyEbqhhM3uKOI6Shm-4Q/live";
const YOUTUBE_PLAYER_API_URL = "https://www.youtube.com/youtubei/v1/player";
const YOUTUBE_CLIENT_VERSION = "21.02.35";
const YOUTUBE_USER_AGENT =
  "com.google.android.youtube/21.02.35 (Linux; U; Android 11) gzip";
const STREAM_CACHE_TTL_MS = 45_000;

const streamCache = new Map();

function pageHeaders(referer) {
  return {
    "User-Agent": BROWSER_USER_AGENT,
    Referer: referer,
    Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
  };
}

async function fetchPage(url, referer) {
  const response = await fetch(url, { headers: pageHeaders(referer) });
  if (!response.ok) {
    throw new Error(`pagina HTTP ${response.status}`);
  }
  return response.text();
}

function validateToken(token, label) {
  if (!token || !/^[A-Za-z0-9._~-]+$/.test(token)) {
    throw new Error(`${label} publico un token inesperado`);
  }
  return token;
}

async function freshTvnUrl() {
  const html = await fetchPage(TVN_LIVE_PAGE, "https://www.tvn.cl/");
  const streamId =
    html.match(/\bid\s*:\s*['"]([a-zA-Z0-9]+)['"]/)?.[1] ?? TVN_DEFAULT_ID;
  const token = validateToken(
    html.match(/\baccess_token\s*:\s*['"]([^'"]+)['"]/)?.[1],
    "TVN",
  );
  return `https://mdstrm.com/live-stream-playlist/${streamId}.m3u8?access_token=${encodeURIComponent(token)}`;
}

async function freshMeganoticiasUrl() {
  const html = await fetchPage(MEGANOTICIAS_LIVE_PAGE, MEGANOTICIAS_LIVE_PAGE);
  const config = html.match(
    /var\s+VideoSenalEnVivo\s*=\s*\{\s*id:\s*'([^']+)'.*?serverKey\s*:\s*'([^']+)'/s,
  );
  if (!config) {
    throw new Error("Meganoticias no publico la configuracion del reproductor");
  }

  const [, configuredId, serverKey] = config;
  const streamId = configuredId || MEGANOTICIAS_DEFAULT_ID;
  const params = new URLSearchParams({
    id: streamId,
    ua: BROWSER_USER_AGENT,
    type: "live",
    process: "access_token",
    key: serverKey,
  });
  const response = await fetch(`${MEGAMEDIA_API_URL}?${params}`, {
    headers: {
      "User-Agent": BROWSER_USER_AGENT,
      Referer: MEGANOTICIAS_LIVE_PAGE,
      Origin: "https://www.meganoticias.cl",
      Accept: "application/json",
    },
  });
  if (!response.ok) {
    throw new Error(`API de Meganoticias HTTP ${response.status}`);
  }
  const body = await response.json();
  const token = validateToken(body?.access_token, "Meganoticias");
  return `https://mdstrm.com/live-stream-playlist/${streamId}.m3u8?access_token=${encodeURIComponent(token)}`;
}

async function freshMegaPlaylist() {
  const response = await fetch(MEGA_MASTER_URL, {
    headers: {
      "User-Agent": BROWSER_USER_AGENT,
      Referer: "https://www.mega.cl/senal-en-vivo/",
      Origin: "https://www.mega.cl",
      Accept: "application/vnd.apple.mpegurl,*/*;q=0.8",
    },
  });
  if (!response.ok) {
    throw new Error(`master de Mega HTTP ${response.status}`);
  }
  const body = await response.text();
  if (!body.trimStart().startsWith("#EXTM3U")) {
    throw new Error("Mega no devolvio una playlist HLS");
  }
  return megaCompatibilityPlaylist(body, response.url || MEGA_MASTER_URL);
}

function secureHlsUrl(value, baseUrl) {
  if (value.startsWith("data:")) {
    return value;
  }
  const url = new URL(value, baseUrl);
  if (url.protocol === "http:") {
    url.protocol = "https:";
  }
  return url.toString();
}

function rewriteHlsPlaylist(body, baseUrl) {
  return body
    .split(/\r?\n/)
    .map((line) => {
      if (line.includes('URI="')) {
        return line.replace(
          /URI="([^"]+)"/g,
          (_match, uri) => `URI="${secureHlsUrl(uri, baseUrl)}"`,
        );
      }
      const trimmed = line.trim();
      return trimmed && !trimmed.startsWith("#")
        ? secureHlsUrl(trimmed, baseUrl)
        : line;
    })
    .join("\n");
}

function isAllowedMeganoticiasTarget(value) {
  let url;
  try {
    url = new URL(value);
  } catch {
    return false;
  }
  const hostname = url.hostname.toLowerCase();
  return (
    url.protocol === "https:" &&
    (hostname === "mdstrm.com" || hostname.endsWith(".mdstrm.com"))
  );
}

function encodeProxyTarget(value) {
  return btoa(value)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function decodeProxyTarget(value) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padding = "=".repeat((4 - (normalized.length % 4)) % 4);
  return atob(normalized + padding);
}

function proxyTargetUrl(target, origin) {
  return `${origin}${MEGANOTICIAS_PROXY_PATH}?u=${encodeProxyTarget(target)}`;
}

function proxyTargetUrlForPath(target, origin, path) {
  return `${origin}${path}?u=${encodeProxyTarget(target)}`;
}

function rewriteMeganoticiasHlsPlaylist(body, baseUrl, origin) {
  return body
    .split(/\r?\n/)
    .map((line) => {
      if (line.includes('URI="')) {
        return line.replace(
          /URI="([^"]+)"/g,
          (_match, uri) => {
            if (/^(?:data|skd):/i.test(uri)) {
              return `URI="${uri}"`;
            }
            const target = secureHlsUrl(uri, baseUrl);
            if (!isAllowedMeganoticiasTarget(target)) {
              throw new Error("Meganoticias publico un recurso HLS externo");
            }
            return `URI="${proxyTargetUrl(target, origin)}"`;
          },
        );
      }
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) {
        return line;
      }
      const target = secureHlsUrl(trimmed, baseUrl);
      if (!isAllowedMeganoticiasTarget(target)) {
        throw new Error("Meganoticias publico una variante HLS externa");
      }
      return proxyTargetUrl(target, origin);
    })
    .join("\n");
}

function isHlsPlaylist(response, target) {
  const contentType = response.headers.get("Content-Type") ?? "";
  if (/mpegurl|m3u8/i.test(contentType)) {
    return true;
  }
  try {
    return new URL(response.url || target).pathname.toLowerCase().endsWith(".m3u8");
  } catch {
    return target.toLowerCase().includes(".m3u8");
  }
}

function meganoticiasUpstreamHeaders(request, target) {
  const headers = {
    "User-Agent": BROWSER_USER_AGENT,
    Referer: MEGANOTICIAS_LIVE_PAGE,
    Origin: "https://www.meganoticias.cl",
    Accept: isHlsPlaylist({ headers: new Headers(), url: target }, target)
      ? "application/vnd.apple.mpegurl,*/*;q=0.8"
      : "*/*",
  };
  const range = request.headers.get("Range");
  if (range) {
    headers.Range = range;
  }
  return headers;
}

async function fetchMeganoticiasTarget(request, target) {
  return fetch(target, {
    headers: meganoticiasUpstreamHeaders(request, target),
  });
}

async function proxyMeganoticias(request, requestUrl) {
  const encodedTarget = requestUrl.searchParams.get("u");
  let target;
  if (encodedTarget) {
    try {
      target = decodeProxyTarget(encodedTarget);
    } catch {
      return textResponse(400, "recurso HLS invalido\n");
    }
  } else {
    target = await cachedStreamUrl("Meganoticias", freshMeganoticiasUrl);
  }

  if (!isAllowedMeganoticiasTarget(target)) {
    return textResponse(400, "recurso HLS no permitido\n");
  }

  const response = await fetchMeganoticiasTarget(request, target);
  if (!response.ok) {
    console.error(`[FALLO] Meganoticias HLS HTTP ${response.status}`);
    return textResponse(response.status, "Meganoticias HLS no disponible\n");
  }

  if (isHlsPlaylist(response, target)) {
    const body = await response.text();
    if (!body.trimStart().startsWith("#EXTM3U")) {
      throw new Error("Meganoticias no devolvio una playlist HLS valida");
    }
    return playlistResponse(
      rewriteMeganoticiasHlsPlaylist(
        body,
        response.url || target,
        requestUrl.origin,
      ),
    );
  }

  const headers = new Headers();
  for (const name of [
    "Accept-Ranges",
    "Content-Range",
    "Content-Type",
    "ETag",
    "Last-Modified",
  ]) {
    const value = response.headers.get(name);
    if (value) {
      headers.set(name, value);
    }
  }
  headers.set("Cache-Control", "no-store, no-cache, must-revalidate");
  headers.set("Access-Control-Allow-Origin", "*");
  return new Response(response.body, {
    status: response.status,
    headers,
  });
}

function isAllowedYoutubeTarget(value) {
  let url;
  try {
    url = new URL(value);
  } catch {
    return false;
  }
  const hostname = url.hostname.toLowerCase();
  return (
    url.protocol === "https:" &&
    (hostname === "googlevideo.com" || hostname.endsWith(".googlevideo.com"))
  );
}

function extractYoutubeLiveId(html) {
  const match = html.match(
    /"videoDetails":\{"videoId":"([A-Za-z0-9_-]{11})".{0,2000}?"isLive":true/s,
  );
  if (!match) {
    throw new Error("YouTube no publico una emision en vivo de Meganoticias");
  }
  return match[1];
}

async function freshMeganoticiasYoutubeUrl() {
  const channelHtml = await fetchPage(
    MEGANOTICIAS_YOUTUBE_CHANNEL_LIVE,
    "https://www.youtube.com/",
  );
  const videoId = extractYoutubeLiveId(channelHtml);
  const watchUrl = `https://www.youtube.com/watch?v=${videoId}`;
  const watchHtml = await fetchPage(watchUrl, "https://www.youtube.com/");
  const apiKey = watchHtml.match(/"INNERTUBE_API_KEY":"([^"]+)"/)?.[1];
  if (!apiKey) {
    throw new Error("YouTube no publico su clave de reproduccion");
  }

  const payload = {
    context: {
      client: {
        clientName: "ANDROID",
        clientVersion: YOUTUBE_CLIENT_VERSION,
        androidSdkVersion: 30,
        userAgent: YOUTUBE_USER_AGENT,
        osName: "Android",
        osVersion: "11",
      },
    },
    videoId,
  };
  const response = await fetch(
    `${YOUTUBE_PLAYER_API_URL}?key=${encodeURIComponent(apiKey)}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "User-Agent": YOUTUBE_USER_AGENT,
        "X-YouTube-Client-Name": "3",
        "X-YouTube-Client-Version": YOUTUBE_CLIENT_VERSION,
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) {
    throw new Error(`API de reproduccion de YouTube HTTP ${response.status}`);
  }
  const body = await response.json();
  const manifest = body?.streamingData?.hlsManifestUrl;
  if (!isAllowedYoutubeTarget(manifest)) {
    throw new Error("YouTube no devolvio un master HLS permitido");
  }
  return manifest;
}

function rewriteYoutubeHlsPlaylist(body, baseUrl, origin) {
  return body
    .split(/\r?\n/)
    .map((line) => {
      if (line.includes('URI="')) {
        return line.replace(
          /URI="([^"]+)"/g,
          (_match, uri) => {
            if (/^(?:data|skd):/i.test(uri)) {
              return `URI="${uri}"`;
            }
            const target = secureHlsUrl(uri, baseUrl);
            if (!isAllowedYoutubeTarget(target)) {
              throw new Error("YouTube publico un recurso HLS externo");
            }
            return `URI="${proxyTargetUrlForPath(
              target,
              origin,
              MEGANOTICIAS_YOUTUBE_PATH,
            )}"`;
          },
        );
      }
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) {
        return line;
      }
      const target = secureHlsUrl(trimmed, baseUrl);
      if (!isAllowedYoutubeTarget(target)) {
        throw new Error("YouTube publico una variante HLS externa");
      }
      return proxyTargetUrlForPath(
        target,
        origin,
        MEGANOTICIAS_YOUTUBE_PATH,
      );
    })
    .join("\n");
}

function youtubeUpstreamHeaders(request, target) {
  const headers = {
    "User-Agent": BROWSER_USER_AGENT,
    Referer: "https://www.youtube.com/",
    Origin: "https://www.youtube.com",
    Accept: isHlsPlaylist({ headers: new Headers(), url: target }, target)
      ? "application/vnd.apple.mpegurl,*/*;q=0.8"
      : "*/*",
  };
  const range = request.headers.get("Range");
  if (range) {
    headers.Range = range;
  }
  return headers;
}

async function proxyMeganoticiasYoutube(request, requestUrl) {
  const encodedTarget = requestUrl.searchParams.get("u");
  let target;
  if (encodedTarget) {
    try {
      target = decodeProxyTarget(encodedTarget);
    } catch {
      return textResponse(400, "recurso HLS de YouTube invalido\n");
    }
  } else {
    target = await cachedStreamUrl(
      "MeganoticiasYouTube",
      freshMeganoticiasYoutubeUrl,
    );
  }

  if (!isAllowedYoutubeTarget(target)) {
    return textResponse(400, "recurso HLS de YouTube no permitido\n");
  }

  const response = await fetch(target, {
    headers: youtubeUpstreamHeaders(request, target),
  });
  if (!response.ok) {
    console.error(`[FALLO] YouTube HLS HTTP ${response.status}`);
    return textResponse(response.status, "YouTube HLS no disponible\n");
  }

  if (isHlsPlaylist(response, target)) {
    const body = await response.text();
    if (!body.trimStart().startsWith("#EXTM3U")) {
      throw new Error("YouTube no devolvio una playlist HLS valida");
    }
    return playlistResponse(
      rewriteYoutubeHlsPlaylist(
        body,
        response.url || target,
        requestUrl.origin,
      ),
    );
  }

  const headers = new Headers();
  for (const name of [
    "Accept-Ranges",
    "Content-Range",
    "Content-Type",
    "ETag",
    "Last-Modified",
  ]) {
    const value = response.headers.get(name);
    if (value) {
      headers.set(name, value);
    }
  }
  headers.set("Cache-Control", "no-store, no-cache, must-revalidate");
  headers.set("Access-Control-Allow-Origin", "*");
  return new Response(response.body, {
    status: response.status,
    headers,
  });
}

export class MeganoticiasProxy {
  async fetch(request) {
    const requestUrl = new URL(request.url);
    if (requestUrl.pathname === MEGANOTICIAS_YOUTUBE_PATH) {
      return proxyMeganoticiasYoutube(request, requestUrl);
    }
    return proxyMeganoticias(request, requestUrl);
  }
}

function hlsAttribute(line, name) {
  const match = line.match(
    new RegExp(`(?:^|[:,])${name}=(?:"([^"]*)"|([^,]*))`),
  );
  return match?.[1] ?? match?.[2]?.trim();
}

function replaceHlsAttribute(line, name, value) {
  return line.replace(
    new RegExp(`(${name}=)(?:"[^"]*"|[^,]*)`),
    `$1"${value}"`,
  );
}

function megaCompatibilityPlaylist(body, baseUrl) {
  const lines = body.split(/\r?\n/);
  const variants = [];
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (!line.startsWith("#EXT-X-STREAM-INF:") || !lines[index + 1]) {
      continue;
    }
    const resolution = hlsAttribute(line, "RESOLUTION")?.match(/^(\d+)x(\d+)$/);
    const audioGroup = hlsAttribute(line, "AUDIO");
    const child = lines[index + 1].trim();
    if (!resolution || !audioGroup || !child || child.startsWith("#")) {
      continue;
    }
    const width = Number(resolution[1]);
    const height = Number(resolution[2]);
    if (height > 1080) {
      continue;
    }
    variants.push({
      line,
      child,
      audioGroup,
      width,
      height,
      bandwidth: Number(hlsAttribute(line, "BANDWIDTH") ?? 0),
    });
  }

  const selected = variants.sort(
    (left, right) =>
      left.height - right.height ||
      left.width - right.width ||
      left.bandwidth - right.bandwidth,
  ).at(-1);
  if (!selected) {
    return rewriteHlsPlaylist(body, baseUrl);
  }

  const sourceAudio = lines.find(
    (line) =>
      line.startsWith("#EXT-X-MEDIA:") &&
      hlsAttribute(line, "TYPE") === "AUDIO" &&
      hlsAttribute(line, "GROUP-ID") === selected.audioGroup &&
      hlsAttribute(line, "URI"),
  );
  if (!sourceAudio) {
    return rewriteHlsPlaylist(body, baseUrl);
  }

  const audioUrl = secureHlsUrl(hlsAttribute(sourceAudio, "URI"), baseUrl);
  const videoUrl = secureHlsUrl(selected.child, baseUrl);
  let audioLine = replaceHlsAttribute(sourceAudio, "GROUP-ID", "mega-audio");
  audioLine = replaceHlsAttribute(audioLine, "URI", audioUrl);
  if (!hlsAttribute(audioLine, "DEFAULT")) {
    audioLine = audioLine.replace("TYPE=AUDIO,", "TYPE=AUDIO,DEFAULT=YES,");
  }
  const streamLine = replaceHlsAttribute(selected.line, "AUDIO", "mega-audio");
  return ["#EXTM3U", "#EXT-X-VERSION:5", audioLine, streamLine, videoUrl, ""].join(
    "\n",
  );
}

async function cachedStreamUrl(label, factory) {
  const now = Date.now();
  const cached = streamCache.get(label);
  if (cached && now - cached.createdAt < STREAM_CACHE_TTL_MS) {
    return cached.url;
  }
  const url = await factory();
  streamCache.set(label, { createdAt: Date.now(), url });
  return url;
}

function textResponse(status, body) {
  return new Response(body, {
    status,
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store, no-cache, must-revalidate",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

function playlistResponse(body) {
  return new Response(body, {
    status: 200,
    headers: {
      "Content-Type": "application/vnd.apple.mpegurl",
      "Cache-Control": "no-store, no-cache, must-revalidate",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

export default {
  async fetch(request, env) {
    if (request.method !== "GET") {
      return textResponse(405, "method not allowed\n");
    }

    const path = new URL(request.url).pathname;
    if (path === "/health") {
      return textResponse(200, "ok\n");
    }

    if (path === "/mega.m3u8") {
      try {
        return playlistResponse(await freshMegaPlaylist());
      } catch (error) {
        console.error(`[FALLO] Mega: ${error?.constructor?.name ?? "Error"}`);
        return textResponse(503, "Mega no disponible temporalmente\n");
      }
    }

    if (
      path === MEGANOTICIAS_PROXY_PATH ||
      path === MEGANOTICIAS_YOUTUBE_PATH
    ) {
      if (!env.MEGANOTICIAS_PROXY) {
        return textResponse(503, "Meganoticias proxy no configurado\n");
      }
      const id = env.MEGANOTICIAS_PROXY.idFromName(
        path === MEGANOTICIAS_YOUTUBE_PATH
          ? "meganoticias-youtube"
          : "meganoticias",
      );
      return env.MEGANOTICIAS_PROXY.get(id).fetch(request);
    }

    const routes = {
      "/tvn.m3u8": ["TVN", freshTvnUrl],
      "/meganoticias.m3u8": ["Meganoticias", freshMeganoticiasUrl],
    };
    const route = routes[path];
    if (!route) {
      return textResponse(404, "not found\n");
    }

    const [label, factory] = route;
    try {
      const streamUrl = await cachedStreamUrl(label, factory);
      return new Response(null, {
        status: 302,
        headers: {
          Location: streamUrl,
          "Cache-Control": "no-store, no-cache, must-revalidate",
          Pragma: "no-cache",
          "Access-Control-Allow-Origin": "*",
        },
      });
    } catch (error) {
      console.error(`[FALLO] ${label}: ${error?.constructor?.name ?? "Error"}`);
      return textResponse(503, `${label} no disponible temporalmente\n`);
    }
  },
};
