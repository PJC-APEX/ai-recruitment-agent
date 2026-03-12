import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';

/**
 * ChatBox component for displaying conversation history
 */
const ChatBox = ({ messages, isLoading }) => {
  const chatEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {messages.length === 0 ? (
        <div className="flex items-center justify-center h-full text-gray-400">
          <div className="text-center">
            <svg
              className="w-16 h-16 mx-auto mb-4 opacity-50"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
              />
            </svg>
            <p className="text-lg font-medium mb-2">Start a Conversation</p>
            <p className="text-sm">
              Ask me to find candidates, score resumes, or rank applicants
            </p>
            <div className="mt-4 text-xs space-y-1">
              <p className="text-gray-500">Try asking:</p>
              <p className="text-primary-400">
                "Find candidates with 5 years of Python experience"
              </p>
              <p className="text-primary-400">
                "Rank candidates for a senior developer role"
              </p>
            </div>
          </div>
        </div>
      ) : (
        <>
          {messages.map((message, index) => (
            <MessageBubble
              key={index}
              message={message}
              isUser={message.isUser}
            />
          ))}

          {isLoading && (
            <div className="flex justify-start mb-4">
              <div className="bg-gray-700 rounded-lg px-4 py-3">
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce"></div>
                  <div
                    className="w-2 h-2 bg-primary-500 rounded-full animate-bounce"
                    style={{ animationDelay: '0.2s' }}
                  ></div>
                  <div
                    className="w-2 h-2 bg-primary-500 rounded-full animate-bounce"
                    style={{ animationDelay: '0.4s' }}
                  ></div>
                </div>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </>
      )}
    </div>
  );
};

export default ChatBox;
