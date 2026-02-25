import { motion } from 'framer-motion';
import Header from './Header';
import Sidebar from './Sidebar';
import ChatPanel from '../chat/ChatPanel';
import { useUIStore } from '../../stores/useStore';
import styles from './PageLayout.module.css';

const pageVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { 
    opacity: 1, 
    y: 0,
    transition: {
      duration: 0.3,
      ease: [0.25, 0.1, 0.25, 1],
    }
  },
  exit: { 
    opacity: 0, 
    y: -10,
    transition: { duration: 0.2 }
  },
};

export default function PageLayout({ 
  children, 
  showSidebar = true,
  showHeader = true,
  fullWidth = false,
  className = '',
}) {
  const { sidebarOpen } = useUIStore();

  return (
    <div className={styles.layout}>
      {showSidebar && <Sidebar />}
      
      <div 
        className={styles.mainWrapper}
        style={{ 
          marginLeft: showSidebar ? (sidebarOpen ? 'var(--sidebar-width)' : '72px') : 0,
          transition: 'margin-left 0.3s ease',
        }}
      >
        {showHeader && <Header />}
        
        <motion.main
          className={`${styles.main} ${fullWidth ? styles.fullWidth : ''} ${className}`}
          variants={pageVariants}
          initial="initial"
          animate="animate"
          exit="exit"
        >
          {children}
        </motion.main>
      </div>

      <ChatPanel />
      
      {/* Floating decorative elements */}
      <div className={styles.floatingDecor} aria-hidden="true">
        <div className={styles.leaf1} />
        <div className={styles.leaf2} />
        <div className={styles.leaf3} />
      </div>
    </div>
  );
}

export function PageHeader({ 
  title, 
  description, 
  actions,
  breadcrumbs,
  className = '' 
}) {
  return (
    <header className={`${styles.pageHeader} ${className}`}>
      {breadcrumbs && (
        <nav className={styles.breadcrumbs} aria-label="Breadcrumb">
          {breadcrumbs}
        </nav>
      )}
      <div className={styles.pageHeaderContent}>
        <div className={styles.pageHeaderText}>
          <motion.h1 
            className={styles.pageTitle}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            {title}
          </motion.h1>
          {description && (
            <motion.p 
              className={styles.pageDescription}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              {description}
            </motion.p>
          )}
        </div>
        {actions && (
          <motion.div 
            className={styles.pageActions}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
          >
            {actions}
          </motion.div>
        )}
      </div>
    </header>
  );
}

export function PageSection({ 
  children, 
  title, 
  description,
  actions,
  className = '' 
}) {
  return (
    <section className={`${styles.section} ${className}`}>
      {(title || actions) && (
        <div className={styles.sectionHeader}>
          <div>
            {title && <h2 className={styles.sectionTitle}>{title}</h2>}
            {description && <p className={styles.sectionDescription}>{description}</p>}
          </div>
          {actions && <div className={styles.sectionActions}>{actions}</div>}
        </div>
      )}
      <div className={styles.sectionContent}>
        {children}
      </div>
    </section>
  );
}
