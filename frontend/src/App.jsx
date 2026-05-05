import React, { useState, useEffect } from 'react';
import PromptBuilder from './PromptBuilder';
import { LanguageProvider, useLanguage } from './LanguageContext';
import './index.css';
import './App.css';

function AppContent() {
  const { t, toggleLanguage, language } = useLanguage();
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
        <h1 className="app-title">{t('appTitle')}</h1>
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
        <PromptBuilder />
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