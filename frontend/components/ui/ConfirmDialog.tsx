"use client";

import React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { AlertTriangle, X } from "lucide-react";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "warning" | "primary";
  isLoading?: boolean;
  onConfirm: () => void | Promise<void>;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "danger",
  isLoading = false,
  onConfirm,
}: ConfirmDialogProps) {
  const confirmBtnClass =
    variant === "danger"
      ? "bg-rose-600 hover:bg-rose-500 text-white focus-visible:ring-rose-500 shadow-rose-900/40"
      : variant === "warning"
      ? "bg-amber-600 hover:bg-amber-500 text-white focus-visible:ring-amber-500 shadow-amber-900/40"
      : "bg-emerald-500 hover:bg-emerald-400 text-slate-950 focus-visible:ring-emerald-400 shadow-emerald-900/40";

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200 focus:outline-none">
          <div className="flex items-start gap-4">
            <div
              className={`h-11 w-11 shrink-0 rounded-2xl flex items-center justify-center border ${
                variant === "danger"
                  ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                  : variant === "warning"
                  ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                  : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
              }`}
            >
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <Dialog.Title className="text-lg font-bold text-white tracking-tight">
                {title}
              </Dialog.Title>
              <Dialog.Description className="mt-2 text-sm text-slate-400 leading-relaxed">
                {description}
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="text-slate-400 hover:text-white rounded-lg p-1 transition-colors"
                aria-label="Close dialog"
              >
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          <div className="mt-6 flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
            <Dialog.Close asChild>
              <button
                type="button"
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white rounded-xl hover:bg-slate-800 transition-colors cursor-pointer"
              >
                {cancelLabel}
              </button>
            </Dialog.Close>
            <button
              type="button"
              disabled={isLoading}
              onClick={async () => {
                await onConfirm();
              }}
              className={`px-5 py-2 text-sm font-semibold rounded-xl transition-all shadow-md cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${confirmBtnClass}`}
            >
              {isLoading ? "Processing..." : confirmLabel}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
