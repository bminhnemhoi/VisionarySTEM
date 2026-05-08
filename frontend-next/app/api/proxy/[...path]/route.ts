import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

/**
 * Universal proxy: /api/proxy/* → BACKEND_URL/*
 *
 * Hides backend from browser, avoids CORS, stays edge-friendly.
 * Streams response body so SSE works.
 */

async function proxy(req: NextRequest, params: { path: string[] }) {
  const path = params.path.join("/");
  const search = req.nextUrl.search;
  const backendUrl = `${BACKEND_URL}/${path}${search}`;

  const headers = new Headers();
  // Forward content-type only (avoid host/origin pollution)
  const ct = req.headers.get("content-type");
  if (ct) headers.set("content-type", ct);
  const auth = req.headers.get("authorization");
  if (auth) headers.set("authorization", auth);
  const tenant = req.headers.get("x-tenant-id");
  if (tenant) headers.set("x-tenant-id", tenant);

  const init: RequestInit = {
    method: req.method,
    headers,
    // For non-GET/HEAD: pass body through
    body: req.method !== "GET" && req.method !== "HEAD" ? req.body : undefined,
    // Required for streaming bodies in fetch
    // @ts-expect-error -- not in types but Next supports it
    duplex: "half",
    // Don't auto-redirect
    redirect: "manual",
  };

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl, init);
  } catch (e) {
    return NextResponse.json(
      { error: "Backend unreachable", detail: String(e), backend: backendUrl },
      { status: 502 },
    );
  }

  // Pass-through response with all headers (including X-Document-Id, content-type)
  const respHeaders = new Headers(upstream.headers);
  respHeaders.delete("content-encoding"); // let Next re-encode
  respHeaders.delete("content-length");

  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: respHeaders,
  });
}

export async function GET(req: NextRequest, ctx: { params: { path: string[] } }) {
  return proxy(req, ctx.params);
}
export async function POST(req: NextRequest, ctx: { params: { path: string[] } }) {
  return proxy(req, ctx.params);
}
export async function PUT(req: NextRequest, ctx: { params: { path: string[] } }) {
  return proxy(req, ctx.params);
}
export async function DELETE(req: NextRequest, ctx: { params: { path: string[] } }) {
  return proxy(req, ctx.params);
}

export const dynamic = "force-dynamic";
export const runtime = "nodejs"; // need streaming + Node fetch
