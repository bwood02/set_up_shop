import type { Customer, Order, PipelinePrediction } from "@/lib/shop-types";

const customers: Customer[] = [
  { id: 1, firstName: "Ava", lastName: "Reed", email: "ava.reed@example.com" },
  { id: 2, firstName: "Noah", lastName: "Bennett", email: "noah.bennett@example.com" },
  { id: 3, firstName: "Mia", lastName: "Watson", email: "mia.watson@example.com" },
  { id: 4, firstName: "Liam", lastName: "Foster", email: "liam.foster@example.com" },
];

let orders: Order[] = [
  {
    id: 101,
    customerId: 1,
    orderDate: "2026-03-10",
    totalAmount: 149.99,
    isFraud: false,
    lateDeliveryProbability: 0.12,
  },
  {
    id: 102,
    customerId: 1,
    orderDate: "2026-03-12",
    totalAmount: 68.5,
    isFraud: false,
    lateDeliveryProbability: 0.21,
  },
  {
    id: 103,
    customerId: 2,
    orderDate: "2026-03-11",
    totalAmount: 315,
    isFraud: false,
    lateDeliveryProbability: 0.63,
  },
  {
    id: 104,
    customerId: 3,
    orderDate: "2026-03-08",
    totalAmount: 22.99,
    isFraud: false,
    lateDeliveryProbability: 0.08,
  },
  {
    id: 105,
    customerId: 4,
    orderDate: "2026-03-09",
    totalAmount: 499.99,
    isFraud: true,
    lateDeliveryProbability: 0.77,
  },
];

let lastScoringRunAt: string | null = null;
let pipelinePredictions: PipelinePrediction[] = [];

export function getCustomers(): Customer[] {
  return [...customers];
}

export function getCustomerById(customerId: number): Customer | undefined {
  return customers.find((customer) => customer.id === customerId);
}

export function getOrdersByCustomer(customerId: number): Order[] {
  return orders
    .filter((order) => order.customerId === customerId)
    .sort((a, b) => (a.orderDate < b.orderDate ? 1 : -1));
}

export function createOrder(customerId: number, totalAmount: number): Order {
  const nextId = Math.max(...orders.map((order) => order.id), 100) + 1;
  const order: Order = {
    id: nextId,
    customerId,
    orderDate: new Date().toISOString().slice(0, 10),
    totalAmount,
    isFraud: false,
    lateDeliveryProbability: 0,
  };
  orders = [order, ...orders];
  return order;
}

export function runLateDeliveryScoring(): {
  predictions: PipelinePrediction[];
  scoredAt: string;
} {
  const scoredAt = new Date().toISOString();

  orders = orders.map((order, idx) => {
    const signal = ((order.totalAmount % 100) / 100 + (idx % 7) * 0.07) % 1;
    return {
      ...order,
      lateDeliveryProbability: Number(signal.toFixed(3)),
    };
  });

  pipelinePredictions = orders
    .map((order) => ({
      orderId: order.id,
      lateDeliveryProbability: order.lateDeliveryProbability,
      scoredAt,
    }))
    .sort((a, b) => b.lateDeliveryProbability - a.lateDeliveryProbability)
    .slice(0, 50);

  lastScoringRunAt = scoredAt;
  return { predictions: pipelinePredictions, scoredAt };
}

export function getPriorityQueue(): Order[] {
  return [...orders]
    .sort((a, b) => b.lateDeliveryProbability - a.lateDeliveryProbability)
    .slice(0, 50);
}

export function getPipelinePredictions(): PipelinePrediction[] {
  return [...pipelinePredictions];
}

export function getLastScoringRunAt(): string | null {
  return lastScoringRunAt;
}
