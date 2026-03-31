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
          <span className="text-slate-700">Order Total Amount</span>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2"
            min="0.01"
            name="totalAmount"
            required
            step="0.01"
            type="number"
          />
        </label>
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
