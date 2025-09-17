```jsx
// TikTokAffiliatePro Frontend - React App
// Enhanced with Login page, Tailwind CSS, Notification dropdown
// Dependencies: npm install react-router-dom axios recharts @stripe/stripe-js @stripe/react-stripe-js react-hot-toast react-joyride tailwindcss
// Setup Tailwind: npx tailwindcss init; configure tailwind.config.js
// tailwind.config.js: module.exports = { content: ["./src/**/*.{js,jsx}"], theme: { extend: {} }, plugins: [] }

import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { loadStripe } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';
import { toast, Toaster } from 'react-hot-toast';
import Joyride from 'react-joyride';

// API Base URL
const API_BASE = 'http://localhost:8000';
const stripePromise = loadStripe('pk_test_your_stripe_public_key_here'); // Replace with actual key

// Auth Context
const AuthContext = React.createContext();
export const useAuth = () => React.useContext(AuthContext);

const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null);
  const [tier, setTier] = useState('basic');

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      axios.get(`${API_BASE}/auth/me`).then(res => {
        setUser(res.data.user);
        setTier(res.data.tier);
      }).catch(() => {
        setToken(null);
        localStorage.removeItem('token');
      });
    }
  }, [token]);

  const login = async (username, password) => {
    try {
      const res = await axios.post(`${API_BASE}/auth/login`, { username, password });
      setToken(res.data.access_token);
      localStorage.setItem('token', res.data.access_token);
      toast.success('Logged in successfully!');
    } catch (err) {
      toast.error('Login failed: Invalid credentials');
      throw err;
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    toast.success('Logged out');
  };

  return (
    <AuthContext.Provider value={{ token, user, tier, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

// Login Page
const LoginPage = () => {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await login(credentials.username, credentials.password);
      navigate(`/dashboard/${credentials.username.split('@')[1] || '1'}`); // Assume tenant_id from username
    } catch (err) {}
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-md">
        <h1 className="text-2xl font-bold mb-6 text-center">Login to TikTokAffiliatePro</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            placeholder="Username"
            value={credentials.username}
            onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
            className="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={credentials.password}
            onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
            className="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          <button type="submit" className="w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-700">
            Login
          </button>
        </form>
      </div>
    </div>
  );
};

// Main Dashboard
const MainDashboard = () => {
  const { tenant_id } = useParams();
  const [data, setData] = useState({ total_analyses: 0, total_views: 0, recent_analyses: [] });
  const [chartData, setChartData] = useState([]);

  useEffect(() => {
    axios.get(`${API_BASE}/dashboard/tenant?limit=20`).then(res => {
      setData(res.data);
      // Aggregate views by month for chart
      const monthlyViews = {};
      res.data.recent_analyses.forEach(item => {
        const date = new Date(item.date);
        const month = date.toLocaleString('default', { month: 'short', year: 'numeric' });
        monthlyViews[month] = (monthlyViews[month] || 0) + (item.summary.includes('video_data') ? JSON.parse(item.summary).video_data?.views || 0 : 0);
      });
      setChartData(Object.entries(monthlyViews).map(([name, views]) => ({ name, views })));
    });
  }, [tenant_id]);

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Affiliate Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-xl font-semibold">{data.total_analyses}</h2>
          <p>Videos Analyzed</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-xl font-semibold">{data.total_views}</h2>
          <p>Total Viewers</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-xl font-semibold">Active</h2>
          <p>Trend Status</p>
        </div>
      </div>
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <h3 className="text-lg font-semibold mb-2">Viewership Trend</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="views" stroke="#3b82f6" />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-2">Recent Analyses</h3>
        {data.recent_analyses.map(item => (
          <div key={item.id} className="border-b py-2">
            <p className="text-sm">{item.type.toUpperCase()} on {new Date(item.date).toLocaleString()}:</p>
            <p className="text-gray-600 truncate">{item.summary}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

// Content Generator
const ContentGenerator = () => {
  const [formData, setFormData] = useState({ product_desc: '', niche: '', target_audience: '' });
  const [result, setResult] = useState(null);
  const { tier } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (tier !== 'pro' && tier !== 'enterprise') {
      toast.error('Upgrade to Pro+ for Content Generation');
      return;
    }
    try {
      const res = await axios.post(`${API_BASE}/generate/content/advanced`, formData);
      setResult(res.data);
      toast.success('Content Generated!');
    } catch (err) {
      toast.error('Generation failed');
    }
  };

  return (
    <div className="p-6 content-gen">
      <h1 className="text-3xl font-bold mb-6">AI Content Generator</h1>
      <form onSubmit={handleSubmit} className="space-y-4 mb-6">
        <input
          type="text"
          placeholder="Product Description"
          value={formData.product_desc}
          onChange={(e) => setFormData({ ...formData, product_desc: e.target.value })}
          className="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          required
        />
        <input
          type="text"
          placeholder="Niche"
          value={formData.niche}
          onChange={(e) => setFormData({ ...formData, niche: e.target.value })}
          className="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          required
        />
        <input
          type="text"
          placeholder="Target Audience"
          value={formData.target_audience}
          onChange={(e) => setFormData({ ...formData, target_audience: e.target.value })}
          className="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          required
        />
        <button type="submit" className="w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-700">
          Generate
        </button>
      </form>
      {result && (
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Generated Content</h2>
          <section className="mb-4">
            <h3 className="text-lg font-medium">Video Ideas</h3>
            <ul className="list-disc pl-5">{result.ideas?.map((idea, i) => <li key={i}>{idea}</li>)}</ul>
          </section>
          <section className="mb-4">
            <h3 className="text-lg font-medium">Script</h3>
            <textarea value={result.script} readOnly className="w-full p-2 border rounded" rows={6} />
            <button
              onClick={() => navigator.clipboard.writeText(result.script)}
              className="mt-2 bg-gray-200 p-2 rounded hover:bg-gray-300"
            >
              Copy
            </button>
          </section>
          <section className="mb-4">
            <h3 className="text-lg font-medium">Captions</h3>
            <ul className="list-disc pl-5">
              {result.captions?.map((cap, i) => (
                <li key={i} className="flex justify-between">
                  {cap}
                  <button
                    onClick={() => navigator.clipboard.writeText(cap)}
                    className="ml-2 bg-gray-200 p-1 rounded hover:bg-gray-300"
                  >
                    Copy
                  </button>
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h3 className="text-lg font-medium">Hashtags</h3>
            <p>{result.hashtags?.join(' ')}</p>
            <button
              onClick={() => navigator.clipboard.writeText(result.hashtags?.join(' '))}
              className="mt-2 bg-gray-200 p-2 rounded hover:bg-gray-300"
            >
              Copy
            </button>
          </section>
        </div>
      )}
    </div>
  );
};

// Performance Tracking
const PerformanceTracking = () => {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    axios.get(`${API_BASE}/analytics?limit=20`).then(res => setHistory(res.data.recent));
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Performance History</h1>
      <div className="bg-white p-4 rounded-lg shadow">
        {history.map(item => (
          <div key={item.id} className="border-b py-2">
            <h3 className="text-lg font-medium">{item.type.toUpperCase()} - {new Date(item.created_at).toLocaleString()}</h3>
            <p className="text-gray-600">{item.preview}</p>
            {item.type === 'advanced_video_analysis' && item.video_data && (
              <div className="mt-2 text-sm text-gray-500">
                <span>Views: {item.video_data.views || 0}</span> | 
                <span> Likes: {item.video_data.likes || 0}</span> | 
                <span> Shares: {item.video_data.shares || 0}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

// Account Management
const AccountManagement = () => {
  const { tier, logout, user } = useAuth();
  const [upgrading, setUpgrading] = useState(false);
  const [selectedTier, setSelectedTier] = useState('');
  const [subData, setSubData] = useState(null);

  useEffect(() => {
    axios.get(`${API_BASE}/dashboard/tenant`).then(res => {
      setSubData(res.data);
    });
  }, []);

  const handleUpgrade = async () => {
    try {
      const res = await axios.post(`${API_BASE}/subscribe/create-session`, { tier: selectedTier });
      window.location.href = res.data.url;
    } catch (err) {
      toast.error('Upgrade failed');
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Account Management</h1>
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <h2 className="text-xl font-semibold">Current Tier: {tier.toUpperCase()}</h2>
        <p>Active until: {subData?.metrics?.active_until || 'Loading...'}</p>
      </div>
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-2">Upgrade Plan</h3>
        <div className="flex space-x-4">
          <button
            onClick={() => { setSelectedTier('pro'); setUpgrading(true); }}
            className="bg-blue-600 text-white p-2 rounded hover:bg-blue-700"
          >
            Upgrade to Pro
          </button>
          <button
            onClick={() => { setSelectedTier('enterprise'); setUpgrading(true); }}
            className="bg-blue-600 text-white p-2 rounded hover:bg-blue-700"
          >
            Upgrade to Enterprise
          </button>
        </div>
        {upgrading && (
          <div className="mt-4 p-4 border rounded bg-gray-50">
            <p>Redirecting to secure payment for {selectedTier.toUpperCase()}...</p>
            <div className="flex space-x-2 mt-2">
              <button onClick={handleUpgrade} className="bg-green-600 text-white p-2 rounded hover:bg-green-700">
                Confirm & Pay
              </button>
              <button onClick={() => setUpgrading(false)} className="bg-red-600 text-white p-2 rounded hover:bg-red-700">
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
      <button onClick={logout} className="mt-4 bg-gray-600 text-white p-2 rounded hover:bg-gray-700">
        Logout
      </button>
    </div>
  );
};

// Notification Bell
const NotificationBell = () => {
  const [notifications, setNotifications] = useState([]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const res = await axios.get(`${API_BASE}/notifications?limit=10`);
        setNotifications(res.data);
        if (res.data.some(n => !n.is_read)) {
          toast('New notifications available!');
        }
      } catch (err) {}
    };
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 rounded-full hover:bg-gray-200 relative"
      >
        🔔 {notifications.filter(n => !n.is_read).length > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
            {notifications.filter(n => !n.is_read).length}
          </span>
        )}
      </button>
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border z-10">
          <div className="p-2">
            <h3 className="text-lg font-semibold">Notifications</h3>
            {notifications.length === 0 ? (
              <p className="text-gray-500">No notifications</p>
            ) : (
              notifications.map(n => (
                <div key={n.id} className={`p-2 border-b ${n.is_read ? 'bg-gray-50' : 'bg-blue-50'}`}>
                  <p className="text-sm">{n.message}</p>
                  <p className="text-xs text-gray-500">{new Date(n.created_at).toLocaleString()}</p>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Interactive Tutorial
const InteractiveTutorial = () => {
  const steps = [
    {
      target: '.content-gen input:first-child',
      content: 'Enter your product description here to generate content.',
    },
    {
      target: '.content-gen button[type="submit"]',
      content: 'Click to generate AI-powered video ideas, scripts, and hashtags.',
    },
    {
      target: '.notification-bell',
      content: 'Check here for real-time updates on trends and video performance.',
    },
  ];

  return <Joyride steps={steps} run={true} continuous={true} styles={{ options: { primaryColor: '#3b82f6' } }} />;
};

// Layout Component
const Layout = ({ children }) => {
  const { user } = useAuth();
  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-blue-600 text-white p-4 flex justify-between items-center">
        <div className="flex space-x-4">
          {user && (
            <>
              <Link to={`/dashboard/${user.tenant_id}`} className="hover:underline">Dashboard</Link>
              <Link to="/generate" className="hover:underline">Generator</Link>
              <Link to="/performance" className="hover:underline">Performance</Link>
              <Link to="/account" className="hover:underline">Account</Link>
            </>
          )}
        </div>
        <NotificationBell className="notification-bell" />
      </header>
      <main className="container mx-auto">{children}</main>
      <Toaster />
      <InteractiveTutorial />
    </div>
  );
};

// Main App
function App() {
  return (
    <AuthProvider>
      <Elements stripe={stripePromise}>
        <Router>
          <Routes>
            <Route path="/" element={<LoginPage />} />
            <Route path="/dashboard/:tenant_id" element={<Layout><MainDashboard /></Layout>} />
            <Route path="/generate" element={<Layout><ContentGenerator /></Layout>} />
            <Route path="/performance" element={<Layout><PerformanceTracking /></Layout>} />
            <Route path="/account" element={<Layout><AccountManagement /></Layout>} />
            <Route path="/success" element={<div>Payment Successful! Redirecting...</div>} />
            <Route path="/cancel" element={<div>Payment Cancelled. <Link to="/account">Back to Account</Link></div>} />
          </Routes>
        </Router>
      </Elements>
    </AuthProvider>
  );
}

export default App;
```