import {
  keepPreviousData,
  useInfiniteQuery,
  useQuery,
  type QueryClient,
} from '@tanstack/react-query';
import type { PaginatedResponse } from './inventory';
import api from './client';
import type { FinancialPeriodParams } from '@/utils/financialPeriod';

function periodKeyPart(period: FinancialPeriodParams): FinancialPeriodParams | 'all_time' {
  if (period.from && period.to) {
    return { from: period.from, to: period.to };
  }
  return 'all_time';
}

export type MarginBand = 'negative' | 'low' | 'medium' | 'high';
export type ActivityFilter = 'all' | 'movement' | 'stale';
export type ProductFinancialOrdering = '-created_at' | '-revenue' | '-profit' | '-margin' | 'name';

export interface ProductFinancialListFilters {
  from?: string;
  to?: string;
  search?: string;
  margin_band?: MarginBand;
  activity?: ActivityFilter;
  ordering?: ProductFinancialOrdering;
}

function productFinancialFiltersKey(
  filters: ProductFinancialListFilters,
): ProductFinancialListFilters {
  const key: ProductFinancialListFilters = {};
  if (filters.from && filters.to) {
    key.from = filters.from;
    key.to = filters.to;
  }
  const search = filters.search?.trim();
  if (search) {
    key.search = search;
  }
  if (filters.margin_band) {
    key.margin_band = filters.margin_band;
  }
  if (filters.activity && filters.activity !== 'all') {
    key.activity = filters.activity;
  }
  if (filters.ordering && filters.ordering !== '-created_at') {
    key.ordering = filters.ordering;
  }
  return key;
}

export const FINANCIALS_QUERY_KEYS = {
  overall: (period: FinancialPeriodParams = {}) =>
    ['overall-financials', periodKeyPart(period)] as const,
  productsInfinite: (filters: ProductFinancialListFilters = {}) =>
    ['product-financials', 'infinite', productFinancialFiltersKey(filters)] as const,
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

export const listProductFinancials = async (
  cursor: string | null = null,
  filters: ProductFinancialListFilters = {},
): Promise<PaginatedResponse<ProductFinancials>> => {
  const params: Record<string, string> = {};
  if (cursor) {
    params.cursor = cursor;
  }
  if (filters.from) {
    params.from = filters.from;
  }
  if (filters.to) {
    params.to = filters.to;
  }
  const search = filters.search?.trim();
  if (search) {
    params.search = search;
  }
  if (filters.margin_band) {
    params.margin_band = filters.margin_band;
  }
  if (filters.activity && filters.activity !== 'all') {
    params.activity = filters.activity;
  }
  if (filters.ordering && filters.ordering !== '-created_at') {
    params.ordering = filters.ordering;
  }
  const response = await api.get('/inventory/financials/products/', { params });
  return response.data;
};

export const useOverallFinancials = (
  period: FinancialPeriodParams = {},
  options: { enabled?: boolean } = {},
) => {
  return useQuery({
    queryKey: FINANCIALS_QUERY_KEYS.overall(period),
    queryFn: () => listOverallFinancials(period),
    placeholderData: keepPreviousData,
    enabled: options.enabled ?? true,
  });
};

export const useInfiniteProductFinancials = (
  filters: ProductFinancialListFilters = {},
  options: { enabled?: boolean } = {},
) => {
  return useInfiniteQuery({
    queryKey: FINANCIALS_QUERY_KEYS.productsInfinite(filters),
    queryFn: ({ pageParam }) =>
      listProductFinancials(pageParam as string | null, filters),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => {
      if (!lastPage.next) {
        return null;
      }
      const url = new URL(lastPage.next);
      return url.searchParams.get('cursor');
    },
    placeholderData: keepPreviousData,
    enabled: options.enabled ?? true,
  });
};

async function listOverallFinancials(
  period: FinancialPeriodParams = {},
): Promise<OverallFinancials> {
  const response = await api.get('/inventory/financials/', { params: period });
  return response.data;
}
