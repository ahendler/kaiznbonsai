import { keepPreviousData, useQuery, type QueryClient } from '@tanstack/react-query';
import api from './client';
import type { FinancialPeriodParams } from '@/utils/financialPeriod';

function periodKeyPart(period: FinancialPeriodParams): FinancialPeriodParams | 'all_time' {
  if (period.from && period.to) {
    return { from: period.from, to: period.to };
  }
  return 'all_time';
}

export const FINANCIALS_QUERY_KEYS = {
  overall: (period: FinancialPeriodParams = {}) =>
    ['overall-financials', periodKeyPart(period)] as const,
  products: (period: FinancialPeriodParams = {}) =>
    ['product-financials', periodKeyPart(period)] as const,
};

export function invalidateFinancials(queryClient: QueryClient): void {
  queryClient.invalidateQueries({ queryKey: ['overall-financials'] });
  queryClient.invalidateQueries({ queryKey: ['product-financials'] });
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
  getOverall: async (period: FinancialPeriodParams = {}): Promise<OverallFinancials> => {
    const response = await api.get('/inventory/financials/', { params: period });
    return response.data;
  },
  getProducts: async (period: FinancialPeriodParams = {}): Promise<ProductFinancials[]> => {
    const response = await api.get('/inventory/financials/products/', { params: period });
    return response.data;
  },
};

export const useOverallFinancials = (period: FinancialPeriodParams = {}) => {
  return useQuery({
    queryKey: FINANCIALS_QUERY_KEYS.overall(period),
    queryFn: () => financialsApi.getOverall(period),
    placeholderData: keepPreviousData,
  });
};

export const useProductFinancials = (period: FinancialPeriodParams = {}) => {
  return useQuery({
    queryKey: FINANCIALS_QUERY_KEYS.products(period),
    queryFn: () => financialsApi.getProducts(period),
    placeholderData: keepPreviousData,
  });
};
