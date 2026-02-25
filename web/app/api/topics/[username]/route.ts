import { NextRequest, NextResponse } from "next/server";

const RAILWAY_URL = process.env.RAILWAY_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const res = await fetch(`${RAILWAY_URL}/digest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const txt = await res.text();
    return NextResponse.json({ error: txt }, { status: res.status });
  }

  const data = await res.json();
  return NextResponse.json(data);
}
