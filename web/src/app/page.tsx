import Link from "next/link";
import { getShopRepository } from "@/lib/shop-repository";

export default async function Home() {
  const customers = await getShopRepository().getCustomers();

  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold">Select Customer</h2>
      <p className="text-sm text-slate-600">
        Choose a customer to view the dashboard, place an order, and review history.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {customers.map((customer) => (
          <Link
            className="rounded border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300"
            href={`/customer/${customer.id}`}
            key={customer.id}
          >
            <p className="font-medium">
              {customer.firstName} {customer.lastName}
            </p>
            <p className="text-sm text-slate-600">{customer.email}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
