import { predictFraud } from "@/lib/fraud-inference";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import type { ShopRepository } from "@/lib/shop-repository";
import type { CreateOrderInput, Customer, Order, PipelinePrediction } from "@/lib/shop-types";

type DbCustomer = {
  customer_id: number;
  full_name: string | null;
  email: string | null;
};

type DbCustomerRow = Record<string, unknown>;

type DbOrder = {
  order_id: number;
  customer_id: number;
  order_datetime: string | null;
  order_total: number | null;
  is_fraud: number | null;
  risk_score: number | null;
  fraud_probability?: number | null;
  predicted_fraud?: number | null;
};

const SCORE_INSERT_BATCH_SIZE = 500;

const ORDER_SELECT_BASE =
  "order_id,customer_id,order_datetime,order_total,is_fraud,risk_score,fraud_probability,predicted_fraud";

function normalizeProbability(raw: number | null | undefined): number {
  const value = Number(raw ?? 0);
  if (!Number.isFinite(value)) return 0;
  const scaled = value > 1 ? value / 100 : value;
  return Math.max(0, Math.min(1, scaled));
}

function splitName(fullName: string | null): { firstName: string; lastName: string } {
  const cleaned = (fullName ?? "").trim();
  if (!cleaned) return { firstName: "Unknown", lastName: "Customer" };
  const parts = cleaned.split(/\s+/);
  if (parts.length === 1) return { firstName: parts[0], lastName: "" };
  return { firstName: parts[0], lastName: parts.slice(1).join(" ") };
}

function mapCustomer(row: DbCustomer): Customer {
  const name = splitName(row.full_name);
  return {
    id: row.customer_id,
    firstName: name.firstName,
    lastName: name.lastName,
    email: row.email ?? "unknown@example.com",
  };
}

function mapOrder(row: DbOrder): Order {
  const fraudProb = row.fraud_probability != null && row.fraud_probability !== undefined
    ? Number(row.fraud_probability)
    : undefined;
  const predicted = row.predicted_fraud != null && row.predicted_fraud !== undefined
    ? Number(row.predicted_fraud) === 1
    : undefined;
  return {
    id: row.order_id,
    customerId: row.customer_id,
    orderDate: (row.order_datetime ?? new Date().toISOString()).slice(0, 10),
    totalAmount: Number(row.order_total ?? 0),
    isFraud: Number(row.is_fraud ?? 0) === 1,
    lateDeliveryProbability: normalizeProbability(row.risk_score),
    ...(fraudProb !== undefined ? { fraudProbability: fraudProb } : {}),
    ...(predicted !== undefined ? { predictedFraud: predicted } : {}),
  };
}

function orderRowToPredictPayload(row: Record<string, unknown>): Record<string, unknown> {
  const allowed = [
    "order_id",
    "customer_id",
    "order_datetime",
    "billing_zip",
    "shipping_zip",
    "shipping_state",
    "payment_method",
    "device_type",
    "ip_country",
    "promo_used",
    "promo_code",
    "order_subtotal",
    "shipping_fee",
    "tax_amount",
    "order_total",
    "risk_score",
    "is_fraud",
  ];
  const out: Record<string, unknown> = {};
  for (const key of allowed) {
    if (key in row) out[key] = row[key];
  }
  return out;
}

export function createSupabaseShopRepository(): ShopRepository {
  const supabase = createSupabaseServerClient();

  return {
    async getCustomers() {
      const { data, error } = await supabase
        .from("customers")
        .select("customer_id,full_name,email")
        .order("customer_id", { ascending: true })
        .limit(1000);
      if (error) throw error;
      return (data as DbCustomer[]).map(mapCustomer);
    },

    async getCustomerById(customerId: number) {
      const { data, error } = await supabase
        .from("customers")
        .select("customer_id,full_name,email")
        .eq("customer_id", customerId)
        .maybeSingle();
      if (error) throw error;
      return data ? mapCustomer(data as DbCustomer) : null;
    },

    async getOrdersByCustomer(customerId: number) {
      const { data, error } = await supabase
        .from("orders")
        .select(ORDER_SELECT_BASE)
        .eq("customer_id", customerId)
        .order("order_datetime", { ascending: false })
        .limit(1000);
      if (error) throw error;
      return (data as DbOrder[]).map(mapOrder);
    },

    async createOrder(input: CreateOrderInput) {
      const { data: latestOrder, error: latestOrderError } = await supabase
        .from("orders")
        .select("order_id")
        .order("order_id", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (latestOrderError) throw latestOrderError;
      const nextOrderId = Number(latestOrder?.order_id ?? 0) + 1;

      const orderTotal = input.totalAmount + input.shippingFee + input.taxAmount;
      const payload = {
        order_id: nextOrderId,
        customer_id: input.customerId,
        order_datetime: new Date().toISOString(),
        billing_zip: input.billingZip,
        shipping_zip: input.shippingZip,
        shipping_state: input.shippingState,
        payment_method: input.paymentMethod,
        device_type: input.deviceType,
        ip_country: input.ipCountry,
        promo_used: input.promoUsed ? 1 : 0,
        promo_code: input.promoCode || null,
        order_subtotal: input.totalAmount,
        shipping_fee: input.shippingFee,
        tax_amount: input.taxAmount,
        order_total: orderTotal,
        risk_score: 0,
        is_fraud: 0,
      };
      const { data: inserted, error: insertError } = await supabase
        .from("orders")
        .insert(payload)
        .select("*")
        .single();
      if (insertError) throw insertError;

      const { data: custRow, error: custError } = await supabase
        .from("customers")
        .select("*")
        .eq("customer_id", input.customerId)
        .single();
      if (custError) {
        return mapOrder(inserted as DbOrder);
      }

      try {
        const orderPayload = orderRowToPredictPayload(inserted as Record<string, unknown>);
        const result = await predictFraud(orderPayload, custRow as DbCustomerRow);
        if (result) {
          const { error: updError } = await supabase
            .from("orders")
            .update({
              fraud_probability: result.fraud_probability,
              predicted_fraud: result.predicted_fraud,
              fraud_scored_at: new Date().toISOString(),
            })
            .eq("order_id", nextOrderId);
          if (updError) {
            console.error("[fraud] Supabase update failed:", updError.message, updError);
          } else {
            return mapOrder({
              ...(inserted as DbOrder),
              fraud_probability: result.fraud_probability,
              predicted_fraud: result.predicted_fraud,
            });
          }
        }
      } catch (e) {
        console.error("[fraud] scoring skipped:", e);
      }

      return mapOrder(inserted as DbOrder);
    },

    async runLateDeliveryScoring() {
      const { data: orders, error: ordersError } = await supabase
        .from("orders")
        .select(ORDER_SELECT_BASE)
        .order("order_id", { ascending: true });
      if (ordersError) throw ordersError;

      const scoredAt = new Date().toISOString();
      const mapped = (orders as DbOrder[]).map((row, idx) => {
        const signal = (((Number(row.order_total ?? 0) % 100) / 100 + (idx % 7) * 0.07) % 1).toFixed(3);
        return {
          order_id: row.order_id,
          risk_score: Number(signal),
        };
      });

      const { error: runError } = await supabase.from("scoring_runs").insert({ scored_at: scoredAt });
      if (!runError) {
        const scoreRows = mapped.map((row) => ({
          order_id: row.order_id,
          late_delivery_probability: row.risk_score,
          scored_at: scoredAt,
        }));

        for (let i = 0; i < scoreRows.length; i += SCORE_INSERT_BATCH_SIZE) {
          const batch = scoreRows.slice(i, i + SCORE_INSERT_BATCH_SIZE);
          const { error: scoresError } = await supabase.from("order_scores").insert(batch);
          if (scoresError) {
            break;
          }
        }
      }

      const predictions: PipelinePrediction[] = mapped
        .sort((a, b) => b.risk_score - a.risk_score)
        .slice(0, 50)
        .map((row) => ({
          orderId: row.order_id,
          lateDeliveryProbability: row.risk_score,
          scoredAt,
        }));

      return { predictions, scoredAt };
    },

    async getPriorityQueue() {
      const latest = await this.getLastScoringRunAt();
      if (latest) {
        const { data: scoredRows, error: scoredError } = await supabase
          .from("order_scores")
          .select("order_id,late_delivery_probability")
          .eq("scored_at", latest)
          .order("late_delivery_probability", { ascending: false })
          .limit(50);
        if (!scoredError && scoredRows && scoredRows.length > 0) {
          const orderIds = scoredRows.map((row) => Number(row.order_id));
          const { data: ordersById, error: ordersByIdError } = await supabase
            .from("orders")
            .select(ORDER_SELECT_BASE)
            .in("order_id", orderIds);
          if (ordersByIdError) throw ordersByIdError;
          const orderMap = new Map((ordersById as DbOrder[]).map((row) => [row.order_id, row]));
          return scoredRows
            .map((score) => {
              const base = orderMap.get(Number(score.order_id));
              if (!base) return null;
              return {
                ...mapOrder(base),
                lateDeliveryProbability: normalizeProbability(Number(score.late_delivery_probability ?? 0)),
              };
            })
            .filter((row): row is Order => row !== null);
        }
      }

      const { data, error } = await supabase
        .from("orders")
        .select(ORDER_SELECT_BASE)
        .order("risk_score", { ascending: false })
        .limit(50);
      if (error) throw error;
      return (data as DbOrder[]).map(mapOrder);
    },

    async getPipelinePredictions() {
      const latest = await this.getLastScoringRunAt();
      if (latest) {
        const { data, error } = await supabase
          .from("order_scores")
          .select("order_id,late_delivery_probability,scored_at")
          .eq("scored_at", latest)
          .order("late_delivery_probability", { ascending: false })
          .limit(50);
        if (!error && data) {
          return data.map((row) => ({
            orderId: Number(row.order_id),
            lateDeliveryProbability: normalizeProbability(Number(row.late_delivery_probability ?? 0)),
            scoredAt: String(row.scored_at),
          }));
        }
      }

      const { data, error } = await supabase
        .from("order_scores")
        .select("order_id,late_delivery_probability,scored_at")
        .order("late_delivery_probability", { ascending: false })
        .limit(50);
      if (!error && data) {
        return data.map((row) => ({
          orderId: Number(row.order_id),
          lateDeliveryProbability: normalizeProbability(Number(row.late_delivery_probability ?? 0)),
          scoredAt: String(row.scored_at),
        }));
      }

      const queue = await this.getPriorityQueue();
      const scoredAt = new Date().toISOString();
      return queue.map((order) => ({
        orderId: order.id,
        lateDeliveryProbability: order.lateDeliveryProbability,
        scoredAt,
      }));
    },

    async getLastScoringRunAt() {
      const { data, error } = await supabase
        .from("scoring_runs")
        .select("scored_at")
        .order("scored_at", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (!error && data?.scored_at) {
        return String(data.scored_at);
      }

      const { data: queue, error: queueError } = await supabase
        .from("order_scores")
        .select("scored_at")
        .order("scored_at", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (!queueError && queue?.scored_at) {
        return String(queue.scored_at);
      }
      return null;
    },
  };
}
