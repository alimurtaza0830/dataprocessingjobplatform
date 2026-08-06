import {
  useEffect,
  useState,
  type FormEvent,
} from "react";

import {
  checkBackendReadiness,
  getProcessingJob,
  getProcessingReport,
  uploadCsv,
  type DataQualityReport,
  type ProcessingJob,
} from "./api";

import { JobHistory } from "./JobHistory";

import "./App.css";


type BackendStatus =
  | "checking"
  | "ready"
  | "unavailable";


function App() {
  const [backendStatus, setBackendStatus] =
    useState<BackendStatus>("checking");

  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

  const [job, setJob] =
    useState<ProcessingJob | null>(null);

  const [report, setReport] =
    useState<DataQualityReport | null>(null);

  const [isUploading, setIsUploading] =
    useState(false);

  const [errorMessage, setErrorMessage] =
    useState<string | null>(null);


  useEffect(() => {
    async function checkBackend() {
      try {
        await checkBackendReadiness();
        setBackendStatus("ready");
      } catch {
        setBackendStatus("unavailable");
      }
    }

    void checkBackend();
  }, []);


  useEffect(() => {
    if (
      !job ||
      !["pending", "processing"].includes(job.status)
    ) {
      return;
    }

    const intervalId = window.setInterval(
      async () => {
        try {
          const updatedJob =
            await getProcessingJob(job.id);

          setJob(updatedJob);

          if (updatedJob.status === "completed") {
            const reportResponse =
              await getProcessingReport(updatedJob.id);

            setReport(reportResponse.report);
            window.clearInterval(intervalId);
          }

          if (updatedJob.status === "failed") {
            setErrorMessage(
              updatedJob.error_message ??
              "CSV processing failed.",
            );

            window.clearInterval(intervalId);
          }
        } catch (error) {
          setErrorMessage(
            error instanceof Error
              ? error.message
              : "Could not retrieve job status.",
          );

          window.clearInterval(intervalId);
        }
      },
      1000,
    );

    return () => {
      window.clearInterval(intervalId);
    };
  }, [job]);


  async function handleUpload(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (!selectedFile) {
      setErrorMessage("Please select a CSV file.");
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);
    setReport(null);
    setJob(null);

    try {
      const createdJob =
        await uploadCsv(selectedFile);

      setJob(createdJob);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "CSV upload failed.",
      );
    } finally {
      setIsUploading(false);
    }
  }


  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">
          Cloud-native data processing
        </p>

        <h1>Data Quality Platform</h1>

        <p className="subtitle">
          Upload a CSV file and generate a
          background data-quality report.
        </p>
      </section>

      <section className="card">
        <div className="card-heading">
          <div>
            <h2>System status</h2>
            <p>
              React checks FastAPI, PostgreSQL and
              Redis before enabling uploads.
            </p>
          </div>

          <span
            className={`status status-${backendStatus}`}
          >
            {backendStatus}
          </span>
        </div>
      </section>

      <section className="card">
        <h2>Upload CSV</h2>

        <form
          className="upload-form"
          onSubmit={handleUpload}
        >
          <label htmlFor="csv-file">
            Select CSV file
          </label>

          <input
            id="csv-file"
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => {
              setSelectedFile(
                event.target.files?.[0] ?? null,
              );

              setJob(null);
              setReport(null);
              setErrorMessage(null);
            }}
          />

          {selectedFile && (
            <div className="selected-file">
              <strong>{selectedFile.name}</strong>
              <span>
                {selectedFile.size.toLocaleString()}
                {" bytes"}
              </span>
            </div>
          )}

          <button
            type="submit"
            disabled={
              !selectedFile ||
              isUploading ||
              backendStatus !== "ready"
            }
          >
            {isUploading
              ? "Uploading..."
              : "Upload and process"}
          </button>
        </form>

        {job && (
          <div className="job-result">
            <h3>Processing job</h3>

            <dl>
              <div>
                <dt>Job ID</dt>
                <dd>{job.id}</dd>
              </div>

              <div>
                <dt>Filename</dt>
                <dd>{job.filename}</dd>
              </div>

              <div>
                <dt>Status</dt>
                <dd>
                  <span
                    className={`job-status job-status-${job.status}`}
                  >
                    {job.status}
                  </span>
                </dd>
              </div>
            </dl>

            {["pending", "processing"].includes(
              job.status,
            ) && (
              <p className="processing-message">
                The worker is processing your CSV…
              </p>
            )}
          </div>
        )}

        {errorMessage && (
          <p className="error">
            {errorMessage}
          </p>
        )}
      </section>

      {report && (
        <section className="card">
          <h2>Data-quality report</h2>

          <div className="summary-grid">
            <article>
              <span>Rows</span>
              <strong>{report.row_count}</strong>
            </article>

            <article>
              <span>Columns</span>
              <strong>{report.column_count}</strong>
            </article>

            <article>
              <span>Missing values</span>
              <strong>
                {report.total_missing_values}
              </strong>
            </article>

            <article>
              <span>Duplicate rows</span>
              <strong>{report.duplicate_rows}</strong>
            </article>
          </div>

          <h3>Missing values by column</h3>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Column</th>
                  <th>Data type</th>
                  <th>Missing values</th>
                </tr>
              </thead>

              <tbody>
                {report.columns.map((column) => (
                  <tr key={column}>
                    <td>{column}</td>
                    <td>
                      {report.data_types[column]}
                    </td>
                    <td>
                      {report.missing_values[column]}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {Object.keys(
            report.numeric_summary,
          ).length > 0 && (
            <>
              <h3>Numeric statistics</h3>

              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Column</th>
                      <th>Minimum</th>
                      <th>Maximum</th>
                      <th>Mean</th>
                      <th>Median</th>
                    </tr>
                  </thead>

                  <tbody>
                    {Object.entries(
                      report.numeric_summary,
                    ).map(([column, values]) => (
                      <tr key={column}>
                        <td>{column}</td>
                        <td>{values.minimum}</td>
                        <td>{values.maximum}</td>
                        <td>
                          {values.mean?.toFixed(2)}
                        </td>
                        <td>{values.median}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      )}
      <JobHistory />
    </main>
  );
}


export default App;
