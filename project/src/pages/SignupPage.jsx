import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';

function SignupPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-xl shadow-sm p-8">
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => navigate('/')}
            className="btn btn-ghost text-gray-600"
          >
            <ChevronLeft size={24} />
            Back
          </button>
          <h2 className="text-2xl font-semibold text-gray-900">Sign Up</h2>
          <div></div>
        </div>
        <form className="space-y-4">
          <div>
            <label className="block text-gray-700 mb-1">Full Name</label>
            <input
              type="text"
              placeholder="Enter your full name"
              className="input input-bordered w-full bg-gray-50 border-gray-300 focus:border-cyan-500 focus:ring-0"
            />
          </div>
          <div>
            <label className="block text-gray-700 mb-1">Email</label>
            <input
              type="email"
              placeholder="Enter your email"
              className="input input-bordered w-full bg-gray-50 border-gray-300 focus:border-cyan-500 focus:ring-0"
            />
          </div>
          <div>
            <label className="block text-gray-700 mb-1">Password</label>
            <input
              type="password"
              placeholder="Create a password"
              className="input input-bordered w-full bg-gray-50 border-gray-300 focus:border-cyan-500 focus:ring-0"
            />
          </div>
          <button
            type="submit"
            className="btn bg-cyan-500 text-white border-none hover:bg-cyan-600 w-full"
          >
            Sign Up
          </button>
        </form>
        <p className="text-center text-gray-600 mt-4">
          Already have an account?{' '}
          <a href="/login" className="text-cyan-500 hover:underline">
            Log In
          </a>
        </p>
      </div>
    </div>
  );
}

export default SignupPage;