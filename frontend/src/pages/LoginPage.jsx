import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, Lock, Sparkles, ArrowRight } from 'lucide-react';
import { Button, Input, Card, CardContent } from '../components/ui';
import { useUserStore } from '../stores/useStore';
import { authApi } from '../services/api';
import styles from './LoginPage.module.css';

export default function LoginPage() {
  const navigate = useNavigate();
  const { setUser } = useUserStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const response = await authApi.login(email, password);
      localStorage.setItem('dandori-token', response.token);
      setUser(response.user);
      navigate('/');
    } catch (err) {
      setError(err.message || 'Invalid email or password');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.background}>
        <div className={styles.pattern} />
        <div className={styles.gradient} />
      </div>

      <motion.div 
        className={styles.container}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Link to="/" className={styles.logo}>
          <div className={styles.logoIcon}>
            <Sparkles size={28} />
          </div>
          <span className={styles.logoText}>School of Dandori</span>
        </Link>

        <Card variant="elevated" padding="lg" className={styles.card}>
          <CardContent>
            <div className={styles.header}>
              <h1 className={styles.title}>Welcome Back</h1>
              <p className={styles.subtitle}>
                Sign in to continue your journey of joy
              </p>
            </div>

            <form onSubmit={handleSubmit} className={styles.form}>
              <Input
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                icon={<Mail size={18} />}
                required
                error={error && !email ? 'Email is required' : undefined}
              />

              <Input
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                icon={<Lock size={18} />}
                required
                error={error && !password ? 'Password is required' : undefined}
              />

              {error && (
                <motion.p 
                  className={styles.error}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  {error}
                </motion.p>
              )}

              <div className={styles.forgotPassword}>
                <Link to="/forgot-password">Forgot your password?</Link>
              </div>

              <Button
                type="submit"
                variant="whimsical"
                size="lg"
                fullWidth
                isLoading={isLoading}
                icon={<ArrowRight size={18} />}
                iconPosition="right"
              >
                Sign In
              </Button>
            </form>

            <div className={styles.divider}>
              <span>or</span>
            </div>

            <div className={styles.socialButtons}>
              <Button variant="secondary" size="md" fullWidth>
                Continue with Google
              </Button>
            </div>

            <p className={styles.signupPrompt}>
              New to Dandori?{' '}
              <Link to="/signup" className={styles.signupLink}>
                Create an account
              </Link>
            </p>
          </CardContent>
        </Card>

        <p className={styles.footer}>
          By signing in, you agree to our{' '}
          <Link to="/terms">Terms of Service</Link> and{' '}
          <Link to="/privacy">Privacy Policy</Link>
        </p>
      </motion.div>

      {/* Decorative elements */}
      <div className={styles.decorations} aria-hidden="true">
        <div className={styles.floatingLeaf1} />
        <div className={styles.floatingLeaf2} />
        <div className={styles.floatingCircle1} />
        <div className={styles.floatingCircle2} />
      </div>
    </div>
  );
}
