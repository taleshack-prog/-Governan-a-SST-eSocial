import axios from "axios";
const API_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : "/api";
export const api = axios.create({ baseURL: API_URL });
api.interceptors.request.use(config => {
  const token = localStorage.getItem("radar_func_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
api.interceptors.response.use(
  r => r,
  err => Promise.reject(err)
);
