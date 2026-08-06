const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://localhost:8000";


export interface ReadinessResponse {
  status: string;
  service: string;
  dependencies: {
    database: string;
    redis: string;
  };
}


export interface NumericSummary {
  minimum: number | null;
  maximum: number | null;
  mean: number | null;
  median: number | null;
}


export interface DataQualityReport {
  row_count: number;
  column_count: number;
  columns: string[];
  data_types: Record<string, string>;
  missing_values: Record<string, number>;
  total_missing_values: number;
  duplicate_rows: number;
  numeric_summary: Record<string, NumericSummary>;
}


export interface ProcessingJob {
  id: string;
  filename: string;
  stored_filename: string | null;
  file_size_bytes: number | null;
  status: string;
  report: DataQualityReport | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}


export interface ProcessingReportResponse {
  job_id: string;
  filename: string;
  status: string;
  report: DataQualityReport;
}


async function readErrorMessage(
  response: Response,
): Promise<string> {
  try {
    const body = await response.json();

    if (typeof body.detail === "string") {
      return body.detail;
    }

    return JSON.stringify(body.detail);
  } catch {
    return `Request failed with status ${response.status}`;
  }
}


async function fetchJson<T>(
  url: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(url, options);

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json() as Promise<T>;
}


export function checkBackendReadiness():
Promise<ReadinessResponse> {
  return fetchJson<ReadinessResponse>(
    `${API_BASE_URL}/health/ready`,
  );
}


export function uploadCsv(
  file: File,
): Promise<ProcessingJob> {
  const formData = new FormData();

  formData.append("uploaded_file", file);

  return fetchJson<ProcessingJob>(
    `${API_BASE_URL}/jobs/upload`,
    {
      method: "POST",
      body: formData,
    },
  );
}


export function getProcessingJob(
  jobId: string,
): Promise<ProcessingJob> {
  return fetchJson<ProcessingJob>(
    `${API_BASE_URL}/jobs/${jobId}`,
  );
}


export function getProcessingReport(
  jobId: string,
): Promise<ProcessingReportResponse> {
  return fetchJson<ProcessingReportResponse>(
    `${API_BASE_URL}/jobs/${jobId}/report`,
  );
}

export function getProcessingJobs():
Promise<ProcessingJob[]> {
  return fetchJson<ProcessingJob[]>(
    `${API_BASE_URL}/jobs`,
  );
}