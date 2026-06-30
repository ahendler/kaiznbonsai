import { useQuery, type QueryClient } from '@tanstack/react-query';
import api from './client';

export const FINANCIALS_QUERY_KEYS = {
  overall: ['overall-financials'] as const,
  products: ['product-financials'] as const,
};

export function invalidateFinancials(queryClient: QueryClient): void {
  queryClient.invalidateQueries({ queryKey: FINANCIALS_QUERY_KEYS.overall });
  queryClient.invalidateQueries({ queryKey: FINANCIALS_QUERY_KEYS.products });
}

export interface OverallFinancials {
  revenue: string;
  cogs: string;
  gross_profit: string;
  margin: string;
  inventory_value: string;
}

export interface ProductFinancials {
  id: string;
  name: string;
  sku: string;
  unit_of_measure: 'KG' | 'G' | 'L' | 'ML' | 'UNIT';
  qty_purchased: string;
  qty_sold: string;
  revenue: string;
  cogs: string;
  profit: string;
  margin: string;
}

const financialsApi = {
  getOverall: async (): Promise<OverallFinancials> => {
    const response = await api.get('/inventory/financials/');
    return response.data;
  },
  getProducts: async (): Promise<ProductFinancials[]> => {
    const response = await api.get('/inventory/financials/products/');
    return response.data;
  },
};

export const useOverallFinancials = () => {
  return useQuery({
    queryKey: FINANCIALS_QUERY_KEYS.overall,
    queryFn: financialsApi.getOverall,
  });
};

export const useProductFinancials = () => {
  return useQuery({
    queryKey: FINANCIALS_QUERY_KEYS.products,
    queryFn: financialsApi.getProducts,
  });
};
