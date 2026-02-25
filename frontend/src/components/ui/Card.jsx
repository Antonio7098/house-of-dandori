import { forwardRef } from 'react';
import { motion } from 'framer-motion';
import styles from './Card.module.css';

const Card = forwardRef(({
  children,
  variant = 'default',
  padding = 'md',
  hoverable = false,
  clickable = false,
  className = '',
  as = 'div',
  ...props
}, ref) => {
  const Component = clickable ? motion.button : as === 'article' ? motion.article : motion.div;
  
  const classes = [
    styles.card,
    styles[variant],
    styles[`padding-${padding}`],
    hoverable && styles.hoverable,
    clickable && styles.clickable,
    className,
  ].filter(Boolean).join(' ');

  const hoverAnimation = hoverable || clickable ? {
    y: -4,
    transition: { type: 'spring', stiffness: 300, damping: 20 }
  } : {};

  return (
    <Component
      ref={ref}
      className={classes}
      whileHover={hoverAnimation}
      {...props}
    >
      {children}
    </Component>
  );
});

Card.displayName = 'Card';

const CardHeader = ({ children, className = '', ...props }) => (
  <div className={`${styles.header} ${className}`} {...props}>
    {children}
  </div>
);

const CardTitle = ({ children, as: Tag = 'h3', className = '', ...props }) => (
  <Tag className={`${styles.title} ${className}`} {...props}>
    {children}
  </Tag>
);

const CardDescription = ({ children, className = '', ...props }) => (
  <p className={`${styles.description} ${className}`} {...props}>
    {children}
  </p>
);

const CardContent = ({ children, className = '', ...props }) => (
  <div className={`${styles.content} ${className}`} {...props}>
    {children}
  </div>
);

const CardFooter = ({ children, className = '', ...props }) => (
  <div className={`${styles.footer} ${className}`} {...props}>
    {children}
  </div>
);

const CardImage = ({ src, alt, className = '', aspectRatio = '16/9', ...props }) => (
  <div className={`${styles.imageWrapper} ${className}`} style={{ aspectRatio }} {...props}>
    <img src={src} alt={alt} className={styles.image} loading="lazy" />
  </div>
);

const CardBadge = ({ children, variant = 'default', className = '', ...props }) => (
  <span className={`${styles.badge} ${styles[`badge-${variant}`]} ${className}`} {...props}>
    {children}
  </span>
);

export {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  CardImage,
  CardBadge,
};

export default Card;
