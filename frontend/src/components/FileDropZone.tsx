"use client";

import { useCallback, useState } from "react";
import { Upload, X } from "lucide-react";

interface FileDropZoneProps {
  accept: string;
  onFileSelect: (file: File) => void;
  currentFile?: File | null;
  label?: string;
  className?: string;
}

export default function FileDropZone({
  accept,
  onFileSelect,
  currentFile,
  label = "Drop file here or click to browse",
  className = "",
}: FileDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      onFileSelect(files[0]);
    }
  }, [onFileSelect]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFileSelect(files[0]);
    }
  }, [onFileSelect]);

  const handleClear = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onFileSelect(null as any);
  }, [onFileSelect]);

  const inputId = `file-input-${Math.random().toString(36).substr(2, 9)}`;

  return (
    <div className={className}>
      <input
        type="file"
        accept={accept}
        onChange={handleFileInput}
        className="hidden"
        id={inputId}
      />
      
      <label
        htmlFor={inputId}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          panel p-6 border-dashed cursor-pointer transition-all
          flex flex-col items-center justify-center gap-3 min-h-[120px]
          ${isDragging ? "border-tf-accent bg-tf-accent/5 scale-105" : "hover:border-tf-border-active"}
        `}
      >
        {currentFile ? (
          <>
            <div className="flex items-center gap-3 w-full">
              <Upload className="w-5 h-5 text-tf-accent" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-mono text-white truncate">{currentFile.name}</div>
                <div className="text-xs text-gray-600 font-mono">
                  {(currentFile.size / 1024).toFixed(1)} KB
                </div>
              </div>
              <button
                type="button"
                onClick={handleClear}
                className="p-1 hover:bg-tf-alert/10 border border-tf-border hover:border-tf-alert transition-colors"
              >
                <X className="w-4 h-4 text-gray-500 hover:text-tf-alert" />
              </button>
            </div>
          </>
        ) : (
          <>
            <Upload className="w-8 h-8 text-gray-700" />
            <div className="text-center">
              <p className="text-sm font-mono text-gray-400">{label}</p>
              <p className="text-xs text-gray-600 font-mono mt-1">
                {accept.replace(/,/g, ", ")}
              </p>
            </div>
          </>
        )}
      </label>
    </div>
  );
}
