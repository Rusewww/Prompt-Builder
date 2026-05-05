import React, { useState } from 'react';
import { useLanguage } from './LanguageContext';

const PromptBuilder = () => {
  const { t } = useLanguage();
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    role: 'Act as a Senior QA Engineer',
    context: 'We are using Python and PyTest.',
    task: 'Write unit tests for the auth module.',
    reasoning_pattern: 'Chain-of-Draft',
    use_cove: true,
    use_self_refine: false,
    examples: []
  });

  const [useRole, setUseRole] = useState(true);
  const [useContext, setUseContext] = useState(true);
  const [useTask, setUseTask] = useState(true);
  const [useReasoning, setUseReasoning] = useState(true);
  const [useExamples, setUseExamples] = useState(true);
  const [useGuardrails, setUseGuardrails] = useState(true);

  const [compiledResult, setCompiledResult] = useState('');
  const [templateId, setTemplateId] = useState(null);
  const [executionId, setExecutionId] = useState(null);
  const [llmResponse, setLlmResponse] = useState('');
  const [status, setStatus] = useState('idle'); // idle, compiling, compiled, executing, review, approved

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value
    });
  };

  const handleExampleChange = (index, field, value) => {
    const newExamples = [...formData.examples];
    newExamples[index][field] = value;
    setFormData({ ...formData, examples: newExamples });
  };

  const addExample = () => {
    setFormData({
      ...formData,
      examples: [...formData.examples, { input_text: '', output_text: '' }]
    });
  };

  const removeExample = (index) => {
    const newExamples = formData.examples.filter((_, i) => i !== index);
    setFormData({ ...formData, examples: newExamples });
  };

  const handleCompile = async (e) => {
    e.preventDefault();
    setStatus('compiling');
    try {
      const payload = {
        ...formData,
        role: useRole ? formData.role : '',
        context: useContext ? formData.context : '',
        task: useTask ? formData.task : '',
        reasoning_pattern: useReasoning ? formData.reasoning_pattern : '',
        examples: useExamples ? formData.examples : [],
        use_cove: useGuardrails ? formData.use_cove : false,
        use_self_refine: useGuardrails ? formData.use_self_refine : false,
      };

      const response = await fetch('/api/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      setCompiledResult(data.compiled_prompt);
      setTemplateId(data.template_id);
      setStatus('compiled');
      setLlmResponse('');
      setCurrentStep(2); // Move to next step on success
    } catch (error) {
      console.error('Compilation failed:', error);
      setStatus('idle');
    }
  };

  const handleExecute = async () => {
    setStatus('executing');
    try {
      const response = await fetch('/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: templateId,
          compiled_prompt: compiledResult
        })
      });
      const data = await response.json();
      setLlmResponse(data.llm_response);
      setExecutionId(data.execution_id);
      setStatus('review');
    } catch (error) {
      console.error('Execution failed:', error);
      setStatus('compiled');
    }
  };

  const handleApprove = async () => {
    try {
      await fetch(`/api/hitl/approve?execution_id=${executionId}`, {
        method: 'POST'
      });
      setStatus('approved');
    } catch (error) {
      console.error('Approval failed:', error);
    }
  };

  const handleRefine = async () => {
    setStatus('executing');
    try {
      const response = await fetch('/api/refine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ execution_id: executionId })
      });
      const data = await response.json();
      setLlmResponse(data.llm_response);
      setExecutionId(data.execution_id);
      setStatus('review');
    } catch (error) {
      console.error('Refine failed:', error);
      setStatus('review');
    }
  };

  return (
    <div className="prompt-builder-container">
      {currentStep === 1 && (
        <div className="stage-panel stage-1">
          <h2>{t('stage1Title')}</h2>
          <form onSubmit={handleCompile} className="config-form">
            <div className="form-group">
              <div className="label-with-toggle">
                <label>{t('roleLabel')}</label>
                <label className="switch">
                  <input type="checkbox" checked={useRole} onChange={e => setUseRole(e.target.checked)} />
                  <span className="slider round"></span>
                </label>
              </div>
              <div className={`collapsible-wrapper ${useRole ? 'expanded' : ''}`}>
                <div className="collapsible-inner">
                  <input type="text" name="role" value={formData.role} onChange={handleInputChange} required={useRole} />
                </div>
              </div>
            </div>

            <div className="form-group">
              <div className="label-with-toggle">
                <label>{t('contextLabel')}</label>
                <label className="switch">
                  <input type="checkbox" checked={useContext} onChange={e => setUseContext(e.target.checked)} />
                  <span className="slider round"></span>
                </label>
              </div>
              <div className={`collapsible-wrapper ${useContext ? 'expanded' : ''}`}>
                <div className="collapsible-inner">
                  <textarea name="context" value={formData.context} onChange={handleInputChange} rows="3" required={useContext} />
                </div>
              </div>
            </div>

            <div className="form-group">
              <div className="label-with-toggle">
                <label>{t('taskLabel')}</label>
                <label className="switch">
                  <input type="checkbox" checked={useTask} onChange={e => setUseTask(e.target.checked)} />
                  <span className="slider round"></span>
                </label>
              </div>
              <div className={`collapsible-wrapper ${useTask ? 'expanded' : ''}`}>
                <div className="collapsible-inner">
                  <textarea name="task" value={formData.task} onChange={handleInputChange} rows="3" required={useTask} />
                </div>
              </div>
            </div>

            <div className="form-group">
              <div className="label-with-toggle">
                <label>{t('reasoningLabel')}</label>
                <label className="switch">
                  <input type="checkbox" checked={useReasoning} onChange={e => setUseReasoning(e.target.checked)} />
                  <span className="slider round"></span>
                </label>
              </div>
              <div className={`collapsible-wrapper ${useReasoning ? 'expanded' : ''}`}>
                <div className="collapsible-inner">
                  <select name="reasoning_pattern" value={formData.reasoning_pattern} onChange={handleInputChange}>
                    <option value="Zero-Shot">{t('optZeroShot')}</option>
                    <option value="Chain-of-Thought">{t('optCot')}</option>
                    <option value="Chain-of-Draft">{t('optCod')}</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="form-group examples-group">
              <div className="label-with-toggle">
                <label>{t('examplesLabel')}</label>
                <label className="switch">
                  <input type="checkbox" checked={useExamples} onChange={e => setUseExamples(e.target.checked)} />
                  <span className="slider round"></span>
                </label>
              </div>
              <div className={`collapsible-wrapper ${useExamples ? 'expanded' : ''}`}>
                <div className="collapsible-inner">
                  <div className="examples-header" style={{marginBottom: '1rem'}}>
                    <button type="button" className="btn-secondary btn-small" onClick={addExample}>{t('addExampleBtn')}</button>
                  </div>
                  {formData.examples.map((ex, index) => (
                    <div key={index} className="example-item">
                      <input 
                        type="text" 
                        placeholder={t('inputPlaceholder')}
                        value={ex.input_text} 
                        onChange={(e) => handleExampleChange(index, 'input_text', e.target.value)} 
                        required={useExamples} 
                      />
                      <input 
                        type="text" 
                        placeholder={t('outputPlaceholder')}
                        value={ex.output_text} 
                        onChange={(e) => handleExampleChange(index, 'output_text', e.target.value)} 
                        required={useExamples} 
                      />
                      <button type="button" className="btn-danger btn-small" onClick={() => removeExample(index)}>✕</button>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="form-group guardrails-group">
              <div className="label-with-toggle">
                <label>{t('guardrailsLabel')}</label>
                <label className="switch">
                  <input type="checkbox" checked={useGuardrails} onChange={e => setUseGuardrails(e.target.checked)} />
                  <span className="slider round"></span>
                </label>
              </div>
              <div className={`collapsible-wrapper ${useGuardrails ? 'expanded' : ''}`}>
                <div className="collapsible-inner">
                  <label className="checkbox-label">
                    <input type="checkbox" name="use_cove" checked={formData.use_cove} onChange={handleInputChange} />
                    {t('coveLabel')}
                  </label>
                  <label className="checkbox-label">
                    <input type="checkbox" name="use_self_refine" checked={formData.use_self_refine} onChange={handleInputChange} />
                    {t('selfRefineLabel')}
                  </label>
                </div>
              </div>
            </div>

            <button type="submit" className="btn-primary" disabled={status === 'compiling'}>
              {status === 'compiling' ? t('compilingBtn') : t('compileBtn')}
            </button>
          </form>
        </div>
      )}

      {currentStep === 2 && (
        <div className={`stage-2-wrapper ${llmResponse ? 'has-response' : ''}`}>
          <div className="stage-panel stage-2-main">
            <div className="stage-header">
              <button className="btn-secondary btn-small back-btn" onClick={() => setCurrentStep(1)}>
                {t('backBtn')}
              </button>
              <h2>{t('stage2Title')}</h2>
            </div>
            
            {compiledResult ? (
              <div className="preview-section">
                <h3>{t('compiledPromptHeader')}</h3>
                <pre className="code-block">{compiledResult}</pre>
                
                {(status === 'compiled' || status === 'executing') && (
                  <div className="hitl-actions mt-4">
                    <button 
                      className="btn-secondary" 
                      onClick={() => navigator.clipboard.writeText(compiledResult)}
                    >
                      {t('copyPromptBtn')}
                    </button>
                    <button 
                      className="btn-primary" 
                      onClick={handleExecute} 
                      disabled={status === 'executing'}
                    >
                      {status === 'executing' ? t('executingBtn') : t('sendLlmBtn')}
                    </button>
                    <button 
                      className="btn-success" 
                      onClick={async () => {
                        try {
                          const res = await fetch('/api/prompts/save_direct', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ template_id: templateId, compiled_prompt: compiledResult })
                          });
                          if(res.ok) setStatus('approved');
                        } catch (err) { console.error(err); }
                      }}
                      disabled={status === 'executing'}
                    >
                      {t('saveWithoutTestingBtn')}
                    </button>
                  </div>
                )}

              </div>
            ) : (
              <div className="empty-state">
                <p>{t('emptyPreview')}</p>
              </div>
            )}
          </div>

          {llmResponse && (
            <div className="stage-panel stage-2-response">
              <div className="response-section">
                <h3>{t('llmResponseHeader')}</h3>
                <pre className="code-block">{llmResponse}</pre>
                
                {status === 'review' && (
                  <div className="hitl-actions mt-4">
                    <button className="btn-success" onClick={handleApprove}>
                      {t('approveBtn')}
                    </button>
                    {formData.use_self_refine && (
                      <button className="btn-danger" onClick={handleRefine}>
                        {t('rejectBtn')}
                      </button>
                    )}
                  </div>
                )}
                {status === 'approved' && (
                  <div className="alert-success mt-4">
                    {t('successMsg')}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PromptBuilder;
