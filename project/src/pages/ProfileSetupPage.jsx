import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';

function ProfileSetupPage() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    dateOfBirth: '',
    gender: '',
    maritalStatus: '',
    contactNumber: '',
    residentialAddressCurrent: '',
    residentialAddressPermanent: '',
    nationality: ''
  });
  const [error, setError] = useState('');

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5001/api/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(formData)
      });
      const data = await response.json();
      if (response.ok) {
        navigate('/');  // Changed from '/chat' to '/'
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError('Server error');
    }
  };

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-xl shadow-sm p-8">
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => navigate('/')}
            className="btn btn-ghost text-gray-600 gap-2 hover:bg-gray-100 transition"
          >
            <ChevronLeft size={24} />
            <span className="text-lg font-semibold">Back</span>
          </button>
          <h2 className="text-2xl font-semibold text-gray-900">Complete Your Profile</h2>
          <div></div>
        </div>
        {error && <p className="text-red-500 mb-4">{error}</p>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-gray-700 mb-1">Date of Birth</label>
            <input
              type="date"
              name="dateOfBirth"
              value={formData.dateOfBirth}
              onChange={handleInputChange}
              className="input input-bordered w-full bg-gray-50 border-gray-300 focus:border-cyan-500 focus:ring-0 rounded-xl"
              required
            />
          </div>
          <div>
            <label className="block text-gray-700 mb-1">Gender</label>
            <select
              name="gender"
              value={formData.gender}
              onChange={handleInputChange}
              className="select select-bordered w-full bg-gray-50 border-gray-300 focus:border-cyan-500 focus:ring-0 rounded-xl"
              required
            >
              <option value="">Select Gender</option>
              <option value="Male">Male</option>
              <option value="Female">Female</option>
              <option value="Other">Other</option>
            </select>
          </div>
          <div>
            <label className="block text-gray-700 mb-1">Marital Status</label>
            <select
              name="maritalStatus"
              value={formData.maritalStatus}
              onChange={handleInputChange}
              className="select select-bordered w-full bg-gray-50 border-gray-300 focus:border-cyan-500 focus:ring-0 rounded-xl"
              required
            >
              <option value="">Select Marital Status</option>
              <option value="Single">Single</option>
              <option value="Married">Married</option>
              <option value="Divorced">Divorced</option>
              <option value="Widowed">Widowed</option>
            </select>
          </div>
          <div>
            <label className="block text-gray-700 mb-1">Contact Number</label>
            <input
              type="tel"
              name="contactNumber"
              value={formData.contactNumber}
              onChange={handleInputChange}
              placeholder="Enter your contact number"
              className="input input-bordered w-full bg-gray-50 border-gray-300 focus:border-cyan-500 focus:ring-0 rounded-xl"
              required
            />
          </div>
          <div>
            <label className="block text-gray-700 mb-1">Current Residential Address</label>
            <textarea
              name="residentialAddressCurrent"
              value={formData.residentialAddressCurrent}
              onChange={handleInputChange}
              placeholder="Enter your current residential address"
              className="textarea textarea-bordered w-full bg-gray-50 border-gray-300 focus:border-cyan-500 focus:ring-0 rounded-xl"
              rows={3}
              required
            />
          </div>
          <div>
            <label className="block text-gray-700 mb-1">Permanent Residential Address</label>
            <textarea
              name="residentialAddressPermanent"
              value={formData.residentialAddressPermanent}
              onChange={handleInputChange}
              placeholder="Enter your permanent residential address"
              className="textarea textarea-bordered w-full bg-gray-50 border-gray-300 focus:border-cyan-500 focus:ring-0 rounded-xl"
              rows={3}
              required
            />
          </div>
          <div>
            <label className="block text-gray-700 mb-1">Nationality</label>
            <input
              type="text"
              name="nationality"
              value={formData.nationality}
              onChange={handleInputChange}
              placeholder="Enter your nationality"
              className="input input-bordered w-full bg-gray-50 border-gray-300 focus:border-cyan-500 focus:ring-0 rounded-xl"
              required
            />
          </div>
          <button
            type="submit"
            className="btn bg-cyan-500 text-white border-none hover:bg-cyan-600 w-full rounded-full"
          >
            Save and Continue
          </button>
        </form>
      </div>
    </div>
  );
}

export default ProfileSetupPage;