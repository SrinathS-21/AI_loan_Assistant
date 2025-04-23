import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, PieChart, Pie, Cell } from 'recharts';
import { ChevronLeft, Plus, Trash2, Pencil } from 'lucide-react';
import axios from 'axios';

function PersonalDetails() {
  const navigate = useNavigate();
  const [formVisible, setFormVisible] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingExpenseId, setEditingExpenseId] = useState(null);
  const [formData, setFormData] = useState({
    income: '',
    expense: '',
    date: new Date().toISOString().split('T')[0],
    notes: '',
  });
  const [expenses, setExpenses] = useState([]);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [prediction, setPrediction] = useState(null);
  const [totalIncome, setTotalIncome] = useState(0);
  const [totalSavings, setTotalSavings] = useState(0);
  const [debtToIncomeRatio, setDebtToIncomeRatio] = useState(0);
  const [riskScore, setRiskScore] = useState(0);
  const [advice, setAdvice] = useState('');

  const API_BASE_URL = 'http://172.16.63.225:5001'; // Your backend URL

  useEffect(() => {
    const fetchExpenses = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          setError('Please log in to view your expenses.');
          navigate('/login');
          return;
        }
        const response = await axios.get(`${API_BASE_URL}/api/profile/expenses`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        console.log('Fetched expenses:', response.data);
        setExpenses(response.data);
        calculateFinancialMetrics(response.data);
      } catch (err) {
        if (err.response?.status === 401) {
          setError('Session expired. Please log in again.');
          localStorage.removeItem('token');
          navigate('/login');
        } else {
          setError('Failed to load expenses. Please try again later.');
        }
        console.error('Error fetching expenses:', err);
      }
    };
    fetchExpenses();
  }, [navigate]);

  const calculateFinancialMetrics = (expenseData) => {
    const totalIncomeValue = expenseData.reduce((sum, entry) => sum + (parseFloat(entry.income) || 0), 0);
    const totalExpense = expenseData.reduce((sum, entry) => sum + (parseFloat(entry.expense) || 0), 0);
    const totalSavingsValue = expenseData.reduce((sum, entry) => {
      const savings = (parseFloat(entry.income) || 0) - (parseFloat(entry.expense) || 0);
      return sum + Math.max(0, savings); // Ensure savings is not negative
    }, 0);
    const dti = totalIncomeValue > 0 ? (totalExpense / totalIncomeValue) * 100 : 0;
    const risk = Math.min(100, Math.max(0, Math.round(dti * 1.5 - (totalSavingsValue / totalIncomeValue) * 20)));

    setTotalIncome(totalIncomeValue);
    setTotalSavings(totalSavingsValue);
    setDebtToIncomeRatio(dti.toFixed(2));
    setRiskScore(risk);
    setAdvice(
      risk <= 30
        ? 'Your financial health is strong. It’s safe to consider a loan.'
        : risk <= 50
        ? 'Moderate risk detected. Proceed with caution for loans.'
        : 'High risk. Avoid taking a loan unless you improve your finances.'
    );
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    if (!formData.date || (!formData.income && !formData.expense)) {
      setError('Date and at least one of income or expense are required.');
      setIsSubmitting(false);
      return;
    }

    const savings = Math.max(0, parseFloat(formData.income) || 0 - parseFloat(formData.expense) || 0);
    const data = new FormData();
    data.append('income', formData.income || 0);
    data.append('expense', formData.expense || 0);
    data.append('savings', savings); // Send calculated savings to backend
    data.append('date', formData.date);
    data.append('notes', formData.notes || '');

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Please log in to add an expense.');
        navigate('/login');
        return;
      }

      if (isEditing) {
        const response = await axios.put(
          `${API_BASE_URL}/api/profile/expenses/${editingExpenseId}`,
          data,
          {
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/x-www-form-urlencoded' },
          }
        );

        const updatedExpense = {
          _id: editingExpenseId,
          income: parseFloat(formData.income) || 0,
          expense: parseFloat(formData.expense) || 0,
          savings: savings, // Use calculated savings
          date: formData.date,
          notes: formData.notes || '',
          created_at: response.data.updated_at,
        };

        setExpenses((prev) =>
          prev.map((expense) => (expense._id === editingExpenseId ? updatedExpense : expense))
        );
        calculateFinancialMetrics(
          expenses.map((expense) => (expense._id === editingExpenseId ? updatedExpense : expense))
        );
      } else {
        const response = await axios.post(`${API_BASE_URL}/api/profile/expenses`, data, {
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/x-www-form-urlencoded' },
        });

        const newExpense = {
          _id: response.data.expense_id,
          income: parseFloat(formData.income) || 0,
          expense: parseFloat(formData.expense) || 0,
          savings: savings, // Use calculated savings
          date: formData.date,
          notes: formData.notes || '',
          created_at: new Date().toISOString(),
        };
        setExpenses((prev) => [newExpense, ...prev]);
        calculateFinancialMetrics([newExpense, ...expenses]);
      }

      setFormVisible(false);
      setIsEditing(false);
      setEditingExpenseId(null);
      setFormData({ income: '', expense: '', date: new Date().toISOString().split('T')[0], notes: '' });
    } catch (err) {
      if (err.response?.status === 401) {
        setError('Session expired. Please log in again.');
        localStorage.removeItem('token');
        navigate('/login');
      } else {
        setError(err.response?.data?.error || `Failed to ${isEditing ? 'update' : 'add'} expense.`);
      }
      console.error(`Error ${isEditing ? 'updating' : 'creating'} expense:`, err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (expenseId) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Please log in to delete an expense.');
        navigate('/login');
        return;
      }

      await axios.delete(`${API_BASE_URL}/api/profile/expenses/${expenseId}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      const updatedExpenses = expenses.filter((expense) => expense._id !== expenseId);
      setExpenses(updatedExpenses);
      calculateFinancialMetrics(updatedExpenses);
      console.log(`Deleted expense with ID: ${expenseId}`);
    } catch (err) {
      if (err.response?.status === 401) {
        setError('Session expired. Please log in again.');
        localStorage.removeItem('token');
        navigate('/login');
      } else {
        setError(err.response?.data?.error || 'Failed to delete expense.');
      }
      console.error('Error deleting expense:', err);
    }
  };

  const handleEdit = (expense) => {
    setIsEditing(true);
    setEditingExpenseId(expense._id);
    setFormData({
      income: expense.income || '',
      expense: expense.expense || '',
      date: expense.date,
      notes: expense.notes || '',
    });
    setFormVisible(true);
  };

  const handleCancel = () => {
    setFormVisible(false);
    setIsEditing(false);
    setEditingExpenseId(null);
    setFormData({ income: '', expense: '', date: new Date().toISOString().split('T')[0], notes: '' });
  };

  const handlePredict = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Please log in to predict loan safety.');
        navigate('/login');
        return;
      }

      const response = await axios.post(
        `${API_BASE_URL}/api/predict-loan-safety`,
        {
          total_income: totalIncome,
          debt_to_income_ratio: debtToIncomeRatio,
        },
        { headers: { 'Authorization': `Bearer ${token}` } }
      );

      setPrediction(response.data.prediction);
    } catch (err) {
      if (err.response?.status === 401) {
        setError('Session expired. Please log in again.');
        localStorage.removeItem('token');
        navigate('/login');
      } else {
        setError('Failed to predict loan safety. Please try again later.');
      }
      console.error('Error predicting loan safety:', err);
    }
  };

  // Prepare data for charts
  const pieData = [
    { name: 'Income', value: totalIncome },
    { name: 'Expenses', value: expenses.reduce((sum, entry) => sum + (parseFloat(entry.expense) || 0), 0) },
    { name: 'Savings', value: totalSavings },
  ];
  const COLORS = ['#3B82F6', '#EF4444', '#10B981'];
  const chartData = expenses.map((entry) => ({
    name: new Date(entry.date).toLocaleDateString(),
    income: parseFloat(entry.income) || 0,
    expense: parseFloat(entry.expense) || 0,
  }));

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-7xl mx-auto px-6 py-8">
        <button
          onClick={() => navigate('/')}
          className="btn btn-ghost text-gray-600 gap-2 mb-8 hover:bg-gray-100 transition"
        >
          <ChevronLeft size={20} />
          <span className="text-lg font-semibold">Back to Home</span>
        </button>

        {/* Stacked Layout */}
        <div className="space-y-8">
          {/* Expense Tracker Box (Top) */}
          <div className="bg-white rounded-xl shadow-sm hover:shadow-md p-6 border border-gray-100">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Expense Tracker</h2>
            <div className="space-y-4">
              <p className="text-lg text-gray-700">
                <strong>Total Income:</strong> ${totalIncome.toFixed(2)}
              </p>
              <p className="text-lg text-gray-700">
                <strong>Total Savings:</strong> ${totalSavings.toFixed(2)}
              </p>
              <p className="text-lg text-gray-700">
                <strong>Debt-to-Income Ratio:</strong> {debtToIncomeRatio}%
              </p>
              <p className="text-lg text-gray-700">
                <strong>Risk Score:</strong> {riskScore}%
              </p>
              <p className="text-lg text-gray-700">
                <strong>Advice:</strong> {advice}
              </p>
              {prediction && (
                <p className="text-lg text-gray-700">
                  <strong>Loan Safety Prediction:</strong> {prediction}
                </p>
              )}
            </div>
          </div>

          {/* Scrollable Records Section with Add Button */}
          <div className="bg-white rounded-xl shadow-sm hover:shadow-md border border-gray-100 overflow-y-auto" style={{ maxHeight: '400px' }}>
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-900">Expense Records</h2>
                <button
                  className="btn btn-circle bg-cyan-500 text-white hover:bg-cyan-600 border-none"
                  onClick={() => {
                    setIsEditing(false);
                    setEditingExpenseId(null);
                    setFormData({
                      income: '',
                      expense: '',
                      date: new Date().toISOString().split('T')[0],
                      notes: '',
                    });
                    setFormVisible(true);
                  }}
                >
                  <Plus size={24} />
                </button>
              </div>
              <div className="space-y-4">
                {expenses.length === 0 ? (
                  <p className="text-gray-500 text-center">No expenses yet. Add your first entry!</p>
                ) : (
                  expenses.map((entry) => (
                    <div
                      key={entry._id}
                      className="flex justify-between items-center p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      <div>
                        <span className="font-medium text-gray-700">
                          {entry.income > 0 ? `Income: $${entry.income}` : ''}
                          {entry.expense > 0 ? ` Expense: $${entry.expense}` : ''}
                          {entry.savings > 0 ? ` Savings: $${entry.savings}` : ''}
                        </span>
                        <p className="text-sm text-gray-600">Date: {new Date(entry.date).toLocaleDateString()}</p>
                        {entry.notes && <p className="text-sm text-gray-700">{entry.notes}</p>}
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="badge badge-primary bg-cyan-500 text-white">
                          Added: {new Date(entry.created_at).toLocaleDateString()}
                        </div>
                        <button
                          onClick={() => handleEdit(entry)}
                          className="btn btn-circle bg-yellow-500 text-white hover:bg-yellow-600 border-none"
                        >
                          <Pencil size={20} />
                        </button>
                        <button
                          onClick={() => handleDelete(entry._id)}
                          className="btn btn-circle bg-red-500 text-white hover:bg-red-600 border-none"
                        >
                          <Trash2 size={20} />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Charts Section (Bottom) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Pie Chart */}
            <div className="bg-white rounded-xl shadow-sm hover:shadow-md p-6 border border-gray-100">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Financial Breakdown</h2>
              <div className="overflow-x-auto">
                <PieChart width={400} height={300}>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name}: $${value.toFixed(2)}`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </div>
            </div>

            {/* Line Chart */}
            <div className="bg-white rounded-xl shadow-sm hover:shadow-md p-6 border border-gray-100">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Expense Overview</h2>
              <div className="overflow-x-auto">
                <LineChart width={400} height={300} data={chartData} className="mx-auto">
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="name" stroke="#4b5563" />
                  <YAxis stroke="#4b5563" />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="income" stroke="#3B82F6" strokeWidth={2} name="Income" />
                  <Line type="monotone" dataKey="expense" stroke="#EF4444" strokeWidth={2} name="Expense" />
                </LineChart>
              </div>
            </div>
          </div>
        </div>

        {formVisible && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <form
              onSubmit={handleSubmit}
              className="bg-white rounded-xl shadow-sm p-6 w-full max-w-md border border-gray-200"
            >
              <div className="space-y-4">
                <div>
                  <label htmlFor="income" className="block text-sm font-medium text-gray-700">
                    Income (Optional)
                  </label>
                  <input
                    type="number"
                    id="income"
                    name="income"
                    value={formData.income}
                    onChange={handleInputChange}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
                    placeholder="Enter income amount"
                    step="0.01"
                  />
                </div>
                <div>
                  <label htmlFor="expense" className="block text-sm font-medium text-gray-700">
                    Expense (Optional)
                  </label>
                  <input
                    type="number"
                    id="expense"
                    name="expense"
                    value={formData.expense}
                    onChange={handleInputChange}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
                    placeholder="Enter expense amount"
                    step="0.01"
                  />
                </div>
                <div>
                  <label htmlFor="date" className="block text-sm font-medium text-gray-700">
                    Date
                  </label>
                  <input
                    type="date"
                    id="date"
                    name="date"
                    value={formData.date}
                    onChange={handleInputChange}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
                  />
                </div>
                <div>
                  <label htmlFor="notes" className="block text-sm font-medium text-gray-700">
                    Notes (Optional)
                  </label>
                  <textarea
                    id="notes"
                    name="notes"
                    value={formData.notes}
                    onChange={handleInputChange}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
                    rows="3"
                    placeholder="Add any notes"
                  />
                </div>
                {error && <p className="text-red-600 text-sm">{error}</p>}
                <div className="flex gap-4">
                  <button
                    type="submit"
                    className="w-full bg-cyan-500 text-white py-2 px-4 rounded-md hover:bg-cyan-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-cyan-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? (isEditing ? 'Updating...' : 'Adding...') : (isEditing ? 'Update Entry' : 'Add Entry')}
                  </button>
                  <button
                    type="button"
                    onClick={handleCancel}
                    className="w-full bg-gray-300 text-gray-700 py-2 px-4 rounded-md hover:bg-gray-400"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

export default PersonalDetails;