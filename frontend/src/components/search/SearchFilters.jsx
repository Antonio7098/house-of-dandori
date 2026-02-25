import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Filter, ChevronDown, X, MapPin, PoundSterling, Tag, SortAsc } from 'lucide-react';
import { useSearchStore } from '../../stores/useStore';
import { Button, Badge } from '../ui';
import styles from './SearchFilters.module.css';

const locations = [
  'London', 'Manchester', 'Birmingham', 'Bristol', 'Edinburgh', 
  'Glasgow', 'Leeds', 'Liverpool', 'Newcastle', 'Oxford', 'Cambridge'
];

const courseTypes = [
  'Pottery', 'Painting', 'Cooking', 'Gardening', 'Crafts', 
  'Music', 'Dance', 'Writing', 'Photography', 'Wellness'
];

const sortOptions = [
  { value: 'relevance', label: 'Most Relevant' },
  { value: 'price_low', label: 'Price: Low to High' },
  { value: 'price_high', label: 'Price: High to Low' },
  { value: 'rating', label: 'Highest Rated' },
  { value: 'newest', label: 'Newest First' },
];

export default function SearchFilters({ onApply }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { filters, setFilter, resetFilters } = useSearchStore();

  const activeFiltersCount = [
    filters.location,
    filters.courseType,
    filters.priceRange[0] > 0 || filters.priceRange[1] < 500,
  ].filter(Boolean).length;

  const handleApply = () => {
    onApply?.(filters);
    setIsExpanded(false);
  };

  const handleReset = () => {
    resetFilters();
    onApply?.({});
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <button
          className={styles.toggleButton}
          onClick={() => setIsExpanded(!isExpanded)}
          aria-expanded={isExpanded}
        >
          <Filter size={18} />
          <span>Filters</span>
          {activeFiltersCount > 0 && (
            <Badge variant="primary" size="sm">{activeFiltersCount}</Badge>
          )}
          <motion.span
            className={styles.chevron}
            animate={{ rotate: isExpanded ? 180 : 0 }}
          >
            <ChevronDown size={18} />
          </motion.span>
        </button>

        <div className={styles.sortWrapper}>
          <label htmlFor="sort" className={styles.sortLabel}>
            <SortAsc size={16} />
            Sort by:
          </label>
          <select
            id="sort"
            value={filters.sortBy}
            onChange={(e) => setFilter('sortBy', e.target.value)}
            className={styles.sortSelect}
          >
            {sortOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            className={styles.filtersPanel}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className={styles.filtersGrid}>
              {/* Location filter */}
              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>
                  <MapPin size={16} />
                  Location
                </label>
                <div className={styles.chipGroup}>
                  {locations.map(location => (
                    <button
                      key={location}
                      className={`${styles.chip} ${filters.location === location ? styles.active : ''}`}
                      onClick={() => setFilter('location', filters.location === location ? '' : location)}
                    >
                      {location}
                    </button>
                  ))}
                </div>
              </div>

              {/* Course type filter */}
              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>
                  <Tag size={16} />
                  Course Type
                </label>
                <div className={styles.chipGroup}>
                  {courseTypes.map(type => (
                    <button
                      key={type}
                      className={`${styles.chip} ${filters.courseType === type ? styles.active : ''}`}
                      onClick={() => setFilter('courseType', filters.courseType === type ? '' : type)}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </div>

              {/* Price range filter */}
              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>
                  <PoundSterling size={16} />
                  Price Range: £{filters.priceRange[0]} - £{filters.priceRange[1]}
                </label>
                <div className={styles.rangeWrapper}>
                  <input
                    type="range"
                    min="0"
                    max="500"
                    step="10"
                    value={filters.priceRange[0]}
                    onChange={(e) => setFilter('priceRange', [parseInt(e.target.value), filters.priceRange[1]])}
                    className={styles.rangeInput}
                  />
                  <input
                    type="range"
                    min="0"
                    max="500"
                    step="10"
                    value={filters.priceRange[1]}
                    onChange={(e) => setFilter('priceRange', [filters.priceRange[0], parseInt(e.target.value)])}
                    className={styles.rangeInput}
                  />
                </div>
              </div>
            </div>

            <div className={styles.filtersActions}>
              <Button variant="ghost" size="sm" onClick={handleReset} icon={<X size={16} />}>
                Clear All
              </Button>
              <Button variant="primary" size="sm" onClick={handleApply}>
                Apply Filters
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Active filters display */}
      {activeFiltersCount > 0 && !isExpanded && (
        <div className={styles.activeFilters}>
          {filters.location && (
            <Badge variant="outline-primary" size="md">
              {filters.location}
              <button onClick={() => setFilter('location', '')} className={styles.removeBadge}>
                <X size={12} />
              </button>
            </Badge>
          )}
          {filters.courseType && (
            <Badge variant="outline-primary" size="md">
              {filters.courseType}
              <button onClick={() => setFilter('courseType', '')} className={styles.removeBadge}>
                <X size={12} />
              </button>
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}
