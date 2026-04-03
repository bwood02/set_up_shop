export type FraudPredictResult = {
  fraud_probability: number;
  predicted_fraud: number;
  threshold?: number;
  model_name?: string;
};

function normalizeFraudApiBaseUrl(raw: string | undefined): string | null {
  const trimmed = raw?.trim().replace(/\/$/, "");
  if (!trimmed) return null;
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

export async function predictFraud(order: Record<string, unknown>, customer: Record<string, unknown>): Promise<FraudPredictResult | null> {
  const baseUrl = normalizeFraudApiBaseUrl(process.env.FRAUD_API_URL);
  if (!baseUrl) {
    return null;
  }

  const secret = process.env.FRAUD_API_SECRET;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30_000);
  const res = await fetch(`${baseUrl}/predict`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(secret ? { "X-Fraud-Api-Secret": secret } : {}),
    },
    body: JSON.stringify({ order, customer }),
    signal: controller.signal,
  }).finally(() => clearTimeout(timeoutId));

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Fraud API error ${res.status}: ${text.slice(0, 200)}`);
  }

  return (await res.json()) as FraudPredictResult;
}
