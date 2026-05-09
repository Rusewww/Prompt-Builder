import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import PromptBuilder from './PromptBuilder';
import PromptLibrary from './PromptLibrary';
import { LanguageProvider, useLanguage } from './LanguageContext';
import './index.css';
import './App.css';

function AppContent() {
  const { t, toggleLanguage, language } = useLanguage();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  
  const [theme, setTheme] = useState(() => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) return savedTheme;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
  };

  return (
    <div className="App">
      <nav className={`sidebar ${sidebarOpen ? '' : 'collapsed'}`}>
        <div className="sidebar-brand">
          <h1 className="sidebar-label">{t('appTitle')}</h1>
          <button 
            className="sidebar-toggle-btn"
            onClick={() => setSidebarOpen(prev => !prev)}
            title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            {sidebarOpen ? '◀' : '▶'}
          </button>
        </div>
        <div className="sidebar-nav">
          <button 
            className={`nav-item ${location.pathname === '/' ? 'active' : ''}`}
            onClick={() => navigate('/')}
            title={t('builderBtn')}
          >
            <span className="nav-icon">🔧</span>
            <span className="sidebar-label">{t('builderBtn')}</span>
          </button>
          <button 
            className={`nav-item ${location.pathname === '/library' ? 'active' : ''}`}
            onClick={() => navigate('/library')}
            title={t('libraryBtn')}
          >
            <span className="nav-icon">📚</span>
            <span className="sidebar-label">{t('libraryBtn')}</span>
          </button>
        </div>
        <div className="sidebar-footer">
          <button 
            className="sidebar-footer-btn"
            onClick={toggleLanguage}
            title={`Switch to ${language === 'en' ? 'Ukrainian' : 'English'}`}
          >
            <span className="nav-icon">🌐</span>
            <span className="sidebar-label">{t('toggleLang')}</span>
          </button>
          <button 
            className="sidebar-footer-btn"
            onClick={toggleTheme}
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          >
            <span className="nav-icon">{theme === 'light' ? '🌙' : '☀️'}</span>
            <span className="sidebar-label">{theme === 'light' ? 'Dark Mode' : 'Light Mode'}</span>
          </button>
        </div>
      </nav>
      <div className="main-content">
        <Routes>
          <Route path="/" element={<PromptBuilder />} />
          <Route path="/library" element={<PromptLibrary />} />
        </Routes>
      </div>
    </div>
  );
}

function App() {
  return (
    <LanguageProvider>
      <AppContent />
    </LanguageProvider>
  );
}

export default App;