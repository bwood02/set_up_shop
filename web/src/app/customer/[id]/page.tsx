import Link from "next/link";
import { notFound } from "next/navigation";
import { getShopRepository } from "@/lib/shop-repository";

type Props = {
  params: Promise<{ id: string }>;
};

export const dynamic = "force-dynamic";

export default async function CustomerPage({ params }: Props) {
  const repo = getShopRepository();
  const { id } = await params;
  const customerId = Number(id);
  const customer = await repo.getCustomerById(customerId);
  if (!customer) {
    notFound();
  }

  const orders = await repo.getOrdersByCustomer(customerId);
  const orderCount = orders.length;
  const totalSpent = orders.reduce((sum, order) => sum + order.totalAmount, 0);

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">
            {customer.firstName} {customer.lastName}
          </h2>
          <p className="text-sm text-slate-600">{customer.email}</p>
        </div>
        <Link
          className="rounded bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-700"
          href={`/customer/${customer.id}/new-order`}
        >
          Place New Order
        </Link>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <article className="rounded border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-medium text-slate-600">Total Orders</h3>
          <p className="mt-1 text-2xl font-semibold">{orderCount}</p>
        </article>
        <article className="rounded border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-medium text-slate-600">Total Spent</h3>
          <p className="mt-1 text-2xl font-semibold">${totalSpent.toFixed(2)}</p>
        </article>
      </div>

      <div className="rounded border border-slate-200 bg-white p-4">
        <h3 className="mb-3 text-lg font-semibold">Order History</h3>
        {orders.length === 0 ? (
          <p className="text-sm text-slate-600">No orders found for this customer.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-600">
                  <th className="px-2 py-2">Order ID</th>
                  <th className="px-2 py-2">Date</th>
                  <th className="px-2 py-2">Total</th>
                  <th className="px-2 py-2">Late Delivery Risk</th>
                  <th className="px-2 py-2">Fraud risk (model)</th>
                  <th className="px-2 py-2">Flagged</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr className="border-b border-slate-100" key={order.id}>
                    <td className="px-2 py-2">#{order.id}</td>
                    <td className="px-2 py-2">{order.orderDate}</td>
                    <td className="px-2 py-2">${order.totalAmount.toFixed(2)}</td>
                    <td className="px-2 py-2">
                      {(order.lateDeliveryProbability * 100).toFixed(1)}%
                    </td>
                    <td className="px-2 py-2">
                      {order.fraudProbability != null
                        ? `${(order.fraudProbability * 100).toFixed(1)}%`
                        : "—"}
                    </td>
                    <td className="px-2 py-2">
                      {order.predictedFraud === true ? "Yes" : order.predictedFraud === false ? "No" : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
