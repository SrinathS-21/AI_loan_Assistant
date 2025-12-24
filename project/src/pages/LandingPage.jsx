import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MessageCircle, Users, UserCircle, X, Globe } from 'lucide-react';

function LandingPage() {
  const navigate = useNavigate();
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));

  useEffect(() => {
    setIsAuthenticated(!!localStorage.getItem('token'));
  }, []);

  const handleGetStarted = () => {
    if (!isAuthenticated) {
      setIsAuthModalOpen(true);
    } else {
      navigate('/chat');
    }
  };

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const url = isLogin ? '/api/login' : '/api/register';
      const response = await fetch(`http://localhost:5001${url}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...(isLogin ? { email: formData.email, password: formData.password } : formData),
        }),
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('token', data.token);
        setIsAuthenticated(true);
        setIsAuthModalOpen(false);
        if (data.user.profileCompleted) {
          navigate('/chat');
        } else {
          navigate('/profile-setup');
        }
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError('Server error');
    }
  };

  const handleLogout = () => {
    setIsLogoutModalOpen(true);
  };

  const confirmLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setIsLogoutModalOpen(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex flex-col">
      <nav className="bg-white/80 backdrop-blur-sm sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="text-3xl font-bold bg-gradient-to-r from-cyan-500 to-blue-600 bg-clip-text text-transparent">
            Loan Advisor
          </div>
          <div className="flex items-center gap-6">
            <button className="btn btn-ghost text-gray-600 hover:text-gray-900 flex items-center gap-2 transition-colors duration-200">
              <Globe className="text-cyan-500" size={20} />
              English
            </button>
            <button
              className="btn bg-gradient-to-r from-cyan-500 to-blue-600 text-white border-none hover:shadow-lg hover:opacity-90 rounded-full px-8 py-2 transition-all duration-200 transform hover:scale-105"
              onClick={handleGetStarted}
            >
              Get Started
            </button>
            <button
              className="text-gray-600 hover:text-cyan-500 transition-colors duration-200 p-2 hover:bg-gray-100 rounded-full"
              onClick={handleLogout}
            >
              <UserCircle size={28} />
            </button>
          </div>
        </div>
      </nav>

      <div className="flex-1 flex items-center justify-center p-6 animate-fade-in-up">
        <div className="container max-w-7xl mx-auto px-4">
          <div className="text-center mb-16 space-y-6">
            <h1 className="text-5xl md:text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-600 to-blue-600 mb-6 leading-tight animate-fade-in-down">
              Your AI-Powered Loan Assistant
            </h1>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto leading-relaxed animate-fade-in-up">
              Simplify your financial journey with personalized loan advice, eligibility checks, and multilingual support.
            </p>
            <div className="mt-8 flex justify-center gap-4">
              <button onClick={handleGetStarted} className="px-8 py-3 text-lg font-semibold text-white bg-gradient-to-r from-cyan-500 to-blue-600 rounded-full hover:shadow-lg transform hover:scale-105 transition-all duration-200">
                Get Started Now
              </button>
              <button onClick={() => navigate('/community')} className="px-8 py-3 text-lg font-semibold text-gray-700 bg-white border-2 border-gray-200 rounded-full hover:border-cyan-500 hover:text-cyan-600 transform hover:scale-105 transition-all duration-200">
                Join Community
              </button>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto px-4">
            <div className="bg-white/80 backdrop-blur-lg rounded-2xl shadow-xl hover:shadow-2xl flex-1 p-8 border border-gray-100/20 group hover:-translate-y-1 transition-all duration-300">
              <div className="text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-cyan-100 to-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-6 transform rotate-3 hover:rotate-6 transition-transform duration-300">
                  <MessageCircle size={32} className="text-cyan-500" />
                </div>
                <h3 className="text-xl font-bold text-gray-800 group-hover:text-cyan-600 transition-colors duration-200">Chat with Advisor</h3>
                <button
                  className="btn bg-gradient-to-r from-cyan-500 to-blue-600 text-white border-none hover:shadow-lg hover:opacity-90 rounded-full px-8 py-3 mb-8 transition-all duration-200 transform hover:scale-105 w-full"
                  onClick={handleGetStarted}
                >
                  Start Chat
                </button>
                <div className="text-left space-y-4">
                  <p className="flex items-center gap-3 text-sm text-gray-600 hover:text-cyan-600 transition-all duration-200 p-2 rounded-lg hover:bg-cyan-50 cursor-pointer group">
                    <span className="w-3 h-3 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full group-hover:scale-125 transition-transform duration-200"></span>
                    <span className="group-hover:translate-x-1 transition-transform duration-200">Talk in your native language</span>
                  </p>
                  <p className="flex items-center gap-3 text-sm text-gray-600 hover:text-cyan-600 transition-all duration-200 p-2 rounded-lg hover:bg-cyan-50 cursor-pointer group">
                    <span className="w-3 h-3 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full group-hover:scale-125 transition-transform duration-200"></span>
                    <span className="group-hover:translate-x-1 transition-transform duration-200">Get loan eligibility checks</span>
                  </p>
                  <p className="flex items-center gap-3 text-sm text-gray-600 hover:text-cyan-600 transition-all duration-200 p-2 rounded-lg hover:bg-cyan-50 cursor-pointer group">
                    <span className="w-3 h-3 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full group-hover:scale-125 transition-transform duration-200"></span>
                    <span className="group-hover:translate-x-1 transition-transform duration-200">Receive financial tips</span>
                  </p>
                  <p className="flex items-center gap-3 text-sm text-gray-600 hover:text-cyan-600 transition-all duration-200 p-2 rounded-lg hover:bg-cyan-50 cursor-pointer group">
                    <span className="w-3 h-3 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full group-hover:scale-125 transition-transform duration-200"></span>
                    <span className="group-hover:translate-x-1 transition-transform duration-200">Voice or text interaction</span>
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white/80 backdrop-blur-lg rounded-2xl shadow-xl hover:shadow-2xl flex-1 p-8 border border-gray-100/20 group hover:-translate-y-1 transition-all duration-300">
              <div className="text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-cyan-100 to-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-6 transform -rotate-3 hover:-rotate-6 transition-transform duration-300">
                  <Users size={32} className="text-cyan-500" />
                </div>
                <h3 className="text-xl font-bold text-gray-800 group-hover:text-cyan-600 transition-colors duration-200">Join Community</h3>
                <button
                  className="btn bg-gradient-to-r from-cyan-500 to-blue-600 text-white border-none hover:shadow-lg hover:opacity-90 rounded-full px-8 py-3 mb-8 transition-all duration-200 transform hover:scale-105 w-full"
                  onClick={() => navigate('/community')}
                >
                  Join Now
                </button>
                <div className="text-left space-y-4">
                  <p className="flex items-center gap-3 text-sm text-gray-600 hover:text-cyan-600 transition-all duration-200 p-2 rounded-lg hover:bg-cyan-50 cursor-pointer group">
                    <span className="w-3 h-3 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full group-hover:scale-125 transition-transform duration-200"></span>
                    <span className="group-hover:translate-x-1 transition-transform duration-200">Learn from others</span>
                  </p>
                  <p className="flex items-center gap-3 text-sm text-gray-600 hover:text-cyan-600 transition-all duration-200 p-2 rounded-lg hover:bg-cyan-50 cursor-pointer group">
                    <span className="w-3 h-3 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full group-hover:scale-125 transition-transform duration-200"></span>
                    <span className="group-hover:translate-x-1 transition-transform duration-200">Share experiences</span>
                  </p>
                  <p className="flex items-center gap-3 text-sm text-gray-600 hover:text-cyan-600 transition-all duration-200 p-2 rounded-lg hover:bg-cyan-50 cursor-pointer group">
                    <span className="w-3 h-3 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full group-hover:scale-125 transition-transform duration-200"></span>
                    <span className="group-hover:translate-x-1 transition-transform duration-200">Access gamified learning</span>
                  </p>
                  <p className="flex items-center gap-3 text-sm text-gray-600 hover:text-cyan-600 transition-all duration-200 p-2 rounded-lg hover:bg-cyan-50 cursor-pointer group">
                    <span className="w-3 h-3 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full group-hover:scale-125 transition-transform duration-200"></span>
                    <span className="group-hover:translate-x-1 transition-transform duration-200">Earn rewards</span>
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white/80 backdrop-blur-lg rounded-2xl shadow-xl hover:shadow-2xl flex-1 p-8 border border-gray-100/20 group hover:-translate-y-1 transition-all duration-300">
              <div className="text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-cyan-100 to-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-6 transform rotate-3 hover:rotate-6 transition-transform duration-300">
                  <UserCircle size={32} className="text-cyan-500" />
                </div>
                <h3 className="text-xl font-bold text-gray-800 group-hover:text-cyan-600 transition-colors duration-200">My Profile</h3>
                <button
                  className="btn bg-gradient-to-r from-cyan-500 to-blue-600 text-white border-none hover:shadow-lg hover:opacity-90 rounded-full px-8 py-3 mb-8 transition-all duration-200 transform hover:scale-105 w-full"
                  onClick={() => navigate('/personal-details')}
                >
                  View Profile
                </button>
                <div className="text-left space-y-4">
                  <p className="flex items-center gap-3 text-sm text-gray-600 hover:text-cyan-600 transition-all duration-200 p-2 rounded-lg hover:bg-cyan-50 cursor-pointer group">
                    <span className="w-3 h-3 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full group-hover:scale-125 transition-transform duration-200"></span>
                    <span className="group-hover:translate-x-1 transition-transform duration-200">Manage financial data</span>
                  </p>
                  <p className="flex items-center gap-3 text-sm text-gray-600 hover:text-cyan-600 transition-all duration-200 p-2 rounded-lg hover:bg-cyan-50 cursor-pointer group">
                    <span className="w-3 h-3 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full group-hover:scale-125 transition-transform duration-200"></span>
                    <span className="group-hover:translate-x-1 transition-transform duration-200">Track loan applications</span>
                  </p>
                  <p className="flex items-center gap-3 text-sm text-gray-600 hover:text-cyan-600 transition-all duration-200 p-2 rounded-lg hover:bg-cyan-50 cursor-pointer group">
                    <span className="w-3 h-3 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full group-hover:scale-125 transition-transform duration-200"></span>
                    <span className="group-hover:translate-x-1 transition-transform duration-200">View visualizations</span>
                  </p>
                  <p className="flex items-center gap-3 text-sm text-gray-600 hover:text-cyan-600 transition-all duration-200 p-2 rounded-lg hover:bg-cyan-50 cursor-pointer group">
                    <span className="w-3 h-3 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full group-hover:scale-125 transition-transform duration-200"></span>
                    <span className="group-hover:translate-x-1 transition-transform duration-200">Get predictive insights</span>
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="text-center mt-12">
            <p className="text-gray-600 text-sm">
              Powered by AI for financial inclusion and empowerment
            </p>
          </div>
        </div>
      </div>

      {isAuthModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-8 max-w-md w-full shadow-lg">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-semibold text-gray-900">
                {isLogin ? 'Log In' : 'Sign Up'}
              </h3>
              <button
                className="text-gray-500 hover:text-gray-700"
                onClick={() => setIsAuthModalOpen(false)}
              >
                <X size={24} />
              </button>
            </div>
            {error && <p className="text-red-500 mb-4">{error}</p>}
            <form onSubmit={handleSubmit} className="space-y-4">
              {!isLogin && (
                <div>
                  <label className="block text-gray-700 mb-1">Full Name</label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="Enter your full name"
                    className="input input-bordered w-full bg-gray-50 border-gray-300 focus:border-cyan-500 focus:ring-0 rounded-xl"
                  />
                </div>
              )}
              <div>
                <label className="block text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  placeholder="Enter your email"
                  className="input input-bordered w-full bg-gray-50 border-gray-300 focus:border-cyan-500 focus:ring-0 rounded-xl"
                />
              </div>
              <div>
                <label className="block text-gray-700 mb-1">Password</label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  placeholder="Enter your password"
                  className="input input-bordered w-full bg-gray-50 border-gray-300 focus:border-cyan-500 focus:ring-0 rounded-xl"
                />
              </div>
              <button
                type="submit"
                className="btn bg-cyan-500 text-white border-none hover:bg-cyan-600 w-full rounded-full"
              >
                {isLogin ? 'Log In' : 'Sign Up'}
              </button>
            </form>
            <p className="text-center text-gray-600 mt-4">
              {isLogin ? "Don't have an account?" : "Already have an account?"}{' '}
              <button
                className="text-cyan-500 hover:underline"
                onClick={() => {
                  setIsLogin(!isLogin);
                  setError('');
                }}
              >
                {isLogin ? 'Sign Up' : 'Log In'}
              </button>
            </p>
          </div>
        </div>
      )}

      {isLogoutModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-sm w-full shadow-lg">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Confirm Logout</h3>
              <button
                className="text-gray-500 hover:text-gray-700"
                onClick={() => setIsLogoutModalOpen(false)}
              >
                <X size={20} />
              </button>
            </div>
            <p className="text-gray-600 mb-6">Are you sure you want to log out?</p>
            <div className="flex justify-end gap-4">
              <button
                className="btn btn-outline border-gray-300 text-gray-700 hover:bg-gray-100 rounded-full"
                onClick={() => setIsLogoutModalOpen(false)}
              >
                Cancel
              </button>
              <button
                className="btn bg-cyan-500 text-white border-none hover:bg-cyan-600 rounded-full"
                onClick={confirmLogout}
              >
                Log Out
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default LandingPage;