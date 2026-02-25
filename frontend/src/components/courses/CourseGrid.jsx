import { motion } from 'framer-motion';
import CourseCard from './CourseCard';
import styles from './CourseGrid.module.css';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

export default function CourseGrid({ 
  courses, 
  columns = 3,
  emptyMessage = "No courses found",
  isLoading = false,
}) {
  if (isLoading) {
    return (
      <div className={styles.grid} style={{ '--columns': columns }}>
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className={styles.skeleton}>
            <div className={styles.skeletonImage} />
            <div className={styles.skeletonContent}>
              <div className={styles.skeletonTitle} />
              <div className={styles.skeletonText} />
              <div className={styles.skeletonMeta} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!courses || courses.length === 0) {
    return (
      <div className={styles.empty}>
        <div className={styles.emptyIcon}>
          <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="50" cy="40" r="25" stroke="currentColor" strokeWidth="2" strokeDasharray="4 4" />
            <path d="M30 70 Q50 85, 70 70" stroke="currentColor" strokeWidth="2" />
            <circle cx="40" cy="35" r="3" fill="currentColor" />
            <circle cx="60" cy="35" r="3" fill="currentColor" />
          </svg>
        </div>
        <p className={styles.emptyText}>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <motion.div 
      className={styles.grid}
      style={{ '--columns': columns }}
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {courses.map((course) => (
        <CourseCard 
          key={course.id || course.class_id} 
          course={course} 
        />
      ))}
    </motion.div>
  );
}
