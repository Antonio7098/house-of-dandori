import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Menu, X, Sun, Moon, MessageCircle, User, Search, Sparkles } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useUIStore, useChatStore, useUserStore } from '../../stores/useStore';
import { Button, Avatar } from '../ui';
import styles from './Header.module.css';

const navLinks = [
  { path: '/', label: 'Home' },
  { path: '/courses', label: 'Courses' },
  { path: '/search', label: 'Discover' },
  { path: '/about', label: 'About' },
];

export default function Header() {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const { mobileMenuOpen, toggleMobileMenu, closeMobileMenu } = useUIStore();
  const { openChat } = useChatStore();
  const { user, isAuthenticated } = useUserStore();

  return (
    <header className={styles.header}>
      <div className={styles.container}>
        <Link to="/" className={styles.logo} onClick={closeMobileMenu}>
          <motion.div 
            className={styles.logoIcon}
            whileHover={{ rotate: 15 }}
            transition={{ type: 'spring', stiffness: 300 }}
          >
            <Sparkles size={28} />
          </motion.div>
          <div className={styles.logoText}>
            <span className={styles.logoTitle}>School of Dandori</span>
            <span className={styles.logoTagline}>Reclaim your joy</span>
          </div>
        </Link>

        <nav className={`${styles.nav} ${mobileMenuOpen ? styles.navOpen : ''}`}>
          <ul className={styles.navList}>
            {navLinks.map((link) => (
              <li key={link.path}>
                <Link
                  to={link.path}
                  className={`${styles.navLink} ${location.pathname === link.path ? styles.active : ''}`}
                  onClick={closeMobileMenu}
                >
                  {link.label}
                  {location.pathname === link.path && (
                    <motion.span
                      className={styles.activeIndicator}
                      layoutId="activeNav"
                      transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                    />
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className={styles.actions}>
          <Link to="/search" className={styles.searchButton} aria-label="Search courses">
            <Search size={20} />
          </Link>

          <button
            className={styles.iconButton}
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          >
            <motion.div
              initial={false}
              animate={{ rotate: theme === 'dark' ? 180 : 0 }}
              transition={{ duration: 0.3 }}
            >
              {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
            </motion.div>
          </button>

          <button
            className={styles.iconButton}
            onClick={openChat}
            aria-label="Open chat assistant"
          >
            <MessageCircle size={20} />
          </button>

          {isAuthenticated ? (
            <Link to="/profile" className={styles.profileLink}>
              <Avatar
                name={user?.name}
                src={user?.avatar}
                size="sm"
              />
            </Link>
          ) : (
            <Button as={Link} to="/login" variant="primary" size="sm">
              Sign In
            </Button>
          )}

          <button
            className={styles.menuToggle}
            onClick={toggleMobileMenu}
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>

      {/* Decorative botanical element */}
      <div className={styles.decoration} aria-hidden="true">
        <svg viewBox="0 0 100 20" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M0 10 Q25 0, 50 10 T100 10"
            stroke="currentColor"
            strokeWidth="1"
            fill="none"
            opacity="0.3"
          />
        </svg>
      </div>
    </header>
  );
}
