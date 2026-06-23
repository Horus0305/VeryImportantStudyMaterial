import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import LoginPage from './pages/LoginPage'
import AuthPage from './pages/AuthPage'
import RoomPage from './pages/RoomPage'
import ProfilePage from './pages/ProfilePage'
import MatchDetailPage from './pages/MatchDetailPage'
import TournamentDetailPage from './pages/TournamentDetailPage'
import LeaderboardPage from './pages/LeaderboardPage'

function AuthenticatedLoginRedirect() {
  const redirectTo = sessionStorage.getItem('redirectTo') ?? '/'
  useEffect(() => {
    sessionStorage.removeItem('redirectTo')
  }, [])
  return <Navigate to={redirectTo} replace />
}

function App() {
  const navigate = useNavigate()
  const [token, setToken] = useState<string>(sessionStorage.getItem('token') ?? '')
  const [username, setUsername] = useState<string>(sessionStorage.getItem('username') ?? '')

  useEffect(() => {
    if (!token) {
      const path = window.location.pathname
      if (path !== '/' && path !== '/login') {
        sessionStorage.setItem('redirectTo', path)
      }
    }
  }, [token])

  const handleAuth = (newToken: string, newUsername: string) => {
    setToken(newToken)
    setUsername(newUsername)
    sessionStorage.setItem('token', newToken)
    sessionStorage.setItem('username', newUsername)
  }

  const handleRename = (newToken: string, newUsername: string) => {
    handleAuth(newToken, newUsername)
  }

  const handleLogout = () => {
    setToken('')
    setUsername('')
    sessionStorage.clear()
  }

  if (!token) {
    return (
      <Routes>
        <Route path="/login" element={<AuthPage onAuth={handleAuth} />} />
        <Route path="*" element={<LoginPage />} />
      </Routes>
    )
  }

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-primary/20">
      <Routes>
        <Route path="/login" element={<AuthenticatedLoginRedirect />} />
        <Route path="/leaderboard" element={
          <LeaderboardPage username={username} />
        } />
        <Route path="/profile" element={
          <ProfilePage token={token} username={username} onLogout={handleLogout} onRename={handleRename} />
        } />
        <Route path="/match/:matchId" element={
          <MatchDetailPage />
        } />
        <Route path="/tournament/:tournamentId" element={
          <TournamentDetailPage />
        } />
        <Route path="/room/:roomCode" element={
          <RoomPage token={token} username={username} onLogout={handleLogout} />
        } />
        <Route path="/" element={
          <RoomPage token={token} username={username} onLogout={handleLogout} />
        } />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </div>
  )
}

export default App
