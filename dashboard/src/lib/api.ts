import axios from 'axios';

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for authentication
api.interceptors.request.use(
  (config) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        // Redirect to login page if not already there
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

// Types
export interface DashboardData {
  totalProjects: number;
  totalScans: number;
  totalViolations: number;
  totalWarnings: number;
  highRiskProjects: number;
  pendingScans: number;
  licenseDistribution: Array<{
    name: string;
    value: number;
  }>;
  trend: Array<{
    date: string;
    violations: number;
  }>;
}

export interface ScanSummary {
  id: string;
  project: string;
  status: string;
  violations: number;
  warnings: number;
  generatedAt: string;
  durationSeconds: number;
  reportUrl?: string;
}

export interface ScanResult {
  summary: ScanSummary;
  report: {
    project: string;
    generatedAt: string;
    summary: {
      totalComponents: number;
      licensedComponents: number;
      unlicensedComponents: number;
      multiLicensedComponents: number;
      warnings: number;
      violations?: number;
    };
    findings: any[];
    policyEvaluation?: any;
  };
}

export interface Policy {
  id: string;
  name: string;
  description: string;
  rules: any[];
  enabled: boolean;
}

export interface UserProfile {
  username: string;
  email?: string;
  full_name?: string;
  role: string;
  disabled: boolean;
}

// API Functions

// Authentication
export const login = async (username: string, password: string) => {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);

  const response = await api.post('/auth/login', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });

  if (response.data.access_token) {
    localStorage.setItem('token', response.data.access_token);
  }

  return response.data;
};

export const logout = () => {
  localStorage.removeItem('token');
};

export const getUserProfile = async (): Promise<UserProfile> => {
  const response = await api.get('/auth/me');
  return response.data;
};

// Dashboard
export const getDashboard = async (): Promise<DashboardData> => {
  const response = await api.get('/dashboard');
  return response.data;
};

// Health Check
export const getHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

// Scans
export const getScans = async (): Promise<ScanSummary[]> => {
  const response = await api.get('/scans');
  return response.data;
};

export const getScan = async (id: string): Promise<ScanResult> => {
  const response = await api.get(`/scans/${id}`);
  return response.data;
};

export const createScan = async (repoUrl: string, policy?: string, projectName?: string) => {
  const response = await api.post('/scans', {
    repo_url: repoUrl,
    project_name: projectName,
    policy: policy && policy !== 'none' ? policy : undefined,
  });
  return response.data;
};

// Policies
export const getPolicies = async (): Promise<Policy[]> => {
  const response = await api.get('/policies');
  return response.data;
};

export const getPolicy = async (id: string): Promise<Policy> => {
  const response = await api.get(`/policies/${id}`);
  return response.data;
};

export const evaluatePolicy = async (policyId: string, scanResult: any) => {
  const response = await api.post('/policies/evaluate', {
    policy_id: policyId,
    scan_result: scanResult,
  });
  return response.data;
};

// Export all
export default api;
