import { Routes, Route, Navigate } from 'react-router-dom'
import { useState } from 'react'
import LoginPage from './pages/LoginPage'
import RoomPage from './pages/RoomPage'
import ProfilePage from './pages/ProfilePage'
import MatchDetailPage from './pages/MatchDetailPage'
import TournamentDetailPage from './pages/TournamentDetailPage'

function App() {
  const [token, setToken] = useState<string>(sessionStorage.getItem('token') ?? '')
  const [username, setUsername] = useState<string>(sessionStorage.getItem('username') ?? '')

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
    return <LoginPage onAuth={handleAuth} />
  }

  return (
    <div className="dark min-h-screen">
      <Routes>
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

