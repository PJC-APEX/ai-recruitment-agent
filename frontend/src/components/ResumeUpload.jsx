import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';

/**
 * ResumeUpload component for uploading resume files
 */
const ResumeUpload = ({ onUpload, isUploading }) => {
  const [uploadStatus, setUploadStatus] = useState(null);

  const onDrop = useCallback(
    async (acceptedFiles) => {
      if (acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];

      // Validate file type
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setUploadStatus({
          type: 'error',
          message: 'Only PDF files are allowed',
        });
        return;
      }

      // Validate file size (10MB max)
      if (file.size > 10 * 1024 * 1024) {
        setUploadStatus({
          type: 'error',
          message: 'File size must be less than 10MB',
        });
        return;
      }

      try {
        setUploadStatus(null);
        await onUpload(file);
        setUploadStatus({
          type: 'success',
          message: `Successfully uploaded ${file.name}`,
        });

        // Clear success message after 3 seconds
        setTimeout(() => setUploadStatus(null), 3000);
      } catch (error) {
        setUploadStatus({
          type: 'error',
          message: error.message || 'Upload failed',
        });
      }
    },
    [onUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
    disabled: isUploading,
  });

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all ${
          isDragActive
            ? 'border-primary-500 bg-primary-500 bg-opacity-10'
            : 'border-gray-600 hover:border-primary-500 bg-gray-800'
        } ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} />

        <svg
          className="w-12 h-12 mx-auto mb-4 text-gray-400"
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

        {isUploading ? (
          <div>
            <p className="text-gray-300 mb-2">Uploading...</p>
            <div className="w-full bg-gray-700 rounded-full h-2 max-w-xs mx-auto">
              <div className="bg-primary-500 h-2 rounded-full animate-pulse w-full"></div>
            </div>
          </div>
        ) : (
          <>
            {isDragActive ? (
              <p className="text-primary-400 text-lg">Drop the resume here...</p>
            ) : (
              <>
                <p className="text-gray-300 text-lg mb-2">
                  Drag & drop a resume PDF here
                </p>
                <p className="text-gray-500 text-sm mb-4">or click to browse</p>
                <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors">
                  Select File
                </button>
              </>
            )}
          </>
        )}
      </div>

      {/* Status Messages */}
      {uploadStatus && (
        <div
          className={`mt-4 p-3 rounded-lg text-sm ${
            uploadStatus.type === 'success'
              ? 'bg-green-500 bg-opacity-20 text-green-400 border border-green-500'
              : 'bg-red-500 bg-opacity-20 text-red-400 border border-red-500'
          }`}
        >
          {uploadStatus.message}
        </div>
      )}
    </div>
  );
};

export default ResumeUpload;
