import { NextRequest, NextResponse } from "next/server";

const SITE_URL = "https://www.contentmatepro.com";
const SITE_HOST = "www.contentmatepro.com";
const INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow";
const INDEXNOW_KEY = "3F4D4A59-5467-4324-94AF-5A8B84976F21";
const INDEXNOW_KEY_LOCATION = `${SITE_URL}/${INDEXNOW_KEY}.txt`;

type IndexNowRequestBody = {
  urls?: string[];
};

function getAuthorized(request: NextRequest): boolean {
  const expectedToken = process.env.INDEXNOW_ADMIN_TOKEN?.trim();
  if (!expectedToken) {
    return false;
  }

  const bearerToken = request.headers.get("authorization")?.replace(/^Bearer\s+/i, "").trim();
  const headerToken = request.headers.get("x-indexnow-token")?.trim();

  return bearerToken === expectedToken || headerToken === expectedToken;
}

function normalizeUrls(urls: string[] | undefined): string[] {
  const candidates =
    urls && urls.length > 0
      ? urls
      : [SITE_URL, `${SITE_URL}/privacy`, `${SITE_URL}/terms`, `${SITE_URL}/sitemap.xml`];

  const normalized = candidates
    .map((value) => value.trim())
    .filter(Boolean)
    .map((value) => new URL(value, SITE_URL))
    .filter((value) => value.hostname === SITE_HOST)
    .map((value) => value.toString());

  return Array.from(new Set(normalized));
}

export async function POST(request: NextRequest) {
  if (!getAuthorized(request)) {
    return NextResponse.json({ error: "Unauthorized." }, { status: 401 });
  }

  let body: IndexNowRequestBody = {};

  try {
    body = (await request.json()) as IndexNowRequestBody;
  } catch {
    body = {};
  }

  const urlList = normalizeUrls(body.urls);
  if (urlList.length === 0) {
    return NextResponse.json(
      { error: "No valid ContentMatePro URLs were provided." },
      { status: 400 }
    );
  }

  const response = await fetch(INDEXNOW_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json; charset=utf-8"
    },
    body: JSON.stringify({
      host: SITE_HOST,
      key: INDEXNOW_KEY,
      keyLocation: INDEXNOW_KEY_LOCATION,
      urlList
    }),
    cache: "no-store"
  });

  const responseText = await response.text();

  return NextResponse.json(
    {
      ok: response.ok,
      status: response.status,
      submitted: urlList,
      keyLocation: INDEXNOW_KEY_LOCATION,
      response: responseText || null
    },
    { status: response.ok ? 200 : 502 }
  );
}
