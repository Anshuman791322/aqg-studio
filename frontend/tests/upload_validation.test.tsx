import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { ToastProvider } from "@/components/ui/ToastContext";
import NewDocumentPage from "@/app/documents/new/page";

jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
  }),
}));

describe("Document Upload Validation", () => {
  it("rejects files exceeding 50 MB", () => {
    render(
      <ToastProvider>
        <NewDocumentPage />
      </ToastProvider>
    );

    const oversizedFile = new File([new ArrayBuffer(55 * 1024 * 1024)], "oversized.pdf", {
      type: "application/pdf",
    });

    const fileInput = screen.getByLabelText(/Upload document file/i);
    fireEvent.change(fileInput, { target: { files: [oversizedFile] } });

    expect(
      screen.getByText(/File exceeds the maximum limit of 50 MB/i)
    ).toBeInTheDocument();
  });

  it("rejects unsupported file formats like .exe or .zip", () => {
    render(
      <ToastProvider>
        <NewDocumentPage />
      </ToastProvider>
    );

    const invalidFile = new File(["binary-content"], "malicious.exe", {
      type: "application/x-msdownload",
    });

    const fileInput = screen.getByLabelText(/Upload document file/i);
    fireEvent.change(fileInput, { target: { files: [invalidFile] } });

    expect(
      screen.getByText(/Unsupported file format/i)
    ).toBeInTheDocument();
  });

  it("accepts valid PDF files within the 50 MB limit", () => {
    render(
      <ToastProvider>
        <NewDocumentPage />
      </ToastProvider>
    );

    const validPdf = new File(["sample pdf content"], "chapter1.pdf", {
      type: "application/pdf",
    });

    const fileInput = screen.getByLabelText(/Upload document file/i);
    fireEvent.change(fileInput, { target: { files: [validPdf] } });

    expect(screen.queryByText(/Upload Error/i)).not.toBeInTheDocument();
    expect(screen.getByText(/chapter1.pdf/i)).toBeInTheDocument();
    expect(screen.getByText(/Ready for processing/i)).toBeInTheDocument();
  });
});
