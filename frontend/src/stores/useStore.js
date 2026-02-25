import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { userApi } from '../services/api';

export const useUserStore = create(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      savedCourses: [],
      
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      
      logout: () => {
        localStorage.removeItem('dandori-token');
        set({ user: null, isAuthenticated: false, savedCourses: [] });
      },
      
      fetchSavedCourses: async () => {
        try {
          const courseIds = await userApi.getSavedCourses();
          set({ savedCourses: courseIds || [] });
        } catch (error) {
          console.error('Failed to fetch saved courses:', error);
        }
      },
      
      saveCourse: async (courseId) => {
        const { savedCourses } = get();
        if (!savedCourses.includes(courseId)) {
          set({ savedCourses: [...savedCourses, courseId] });
          try {
            await userApi.saveCourse(courseId);
          } catch (error) {
            console.error('Failed to save course:', error);
            set({ savedCourses: savedCourses.filter(id => id !== courseId) });
          }
        }
      },
      
      unsaveCourse: async (courseId) => {
        const { savedCourses } = get();
        set({ savedCourses: savedCourses.filter(id => id !== courseId) });
        try {
          await userApi.unsaveCourse(courseId);
        } catch (error) {
          console.error('Failed to unsave course:', error);
          set({ savedCourses: [...savedCourses, courseId] });
        }
      },
      
      isCourseSaved: (courseId) => {
        return get().savedCourses.includes(courseId);
      },
    }),
    {
      name: 'dandori-user-storage',
    }
  )
);

export const useChatStore = create((set, get) => ({
  messages: [],
  isOpen: false,
  isFullPage: false,
  isLoading: false,
  artifacts: [],
  
  toggleChat: () => set((state) => ({ isOpen: !state.isOpen })),
  
  openChat: () => set({ isOpen: true }),
  
  closeChat: () => set({ isOpen: false }),
  
  setFullPage: (isFullPage) => set({ isFullPage }),
  
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, { ...message, id: Date.now(), timestamp: new Date() }]
  })),
  
  setLoading: (isLoading) => set({ isLoading }),
  
  addArtifact: (artifact) => set((state) => ({
    artifacts: [...state.artifacts, { ...artifact, id: Date.now() }]
  })),
  
  clearArtifacts: () => set({ artifacts: [] }),
  
  clearMessages: () => set({ messages: [], artifacts: [] }),
}));

export const useSearchStore = create((set) => ({
  query: '',
  results: [],
  filters: {
    location: '',
    priceRange: [0, 500],
    courseType: '',
    sortBy: 'relevance',
  },
  isSearching: false,
  
  setQuery: (query) => set({ query }),
  
  setResults: (results) => set({ results }),
  
  setFilter: (key, value) => set((state) => ({
    filters: { ...state.filters, [key]: value }
  })),
  
  resetFilters: () => set({
    filters: {
      location: '',
      priceRange: [0, 500],
      courseType: '',
      sortBy: 'relevance',
    }
  }),
  
  setSearching: (isSearching) => set({ isSearching }),
}));

export const useUIStore = create((set) => ({
  sidebarOpen: true,
  mobileMenuOpen: false,
  
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  
  toggleMobileMenu: () => set((state) => ({ mobileMenuOpen: !state.mobileMenuOpen })),
  
  closeMobileMenu: () => set({ mobileMenuOpen: false }),
}));
