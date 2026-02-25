import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  Send, 
  Maximize2, 
  Minimize2, 
  Sparkles,
  Bot,
  User,
  Loader2
} from 'lucide-react';
import { useChatStore } from '../../stores/useStore';
import { chatApi } from '../../services/api';
import { Button, Avatar } from '../ui';
import CourseArtifact from './CourseArtifact';
import styles from './ChatPanel.module.css';

const panelVariants = {
  hidden: { 
    x: '100%',
    opacity: 0,
  },
  visible: { 
    x: 0,
    opacity: 1,
    transition: {
      type: 'spring',
      stiffness: 300,
      damping: 30,
    }
  },
  exit: {
    x: '100%',
    opacity: 0,
    transition: { duration: 0.2 }
  }
};

const messageVariants = {
  hidden: { opacity: 0, y: 10, scale: 0.95 },
  visible: { 
    opacity: 1, 
    y: 0, 
    scale: 1,
    transition: { type: 'spring', stiffness: 300, damping: 25 }
  },
};

export default function ChatPanel() {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  
  const { 
    isOpen, 
    closeChat, 
    isFullPage, 
    setFullPage,
    messages, 
    addMessage, 
    isLoading, 
    setLoading,
    artifacts,
    addArtifact,
  } = useChatStore();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    
    addMessage({ role: 'user', content: userMessage });
    setLoading(true);

    try {
      const response = await chatApi.sendMessage(userMessage, messages);
      
      addMessage({ role: 'assistant', content: response.message });
      
      if (response.artifacts) {
        response.artifacts.forEach(artifact => {
          addArtifact(artifact);
        });
      }
    } catch (error) {
      addMessage({ 
        role: 'assistant', 
        content: 'I apologize, but I encountered an issue. Please try again.',
        isError: true 
      });
    } finally {
      setLoading(false);
    }
  };

  const suggestedPrompts = [
    "Find me a relaxing weekend class",
    "What pottery courses are available?",
    "Show me classes under £50",
    "Recommend something creative for beginners",
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            className={styles.backdrop}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeChat}
          />
          
          <motion.div
            className={`${styles.panel} ${isFullPage ? styles.fullPage : ''}`}
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <header className={styles.header}>
              <div className={styles.headerLeft}>
                <div className={styles.botAvatar}>
                  <Sparkles size={20} />
                </div>
                <div className={styles.headerText}>
                  <h2 className={styles.headerTitle}>Dandori Assistant</h2>
                  <span className={styles.headerStatus}>
                    <span className={styles.statusDot} />
                    Ready to help
                  </span>
                </div>
              </div>
              
              <div className={styles.headerActions}>
                <button
                  className={styles.iconButton}
                  onClick={() => setFullPage(!isFullPage)}
                  aria-label={isFullPage ? 'Minimize' : 'Maximize'}
                >
                  {isFullPage ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
                </button>
                <button
                  className={styles.iconButton}
                  onClick={closeChat}
                  aria-label="Close chat"
                >
                  <X size={18} />
                </button>
              </div>
            </header>

            <div className={styles.content}>
              <div className={styles.messagesContainer}>
                {messages.length === 0 ? (
                  <div className={styles.welcome}>
                    <div className={styles.welcomeIcon}>
                      <Sparkles size={40} />
                    </div>
                    <h3 className={styles.welcomeTitle}>
                      Welcome to Dandori
                    </h3>
                    <p className={styles.welcomeText}>
                      I'm here to help you discover the perfect course for your journey of joy and wellbeing. Ask me anything!
                    </p>
                    
                    <div className={styles.suggestions}>
                      {suggestedPrompts.map((prompt, index) => (
                        <motion.button
                          key={index}
                          className={styles.suggestionChip}
                          onClick={() => setInput(prompt)}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.1 * index }}
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                        >
                          {prompt}
                        </motion.button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className={styles.messages}>
                    {messages.map((message, index) => (
                      <motion.div
                        key={message.id || index}
                        className={`${styles.message} ${styles[message.role]}`}
                        variants={messageVariants}
                        initial="hidden"
                        animate="visible"
                      >
                        <div className={styles.messageAvatar}>
                          {message.role === 'user' ? (
                            <Avatar name="You" size="sm" />
                          ) : (
                            <div className={styles.botMessageAvatar}>
                              <Bot size={16} />
                            </div>
                          )}
                        </div>
                        <div className={`${styles.messageBubble} ${message.isError ? styles.error : ''}`}>
                          <p className={styles.messageContent}>{message.content}</p>
                          <span className={styles.messageTime}>
                            {new Date(message.timestamp).toLocaleTimeString([], { 
                              hour: '2-digit', 
                              minute: '2-digit' 
                            })}
                          </span>
                        </div>
                      </motion.div>
                    ))}
                    
                    {isLoading && (
                      <motion.div
                        className={`${styles.message} ${styles.assistant}`}
                        variants={messageVariants}
                        initial="hidden"
                        animate="visible"
                      >
                        <div className={styles.messageAvatar}>
                          <div className={styles.botMessageAvatar}>
                            <Bot size={16} />
                          </div>
                        </div>
                        <div className={styles.messageBubble}>
                          <div className={styles.typingIndicator}>
                            <span />
                            <span />
                            <span />
                          </div>
                        </div>
                      </motion.div>
                    )}
                    
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </div>

              {artifacts.length > 0 && (
                <div className={styles.artifactsPanel}>
                  <h4 className={styles.artifactsTitle}>Recommended Courses</h4>
                  <div className={styles.artifactsList}>
                    {artifacts.map((artifact) => (
                      <CourseArtifact key={artifact.id} course={artifact} />
                    ))}
                  </div>
                </div>
              )}
            </div>

            <form className={styles.inputForm} onSubmit={handleSubmit}>
              <div className={styles.inputWrapper}>
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask about courses, locations, or your interests..."
                  className={styles.input}
                  disabled={isLoading}
                />
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={!input.trim() || isLoading}
                  icon={isLoading ? <Loader2 className={styles.spinner} size={16} /> : <Send size={16} />}
                >
                  Send
                </Button>
              </div>
              <p className={styles.inputHint}>
                Powered by Dandori AI • Your personal course discovery assistant
              </p>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
