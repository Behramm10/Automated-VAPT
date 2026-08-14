import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const fetchDashboardSummary = () => api.get('/dashboard/summary').then((res) => res.data);
export const fetchTargets = () => api.get('/targets').then((res) => res.data);
export const registerTarget = (data: any) => api.post('/targets', data).then((res) => res.data);
export const discoverTarget = (id: string) => api.post(`/targets/${id}/discover`).then((res) => res.data);
export const fetchRuns = () => api.get('/runs').then((res) => res.data);
export const createRun = (data: any) => api.post('/runs', data).then((res) => res.data);
export const startRun = (id: string) => api.post(`/runs/${id}/start`).then((res) => res.data);
export const fetchFindings = () => api.get('/findings').then((res) => res.data);
export const fetchFinding = (id: string) => api.get(`/findings/${id}`).then((res) => res.data);
export const fetchAttackGraph = (runId: string) => api.get(`/runs/${runId}/attack-graph`).then((res) => res.data);
export const fetchReports = () => api.get('/reports').then((res) => res.data);
export const generateReport = (runId: string) => api.post(`/reports/${runId}/generate`).then((res) => res.data);

export default api;
