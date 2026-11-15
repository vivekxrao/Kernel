const API = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const contentType = response.headers.get('content-type') || '';
  const body = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const message = typeof body === 'object' ? (body.detail || body.message) : body;
    throw new Error(message || `Request failed (${response.status})`);
  }
  return body;
}

export const getHealth = () => request('/api/health');
export const getConfig = () => request('/api/config');
export const getSummary = () => request('/api/summary');
export const getBuildings = () => request('/api/buildings');
export const getTasks = () => request('/api/tasks');
export const getLayers = () => request('/api/layers');
export const submitAssessment = (payload) => request('/api/assessment/run', {
  method: 'POST',
  body: JSON.stringify(payload),
});
export const csvExportUrl = `${API}/api/export.csv`;
export { API as API_BASE };
