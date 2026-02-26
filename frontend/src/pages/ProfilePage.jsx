import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  User, 
  Mail, 
  MapPin, 
  Calendar, 
  Heart, 
  Settings, 
  LogOut,
  Edit2,
  Save,
  X
} from 'lucide-react';
import { PageLayout, PageHeader, PageSection } from '../components/layout';
import { CourseGrid } from '../components/courses';
import { Button, Card, CardContent, Avatar, Input, Badge } from '../components/ui';
import { useUserStore } from '../stores/useStore';
import { authApi, coursesApi } from '../services/api';
import styles from './ProfilePage.module.css';

export default function ProfilePage() {
  const navigate = useNavigate();
  const { user, isAuthenticated, setUser, logout, savedCourses, fetchSavedCourses: fetchSavedCoursesFromStore } = useUserStore();
  const [savedCoursesData, setSavedCoursesData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    name: '',
    email: '',
    location: '',
    bio: '',
  });
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    const fetchProfile = async () => {
      try {
        const response = await authApi.getProfile();
        if (response?.user) {
          setUser(response.user);
        }
      } catch (error) {
        console.error('Failed to fetch profile:', error);
      }
    };

    fetchProfile();
  }, [isAuthenticated, setUser]);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    setEditForm({
      name: user?.name || '',
      email: user?.email || '',
      location: user?.location || '',
      bio: user?.bio || '',
    });

    // Fetch saved courses from backend
    fetchSavedCoursesFromStore();
  }, [isAuthenticated, navigate, user]);

  useEffect(() => {
    // When savedCourses changes, fetch the actual course data
    fetchSavedCoursesData();
  }, [savedCourses]);

  const fetchSavedCoursesData = async () => {
    setIsLoading(true);
    try {
      if (savedCourses.length > 0) {
        const allCourses = await coursesApi.getAll();
        const courses = allCourses.courses || allCourses || [];
        const saved = courses.filter(c => 
          savedCourses.includes(c.id) || savedCourses.includes(c.class_id)
        );
        setSavedCoursesData(saved);
      } else {
        setSavedCoursesData([]);
      }
    } catch (error) {
      console.error('Failed to fetch saved courses:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    setIsSaving(true);
    try {
      const updated = await authApi.updateProfile(editForm);
      setUser({ ...user, ...updated });
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to update profile:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <PageLayout>
      <div className={styles.layout}>
        <aside className={styles.sidebar}>
          <Card variant="whimsical" padding="lg" className={styles.profileCard}>
            <CardContent>
              <div className={styles.avatarSection}>
                <Avatar 
                  name={user?.name} 
                  src={user?.avatar} 
                  size="xxl" 
                  variant="organic"
                />
                <button className={styles.editAvatarButton} aria-label="Change avatar">
                  <Edit2 size={14} />
                </button>
              </div>

              {isEditing ? (
                <div className={styles.editForm}>
                  <Input
                    label="Name"
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    icon={<User size={16} />}
                  />
                  <Input
                    label="Email"
                    type="email"
                    value={editForm.email}
                    onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                    icon={<Mail size={16} />}
                  />
                  <Input
                    label="Location"
                    value={editForm.location}
                    onChange={(e) => setEditForm({ ...editForm, location: e.target.value })}
                    icon={<MapPin size={16} />}
                  />
                  <label className={styles.bioLabel} htmlFor="bio">
                    Bio
                  </label>
                  <textarea
                    id="bio"
                    className={styles.bioInput}
                    value={editForm.bio}
                    onChange={(e) => setEditForm({ ...editForm, bio: e.target.value })}
                    maxLength={280}
                    placeholder="Share a little about your playful rituals, weekend wishes, or learning vibe."
                  />
                  
                  <div className={styles.editActions}>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => setIsEditing(false)}
                      icon={<X size={16} />}
                    >
                      Cancel
                    </Button>
                    <Button 
                      variant="primary" 
                      size="sm" 
                      onClick={handleSaveProfile}
                      isLoading={isSaving}
                      icon={<Save size={16} />}
                    >
                      Save
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  <h2 className={styles.userName}>{user?.name || 'Dandori Explorer'}</h2>
                  
                  <div className={styles.userInfo}>
                    <div className={styles.infoItem}>
                      <Mail size={16} />
                      <span>{user?.email || 'No email set'}</span>
                    </div>
                    {user?.location && (
                      <div className={styles.infoItem}>
                        <MapPin size={16} />
                        <span>{user.location}</span>
                      </div>
                    )}
                    <div className={styles.infoItem}>
                      <Calendar size={16} />
                      <span>Member since 2024</span>
                    </div>
                  </div>

                  <div className={styles.stats}>
                    <div className={styles.stat}>
                      <span className={styles.statValue}>{savedCourses.length}</span>
                      <span className={styles.statLabel}>Saved</span>
                    </div>
                    <div className={styles.stat}>
                      <span className={styles.statValue}>0</span>
                      <span className={styles.statLabel}>Completed</span>
                    </div>
                    <div className={styles.stat}>
                      <span className={styles.statValue}>0</span>
                      <span className={styles.statLabel}>Reviews</span>
                    </div>
                  </div>

                  <div className={styles.bioCard}>
                    <h3>About you</h3>
                    <p>{user?.bio?.trim() ? user.bio : 'Add a short bio so the Whimsy Wing can tailor every suggestion just for you.'}</p>
                  </div>

                  <div className={styles.profileActions}>
                    <Button 
                      variant="secondary" 
                      size="sm" 
                      fullWidth
                      icon={<Edit2 size={16} />}
                      onClick={() => setIsEditing(true)}
                    >
                      Edit Profile
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      fullWidth
                      icon={<Settings size={16} />}
                      as={Link}
                      to="/settings"
                    >
                      Settings
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      fullWidth
                      icon={<LogOut size={16} />}
                      onClick={handleLogout}
                      className={styles.logoutButton}
                    >
                      Sign Out
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </aside>

        <main className={styles.mainContent}>
          <PageHeader
            title="My Learning Journey"
            description="Track your progress and manage your saved courses"
          />

          <PageSection
            title="Saved Courses"
            description={`${savedCoursesData.length} courses saved for later`}
            actions={
              savedCoursesData.length > 0 && (
                <Button as={Link} to="/search" variant="outline" size="sm" icon={<Heart size={16} />}>
                  Discover More
                </Button>
              )
            }
          >
            {savedCoursesData.length > 0 ? (
              <CourseGrid 
                courses={savedCoursesData} 
                columns={2} 
                isLoading={isLoading}
              />
            ) : (
              <Card variant="outlined" padding="lg" className={styles.emptyState}>
                <CardContent>
                  <div className={styles.emptyIcon}>
                    <Heart size={40} />
                  </div>
                  <h3 className={styles.emptyTitle}>No Saved Courses Yet</h3>
                  <p className={styles.emptyText}>
                    Start exploring and save courses that spark your curiosity. 
                    They'll appear here for easy access.
                  </p>
                  <Button as={Link} to="/search" variant="whimsical" icon={<Heart size={18} />}>
                    Discover Courses
                  </Button>
                </CardContent>
              </Card>
            )}
          </PageSection>

          <PageSection
            title="My Achievements"
            description="Badges and milestones from your learning journey"
          >
            <div className={styles.achievementsGrid}>
              <Card variant="glass" padding="md" className={styles.achievementCard}>
                <CardContent>
                  <div className={styles.achievementIcon}>🌱</div>
                  <h4 className={styles.achievementTitle}>First Steps</h4>
                  <p className={styles.achievementDesc}>Created your account</p>
                  <Badge variant="success" size="sm">Earned</Badge>
                </CardContent>
              </Card>
              
              <Card variant="outlined" padding="md" className={`${styles.achievementCard} ${styles.locked}`}>
                <CardContent>
                  <div className={styles.achievementIcon}>🎨</div>
                  <h4 className={styles.achievementTitle}>Creative Soul</h4>
                  <p className={styles.achievementDesc}>Complete 3 creative courses</p>
                  <Badge variant="default" size="sm">0/3</Badge>
                </CardContent>
              </Card>
              
              <Card variant="outlined" padding="md" className={`${styles.achievementCard} ${styles.locked}`}>
                <CardContent>
                  <div className={styles.achievementIcon}>⭐</div>
                  <h4 className={styles.achievementTitle}>Reviewer</h4>
                  <p className={styles.achievementDesc}>Write your first review</p>
                  <Badge variant="default" size="sm">Locked</Badge>
                </CardContent>
              </Card>
            </div>
          </PageSection>
        </main>
      </div>
    </PageLayout>
  );
}
