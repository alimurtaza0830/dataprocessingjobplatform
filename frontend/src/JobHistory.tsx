import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  getProcessingJobs,
  type ProcessingJob,
} from "./api";


export function JobHistory() {
  const [jobs, setJobs] =
    useState<ProcessingJob[]>([]);

  const [isLoading, setIsLoading] =
    useState(true);

  const [errorMessage, setErrorMessage] =
    useState<string | null>(null);


  const loadJobs = useCallback(async () => {
    try {
      const processingJobs =
        await getProcessingJobs();

      setJobs(processingJobs);
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Could not load processing jobs.",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);


  useEffect(() => {
    const initialLoadId = window.setTimeout(
      () => {
        void loadJobs();
      },
      0,
    );

    const intervalId = window.setInterval(
      () => {
        void loadJobs();
      },
      3000,
    );

    return () => {
      window.clearTimeout(initialLoadId);
      window.clearInterval(intervalId);
    };
  }, [loadJobs]);


  return (
    <section className="card history-card">
      <div className="card-heading">
        <div>
          <h2>Processing history</h2>

          <p>
            Previous CSV uploads and their current
            processing results.
          </p>
        </div>

        <button
          className="secondary-button"
          type="button"
          onClick={() => void loadJobs()}
        >
          Refresh
        </button>
      </div>

      {isLoading && (
        <p>Loading jobs…</p>
      )}

      {errorMessage && (
        <p className="error">
          {errorMessage}
        </p>
      )}

      {!isLoading &&
        !errorMessage &&
        jobs.length === 0 && (
          <p>No processing jobs exist yet.</p>
        )}

      {jobs.length > 0 && (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Status</th>
                <th>Rows</th>
                <th>Missing</th>
                <th>Duplicates</th>
                <th>Created</th>
              </tr>
            </thead>

            <tbody>
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td>
                    <div className="filename-cell">
                      <strong>
                        {job.filename}
                      </strong>

                      <small>{job.id}</small>
                    </div>
                  </td>

                  <td>
                    <span
                      className={
                        `job-status job-status-${job.status}`
                      }
                    >
                      {job.status}
                    </span>
                  </td>

                  <td>
                    {job.report?.row_count ?? "—"}
                  </td>

                  <td>
                    {
                      job.report
                        ?.total_missing_values ??
                      "—"
                    }
                  </td>

                  <td>
                    {
                      job.report
                        ?.duplicate_rows ??
                      "—"
                    }
                  </td>

                  <td>
                    {new Date(
                      job.created_at,
                    ).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {jobs.some(
        (job) => job.status === "failed",
      ) && (
        <div className="failure-list">
          <h3>Failed jobs</h3>

          {jobs
            .filter(
              (job) => job.status === "failed",
            )
            .map((job) => (
              <p key={job.id}>
                <strong>{job.filename}:</strong>
                {" "}
                {job.error_message ??
                  "Unknown processing error"}
              </p>
            ))}
        </div>
      )}
    </section>
  );
}
