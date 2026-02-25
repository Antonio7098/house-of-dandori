import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Filter, Grid, List } from 'lucide-react';
import { PageLayout, PageHeader, PageSection } from '../components/layout';
import { SearchFilters } from '../components/search';
import { CourseGrid } from '../components/courses';
import { Button } from '../components/ui';
import { coursesApi } from '../services/api';
import styles from './CoursesPage.module.css';

export default function CoursesPage() {
  const [courses, setCourses] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState('grid');

  useEffect(() => {
    fetchCourses();
  }, []);

  const fetchCourses = async (filters = {}) => {
    setIsLoading(true);
    try {
      const data = await coursesApi.getAll(filters);
      setCourses(data.courses || data || []);
    } catch (error) {
      console.error('Failed to fetch courses:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFilterApply = (filters) => {
    fetchCourses({
      location: filters.location,
      course_type: filters.courseType,
      min_price: filters.priceRange?.[0],
      max_price: filters.priceRange?.[1],
      sort_by: filters.sortBy,
    });
  };

  return (
    <PageLayout>
      <PageHeader
        title="All Courses"
        description="Explore our complete collection of whimsical courses designed to nurture your wellbeing"
        actions={
          <div className={styles.viewToggle}>
            <button
              className={`${styles.viewButton} ${viewMode === 'grid' ? styles.active : ''}`}
              onClick={() => setViewMode('grid')}
              aria-label="Grid view"
            >
              <Grid size={18} />
            </button>
            <button
              className={`${styles.viewButton} ${viewMode === 'list' ? styles.active : ''}`}
              onClick={() => setViewMode('list')}
              aria-label="List view"
            >
              <List size={18} />
            </button>
          </div>
        }
      />

      <div className={styles.filtersSection}>
        <SearchFilters onApply={handleFilterApply} />
      </div>

      <PageSection>
        <CourseGrid 
          courses={courses} 
          columns={viewMode === 'grid' ? 3 : 1} 
          isLoading={isLoading}
          emptyMessage="No courses available at the moment. Check back soon!"
        />
      </PageSection>
    </PageLayout>
  );
}
