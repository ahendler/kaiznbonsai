import { useMutation, useQueryClient, useInfiniteQuery, useQuery } from '@tanstack/react-query';
import api from './client';
import type { Product, PaginatedResponse } from './inventory';
import { invalidateFinancials } from './financials';

// TYPES
export type OrderStatus = 'DRAFT' | 'CONFIRMED' | 'CANCELLED';

export type StockAllocationStrategy = 'FIFO' | 'FEFO';

export interface ConfirmSalesOrderInput {
  id: number;
  allocationStrategy?: StockAllocationStrategy;
}

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

export interface OrderListFilters {
  status?: OrderStatus;
}

// API CALLS
const orderApi = {
  getPurchaseOrders: async (
    cursor: string | null = null,
    filters: OrderListFilters = {},
  ): Promise<PaginatedResponse<PurchaseOrder>> => {
    const params: Record<string, string> = {};
    if (cursor) params.cursor = cursor;
    if (filters.status) params.status = filters.status;
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

  getSalesOrders: async (
    cursor: string | null = null,
    filters: OrderListFilters = {},
  ): Promise<PaginatedResponse<SalesOrder>> => {
    const params: Record<string, string> = {};
    if (cursor) params.cursor = cursor;
    if (filters.status) params.status = filters.status;
    const response = await api.get('/orders/sales-orders/', { params });
    return response.data;
  },
  createSalesOrder: async (data: SalesOrderInput): Promise<SalesOrder> => {
    const response = await api.post('/orders/sales-orders/', data);
    return response.data;
  },
  confirmSalesOrder: async (
    id: number,
    allocationStrategy: StockAllocationStrategy = 'FIFO',
  ): Promise<SalesOrder> => {
    const response = await api.post(`/orders/sales-orders/${id}/confirm/`, {
      allocation_strategy: allocationStrategy,
    });
    return response.data;
  },
  cancelSalesOrder: async (id: number): Promise<SalesOrder> => {
    const response = await api.post(`/orders/sales-orders/${id}/cancel/`);
    return response.data;
  },

  getPurchaseOrder: async (id: number): Promise<PurchaseOrder> => {
    const response = await api.get(`/orders/purchase-orders/${id}/`);
    return response.data;
  },

  getSalesOrder: async (id: number): Promise<SalesOrder> => {
    const response = await api.get(`/orders/sales-orders/${id}/`);
    return response.data;
  },
};

export const getPurchaseOrder = orderApi.getPurchaseOrder;
export const getSalesOrder = orderApi.getSalesOrder;

// HOOKS
export const usePurchaseOrders = (filters: OrderListFilters = {}) => {
  return useInfiniteQuery({
    queryKey: ['purchase-orders', filters],
    queryFn: ({ pageParam }) =>
      orderApi.getPurchaseOrders(pageParam as string | null, filters),
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
      queryClient.invalidateQueries({ queryKey: ['stocks'] });
      invalidateFinancials(queryClient);
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
      invalidateFinancials(queryClient);
    },
  });
};

export const useSalesOrders = (filters: OrderListFilters = {}) => {
  return useInfiniteQuery({
    queryKey: ['sales-orders', filters],
    queryFn: ({ pageParam }) =>
      orderApi.getSalesOrders(pageParam as string | null, filters),
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
    mutationFn: ({ id, allocationStrategy = 'FIFO' }: ConfirmSalesOrderInput) =>
      orderApi.confirmSalesOrder(id, allocationStrategy),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sales-orders'] });
      queryClient.invalidateQueries({ queryKey: ['stocks'] });
      invalidateFinancials(queryClient);
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
      invalidateFinancials(queryClient);
    },
  });
};

export const usePurchaseOrder = (id: number | null) => {
  return useQuery({
    queryKey: ['purchase-order', id],
    queryFn: () => orderApi.getPurchaseOrder(id!),
    enabled: id !== null,
  });
};

export const useSalesOrder = (id: number | null) => {
  return useQuery({
    queryKey: ['sales-order', id],
    queryFn: () => orderApi.getSalesOrder(id!),
    enabled: id !== null,
  });
};
