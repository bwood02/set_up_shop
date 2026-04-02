import { getShopRepository } from "@/lib/shop-repository";
import type { CreateOrderInput } from "@/lib/shop-types";
import { NextResponse } from "next/server";

function clientCountry(request: Request): string {
  const country = request.headers.get("x-vercel-ip-country");
  if (country && country.length === 2) return country;
  return "US";
}

export async function POST(request: Request) {
  const formData = await request.formData();
  const customerId = Number(formData.get("customerId"));
  const totalAmount = Number(formData.get("totalAmount"));
  const billingZip = String(formData.get("billingZip") ?? "").trim() || "00000";
  const shippingZip = String(formData.get("shippingZip") ?? "").trim() || "00000";
  const shippingState = String(formData.get("shippingState") ?? "").trim() || "NA";
  const paymentMethod = String(formData.get("paymentMethod") ?? "card");
  const deviceType = String(formData.get("deviceType") ?? "web");
  const promoCodeRaw = formData.get("promoCode");
  const promoCode = promoCodeRaw ? String(promoCodeRaw).trim() || null : null;
  const promoUsed = formData.get("promoUsed") === "on" || formData.get("promoUsed") === "true";
  const shippingFee = Number(formData.get("shippingFee") ?? 0);
  const taxAmount = Number(formData.get("taxAmount") ?? 0);

  if (!Number.isFinite(customerId) || !Number.isFinite(totalAmount) || totalAmount <= 0) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  const input: CreateOrderInput = {
    customerId,
    totalAmount,
    billingZip,
    shippingZip,
    shippingState,
    paymentMethod,
    deviceType,
    ipCountry: clientCountry(request),
    promoUsed,
    promoCode,
    shippingFee: Number.isFinite(shippingFee) ? shippingFee : 0,
    taxAmount: Number.isFinite(taxAmount) ? taxAmount : 0,
  };

  await getShopRepository().createOrder(input);
  return NextResponse.redirect(new URL(`/customer/${customerId}`, request.url));
}
