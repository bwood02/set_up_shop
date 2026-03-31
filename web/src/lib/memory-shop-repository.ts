import type { ShopRepository } from "@/lib/shop-repository";
import {
  createOrder,
  getCustomerById,
  getCustomers,
  getLastScoringRunAt,
  getOrdersByCustomer,
  getPipelinePredictions,
  getPriorityQueue,
  runLateDeliveryScoring,
} from "@/lib/shop-store";

export function createMemoryShopRepository(): ShopRepository {
  return {
    async getCustomers() {
      return getCustomers();
    },
    async getCustomerById(customerId: number) {
      return getCustomerById(customerId) ?? null;
    },
    async getOrdersByCustomer(customerId: number) {
      return getOrdersByCustomer(customerId);
    },
    async createOrder(customerId: number, totalAmount: number) {
      return createOrder(customerId, totalAmount);
    },
    async runLateDeliveryScoring() {
      return runLateDeliveryScoring();
    },
    async getPriorityQueue() {
      return getPriorityQueue();
    },
    async getPipelinePredictions() {
      return getPipelinePredictions();
    },
    async getLastScoringRunAt() {
      return getLastScoringRunAt();
    },
  };
}
