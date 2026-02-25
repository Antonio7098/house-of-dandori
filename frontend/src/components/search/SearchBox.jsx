import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Sparkles, X, Loader2 } from 'lucide-react';
import { useSearchStore } from '../../stores/useStore';
import { Button } from '../ui';
import styles from './SearchBox.module.css';

export default function SearchBox({ 
  onSearch, 
  placeholder = "Search for your next adventure...",
  variant = 'default',
  autoFocus = false,
}) {
  const inputRef = useRef(null);
  const { query, setQuery, isSearching } = useSearchStore();
  const [isFocused, setIsFocused] = useState(false);
  const [localQuery, setLocalQuery] = useState(query);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (localQuery.trim()) {
      setQuery(localQuery.trim());
      onSearch?.(localQuery.trim());
    }
  };

  const handleClear = () => {
    setLocalQuery('');
    setQuery('');
    inputRef.current?.focus();
  };

  const containerClasses = [
    styles.container,
    styles[variant],
    isFocused && styles.focused,
  ].filter(Boolean).join(' ');

  return (
    <form onSubmit={handleSubmit} className={containerClasses}>
      <div className={styles.inputWrapper}>
        <span className={styles.searchIcon}>
          <Search size={20} />
        </span>
        
        <input
          ref={inputRef}
          type="text"
          value={localQuery}
          onChange={(e) => setLocalQuery(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder={placeholder}
          className={styles.input}
          aria-label="Search courses"
        />

        <AnimatePresence>
          {localQuery && (
            <motion.button
              type="button"
              className={styles.clearButton}
              onClick={handleClear}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              aria-label="Clear search"
            >
              <X size={16} />
            </motion.button>
          )}
        </AnimatePresence>

        <Button
          type="submit"
          variant="whimsical"
          size="md"
          disabled={!localQuery.trim() || isSearching}
          icon={isSearching ? <Loader2 className={styles.spinner} size={18} /> : <Sparkles size={18} />}
          className={styles.searchButton}
        >
          {variant === 'hero' ? 'Discover' : 'Search'}
        </Button>
      </div>

      {variant === 'hero' && (
        <p className={styles.hint}>
          Try "relaxing pottery class" or "weekend workshops in London"
        </p>
      )}

      {/* Decorative elements for hero variant */}
      {variant === 'hero' && (
        <div className={styles.decorations} aria-hidden="true">
          <div className={styles.floatingLeaf1} />
          <div className={styles.floatingLeaf2} />
          <div className={styles.floatingCircle} />
        </div>
      )}
    </form>
  );
}
