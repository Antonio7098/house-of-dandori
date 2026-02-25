const API_BASE = import.meta.env.VITE_API_URL || '';

async function fetchWithAuth(endpoint, options = {}) {
  const token = localStorage.getItem('dandori-token');
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }
  
  return response.json();
}

export const coursesApi = {
  getAll: (params = {}) => {
    const searchParams = new URLSearchParams(params);
    return fetchWithAuth(`/api/courses?${searchParams}`);
  },
  
  getById: (id) => fetchWithAuth(`/api/courses/${id}`),
  
  create: (data) => fetchWithAuth('/api/courses', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  
  update: (id, data) => fetchWithAuth(`/api/courses/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  
  delete: (id) => fetchWithAuth(`/api/courses/${id}`, {
    method: 'DELETE',
  }),
  
  search: (query, filters = {}) => {
    const params = new URLSearchParams({ q: query, ...filters });
    return fetchWithAuth(`/api/search?${params}`);
  },
  
  graphSearch: (query, filters = {}) => {
    const params = new URLSearchParams({ q: query, ...filters });
    return fetchWithAuth(`/api/graph-search?${params}`);
  },
};

export const authApi = {
  login: (email, password) => fetchWithAuth('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  }),
  
  signup: (data) => fetchWithAuth('/api/auth/signup', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  
  logout: () => fetchWithAuth('/api/auth/logout', {
    method: 'POST',
  }),
  
  getProfile: () => fetchWithAuth('/api/auth/profile'),
  
  updateProfile: (data) => fetchWithAuth('/api/auth/profile', {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
};

export const chatApi = {
  sendMessage: async (message, history = []) => {
    return fetchWithAuth('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message, history }),
    });
  },
  
  streamMessage: async function* (message, history = []) {
    const token = localStorage.getItem('dandori-token');
    
    const response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
      },
      body: JSON.stringify({ message, history }),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') return;
          try {
            yield JSON.parse(data);
          } catch {
            yield { content: data };
          }
        }
      }
    }
  },
};

export const userApi = {
  getSavedCourses: () => fetchWithAuth('/api/user/saved-courses'),
  
  saveCourse: (courseId) => fetchWithAuth('/api/user/saved-courses', {
    method: 'POST',
    body: JSON.stringify({ course_id: courseId }),
  }),
  
  unsaveCourse: (courseId) => fetchWithAuth(`/api/user/saved-courses/${courseId}`, {
    method: 'DELETE',
  }),
  
  addReview: (courseId, rating, review) => fetchWithAuth(`/api/courses/${courseId}/reviews`, {
    method: 'POST',
    body: JSON.stringify({ rating, review }),
  }),
  
  getReviews: (courseId) => fetchWithAuth(`/api/courses/${courseId}/reviews`),
};
