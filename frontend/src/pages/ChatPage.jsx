import { useState } from 'react';
import CandidateCard from '../components/CandidateCard';
import ChatBox from '../components/ChatBox';
import ResumeUpload from '../components/ResumeUpload';
import { sendChatMessage, uploadResume, getUploadJob } from '../services/api';

/**
 * ChatPage - Main page with chat interface and resume upload
 */
const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [candidates, setCandidates] = useState([]);
  const [showUpload, setShowUpload] = useState(false);
  const [sessionId] = useState(() => {
    const saved = localStorage.getItem('recruitment_session_id');
    if (saved) return saved;
    const id = crypto.randomUUID();
    localStorage.setItem('recruitment_session_id', id);
    return id;
  });

  /**
   * Handle sending a chat message
   */
  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      text: inputMessage,
      isUser: true,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      // Build conversation history in OpenAI format
      // Convert messages to [{"role": "user"|"assistant", "content": "..."}]
      const chatHistory = messages.map(msg => ({
        role: msg.isUser ? "user" : "assistant",
        content: msg.text
      }));

      // Send message to API with full conversation history
      const response = await sendChatMessage(inputMessage, sessionId, chatHistory);

      // Add AI response
      const aiMessage = {
        text: response.response,
        isUser: false,
        timestamp: new Date().toISOString(),
        candidates: response.data?.candidates || null,
      };

      setMessages((prev) => [...prev, aiMessage]);

      // Update candidates panel if candidates are returned
      if (response.data?.candidates) {
        setCandidates(response.data.candidates);
      }
    } catch (error) {
      const errorMessage = {
        text: `Error: ${error.message || 'Failed to get response'}`,
        isUser: false,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle resume upload
   */
  const handleUpload = async (file) => {
    setIsUploading(true);

    try {
      const response = await uploadResume(file);

      if (response.status === 'queued' && response.job_id) {
        setMessages((prev) => [...prev, {
          text: `✓ ${response.file_name} 已接收，正在后台解析和索引（任务 ${response.job_id.slice(0, 12)}…）`,
          isUser: false,
          timestamp: new Date().toISOString(),
        }]);

        // Keep the existing UI simple while exposing the durable job state.
        // Stop polling on completion/failure or after one minute.
        for (let attempt = 0; attempt < 60; attempt += 1) {
          await new Promise((resolve) => setTimeout(resolve, 1000));
          const job = await getUploadJob(response.job_id);
          if (job.status === 'indexed') {
            setMessages((prev) => [...prev, {
              text: `✓ ${response.file_name} 已完成索引，共 ${job.chunks_created || 0} 个分块。`,
              isUser: false,
              timestamp: new Date().toISOString(),
            }]);
            break;
          }
          if (job.status === 'failed') {
            throw new Error(`后台索引失败：${job.error || 'Resume ingestion failed'}`);
          }
        }
        return;
      }

      // Synchronous/local fallback response
      const successMessage = {
        text: `✓ Successfully uploaded ${response.file_name}\n${response.chunks_created} chunks created and indexed.`,
        isUser: false,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, successMessage]);
    } catch (error) {
      const detail = error.response?.data?.detail || error.message || 'Upload failed';
      throw new Error(detail);
    } finally {
      setIsUploading(false);
    }
  };

  /**
   * Handle key press in input
   */
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex h-screen bg-gray-900">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white">
                Resume Screening System
              </h1>
              <p className="text-sm text-gray-400">
                AI-powered candidate search and matching
              </p>
            </div>
            <button
              onClick={() => setShowUpload(!showUpload)}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              {showUpload ? 'Hide Upload' : 'Upload Resume'}
            </button>
          </div>
        </header>

        {/* Upload Section (collapsible) */}
        {showUpload && (
          <div className="bg-gray-800 border-b border-gray-700 p-6">
            <ResumeUpload onUpload={handleUpload} isUploading={isUploading} />
          </div>
        )}

        {/* Chat Messages */}
        <ChatBox messages={messages} isLoading={isLoading} />

        {/* Input Area */}
        <div className="bg-gray-800 border-t border-gray-700 p-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-3">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about candidates, upload resumes, or request rankings..."
                className="flex-1 bg-gray-700 text-white rounded-lg px-4 py-3 resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
                rows="2"
                disabled={isLoading}
              />
              <button
                onClick={handleSendMessage}
                disabled={isLoading || !inputMessage.trim()}
                className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <svg
                  className="w-6 h-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                  />
                </svg>
              </button>
            </div>
            <div className="mt-2 text-xs text-gray-500">
              Press Enter to send, Shift+Enter for new line
            </div>
          </div>
        </div>
      </div>

      {/* Candidates Panel */}
      {candidates.length > 0 && (
        <div className="w-96 bg-gray-800 border-l border-gray-700 flex flex-col">
          <div className="p-4 border-b border-gray-700 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">
              Candidates ({candidates.length})
            </h2>
            <button
              onClick={() => setCandidates([])}
              className="p-1 hover:bg-gray-700 rounded transition-colors"
              title="Close panel"
            >
              <svg
                className="w-5 h-5 text-gray-400 hover:text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {candidates.map((candidate, idx) => (
              <CandidateCard key={idx} candidate={candidate} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatPage;
