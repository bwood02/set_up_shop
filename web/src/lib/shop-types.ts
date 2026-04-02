export type Customer = {
  id: number;
  firstName: string;
  lastName: string;
  email: string;
};

export type Order = {
  id: number;
  customerId: number;
  orderDate: string;
  totalAmount: number;
  isFraud: boolean;
  lateDeliveryProbability: number;
  fraudProbability?: number;
  predictedFraud?: boolean;
};

export type PipelinePrediction = {
  orderId: number;
  lateDeliveryProbability: number;
  scoredAt: string;
};

export type CreateOrderInput = {
  customerId: number;
  totalAmount: number;
  billingZip: string;
  shippingZip: string;
  shippingState: string;
  paymentMethod: string;
  deviceType: string;
  ipCountry: string;
  promoUsed: boolean;
  promoCode: string | null;
  shippingFee: number;
  taxAmount: number;
};
