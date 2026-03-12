
/**
 * MessageBubble component for displaying individual chat messages
 */
const MessageBubble = ({ message, isUser }) => {
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[70%] rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-gray-700 text-gray-100'
        }`}
      >
        {/* Message header */}
        <div className="flex items-center mb-1">
          <span className="text-xs font-semibold opacity-75">
            {isUser ? 'You' : 'AI Assistant'}
          </span>
        </div>

        {/* Message content */}
        <div className="text-sm whitespace-pre-wrap break-words">
          {message.text}
        </div>

        {/* Timestamp */}
        {message.timestamp && (
          <div className="mt-1 text-xs opacity-60">
            {new Date(message.timestamp).toLocaleTimeString()}
          </div>
        )}

        {/* Candidates data if present */}
        {message.candidates && message.candidates.length > 0 && (
          <div className="mt-3 space-y-2">
            {message.candidates.map((candidate, idx) => (
              <div
                key={idx}
                className="bg-gray-800 bg-opacity-50 rounded p-2 text-xs"
              >
                <div className="font-semibold">
                  {candidate.candidate_name || 'Unknown'}
                </div>
                <div className="text-gray-400">{candidate.file_name}</div>
                <div className="text-primary-400">
                  Relevance: {(candidate.relevance_score * 100).toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
