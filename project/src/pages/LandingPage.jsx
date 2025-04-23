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
    <div className="min-h-screen bg-white flex flex-col">
      <div className="bg-white">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="text-2xl font-semibold text-cyan-500">
            Loan Advisor
          </div>
          <div className="flex items-center gap-4">
            <button className="btn btn-ghost text-gray-600 hover:text-gray-900 flex items-center gap-2">
              <Globe size={20} />
              English
            </button>
            <button
              className="btn bg-cyan-500 text-white border-none hover:bg-cyan-600 rounded-full px-6"
              onClick={handleGetStarted}
            >
              Get Started
            </button>
            <button
              className="text-gray-600 hover:text-cyan-500 transition"
              onClick={handleLogout}
            >
              <UserCircle size={28} />
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-6">
        <div className="container max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Your AI-Powered Loan Assistant
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Simplify your financial journey with personalized loan advice, eligibility checks, and multilingual support.
            </p>
          </div>

          <div className="flex flex-col md:flex-row gap-8 justify-center">
            <div className="bg-gray-50 rounded-xl shadow-lg flex-1 p-6 border-2 border-gray-200 hover:bg-cyan-50 hover:border-cyan-500 transition-all duration-300">
              <div className="text-center">
                <div className="w-12 h-12 bg-cyan-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <MessageCircle size={24} className="text-cyan-500" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Chat with Advisor</h3>
                <button
                  className="btn bg-cyan-500 text-white border-none hover:bg-cyan-600 rounded-full px-6 mb-6"
                  onClick={handleGetStarted}
                >
                  Start Chat
                </button>
                <div className="text-left space-y-3">
                  <p className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="w-2 h-2 bg-cyan-500 rounded-full"></span>
                    Talk in your native language
                  </p>
                  <p className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="w-2 h-2 bg-cyan-500 rounded-full"></span>
                    Get loan eligibility checks
                  </p>
                  <p className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="w-2 h-2 bg-cyan-500 rounded-full"></span>
                    Receive financial tips
                  </p>
                  <p className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="w-2 h-2 bg-cyan-500 rounded-full"></span>
                    Voice or text interaction
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-gray-50 rounded-xl shadow-lg flex-1 p-6 border-2 border-gray-200 hover:bg-cyan-50 hover:border-cyan-500 transition-all duration-300">
              <div className="text-center">
                <div className="w-12 h-12 bg-cyan-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Users size={24} className="text-cyan-500" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Join Community</h3>
                <button
                  className="btn bg-cyan-500 text-white border-none hover:bg-cyan-600 rounded-full px-6 mb-6"
                  onClick={() => navigate('/community')}
                >
                  Join Now
                </button>
                <div className="text-left space-y-3">
                  <p className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="w-2 h-2 bg-cyan-500 rounded-full"></span>
                    Learn from others
                  </p>
                  <p className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="w-2 h-2 bg-cyan-500 rounded-full"></span>
                    Share experiences
                  </p>
                  <p className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="w-2 h-2 bg-cyan-500 rounded-full"></span>
                    Access gamified learning
                  </p>
                  <p className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="w-2 h-2 bg-cyan-500 rounded-full"></span>
                    Earn rewards
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-gray-50 rounded-xl shadow-lg flex-1 p-6 border-2 border-gray-200 hover:bg-cyan-50 hover:border-cyan-500 transition-all duration-300">
              <div className="text-center">
                <div className="w-12 h-12 bg-cyan-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <UserCircle size={24} className="text-cyan-500" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">My Profile</h3>
                <button
                  className="btn bg-cyan-500 text-white border-none hover:bg-cyan-600 rounded-full px-6 mb-6"
                  onClick={() => navigate('/personal-details')}
                >
                  View Profile
                </button>
                <div className="text-left space-y-3">
                  <p className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="w-2 h-2 bg-cyan-500 rounded-full"></span>
                    Manage financial data
                  </p>
                  <p className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="w-2 h-2 bg-cyan-500 rounded-full"></span>
                    Track loan applications
                  </p>
                  <p className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="w-2 h-2 bg-cyan-500 rounded-full"></span>
                    View visualizations
                  </p>
                  <p className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="w-2 h-2 bg-cyan-500 rounded-full"></span>
                    Get predictive insights
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