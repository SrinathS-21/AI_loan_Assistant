import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import PersonalDetails from './pages/PersonalDetails';
import ChatPage from './pages/ChatPage';
import CommunityPage from './pages/CommunityPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import ProfileSetupPage from './pages/ProfileSetupPage';
import ProtectedRoute from './pages/ProtectedRoute';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/personal-details" element={<ProtectedRoute><PersonalDetails /></ProtectedRoute>} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/community" element={<ProtectedRoute><CommunityPage/></ProtectedRoute>}/>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/profile-setup" element={<ProfileSetupPage />} />
      </Routes>
    </Router>
  );
}

export default App;