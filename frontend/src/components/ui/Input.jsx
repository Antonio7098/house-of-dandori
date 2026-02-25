import { forwardRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Eye, EyeOff } from 'lucide-react';
import styles from './Input.module.css';

const Input = forwardRef(({
  label,
  error,
  hint,
  icon,
  type = 'text',
  size = 'md',
  variant = 'default',
  className = '',
  containerClassName = '',
  ...props
}, ref) => {
  const [showPassword, setShowPassword] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  
  const isPassword = type === 'password';
  const inputType = isPassword && showPassword ? 'text' : type;
  
  const containerClasses = [
    styles.container,
    containerClassName,
  ].filter(Boolean).join(' ');
  
  const wrapperClasses = [
    styles.inputWrapper,
    styles[variant],
    styles[size],
    isFocused && styles.focused,
    error && styles.error,
    props.disabled && styles.disabled,
  ].filter(Boolean).join(' ');
  
  const inputClasses = [
    styles.input,
    icon && styles.hasIcon,
    isPassword && styles.hasPasswordToggle,
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={containerClasses}>
      {label && (
        <label className={styles.label} htmlFor={props.id}>
          {label}
        </label>
      )}
      
      <div className={wrapperClasses}>
        {icon && <span className={styles.icon}>{icon}</span>}
        
        <input
          ref={ref}
          type={inputType}
          className={inputClasses}
          onFocus={(e) => {
            setIsFocused(true);
            props.onFocus?.(e);
          }}
          onBlur={(e) => {
            setIsFocused(false);
            props.onBlur?.(e);
          }}
          {...props}
        />
        
        {isPassword && (
          <button
            type="button"
            className={styles.passwordToggle}
            onClick={() => setShowPassword(!showPassword)}
            tabIndex={-1}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        )}
      </div>
      
      <AnimatePresence mode="wait">
        {error && (
          <motion.span
            className={styles.errorText}
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            transition={{ duration: 0.15 }}
          >
            {error}
          </motion.span>
        )}
        {hint && !error && (
          <motion.span
            className={styles.hint}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            {hint}
          </motion.span>
        )}
      </AnimatePresence>
    </div>
  );
});

Input.displayName = 'Input';

export default Input;
