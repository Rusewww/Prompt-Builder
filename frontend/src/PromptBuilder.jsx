import React, { useState } from 'react';

const PromptBuilder = () => {
  const [formData, setFormData] = useState({
    role: 'Act as a Senior QA Engineer',
    context: 'We are using Python and PyTest.',
    task: 'Write unit tests for the auth module.',
    reasoning_pattern: 'Chain-of-Draft',
    use_cove: true,
    use_self_refine: false,
    examples: []
  });

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
      const response = await fetch('/api/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      const data = await response.json();
      setCompiledResult(data.compiled_prompt);
      setTemplateId(data.template_id);
      setStatus('compiled');
      setLlmResponse('');
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
      {/* Stage 1: Configuration */}
      <div className="stage-panel stage-1">
        <h2>Stage 1: Configuration & Structuring</h2>
        <form onSubmit={handleCompile} className="config-form">
          <div className="form-group">
            <label>Role & Expertise:</label>
            <input type="text" name="role" value={formData.role} onChange={handleInputChange} required />
          </div>

          <div className="form-group">
            <label>Context Awareness:</label>
            <textarea name="context" value={formData.context} onChange={handleInputChange} rows="3" required />
          </div>

          <div className="form-group">
            <label>Task Description:</label>
            <textarea name="task" value={formData.task} onChange={handleInputChange} rows="3" required />
          </div>

          <div className="form-group">
            <label>Reasoning Strategy:</label>
            <select name="reasoning_pattern" value={formData.reasoning_pattern} onChange={handleInputChange}>
              <option value="Zero-Shot">Option A: Zero-Shot</option>
              <option value="Chain-of-Thought">Option B: Chain-of-Thought (CoT)</option>
              <option value="Chain-of-Draft">Option C: Chain-of-Draft (CoD)</option>
            </select>
          </div>

          <div className="form-group examples-group">
            <div className="examples-header">
              <label>Few-Shot Examples:</label>
              <button type="button" className="btn-secondary btn-small" onClick={addExample}>+ Add Example</button>
            </div>
            {formData.examples.map((ex, index) => (
              <div key={index} className="example-item">
                <input 
                  type="text" 
                  placeholder="Input" 
                  value={ex.input_text} 
                  onChange={(e) => handleExampleChange(index, 'input_text', e.target.value)} 
                  required 
                />
                <input 
                  type="text" 
                  placeholder="Output" 
                  value={ex.output_text} 
                  onChange={(e) => handleExampleChange(index, 'output_text', e.target.value)} 
                  required 
                />
                <button type="button" className="btn-danger btn-small" onClick={() => removeExample(index)}>✕</button>
              </div>
            ))}
          </div>

          <div className="form-group guardrails-group">
            <label>Guardrails:</label>
            <label className="checkbox-label">
              <input type="checkbox" name="use_cove" checked={formData.use_cove} onChange={handleInputChange} />
              Enable CoVe Fact-Check List
            </label>
            <label className="checkbox-label">
              <input type="checkbox" name="use_self_refine" checked={formData.use_self_refine} onChange={handleInputChange} />
              Enable Self-Refine Iteration
            </label>
          </div>

          <button type="submit" className="btn-primary" disabled={status === 'compiling'}>
            {status === 'compiling' ? 'Compiling...' : 'Compile Prompt'}
          </button>
        </form>
      </div>

      {/* Stage 2: Interactive Testing & HITL */}
      <div className="stage-panel stage-2">
        <h2>Stage 2: Interactive Testing & HITL</h2>
        
        {compiledResult ? (
          <div className="preview-section">
            <h3>Compiled Prompt</h3>
            <pre className="code-block">{compiledResult}</pre>
            
            {(status === 'compiled' || status === 'executing') && (
              <button 
                className="btn-primary mt-4" 
                onClick={handleExecute} 
                disabled={status === 'executing'}
              >
                {status === 'executing' ? 'Executing LLM...' : 'Send to LLM'}
              </button>
            )}

            {llmResponse && (
              <div className="response-section mt-6">
                <h3>LLM Response</h3>
                <pre className="code-block">{llmResponse}</pre>
                
                {status === 'review' && (
                  <div className="hitl-actions mt-4">
                    <button className="btn-success" onClick={handleApprove}>
                      Approve (No Hallucinations)
                    </button>
                    {formData.use_self_refine && (
                      <button className="btn-danger" onClick={handleRefine}>
                        Reject / Self-Refine
                      </button>
                    )}
                  </div>
                )}
                {status === 'approved' && (
                  <div className="alert-success mt-4">
                    Response Approved & Saved successfully!
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="empty-state">
            <p>Compile a prompt in Stage 1 to see the preview here.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default PromptBuilder;
