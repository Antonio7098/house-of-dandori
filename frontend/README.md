# School of Dandori - Frontend

A whimsical, production-grade React frontend for the School of Dandori course platform.

## Design Philosophy

**Aesthetic**: *Nostalgic Whimsy meets Modern Craft* — Warm, inviting palette inspired by vintage botanical illustrations, evening candlelight, and playful wonder.

- **Typography**: Fraunces (display) + Crimson Pro (body)
- **Colors**: Forest greens, terracotta accents, cream backgrounds, golden honey highlights
- **Motion**: Gentle floating animations, spring-based interactions

## Tech Stack

- **Framework**: React 19 + Vite
- **Routing**: React Router DOM
- **State**: Zustand (global state) + React Query (server state)
- **Animations**: Framer Motion
- **Icons**: Lucide React
- **Styling**: CSS Modules with CSS Variables

## Project Structure

```
src/
├── components/
│   ├── ui/          # Reusable UI components (Button, Card, Input, etc.)
│   ├── layout/      # Layout components (Header, Sidebar, PageLayout)
│   ├── chat/        # Chatbot components
│   ├── courses/     # Course-related components
│   └── search/      # Search components
├── pages/           # Page components
├── context/         # React contexts (Theme)
├── stores/          # Zustand stores
├── services/        # API services
└── styles/          # Global styles and theme
```

## Getting Started

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Start development server
npm run dev

# Build for production
npm run build
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:5000` |

## Features

- **Vibe Search**: AI-powered semantic course search
- **Chatbot**: Side panel assistant with course recommendations
- **Course Discovery**: Browse, filter, and save courses
- **User Profiles**: Save courses, write reviews, track progress
- **Dark Mode**: Full theme support
- **Responsive**: Mobile-first design

## Component Architecture

All components are theme-controlled via CSS variables defined in `src/styles/theme.css`. Components use CSS Modules for scoped styling with consistent naming conventions.

### UI Components
- `Button` - Multiple variants (primary, secondary, accent, whimsical, ghost, outline)
- `Card` - Flexible card with header, content, footer, image support
- `Input` - Form input with validation states
- `Modal` - Accessible modal dialogs
- `Rating` - Star rating component
- `Badge` - Status and category badges
- `Avatar` - User avatars with fallback initials
