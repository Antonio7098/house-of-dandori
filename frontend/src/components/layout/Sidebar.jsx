import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Home, 
  Search, 
  BookOpen, 
  Heart, 
  User, 
  Settings, 
  LogOut,
  ChevronLeft,
  Sparkles
} from 'lucide-react';
import { useUIStore, useUserStore } from '../../stores/useStore';
import { Avatar } from '../ui';
import styles from './Sidebar.module.css';

const mainNavItems = [
  { path: '/', icon: Home, label: 'Home' },
  { path: '/search', icon: Search, label: 'Discover' },
  { path: '/courses', icon: BookOpen, label: 'All Courses' },
  { path: '/saved', icon: Heart, label: 'Saved Courses' },
];

const bottomNavItems = [
  { path: '/profile', icon: User, label: 'Profile' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
  const location = useLocation();
  const { sidebarOpen, toggleSidebar } = useUIStore();
  const { user, isAuthenticated, logout } = useUserStore();

  const sidebarVariants = {
    open: { width: 'var(--sidebar-width)', transition: { duration: 0.3 } },
    closed: { width: '72px', transition: { duration: 0.3 } },
  };

  return (
    <motion.aside
      className={styles.sidebar}
      variants={sidebarVariants}
      animate={sidebarOpen ? 'open' : 'closed'}
      initial={false}
    >
      <div className={styles.header}>
        <Link to="/" className={styles.logo}>
          <div className={styles.logoIcon}>
            <Sparkles size={24} />
          </div>
          <AnimatePresence>
            {sidebarOpen && (
              <motion.span
                className={styles.logoText}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
              >
                Dandori
              </motion.span>
            )}
          </AnimatePresence>
        </Link>

        <button
          className={styles.toggleButton}
          onClick={toggleSidebar}
          aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          <motion.div
            animate={{ rotate: sidebarOpen ? 0 : 180 }}
            transition={{ duration: 0.3 }}
          >
            <ChevronLeft size={18} />
          </motion.div>
        </button>
      </div>

      <nav className={styles.nav}>
        <ul className={styles.navList}>
          {mainNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`${styles.navLink} ${isActive ? styles.active : ''}`}
                  title={!sidebarOpen ? item.label : undefined}
                >
                  <span className={styles.navIcon}>
                    <Icon size={20} />
                  </span>
                  <AnimatePresence>
                    {sidebarOpen && (
                      <motion.span
                        className={styles.navLabel}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -10 }}
                        transition={{ duration: 0.2 }}
                      >
                        {item.label}
                      </motion.span>
                    )}
                  </AnimatePresence>
                  {isActive && (
                    <motion.span
                      className={styles.activeIndicator}
                      layoutId="sidebarActive"
                      transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                    />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className={styles.divider} />

      <nav className={styles.bottomNav}>
        <ul className={styles.navList}>
          {bottomNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`${styles.navLink} ${isActive ? styles.active : ''}`}
                  title={!sidebarOpen ? item.label : undefined}
                >
                  <span className={styles.navIcon}>
                    <Icon size={20} />
                  </span>
                  <AnimatePresence>
                    {sidebarOpen && (
                      <motion.span
                        className={styles.navLabel}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -10 }}
                        transition={{ duration: 0.2 }}
                      >
                        {item.label}
                      </motion.span>
                    )}
                  </AnimatePresence>
                </Link>
              </li>
            );
          })}
          
          {isAuthenticated && (
            <li>
              <button
                className={styles.navLink}
                onClick={logout}
                title={!sidebarOpen ? 'Sign Out' : undefined}
              >
                <span className={styles.navIcon}>
                  <LogOut size={20} />
                </span>
                <AnimatePresence>
                  {sidebarOpen && (
                    <motion.span
                      className={styles.navLabel}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -10 }}
                      transition={{ duration: 0.2 }}
                    >
                      Sign Out
                    </motion.span>
                  )}
                </AnimatePresence>
              </button>
            </li>
          )}
        </ul>
      </nav>

      {isAuthenticated && (
        <div className={styles.userSection}>
          <Link to="/profile" className={styles.userCard}>
            <Avatar name={user?.name} src={user?.avatar} size="sm" />
            <AnimatePresence>
              {sidebarOpen && (
                <motion.div
                  className={styles.userInfo}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  transition={{ duration: 0.2 }}
                >
                  <span className={styles.userName}>{user?.name || 'Guest'}</span>
                  <span className={styles.userEmail}>{user?.email}</span>
                </motion.div>
              )}
            </AnimatePresence>
          </Link>
        </div>
      )}

      {/* Decorative leaf */}
      <div className={styles.decoration} aria-hidden="true">
        <svg viewBox="0 0 40 60" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M20 0 C30 15, 35 30, 20 60 C5 30, 10 15, 20 0"
            fill="currentColor"
            opacity="0.1"
          />
          <path
            d="M20 10 L20 50"
            stroke="currentColor"
            strokeWidth="1"
            opacity="0.2"
          />
        </svg>
      </div>
    </motion.aside>
  );
}
