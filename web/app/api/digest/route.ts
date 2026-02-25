import { NextRequest, NextResponse } from "next/server";

const RAILWAY_URL = process.env.RAILWAY_API_URL ?? "http://localhost:8000";

export async function GET(
  _req: NextRequest,
  { params }: { params: { username: string } }
) {
  const res = await fetch(`${RAILWAY_URL}/topics/${params.username}`);
  const data = await res.json();
  return NextResponse.json(data);
}

export async function POST(
  req: NextRequest,
  { params }: { params: { username: string } }
) {
  const body = await req.json();
  const res = await fetch(`${RAILWAY_URL}/topics/${params.username}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return NextResponse.json(data);
}
