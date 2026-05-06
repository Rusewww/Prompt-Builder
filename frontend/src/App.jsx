import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import PromptBuilder from './PromptBuilder';
import PromptLibrary from './PromptLibrary';
import { LanguageProvider, useLanguage } from './LanguageContext';
import './index.css';
import './App.css';

function AppContent() {
  const { t, toggleLanguage, language } = useLanguage();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  
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
      <header className="app-header">
        <div className="header-left">
          <div className="burger-menu-container">
            <button className="burger-btn" onClick={() => setMenuOpen(!menuOpen)} aria-label={t('menuBtn')}>
              ☰
            </button>
            {menuOpen && (
              <div className="burger-dropdown">
                <button onClick={() => { navigate('/'); setMenuOpen(false); }}>
                  {t('builderBtn')}
                </button>
                <button onClick={() => { navigate('/library'); setMenuOpen(false); }}>
                  {t('libraryBtn')}
                </button>
              </div>
            )}
          </div>
          <h1 className="app-title">{t('appTitle')}</h1>
        </div>
        <div className="header-actions">
          <button 
            className="theme-toggle-btn lang-toggle-btn" 
            onClick={toggleLanguage}
            aria-label="Toggle language"
            title={`Switch to ${language === 'en' ? 'Ukrainian' : 'English'}`}
          >
            {t('toggleLang')}
          </button>
          <button 
            className="theme-toggle-btn" 
            onClick={toggleTheme} 
            aria-label="Toggle theme"
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          >
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<PromptBuilder />} />
          <Route path="/library" element={<PromptLibrary />} />
        </Routes>
      </main>
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