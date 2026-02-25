import { forwardRef } from 'react';
import styles from './Avatar.module.css';

const Avatar = forwardRef(({
  src,
  alt = '',
  name,
  size = 'md',
  variant = 'circle',
  status,
  className = '',
  ...props
}, ref) => {
  const initials = name
    ? name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : '?';
  
  const classes = [
    styles.avatar,
    styles[size],
    styles[variant],
    className,
  ].filter(Boolean).join(' ');

  return (
    <div ref={ref} className={classes} {...props}>
      {src ? (
        <img src={src} alt={alt || name || 'Avatar'} className={styles.image} />
      ) : (
        <span className={styles.initials}>{initials}</span>
      )}
      {status && (
        <span className={`${styles.status} ${styles[`status-${status}`]}`} />
      )}
    </div>
  );
});

Avatar.displayName = 'Avatar';

export default Avatar;
