import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  MapPin, 
  Clock, 
  PoundSterling, 
  Heart, 
  Share2, 
  Calendar,
  User,
  BookOpen,
  CheckCircle,
  ChevronLeft,
  Star,
  MessageCircle
} from 'lucide-react';
import { PageLayout } from '../components/layout';
import { Button, Badge, Rating, Card, CardContent, Avatar, Modal, ModalFooter, Input } from '../components/ui';
import { useUserStore } from '../stores/useStore';
import { coursesApi, userApi } from '../services/api';
import styles from './CourseDetailPage.module.css';

export default function CourseDetailPage() {
  const { id } = useParams();
  const [course, setCourse] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewRating, setReviewRating] = useState(0);
  const [reviewText, setReviewText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { isCourseSaved, saveCourse, unsaveCourse, isAuthenticated } = useUserStore();
  const isSaved = isCourseSaved(id);

  useEffect(() => {
    const fetchCourse = async () => {
      try {
        const data = await coursesApi.getById(id);
        setCourse(data);
        
        try {
          const reviewsData = await userApi.getReviews(id);
          setReviews(reviewsData.reviews || []);
        } catch {
          setReviews([]);
        }
      } catch (error) {
        console.error('Failed to fetch course:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchCourse();
  }, [id]);

  const handleSaveToggle = () => {
    if (isSaved) {
      unsaveCourse(id);
    } else {
      saveCourse(id);
    }
  };

  const handleSubmitReview = async () => {
    if (!reviewRating || !reviewText.trim()) return;
    
    setIsSubmitting(true);
    try {
      await userApi.addReview(id, reviewRating, reviewText);
      const reviewsData = await userApi.getReviews(id);
      setReviews(reviewsData.reviews || []);
      setShowReviewModal(false);
      setReviewRating(0);
      setReviewText('');
    } catch (error) {
      console.error('Failed to submit review:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <PageLayout>
        <div className={styles.loading}>
          <div className={styles.loadingSpinner} />
          <p>Loading course details...</p>
        </div>
      </PageLayout>
    );
  }

  if (!course) {
    return (
      <PageLayout>
        <div className={styles.notFound}>
          <h2>Course Not Found</h2>
          <p>The course you're looking for doesn't exist or has been removed.</p>
          <Button as={Link} to="/courses" variant="primary">
            Browse All Courses
          </Button>
        </div>
      </PageLayout>
    );
  }

  const learningObjectives = course.learning_objectives?.split('\n').filter(Boolean) || [];
  const skills = course.skills?.split(',').map(s => s.trim()).filter(Boolean) || [];

  return (
    <PageLayout>
      <div className={styles.breadcrumb}>
        <Link to="/courses" className={styles.backLink}>
          <ChevronLeft size={18} />
          Back to Courses
        </Link>
      </div>

      <div className={styles.layout}>
        <div className={styles.mainContent}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <div className={styles.header}>
              <Badge variant="primary" size="lg">
                {course.course_type || 'Workshop'}
              </Badge>
              
              <h1 className={styles.title}>{course.title}</h1>
              
              <div className={styles.instructor}>
                <Avatar name={course.instructor} size="md" />
                <div>
                  <span className={styles.instructorLabel}>Taught by</span>
                  <span className={styles.instructorName}>{course.instructor}</span>
                </div>
              </div>

              <div className={styles.meta}>
                <span className={styles.metaItem}>
                  <MapPin size={18} />
                  {course.location}
                </span>
                {course.cost && (
                  <span className={styles.metaItem}>
                    <PoundSterling size={18} />
                    {course.cost}
                  </span>
                )}
                {course.rating && (
                  <span className={styles.metaItem}>
                    <Star size={18} fill="currentColor" className={styles.starIcon} />
                    {course.rating.toFixed(1)} ({reviews.length} reviews)
                  </span>
                )}
              </div>
            </div>

            {course.description && (
              <section className={styles.section}>
                <h2 className={styles.sectionTitle}>About This Course</h2>
                <p className={styles.description}>{course.description}</p>
              </section>
            )}

            {learningObjectives.length > 0 && (
              <section className={styles.section}>
                <h2 className={styles.sectionTitle}>What You'll Learn</h2>
                <ul className={styles.objectivesList}>
                  {learningObjectives.map((objective, index) => (
                    <motion.li 
                      key={index}
                      className={styles.objectiveItem}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                    >
                      <CheckCircle size={20} className={styles.checkIcon} />
                      <span>{objective}</span>
                    </motion.li>
                  ))}
                </ul>
              </section>
            )}

            {skills.length > 0 && (
              <section className={styles.section}>
                <h2 className={styles.sectionTitle}>Skills You'll Develop</h2>
                <div className={styles.skillsGrid}>
                  {skills.map((skill, index) => (
                    <Badge key={index} variant="outline-primary" size="lg">
                      {skill}
                    </Badge>
                  ))}
                </div>
              </section>
            )}

            {course.provided_materials && (
              <section className={styles.section}>
                <h2 className={styles.sectionTitle}>Materials Provided</h2>
                <p className={styles.materials}>{course.provided_materials}</p>
              </section>
            )}

            {/* Reviews Section */}
            <section className={styles.section}>
              <div className={styles.reviewsHeader}>
                <h2 className={styles.sectionTitle}>Reviews</h2>
                {isAuthenticated && (
                  <Button 
                    variant="outline" 
                    size="sm" 
                    icon={<MessageCircle size={16} />}
                    onClick={() => setShowReviewModal(true)}
                  >
                    Write a Review
                  </Button>
                )}
              </div>
              
              {reviews.length > 0 ? (
                <div className={styles.reviewsList}>
                  {reviews.map((review, index) => (
                    <Card key={index} variant="outlined" padding="md" className={styles.reviewCard}>
                      <CardContent>
                        <div className={styles.reviewHeader}>
                          <Avatar name={review.user_name} size="sm" />
                          <div className={styles.reviewMeta}>
                            <span className={styles.reviewAuthor}>{review.user_name}</span>
                            <Rating value={review.rating} size="sm" readonly />
                          </div>
                        </div>
                        <p className={styles.reviewText}>{review.review}</p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className={styles.noReviews}>
                  No reviews yet. Be the first to share your experience!
                </p>
              )}
            </section>
          </motion.div>
        </div>

        <aside className={styles.sidebar}>
          <Card variant="elevated" padding="lg" className={styles.bookingCard}>
            <CardContent>
              <div className={styles.price}>
                <span className={styles.priceLabel}>Course Fee</span>
                <span className={styles.priceValue}>
                  {course.cost ? `£${course.cost}` : 'Free'}
                </span>
              </div>

              <div className={styles.bookingActions}>
                <Button variant="whimsical" size="lg" fullWidth>
                  Book This Course
                </Button>
                
                {isAuthenticated && (
                  <Button 
                    variant={isSaved ? 'accent' : 'secondary'} 
                    size="lg" 
                    fullWidth
                    icon={<Heart size={18} fill={isSaved ? 'currentColor' : 'none'} />}
                    onClick={handleSaveToggle}
                  >
                    {isSaved ? 'Saved' : 'Save for Later'}
                  </Button>
                )}
                
                <Button variant="ghost" size="md" fullWidth icon={<Share2 size={18} />}>
                  Share Course
                </Button>
              </div>

              <div className={styles.courseInfo}>
                <div className={styles.infoItem}>
                  <Calendar size={18} />
                  <span>Evening & Weekend Sessions</span>
                </div>
                <div className={styles.infoItem}>
                  <User size={18} />
                  <span>Small Group Setting</span>
                </div>
                <div className={styles.infoItem}>
                  <BookOpen size={18} />
                  <span>All Materials Included</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </aside>
      </div>

      {/* Review Modal */}
      <Modal
        isOpen={showReviewModal}
        onClose={() => setShowReviewModal(false)}
        title="Write a Review"
        description="Share your experience with this course"
      >
        <div className={styles.reviewForm}>
          <div className={styles.ratingInput}>
            <label>Your Rating</label>
            <Rating value={reviewRating} onChange={setReviewRating} size="lg" />
          </div>
          
          <Input
            label="Your Review"
            as="textarea"
            value={reviewText}
            onChange={(e) => setReviewText(e.target.value)}
            placeholder="Tell others about your experience..."
            rows={4}
          />
        </div>
        
        <ModalFooter>
          <Button variant="ghost" onClick={() => setShowReviewModal(false)}>
            Cancel
          </Button>
          <Button 
            variant="primary" 
            onClick={handleSubmitReview}
            disabled={!reviewRating || !reviewText.trim()}
            isLoading={isSubmitting}
          >
            Submit Review
          </Button>
        </ModalFooter>
      </Modal>
    </PageLayout>
  );
}
