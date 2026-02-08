NAS Frontend
============

Overview
--------
This is the Vite + React frontend for the NAS project. It provides a unified
security dashboard with pages for live traffic, detected attacks, blocked IPs,
and risk analytics. The UI includes real-time polling hooks and interactive
cursor/particle effects for a dynamic monitoring experience.

Tech Stack
----------
- React + Vite
- CSS modules and custom animation styles

Requirements
------------
- Node.js v18.0+ (recommended)
- npm (or compatible package manager)

Getting Started
--------------
1) Install dependencies:
	npm install

2) Run the dev server:
	npm run dev

3) Build for production:
	npm run build

4) Preview the production build:
	npm run preview

Project Structure
-----------------
- src/App.jsx: Root app shell and routing
- src/pages/: Main views (Dashboard, LiveTraffic, DetectedAttacks, etc.)
- src/components/: Reusable UI and visual effects components
- src/hooks/: Polling, cursor physics, and scroll animation hooks
- src/index.css: Global styles

Notes
-----
- The frontend expects the backend API to be available and reachable by the
  configured endpoints (see any API base URL setup in the app if present).

