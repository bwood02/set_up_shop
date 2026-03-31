import { getShopRepository } from "@/lib/shop-repository";
import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const formData = await request.formData();
  const customerId = Number(formData.get("customerId"));
  const totalAmount = Number(formData.get("totalAmount"));

  if (!Number.isFinite(customerId) || !Number.isFinite(totalAmount) || totalAmount <= 0) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  await getShopRepository().createOrder(customerId, totalAmount);
  return NextResponse.redirect(new URL(`/customer/${customerId}`, request.url));
}
