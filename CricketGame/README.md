# Cricket Game Application

A full-stack cricket game application built with FastAPI (backend) and React/Vite (frontend).

## Features
- 🎮 **Multiplayer Modes**: 1v1, 2v2, and Tournament formats
- 📊 **Player Profiles**: Track your stats across different game formats
- 🏆 **Statistics Tracking**: Batting, bowling, and match records
- 🌐 **LAN Support**: Play with friends on the same network
- ⚡ **Real-time Gameplay**: WebSocket-powered live matches

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, WebSockets
- **Frontend**: Node.js 20+, React, TypeScript, Vite
- **Database**: SQLite (local `cricket.db`)

---

## Installation

### Clone the Repository
```bash
git clone https://github.com/username/cricket-game.git
cd cricket-game
```

---

## Backend Setup (MANDATORY)

⚠️ **IMPORTANT:** You must use a virtual environment.

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv backend_venv
   ```

3. **Activate the environment (REQUIRED):**
   - **Windows:**
     ```cmd
     backend_venv\Scripts\activate
     ```
   - **Mac/Linux:**
     ```bash
     source backend_venv/bin/activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the backend server:**
   ```bash
    THEN
   .\backend\backend_venv\Scripts\activate ; python -m backend.main
   ```
   The backend will be available at `http://localhost:8000`.

---

## Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd ../frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```
   The frontend will be available at `http://localhost:5173` (or similar).

---

## Environment Variables

- Copy `.env.example` in the `backend` folder to `.env` and configure if necessary.
- Frontend environment variables are managed via Vite (prefix `VITE_`).

---

## Notes
- **ALWAYS use the virtual environment for Python.**
- Do not commit `backend_venv`, `node_modules`, or `.env` files.
- The SQLite database `cricket.db` is ignored by git; it will be created automatically on first run.

---

## Playing with Friends (LAN)

To allow friends on the same WiFi/network to join your game:

1. **Find your local IP address:**
   - **Windows**: Open Command Prompt and run `ipconfig`, look for `IPv4 Address` (usually `192.168.x.x`)
   - **Mac/Linux**: Run `ifconfig` or `ip addr`, look for your local network IP

2. **Share the correct link:**
   - Instead of `http://localhost:5173/room/ABCD123`
   - Share `http://YOUR_IP:5173/room/ABCD123` (e.g., `http://192.168.1.100:5173/room/ABCD123`)

3. **Ensure firewall allows connections:**
   - Windows: Allow Python and Node through Windows Firewall
   - Mac: System Settings → Network → Firewall (allow incoming connections)

