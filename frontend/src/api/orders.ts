import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import api from './client';
import type { Product, PaginatedResponse } from './inventory';

// TYPES
export type OrderStatus = 'DRAFT' | 'CONFIRMED' | 'CANCELLED';

export interface PurchaseOrderItem {
  id: number;
  product_details: Product;
  quantity: string;
  unit_cost: string;
  lot_code: string;
  best_before: string | null;
}

export interface PurchaseOrder {
  id: number;
  title?: string;
  status: OrderStatus;
  order_date: string;
  created_at: string;
  updated_at: string;
  items: PurchaseOrderItem[];
}

export interface PurchaseOrderItemInput {
  product_id: number;
  quantity: number | string;
  unit_cost: number | string;
  lot_code?: string;
  best_before?: string | null;
}

export interface PurchaseOrderInput {
  title?: string;
  items_data: PurchaseOrderItemInput[];
}

export interface SalesOrderItem {
  id: number;
  product_details: Product;
  quantity: string;
  unit_price: string;
}

export interface SalesOrder {
  id: number;
  title?: string;
  status: OrderStatus;
  order_date: string;
  created_at: string;
  updated_at: string;
  items: SalesOrderItem[];
}

export interface SalesOrderItemInput {
  product_id: number;
  quantity: number | string;
  unit_price: number | string;
}

export interface SalesOrderInput {
  title?: string;
  items_data: SalesOrderItemInput[];
}

// API CALLS
const orderApi = {
  getPurchaseOrders: async (cursor: string | null = null): Promise<PaginatedResponse<PurchaseOrder>> => {
    const params = cursor ? { cursor } : {};
    const response = await api.get('/orders/purchase-orders/', { params });
    return response.data;
  },
  createPurchaseOrder: async (data: PurchaseOrderInput): Promise<PurchaseOrder> => {
    const response = await api.post('/orders/purchase-orders/', data);
    return response.data;
  },
  confirmPurchaseOrder: async (id: number): Promise<PurchaseOrder> => {
    const response = await api.post(`/orders/purchase-orders/${id}/confirm/`);
    return response.data;
  },
  cancelPurchaseOrder: async (id: number): Promise<PurchaseOrder> => {
    const response = await api.post(`/orders/purchase-orders/${id}/cancel/`);
    return response.data;
  },

  getSalesOrders: async (cursor: string | null = null): Promise<PaginatedResponse<SalesOrder>> => {
    const params = cursor ? { cursor } : {};
    const response = await api.get('/orders/sales-orders/', { params });
    return response.data;
  },
  createSalesOrder: async (data: SalesOrderInput): Promise<SalesOrder> => {
    const response = await api.post('/orders/sales-orders/', data);
    return response.data;
  },
  confirmSalesOrder: async (id: number): Promise<SalesOrder> => {
    const response = await api.post(`/orders/sales-orders/${id}/confirm/`);
    return response.data;
  },
  cancelSalesOrder: async (id: number): Promise<SalesOrder> => {
    const response = await api.post(`/orders/sales-orders/${id}/cancel/`);
    return response.data;
  },
};

// HOOKS
export const usePurchaseOrders = () => {
  return useInfiniteQuery({
    queryKey: ['purchase-orders'],
    queryFn: ({ pageParam }) => orderApi.getPurchaseOrders(pageParam as string | null),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => {
      if (!lastPage.next) return null;
      const url = new URL(lastPage.next);
      return url.searchParams.get('cursor');
    },
  });
};

export const useCreatePurchaseOrder = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: orderApi.createPurchaseOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
    },
  });
};

export const useConfirmPurchaseOrder = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: orderApi.confirmPurchaseOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      // Confirming a PO generates stock, so we invalidate inventory too
      queryClient.invalidateQueries({ queryKey: ['stocks'] });
    },
  });
};

export const useCancelPurchaseOrder = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: orderApi.cancelPurchaseOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      queryClient.invalidateQueries({ queryKey: ['stocks'] });
    },
  });
};

export const useSalesOrders = () => {
  return useInfiniteQuery({
    queryKey: ['sales-orders'],
    queryFn: ({ pageParam }) => orderApi.getSalesOrders(pageParam as string | null),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => {
      if (!lastPage.next) return null;
      const url = new URL(lastPage.next);
      return url.searchParams.get('cursor');
    },
  });
};

export const useCreateSalesOrder = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: orderApi.createSalesOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sales-orders'] });
    },
  });
};

export const useConfirmSalesOrder = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: orderApi.confirmSalesOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sales-orders'] });
      // Confirming an SO consumes stock, invalidate inventory
      queryClient.invalidateQueries({ queryKey: ['stocks'] });
    },
  });
};

export const useCancelSalesOrder = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: orderApi.cancelSalesOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sales-orders'] });
      queryClient.invalidateQueries({ queryKey: ['stocks'] });
    },
  });
};
