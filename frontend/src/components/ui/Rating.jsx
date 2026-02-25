import { useState } from 'react';
import { Star } from 'lucide-react';
import { motion } from 'framer-motion';
import styles from './Rating.module.css';

export default function Rating({
  value = 0,
  max = 5,
  size = 'md',
  readonly = false,
  onChange,
  showValue = false,
  className = '',
  ...props
}) {
  const [hoverValue, setHoverValue] = useState(0);
  
  const displayValue = hoverValue || value;
  
  const classes = [
    styles.rating,
    styles[size],
    readonly && styles.readonly,
    className,
  ].filter(Boolean).join(' ');

  const handleClick = (rating) => {
    if (!readonly && onChange) {
      onChange(rating);
    }
  };

  return (
    <div className={classes} {...props}>
      <div className={styles.stars}>
        {Array.from({ length: max }, (_, i) => {
          const rating = i + 1;
          const isFilled = rating <= displayValue;
          const isHalf = rating - 0.5 === displayValue;
          
          return (
            <motion.button
              key={i}
              type="button"
              className={`${styles.star} ${isFilled ? styles.filled : ''} ${isHalf ? styles.half : ''}`}
              onClick={() => handleClick(rating)}
              onMouseEnter={() => !readonly && setHoverValue(rating)}
              onMouseLeave={() => !readonly && setHoverValue(0)}
              disabled={readonly}
              whileHover={readonly ? {} : { scale: 1.2 }}
              whileTap={readonly ? {} : { scale: 0.9 }}
              transition={{ type: 'spring', stiffness: 400, damping: 17 }}
            >
              <Star
                className={styles.starIcon}
                fill={isFilled ? 'currentColor' : 'none'}
                strokeWidth={1.5}
              />
            </motion.button>
          );
        })}
      </div>
      {showValue && (
        <span className={styles.value}>{value.toFixed(1)}</span>
      )}
    </div>
  );
}
