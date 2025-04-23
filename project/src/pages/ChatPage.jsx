import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Send, Lightbulb } from 'lucide-react';
import axios from 'axios';
import './ChatPage.css';

const suggestions = [
  "Check my loan eligibility",
  "Guide me through loan application",
  "Show me financial tips",
  "Explain loan terms in my language"
];

function ChatPage() {
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    {
      type: 'assistant',
      content: "Hello! I'm your Loan Advisor AI. How can I assist you with your financial journey today?"
    }
  ]);
  const [userDetails, setUserDetails] = useState('');

  useEffect(() => {
    const fetchUserDetails = async () => {
      try {
        const token = localStorage.getItem('token');
        const response = await axios.get('http://localhost:5001/api/user-details', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        setUserDetails(response.data.userDetails);
      } catch (error) {
        console.error('Error fetching user details:', error);
      }
    };
    fetchUserDetails();
  }, []);

  const handleSend = async () => {
    if (!input.trim()) return;

    setMessages([
      ...messages,
      { type: 'user', content: input },
      { type: 'assistant', content: 'Processing your request...' }
    ]);

    setInput('');

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post('http://localhost:5001/api/chat', {
        message: input
      }, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      setMessages(prev => [
        ...prev.slice(0, -1),
        { type: 'assistant', content: response.data.response }
      ]);
    } catch (error) {
      console.error('Error sending message to backend:', error);
      setMessages(prev => [
        ...prev.slice(0, -1),
        { type: 'assistant', content: 'Error connecting to the chat service. Please try again.' }
      ]);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <div className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <button
            onClick={() => navigate('/')}
            className="btn btn-ghost text-gray-600 gap-2 hover:bg-gray-100 transition"
          >
            <ChevronLeft size={24} className="text-gray-600" />
            <span className="text-lg font-semibold">Back to Home</span>
          </button>
        </div>
      </div>

      <div className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 flex flex-col">
        <div className="flex-1 space-y-6 mb-8 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-400 scrollbar-track-gray-100">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex animate-fade-in-up ${
                message.type === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`max-w-[70%] rounded-xl p-4 ${
                  message.type === 'user'
                    ? 'bg-indigo-500 text-white shadow-md shadow-gray-300'
                    : 'bg-gray-50 text-gray-900 shadow-md shadow-gray-200'
                }`}
              >
                {message.type === 'user' ? (
                  <p className="text-white">{message.content}</p>
                ) : (
                  <div dangerouslySetInnerHTML={{ __html: message.content }} />
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {suggestions.map((suggestion, index) => (
            <button
              key={index}
              className="btn btn-outline text-gray-700 border-gray-300 hover:bg-gray-100 hover:border-gray-400 gap-2 transition-all shadow-sm shadow-gray-200"
              onClick={() => setInput(suggestion)}
            >
              <Lightbulb size={16} className="text-yellow-500" />
              <span className="text-sm">{suggestion}</span>
            </button>
          ))}
        </div>

        <div className="bg-white rounded-xl shadow-lg shadow-gray-300 p-4 border border-gray-200">
          <div className="flex gap-4 items-center">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me anything about loans or finances..."
              className="flex-1 textarea bg-gray-50 text-gray-900 placeholder-gray-500 border-gray-300 focus:border-indigo-500 focus:ring-0 resize-none scrollbar-thin scrollbar-thumb-gray-400 scrollbar-track-gray-100"
              rows={2}
            />
            <button
              className="btn btn-circle bg-indigo-500 hover:bg-indigo-600 text-white border-none"
              onClick={handleSend}
              disabled={!input.trim()}
            >
              <Send size={24} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChatPage;