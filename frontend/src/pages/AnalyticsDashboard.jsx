import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import DashboardSidebar from "../components/DashboardSidebar";
import { fetchFileAnalytics } from "../services/api";

const COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16"];

export default function AnalyticsDashboard({ documents, onRefresh }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentSheet, setCurrentSheet] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");

  // Load analytics when file is selected or sheet changes
  useEffect(() => {
    if (!selectedFile) {
      setAnalytics(null);
      return;
    }

    const loadAnalytics = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchFileAnalytics(selectedFile, currentSheet);
        setAnalytics(data);
      } catch (err) {
        console.error("Failed to load analytics:", err);
        setError(err.response?.data?.detail || "Failed to load analytics");
        setAnalytics(null);
      } finally {
        setLoading(false);
      }
    };

    loadAnalytics();
  }, [selectedFile, currentSheet]);

  const handleSelectFile = (fileName) => {
    setSelectedFile(fileName);
    setCurrentSheet(null);
    setError(null);
  };

  const handleSheetChange = (newSheet) => {
    setCurrentSheet(newSheet);
  };

  // Calculate summary stats
  const calculateSummaryStats = () => {
    if (!analytics || !analytics.numeric_columns || analytics.numeric_columns.length === 0) {
      return null;
    }

    const numericCols = analytics.numeric_columns.slice(0, 4);
    return numericCols.map(col => {
      const stats = analytics.column_stats[col];
      if (!stats) return null;
      return {
        title: col,
        value: stats.mean.toFixed(2),
        change: ((stats.mean - stats.min) / (stats.max - stats.min) * 100).toFixed(1),
        trend: "up"
      };
    }).filter(Boolean);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <div className="w-64 bg-slate-800 text-white flex-shrink-0">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-8">
            <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <h2 className="text-2xl font-bold">Analytics</h2>
          </div>
          <nav className="space-y-2">
            <div className="bg-blue-600 text-white px-4 py-3 rounded-lg flex items-center gap-3">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
              </svg>
              <span className="font-medium">Dashboard</span>
            </div>
            <Link
              to="/"
              className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-700 transition-all"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              <span className="font-medium">RAG Home</span>
            </Link>
          </nav>
        </div>
        
        {/* File Selector in Sidebar */}
        <div className="px-6 py-4 border-t border-slate-700">
          <h3 className="text-xs font-semibold text-slate-400 uppercase mb-3">Select File</h3>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {documents?.documents && documents.documents.length > 0 ? documents.documents.filter(doc => 
              doc.source_type === "xlsx" || doc.source_type === "excel" || doc.source_type === "csv"
            ).map((doc) => (
              <button
                key={doc.file_name}
                onClick={() => handleSelectFile(doc.file_name)}
                className={`w-full text-left px-3 py-2 rounded text-sm transition-all ${
                  selectedFile === doc.file_name
                    ? "bg-blue-600 text-white"
                    : "bg-slate-700 hover:bg-slate-600"
                }`}
              >
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="truncate font-medium">{doc.file_name}</span>
                </div>
                <div className="text-xs opacity-70 mt-1 ml-6">
                  {doc.analysis_report?.row_count || 0} rows × {doc.analysis_report?.column_count || 0} cols
                </div>
              </button>
            )) : (
              <p className="text-sm text-slate-400 text-center py-4">No files uploaded</p>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-8 overflow-auto">
        {/* Top Navigation Bar */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Analytics Dashboard</h1>
            <p className="text-gray-600 mt-1">Interactive data visualization and insights</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={onRefresh}
              className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-all shadow-sm"
            >
              🔄 Refresh
            </button>
          </div>
        </div>
        {/* Loading State */}
        {loading && (
          <div className="bg-white rounded-xl p-12 shadow-sm text-center">
            <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-blue-600 border-t-transparent"></div>
            <p className="mt-4 text-gray-600">Loading analytics...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 shadow-sm">
            <div className="flex items-center">
              <span className="text-3xl">⚠️</span>
              <div className="ml-4">
                <p className="font-semibold text-red-900">Error loading analytics</p>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && !selectedFile && (
          <div className="bg-white rounded-xl p-16 shadow-sm text-center">
            <div className="text-7xl mb-4">📊</div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">Select a File to Begin</h2>
            <p className="text-gray-600">
              Choose an Excel or CSV file from the sidebar to view interactive analytics
            </p>
          </div>
        )}

        {/* PDF Not Supported */}
        {!loading && !error && analytics && analytics.analytics_available === false && (
          <div className="bg-white rounded-xl p-16 shadow-sm text-center">
            <div className="text-7xl mb-4">📄</div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">Analytics Not Available</h2>
            <p className="text-gray-600">
              PDF files don't support chart visualization. Please select an Excel or CSV file.
            </p>
          </div>
        )}

        {/* Analytics Content */}
        {!loading && !error && analytics && analytics.analytics_available && (
          <div className="space-y-6">
            {/* File Info & Sheet Selector */}
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-gray-800">{analytics.file_name}</h2>
                  <p className="text-sm text-gray-600 mt-1">
                    {analytics.total_rows.toLocaleString()} rows × {analytics.total_columns} columns
                  </p>
                </div>
                {analytics.sheet_names && analytics.sheet_names.length > 1 && (
                  <select
                    value={currentSheet || analytics.selected_sheet}
                    onChange={(e) => handleSheetChange(e.target.value)}
                    className="px-4 py-2 border border-gray-300 rounded-lg bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {analytics.sheet_names.map((sheet) => (
                      <option key={sheet} value={sheet}>
                        {sheet}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            {/* Summary Stats Cards */}
            {calculateSummaryStats() && calculateSummaryStats().length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {calculateSummaryStats().map((stat, idx) => (
                  <div key={idx} className="bg-white rounded-xl p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-600 mb-2">{stat.title}</p>
                        <h3 className="text-3xl font-bold text-gray-900">{stat.value}</h3>
                        <div className="flex items-center mt-2">
                          <span className={`text-sm font-medium ${stat.trend === 'up' ? 'text-green-600' : 'text-red-600'}`}>
                            {stat.trend === 'up' ? '↑' : '↓'} {stat.change}%
                          </span>
                          <span className="text-xs text-gray-500 ml-2">vs min</span>
                        </div>
                      </div>
                      <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                        idx % 4 === 0 ? 'bg-blue-100 text-blue-600' :
                        idx % 4 === 1 ? 'bg-green-100 text-green-600' :
                        idx % 4 === 2 ? 'bg-orange-100 text-orange-600' :
                        'bg-purple-100 text-purple-600'
                      }`}>
                        <span className="text-xl">📊</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Area Chart - Numeric Trends */}
              {analytics.numeric_columns && analytics.numeric_columns.length > 0 && (
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200 lg:col-span-2">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-bold text-gray-800">Numeric Column Trends</h3>
                    <div className="flex gap-2">
                      <button className="px-3 py-1 text-xs rounded-lg bg-blue-600 text-white">All data</button>
                      <button className="px-3 py-1 text-xs rounded-lg hover:bg-gray-100 text-gray-600">Stats</button>
                    </div>
                  </div>
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart
                      data={analytics.numeric_columns.slice(0, 8).map((col, idx) => ({
                        name: col,
                        value: analytics.column_stats[col]?.mean || 0,
                        max: analytics.column_stats[col]?.max || 0,
                      }))}
                      margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.8}/>
                          <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.1}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                      />
                      <Area type="monotone" dataKey="value" stroke="#3B82F6" fillOpacity={1} fill="url(#colorValue)" strokeWidth={2} />
                      <Area type="monotone" dataKey="max" stroke="#10B981" fillOpacity={0.3} fill="#10B981" strokeWidth={1} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Bar Chart - Column Comparison */}
              {analytics.numeric_columns && analytics.numeric_columns.length > 0 && (
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
                  <h3 className="text-lg font-bold text-gray-800 mb-6">Column Statistics Comparison</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart
                      data={analytics.numeric_columns.slice(0, 6).map((col) => ({
                        name: col.substring(0, 10),
                        min: analytics.column_stats[col]?.min || 0,
                        mean: analytics.column_stats[col]?.mean || 0,
                        max: analytics.column_stats[col]?.max || 0,
                      }))}
                      margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                      />
                      <Legend />
                      <Bar dataKey="min" fill="#EF4444" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="mean" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="max" fill="#10B981" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Ranking/Top Values */}
              {analytics.categorical_columns && analytics.categorical_columns.length > 0 && analytics.top_values && (
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
                  <h3 className="text-lg font-bold text-gray-800 mb-6">
                    {analytics.categorical_columns[0]} - Rankings
                  </h3>
                  <div className="space-y-3">
                    {analytics.top_values[analytics.categorical_columns[0]]?.slice(0, 6).map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                            idx === 0 ? 'bg-blue-100 text-blue-600' :
                            idx === 1 ? 'bg-green-100 text-green-600' :
                            idx === 2 ? 'bg-orange-100 text-orange-600' :
                            'bg-gray-100 text-gray-600'
                          }`}>
                            {idx + 1}
                          </div>
                          <span className="text-sm font-medium text-gray-700">{item.name}</span>
                        </div>
                        <span className="text-sm font-bold text-gray-900">{item.count.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Pie Charts for Categorical Data */}
            {analytics.categorical_columns && analytics.categorical_columns.length > 1 && analytics.top_values && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {analytics.categorical_columns.slice(0, 2).map((col) => {
                  const topValues = analytics.top_values[col];
                  if (!topValues || topValues.length === 0) return null;
                  return (
                    <div key={col} className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
                      <h3 className="text-lg font-bold text-gray-800 mb-6">{col} Distribution</h3>
                      <ResponsiveContainer width="100%" height={280}>
                        <PieChart>
                          <Pie
                            data={topValues.slice(0, 6)}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={90}
                            fill="#8884d8"
                            paddingAngle={2}
                            dataKey="count"
                            label={({ name, percent }) => `${name.substring(0, 8)} ${(percent * 100).toFixed(0)}%`}
                          >
                            {topValues.slice(0, 6).map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip 
                            contentStyle={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
