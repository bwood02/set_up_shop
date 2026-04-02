import type { CreateOrderInput, Customer, Order, PipelinePrediction } from "@/lib/shop-types";
import { createMemoryShopRepository } from "@/lib/memory-shop-repository";
import { createSupabaseShopRepository } from "@/lib/supabase-shop-repository";

export type RunScoringResult = {
  predictions: PipelinePrediction[];
  scoredAt: string;
};

export interface ShopRepository {
  getCustomers(): Promise<Customer[]>;
  getCustomerById(customerId: number): Promise<Customer | null>;
  getOrdersByCustomer(customerId: number): Promise<Order[]>;
  createOrder(input: CreateOrderInput): Promise<Order>;
  runLateDeliveryScoring(): Promise<RunScoringResult>;
  getPriorityQueue(): Promise<Order[]>;
  getPipelinePredictions(): Promise<PipelinePrediction[]>;
  getLastScoringRunAt(): Promise<string | null>;
}

let repository: ShopRepository | null = null;

function shouldUseSupabase(): boolean {
  return Boolean(process.env.SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY);
}

export function getShopRepository(): ShopRepository {
  if (repository) {
    return repository;
  }
  repository = shouldUseSupabase() ? createSupabaseShopRepository() : createMemoryShopRepository();
  return repository;
}
