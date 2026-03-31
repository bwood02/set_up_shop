import { getShopRepository } from "@/lib/shop-repository";
import { NextResponse } from "next/server";

export async function POST(request: Request) {
  await getShopRepository().runLateDeliveryScoring();
  return NextResponse.redirect(new URL("/warehouse?ran=1", request.url));
}
