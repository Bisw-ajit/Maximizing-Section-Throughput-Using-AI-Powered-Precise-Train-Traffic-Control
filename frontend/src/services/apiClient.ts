import { APIResponse } from '../types/api';

const BASE_URL = 'http://localhost:8000/api';

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`HTTP Error ${response.status}: ${response.statusText}`);
  }

  const json: APIResponse<T> = await response.json();

  if (!json.success || json.data === null) {
    throw new Error(json.error?.message || 'API request failed');
  }

  return json.data;
}
