import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { MapPin, Clock, PoundSterling, Heart, ExternalLink } from 'lucide-react';
import { useUserStore } from '../../stores/useStore';
import styles from './CourseArtifact.module.css';

export default function CourseArtifact({ course }) {
  const { isCourseSaved, saveCourse, unsaveCourse, isAuthenticated } = useUserStore();
  const courseId = course.id || course.class_id;
  const isSaved = isCourseSaved(courseId);

  const handleSaveToggle = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (isSaved) {
      unsaveCourse(courseId);
    } else {
      saveCourse(courseId);
    }
  };

  return (
    <motion.div
      className={styles.artifact}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
    >
      <div className={styles.header}>
        <span className={styles.type}>{course.course_type || 'Workshop'}</span>
        {isAuthenticated && (
          <button
            className={`${styles.saveButton} ${isSaved ? styles.saved : ''}`}
            onClick={handleSaveToggle}
            aria-label={isSaved ? 'Remove from saved' : 'Save course'}
          >
            <Heart size={14} fill={isSaved ? 'currentColor' : 'none'} />
          </button>
        )}
      </div>
      
      <h4 className={styles.title}>{course.title}</h4>
      
      <p className={styles.instructor}>with {course.instructor}</p>
      
      <div className={styles.meta}>
        <span className={styles.metaItem}>
          <MapPin size={12} />
          {course.location}
        </span>
        {course.cost && (
          <span className={styles.metaItem}>
            <PoundSterling size={12} />
            {course.cost}
          </span>
        )}
      </div>
      
      <Link to={`/courses/${courseId}`} className={styles.viewLink}>
        View Details
        <ExternalLink size={12} />
      </Link>
    </motion.div>
  );
}
