import Link from "next/link";
import { notFound } from "next/navigation";
import { getShopRepository } from "@/lib/shop-repository";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function NewOrderPage({ params }: Props) {
  const repo = getShopRepository();
  const { id } = await params;
  const customerId = Number(id);
  const customer = await repo.getCustomerById(customerId);
  if (!customer) {
    notFound();
  }

  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold">Place New Order</h2>
      <p className="text-sm text-slate-600">
        Customer: {customer.firstName} {customer.lastName}
      </p>

      <form
        action="/api/orders"
        className="max-w-md space-y-3 rounded border border-slate-200 bg-white p-4"
        method="POST"
      >
        <input name="customerId" type="hidden" value={customer.id} />
        <label className="block space-y-1 text-sm">
          <span className="text-slate-700">Order subtotal</span>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2"
            min="0.01"
            name="totalAmount"
            required
            step="0.01"
            type="number"
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-slate-700">Shipping fee</span>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2"
            min="0"
            name="shippingFee"
            step="0.01"
            type="number"
            defaultValue={0}
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-slate-700">Tax amount</span>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2"
            min="0"
            name="taxAmount"
            step="0.01"
            type="number"
            defaultValue={0}
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-slate-700">Billing ZIP</span>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2"
            name="billingZip"
            required
            pattern="[0-9A-Za-z\- ]+"
            placeholder="84101"
            type="text"
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-slate-700">Shipping ZIP</span>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2"
            name="shippingZip"
            required
            pattern="[0-9A-Za-z\- ]+"
            placeholder="84101"
            type="text"
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-slate-700">Shipping state</span>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2"
            maxLength={2}
            name="shippingState"
            placeholder="UT"
            type="text"
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-slate-700">Payment method</span>
          <select className="w-full rounded border border-slate-300 px-3 py-2" name="paymentMethod">
            <option value="card">Card</option>
            <option value="paypal">PayPal</option>
            <option value="apple_pay">Apple Pay</option>
            <option value="other">Other</option>
          </select>
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-slate-700">Device type</span>
          <select className="w-full rounded border border-slate-300 px-3 py-2" name="deviceType">
            <option value="web">Web</option>
            <option value="mobile">Mobile</option>
            <option value="tablet">Tablet</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input name="promoUsed" type="checkbox" value="true" />
          <span className="text-slate-700">Promo used</span>
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-slate-700">Promo code (optional)</span>
          <input className="w-full rounded border border-slate-300 px-3 py-2" name="promoCode" type="text" />
        </label>
        <p className="text-xs text-slate-500">
          Country for fraud signals is inferred from your request IP on the server.
        </p>
        <button
          className="rounded bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-700"
          type="submit"
        >
          Save Order
        </button>
      </form>

      <Link
        className="inline-block text-sm text-slate-700 underline"
        href={`/customer/${customer.id}`}
      >
        Back to customer dashboard
      </Link>
    </section>
  );
}
