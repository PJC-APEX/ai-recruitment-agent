/**
 * API service for communicating with the backend
 */

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Upload a resume PDF file
 * @param {File} file - PDF file to upload
 * @returns {Promise} - Upload response
 */
export const uploadResume = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/upload-resume', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

/**
 * Search for resumes matching a query
 * @param {string} query - Natural language query
 * @param {number} topK - Number of results to return
 * @returns {Promise} - Search results
 */
export const searchResumes = async (query, topK = 5) => {
  const response = await api.post('/search-resumes', {
    query,
    top_k: topK,
  });

  return response.data;
};

/**
 * Score a resume against a job description
 * @param {string} resumeText - Resume text content
 * @param {string} jobDescription - Job description
 * @returns {Promise} - Scoring results
 */
export const scoreResume = async (resumeText, jobDescription) => {
  const response = await api.post('/score-resume', {
    resume_text: resumeText,
    job_description: jobDescription,
  });

  return response.data;
};

/**
 * Rank candidates for a job
 * @param {string} jobDescription - Job description
 * @param {string} query - Optional search query
 * @param {number} topK - Number of candidates to rank
 * @returns {Promise} - Ranked candidates
 */
export const rankCandidates = async (jobDescription, query = null, topK = 5) => {
  const response = await api.post('/rank-candidates', {
    job_description: jobDescription,
    query,
    top_k: topK,
  });

  return response.data;
};

/**
 * Send a chat message
 * @param {string} message - User message
 * @param {Array} chatHistory - Previous chat history
 * @returns {Promise} - Chat response
 */
export const sendChatMessage = async (message, sessionId, chatHistory = []) => {
  const response = await api.post('/chat', {
    message,
    session_id: sessionId,
    chat_history: chatHistory,
  });

  return response.data;
};

/**
 * Get list of all resumes
 * @returns {Promise} - List of resumes
 */
export const listResumes = async () => {
  const response = await api.get('/resumes/list');
  return response.data;
};

/**
 * Get count of indexed resumes
 * @returns {Promise} - Resume count
 */
export const getResumeCount = async () => {
  const response = await api.get('/resumes/count');
  return response.data;
};

export default api;
