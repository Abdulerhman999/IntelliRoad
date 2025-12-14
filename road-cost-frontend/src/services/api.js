import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Auth APIs
export const register = async (userData) => {
  const response = await api.post('/auth/register', userData);
  return response.data;
};

export const login = async (credentials) => {
  const response = await api.post('/auth/login', credentials);
  return response.data;
};

// Project APIs
export const getUserProjects = async (userId) => {
  const response = await api.get(`/projects/${userId}`);
  return response.data;
};

export const predictProject = async (projectData, userId) => {
  const response = await api.post(`/predict?user_id=${userId}`, projectData);
  return response.data;
};

export const downloadPDF = (projectId) => {
  return `${API_BASE_URL}/download/${projectId}`;
};

export default api;