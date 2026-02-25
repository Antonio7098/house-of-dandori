import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sparkles, ArrowRight, Heart, Users, Calendar, MapPin } from 'lucide-react';
import { PageLayout, PageSection } from '../components/layout';
import { SearchBox } from '../components/search';
import { CourseGrid } from '../components/courses';
import { Button, Card, CardContent } from '../components/ui';
import { coursesApi } from '../services/api';
import styles from './HomePage.module.css';

const features = [
  {
    icon: Heart,
    title: 'Nurture Your Wellbeing',
    description: 'Reconnect with joy through carefully curated classes designed for adult learners seeking balance.',
  },
  {
    icon: Users,
    title: 'Community of Curious Minds',
    description: 'Join hundreds of like-minded individuals on a journey of playful discovery and growth.',
  },
  {
    icon: Calendar,
    title: 'Evening & Weekend Classes',
    description: 'Flexible scheduling that fits your life. Learn at your own pace, on your own time.',
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { type: 'spring', stiffness: 300, damping: 25 }
  },
};

export default function HomePage() {
  const [featuredCourses, setFeaturedCourses] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const data = await coursesApi.getAll({ limit: 6 });
        setFeaturedCourses(data.courses || data || []);
      } catch (error) {
        console.error('Failed to fetch courses:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchCourses();
  }, []);

  const handleSearch = (query) => {
    window.location.href = `/search?q=${encodeURIComponent(query)}`;
  };

  return (
    <PageLayout showSidebar={false} fullWidth>
      {/* Hero Section */}
      <section className={styles.hero}>
        <div className={styles.heroBackground}>
          <div className={styles.heroPattern} />
          <div className={styles.heroGradient} />
        </div>
        
        <motion.div 
          className={styles.heroContent}
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.div className={styles.heroBadge} variants={itemVariants}>
            <Sparkles size={16} />
            <span>Reclaim Your Joy</span>
          </motion.div>
          
          <motion.h1 className={styles.heroTitle} variants={itemVariants}>
            The School of <span className={styles.highlight}>Dandori</span>
          </motion.h1>
          
          <motion.p className={styles.heroSubtitle} variants={itemVariants}>
            Discover the art of managing your time and wellbeing through whimsical 
            evening and weekend classes designed to reconnect you with your most playful self.
          </motion.p>
          
          <motion.div className={styles.heroSearch} variants={itemVariants}>
            <SearchBox 
              variant="hero" 
              onSearch={handleSearch}
              placeholder="What sparks your curiosity today?"
            />
          </motion.div>

          <motion.div className={styles.heroStats} variants={itemVariants}>
            <div className={styles.stat}>
              <span className={styles.statValue}>500+</span>
              <span className={styles.statLabel}>Courses</span>
            </div>
            <div className={styles.statDivider} />
            <div className={styles.stat}>
              <span className={styles.statValue}>200+</span>
              <span className={styles.statLabel}>Instructors</span>
            </div>
            <div className={styles.statDivider} />
            <div className={styles.stat}>
              <span className={styles.statValue}>50+</span>
              <span className={styles.statLabel}>Locations</span>
            </div>
          </motion.div>
        </motion.div>

        {/* Decorative elements */}
        <div className={styles.heroDecorations} aria-hidden="true">
          <div className={styles.floatingShape1} />
          <div className={styles.floatingShape2} />
          <div className={styles.floatingShape3} />
          <div className={styles.floatingLeaf1} />
          <div className={styles.floatingLeaf2} />
        </div>
      </section>

      {/* Features Section */}
      <section className={styles.features}>
        <div className={styles.container}>
          <motion.div 
            className={styles.featuresGrid}
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
          >
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <motion.div key={index} variants={itemVariants}>
                  <Card variant="whimsical" padding="lg" className={styles.featureCard}>
                    <CardContent>
                      <div className={styles.featureIcon}>
                        <Icon size={28} />
                      </div>
                      <h3 className={styles.featureTitle}>{feature.title}</h3>
                      <p className={styles.featureDescription}>{feature.description}</p>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </motion.div>
        </div>
      </section>

      {/* Featured Courses Section */}
      <section className={styles.coursesSection}>
        <div className={styles.container}>
          <PageSection
            title="Discover Your Next Adventure"
            description="Handpicked courses to ignite your curiosity and nurture your wellbeing"
            actions={
              <Button as={Link} to="/courses" variant="outline" icon={<ArrowRight size={18} />} iconPosition="right">
                View All Courses
              </Button>
            }
          >
            <CourseGrid 
              courses={featuredCourses} 
              columns={3} 
              isLoading={isLoading}
              emptyMessage="Courses are being prepared with care..."
            />
          </PageSection>
        </div>
      </section>

      {/* CTA Section */}
      <section className={styles.cta}>
        <div className={styles.ctaBackground} />
        <div className={styles.container}>
          <motion.div 
            className={styles.ctaContent}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className={styles.ctaTitle}>Ready to Begin Your Journey?</h2>
            <p className={styles.ctaText}>
              Join thousands of adults who have rediscovered the joy of learning. 
              Your next adventure awaits.
            </p>
            <div className={styles.ctaActions}>
              <Button as={Link} to="/search" variant="whimsical" size="lg" icon={<Sparkles size={20} />}>
                Explore Courses
              </Button>
              <Button as={Link} to="/about" variant="secondary" size="lg">
                Learn More
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className={styles.footer}>
        <div className={styles.container}>
          <div className={styles.footerContent}>
            <div className={styles.footerBrand}>
              <div className={styles.footerLogo}>
                <Sparkles size={24} />
                <span>School of Dandori</span>
              </div>
              <p className={styles.footerTagline}>
                The art of managing time and wellbeing through joyful learning.
              </p>
            </div>
            
            <div className={styles.footerLinks}>
              <div className={styles.footerColumn}>
                <h4>Explore</h4>
                <Link to="/courses">All Courses</Link>
                <Link to="/search">Discover</Link>
                <Link to="/instructors">Instructors</Link>
              </div>
              <div className={styles.footerColumn}>
                <h4>Company</h4>
                <Link to="/about">About Us</Link>
                <Link to="/contact">Contact</Link>
                <Link to="/careers">Careers</Link>
              </div>
              <div className={styles.footerColumn}>
                <h4>Support</h4>
                <Link to="/help">Help Center</Link>
                <Link to="/privacy">Privacy</Link>
                <Link to="/terms">Terms</Link>
              </div>
            </div>
          </div>
          
          <div className={styles.footerBottom}>
            <p>© 2024 School of Dandori. Founded by Ada Calm & Tessa Forman.</p>
          </div>
        </div>
      </footer>
    </PageLayout>
  );
}
