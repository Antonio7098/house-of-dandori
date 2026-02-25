import styles from './Badge.module.css';

export default function Badge({
  children,
  variant = 'default',
  size = 'md',
  icon,
  className = '',
  ...props
}) {
  const classes = [
    styles.badge,
    styles[variant],
    styles[size],
    className,
  ].filter(Boolean).join(' ');

  return (
    <span className={classes} {...props}>
      {icon && <span className={styles.icon}>{icon}</span>}
      {children}
    </span>
  );
}
