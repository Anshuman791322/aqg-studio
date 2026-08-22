"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useRef, DragEvent, ChangeEvent } from "react";
import { apiClient, ApiClientError } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { useToast } from "@/components/ui/ToastContext";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  FileCheck,
  FileType,
  FileUp,
  Loader2,
  UploadCloud,
  X,
} from "lucide-react";

const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024; // 50MB

const ALLOWED_MIME_TYPES: Record<string, string> = {
  "application/pdf": "PDF",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
  "application/msword": "DOC",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": "PPTX",
  "text/plain": "TXT",
  "text/markdown": "MD",
};

const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".doc", ".pptx", ".txt", ".md"];

export default function NewDocumentPage() {
  const router = useRouter();
  const { success, error: toastError } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const validateFile = (file: File): string | null => {
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return `File exceeds the maximum limit of 50 MB (selected file is ${(
        file.size /
        (1024 * 1024)
      ).toFixed(1)} MB).`;
    }

    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    const isAllowedExt = ALLOWED_EXTENSIONS.includes(ext);
    const isAllowedMime = file.type ? Boolean(ALLOWED_MIME_TYPES[file.type]) : false;

    if (!isAllowedExt && !isAllowedMime) {
      return `Unsupported file format. Please upload a PDF, Word document (.docx), PowerPoint (.pptx), or plain text (.txt / .md) file.`;
    }

    return null;
  };

  const handleFileSelect = (file: File) => {
    setErrorMessage(null);
    const validationError = validateFile(file);
    if (validationError) {
      setErrorMessage(validationError);
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleUploadAndProcess = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setErrorMessage(null);
    setUploadProgress(10);
    setCurrentStage("Initiating document upload session...");

    try {
      // 1. Initiate upload record in database
      const initiateRes = await apiClient.initiateDocumentUpload({
        original_filename: selectedFile.name,
        declared_mime_type: selectedFile.type || "application/octet-stream",
        size_bytes: selectedFile.size,
      });

      const { document_id, storage_path, upload_bucket } = initiateRes.data;
      setUploadProgress(35);
      setCurrentStage("Uploading file to secure storage...");

      // 2. Upload directly to Supabase Storage
      let uploadSucceeded = false;
      try {
        const supabase = createClient();
        const { error: storageError } = await supabase.storage
          .from(upload_bucket)
          .upload(storage_path, selectedFile, {
            contentType: selectedFile.type || "application/octet-stream",
            upsert: true,
          });

        if (!storageError) {
          uploadSucceeded = true;
        }
      } catch {
        // Fallback to direct backend processing if client storage fails
      }

      setUploadProgress(65);

      if (uploadSucceeded) {
        // 3. Mark complete in backend
        setCurrentStage("Verifying storage integrity...");
        await apiClient.completeDocumentUpload(document_id);
      }

      // 4. Enqueue document extraction & chunking workflow
      setCurrentStage("Queueing 7-node LangGraph parsing workflow...");
      setUploadProgress(85);

      await apiClient.processDocument(document_id, uploadSucceeded ? undefined : selectedFile);

      setUploadProgress(100);
      setCurrentStage("Document queued for knowledge analysis!");
      success("Document uploaded and queued for processing!");

      // Route to document detail view
      setTimeout(() => {
        router.push(`/documents/${document_id}`);
      }, 500);
    } catch (err: unknown) {
      setIsProcessing(false);
      const msg =
        err instanceof ApiClientError
          ? err.message
          : err instanceof Error
          ? err.message
          : "Failed to upload document. Please check your connection and try again.";
      setErrorMessage(msg);
      toastError(msg);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto space-y-8">
        {/* Navigation & Header */}
        <div>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-white transition mb-4"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
          <div className="space-y-1">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Upload Learning Material
            </h1>
            <p className="text-sm text-slate-400">
              Upload course material to be parsed, chunked, and analyzed for assessment generation.
            </p>
          </div>
        </div>

        {/* Upload Limits & Specs Banner */}
        <div className="p-5 rounded-3xl bg-slate-900/40 border border-slate-800/80 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center shrink-0">
              <FileType className="h-4 w-4" />
            </div>
            <div>
              <div className="font-semibold text-slate-200">Supported Formats</div>
              <div className="text-slate-500">PDF, DOCX, PPTX, TXT, MD</div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-xl bg-sky-500/10 text-sky-400 border border-sky-500/20 flex items-center justify-center shrink-0">
              <UploadCloud className="h-4 w-4" />
            </div>
            <div>
              <div className="font-semibold text-slate-200">Max File Size</div>
              <div className="text-slate-500">50 MB per file</div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/20 flex items-center justify-center shrink-0">
              <CheckCircle2 className="h-4 w-4" />
            </div>
            <div>
              <div className="font-semibold text-slate-200">Privacy & Security</div>
              <div className="text-slate-500">Private Supabase RLS Storage</div>
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div
            role="alert"
            className="p-4 rounded-2xl bg-rose-950/80 border border-rose-500/40 text-rose-200 text-xs flex items-start gap-3 animate-in fade-in"
          >
            <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="font-semibold">Upload Error</div>
              <div className="mt-0.5 leading-relaxed">{errorMessage}</div>
            </div>
            <button
              type="button"
              onClick={() => setErrorMessage(null)}
              className="text-rose-400 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Drag & Drop Upload Container */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !isProcessing && fileInputRef.current?.click()}
          className={`relative rounded-3xl border-2 border-dashed p-8 sm:p-12 text-center transition-all cursor-pointer ${
            isDragging
              ? "border-emerald-500 bg-emerald-950/20 scale-[0.99]"
              : selectedFile
              ? "border-slate-700 bg-slate-900/60"
              : "border-slate-800 bg-slate-900/30 hover:border-slate-700 hover:bg-slate-900/50"
          } ${isProcessing ? "opacity-60 pointer-events-none" : ""}`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.doc,.pptx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.presentationml.presentation,text/plain"
            onChange={handleInputChange}
            className="hidden"
            aria-label="Upload document file"
          />

          {selectedFile ? (
            <div className="space-y-4 max-w-md mx-auto">
              <div className="h-14 w-14 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 mx-auto flex items-center justify-center">
                <FileCheck className="h-7 w-7" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white truncate">
                  {selectedFile.name}
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready for processing
                </p>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                }}
                className="text-xs text-slate-400 hover:text-rose-400 underline transition"
              >
                Choose a different file
              </button>
            </div>
          ) : (
            <div className="space-y-4 max-w-md mx-auto">
              <div className="h-14 w-14 rounded-2xl bg-slate-800 text-slate-400 mx-auto flex items-center justify-center">
                <UploadCloud className="h-7 w-7" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-semibold text-white">
                  Drag and drop your file here, or browse
                </h3>
                <p className="text-xs text-slate-400">
                  PDF, DOCX, PPTX, or TXT up to 50 MB
                </p>
              </div>
              <div className="pt-2">
                <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-slate-200 hover:bg-slate-700 transition">
                  <FileUp className="h-4 w-4 text-emerald-400" />
                  Select File
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Progress & Upload Action */}
        {isProcessing && (
          <div className="p-6 rounded-3xl border border-slate-800 bg-slate-900/60 space-y-4 animate-in fade-in">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-200 flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-emerald-400" />
                {currentStage}
              </span>
              <span className="font-mono text-emerald-400 font-bold">{uploadProgress}%</span>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        )}

        <div className="flex items-center justify-end gap-4 pt-4">
          <Link
            href="/dashboard"
            className="px-5 py-2.5 rounded-2xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            Cancel
          </Link>
          <button
            type="button"
            disabled={!selectedFile || isProcessing}
            onClick={handleUploadAndProcess}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-2xl text-xs font-semibold text-slate-950 bg-emerald-500 hover:bg-emerald-400 transition shadow-lg shadow-emerald-500/20 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {isProcessing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Processing Document...
              </>
            ) : (
              <>
                <FileUp className="h-4 w-4" />
                Upload and Ingest Document
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
