import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { MapPin, Clock, PoundSterling, Heart, Star, Users } from 'lucide-react';
import { useUserStore } from '../../stores/useStore';
import { Card, CardImage, Badge, Rating } from '../ui';
import styles from './CourseCard.module.css';

export default function CourseCard({ course, variant = 'default' }) {
  const { isCourseSaved, saveCourse, unsaveCourse, isAuthenticated } = useUserStore();
  const isSaved = isCourseSaved(course.id || course.class_id);

  const handleSaveToggle = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const courseId = course.id || course.class_id;
    if (isSaved) {
      unsaveCourse(courseId);
    } else {
      saveCourse(courseId);
    }
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { type: 'spring', stiffness: 300, damping: 25 }
    },
  };

  return (
    <motion.div variants={cardVariants}>
      <Link to={`/courses/${course.id || course.class_id}`} className={styles.link}>
        <Card 
          variant={variant === 'featured' ? 'whimsical' : 'default'} 
          hoverable 
          padding="none"
          className={styles.card}
        >
          <div className={styles.imageContainer}>
            {course.image_url ? (
              <CardImage 
                src={course.image_url} 
                alt={course.title}
                aspectRatio="4/3"
              />
            ) : (
              <div className={styles.placeholderImage}>
                <div className={styles.placeholderPattern}>
                  <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="20" cy="20" r="15" fill="currentColor" opacity="0.1" />
                    <circle cx="80" cy="30" r="10" fill="currentColor" opacity="0.15" />
                    <circle cx="50" cy="70" r="20" fill="currentColor" opacity="0.08" />
                    <path d="M10 80 Q30 60, 50 80 T90 80" stroke="currentColor" strokeWidth="2" opacity="0.1" />
                  </svg>
                </div>
                <span className={styles.placeholderText}>{course.course_type || 'Workshop'}</span>
              </div>
            )}
            
            <div className={styles.badges}>
              <Badge variant="primary" size="sm">
                {course.course_type || 'Workshop'}
              </Badge>
              {course.is_new && (
                <Badge variant="accent" size="sm">New</Badge>
              )}
            </div>

            {isAuthenticated && (
              <motion.button
                className={`${styles.saveButton} ${isSaved ? styles.saved : ''}`}
                onClick={handleSaveToggle}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                aria-label={isSaved ? 'Remove from saved' : 'Save course'}
              >
                <Heart size={18} fill={isSaved ? 'currentColor' : 'none'} />
              </motion.button>
            )}
          </div>

          <div className={styles.content}>
            <h3 className={styles.title}>{course.title}</h3>
            
            <p className={styles.instructor}>with {course.instructor}</p>

            {course.description && (
              <p className={styles.description}>
                {course.description.length > 100 
                  ? `${course.description.slice(0, 100)}...` 
                  : course.description}
              </p>
            )}

            <div className={styles.meta}>
              <span className={styles.metaItem}>
                <MapPin size={14} />
                {course.location}
              </span>
              {course.cost && (
                <span className={styles.metaItem}>
                  <PoundSterling size={14} />
                  {course.cost}
                </span>
              )}
            </div>

            {(course.rating || course.reviews_count) && (
              <div className={styles.footer}>
                <div className={styles.rating}>
                  <Rating value={course.rating || 0} size="sm" readonly />
                  <span className={styles.ratingText}>
                    {course.rating?.toFixed(1) || '0.0'}
                  </span>
                </div>
                {course.reviews_count && (
                  <span className={styles.reviews}>
                    ({course.reviews_count} reviews)
                  </span>
                )}
              </div>
            )}
          </div>

          <div className={styles.hoverOverlay}>
            <span className={styles.viewText}>View Course</span>
          </div>
        </Card>
      </Link>
    </motion.div>
  );
}
