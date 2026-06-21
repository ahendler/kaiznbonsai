import { useQuery } from '@tanstack/react-query';
import api from './client';

export interface OverallFinancials {
  revenue: number;
  cogs: number;
  gross_profit: number;
  margin: number;
  inventory_value: number;
}

export interface ProductFinancials {
  id: number;
  name: string;
  sku: string;
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
    queryKey: ['overall-financials'],
    queryFn: financialsApi.getOverall,
  });
};

export const useProductFinancials = () => {
  return useQuery({
    queryKey: ['product-financials'],
    queryFn: financialsApi.getProducts,
  });
};
