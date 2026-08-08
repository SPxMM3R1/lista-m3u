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
  return rewriteHlsPlaylist(body, response.url || MEGA_MASTER_URL);
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
  async fetch(request) {
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
