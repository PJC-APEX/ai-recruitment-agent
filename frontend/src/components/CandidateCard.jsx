
/**
 * CandidateCard component for displaying candidate information
 */
const CandidateCard = ({ candidate }) => {
  const {
    candidate_name,
    file_name,
    skills = [],
    match_score,
    relevance_score,
    years_experience,
    summary,
    matching_skills = [],
    missing_skills = [],
    rank,
  } = candidate;

  // Calculate display score (either match_score or relevance_score)
  const score = match_score !== undefined 
    ? match_score 
    : relevance_score !== undefined 
      ? Math.round(relevance_score * 100) 
      : null;

  // Determine score color
  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-400 bg-green-500';
    if (score >= 60) return 'text-yellow-400 bg-yellow-500';
    return 'text-red-400 bg-red-500';
  };

  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-gray-700 hover:border-primary-500 transition-all overflow-hidden">
      {/* Header */}
      <div className="flex items-start justify-between mb-3 gap-3">
        <div className="flex-1 min-w-0">
          {rank && (
            <div className="inline-block px-2 py-1 bg-primary-600 text-white text-xs font-bold rounded mb-2">
              Rank #{rank}
            </div>
          )}
          <h3 className="text-lg font-semibold text-white break-words">
            {candidate_name || 'Unknown Candidate'}
          </h3>
          <p className="text-sm text-gray-400 truncate" title={file_name}>{file_name}</p>
        </div>

        {/* Score Badge */}
        {score !== null && (
          <div
            className={`flex-shrink-0 px-3 py-2 rounded-lg bg-opacity-20 border ${getScoreColor(
              score
            )}`}
          >
            <div className="text-2xl font-bold">{score}</div>
            <div className="text-xs opacity-75">Score</div>
          </div>
        )}
      </div>

      {/* Experience */}
      {years_experience && (
        <div className="mb-3">
          <span className="text-sm text-gray-400">Experience: </span>
          <span className="text-sm text-white font-medium">
            {years_experience} years
          </span>
        </div>
      )}

      {/* Skills */}
      {(skills.length > 0 || matching_skills.length > 0) && (
        <div className="mb-3">
          <div className="text-xs text-gray-400 mb-2">Skills:</div>
          <div className="flex flex-wrap gap-2 overflow-x-auto">
            {(matching_skills.length > 0 ? matching_skills : skills).map(
              (skill, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 bg-primary-600 bg-opacity-30 text-primary-300 text-xs rounded border border-primary-600 whitespace-nowrap"
                >
                  {skill}
                </span>
              )
            )}
          </div>
        </div>
      )}

      {/* Missing Skills */}
      {missing_skills.length > 0 && (
        <div className="mb-3">
          <div className="text-xs text-gray-400 mb-2">Missing Skills:</div>
          <div className="flex flex-wrap gap-2 overflow-x-auto">
            {missing_skills.map((skill, idx) => (
              <span
                key={idx}
                className="px-2 py-1 bg-red-600 bg-opacity-20 text-red-400 text-xs rounded border border-red-600 whitespace-nowrap"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Summary */}
      {summary && (
        <div className="mt-3 pt-3 border-t border-gray-700">
          <p className="text-sm text-gray-300 break-words">{summary}</p>
        </div>
      )}
    </div>
  );
};

export default CandidateCard;
