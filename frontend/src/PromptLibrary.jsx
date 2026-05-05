import React, { useState, useEffect } from 'react';
import { useLanguage } from './LanguageContext';

const PromptLibrary = () => {
  const { t } = useLanguage();
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    fetchLibrary();
  }, []);

  const fetchLibrary = async () => {
    try {
      const response = await fetch('/api/prompts/library');
      const data = await response.json();
      setPrompts(data);
    } catch (error) {
      console.error('Failed to fetch library:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleDelete = async (id) => {
    try {
      await fetch(`/api/prompts/library/${id}`, { method: 'DELETE' });
      setPrompts(prompts.filter(p => p.id !== id));
    } catch (error) {
      console.error('Failed to delete prompt:', error);
    }
  };

  const handleFavorite = async (id) => {
    try {
      const response = await fetch(`/api/prompts/library/${id}/favorite`, { method: 'PATCH' });
      const data = await response.json();
      if (data.status === 'success') {
        setPrompts(prompts.map(p => p.id === id ? { ...p, is_favorite: data.is_favorite } : p));
      }
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
    }
  };

  if (loading) {
    return <div className="empty-state"><p>Loading...</p></div>;
  }

  return (
    <div className="library-container stage-panel">
      <h2>{t('libraryTitle')}</h2>
      
      {prompts.length === 0 ? (
        <div className="empty-state">
          <p>{t('noSavedPrompts')}</p>
        </div>
      ) : (
        <div className="library-grid">
          {prompts.map((prompt) => (
            <div key={prompt.id} className={`library-card ${prompt.is_favorite ? 'favorite-glow' : ''}`}>
              <div className="card-header">
                <span className="card-role">{prompt.role}</span>
                <div className="card-actions">
                  <button 
                    className="icon-btn favorite-btn"
                    onClick={() => handleFavorite(prompt.id)}
                    title={prompt.is_favorite ? t('unfavoriteBtn') : t('favoriteBtn')}
                  >
                    {prompt.is_favorite ? '★' : '☆'}
                  </button>
                  <button 
                    className="btn-secondary btn-small copy-btn"
                    onClick={() => handleCopy(prompt.id, prompt.compiled_prompt)}
                  >
                    {copiedId === prompt.id ? t('copiedBtn') : t('copyBtn')}
                  </button>
                  <button 
                    className="icon-btn delete-btn"
                    onClick={() => handleDelete(prompt.id)}
                    title={t('deleteBtn')}
                  >
                    🗑️
                  </button>
                </div>
              </div>
              <p className="card-task">{prompt.task}</p>
              <pre className="code-block small-code">{prompt.compiled_prompt}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default PromptLibrary;
