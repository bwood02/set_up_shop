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
};

export type PipelinePrediction = {
  orderId: number;
  lateDeliveryProbability: number;
  scoredAt: string;
};
