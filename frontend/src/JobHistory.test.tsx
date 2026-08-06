import {
  render,
  screen,
} from "@testing-library/react";

import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { getProcessingJobs } from "./api";
import { JobHistory } from "./JobHistory";


vi.mock("./api", () => ({
  getProcessingJobs: vi.fn(),
}));


const mockedGetProcessingJobs =
  vi.mocked(getProcessingJobs);


describe("JobHistory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });


  it("displays completed processing jobs", async () => {
    mockedGetProcessingJobs.mockResolvedValue([
      {
        id: "job-123",
        filename: "customers.csv",
        stored_filename: "stored-customers.csv",
        file_size_bytes: 1250,
        status: "completed",
        report: {
          row_count: 4,
          column_count: 4,
          columns: [
            "id",
            "name",
            "email",
            "age",
          ],
          data_types: {
            id: "int64",
            name: "object",
            email: "object",
            age: "int64",
          },
          missing_values: {
            id: 0,
            name: 0,
            email: 1,
            age: 0,
          },
          total_missing_values: 1,
          duplicate_rows: 1,
          numeric_summary: {},
        },
        error_message: null,
        started_at: "2026-08-06T20:00:00Z",
        completed_at: "2026-08-06T20:00:01Z",
        created_at: "2026-08-06T20:00:00Z",
        updated_at: "2026-08-06T20:00:01Z",
      },
    ]);

    render(<JobHistory />);

    expect(
      await screen.findByText("customers.csv"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("completed"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("4"),
    ).toBeInTheDocument();

    expect(
      screen.getAllByText("1"),
    ).toHaveLength(2);
  });


  it("displays an empty-state message", async () => {
    mockedGetProcessingJobs.mockResolvedValue([]);

    render(<JobHistory />);

    expect(
      await screen.findByText(
        "No processing jobs exist yet.",
      ),
    ).toBeInTheDocument();
  });


  it("displays failed-job information", async () => {
    mockedGetProcessingJobs.mockResolvedValue([
      {
        id: "job-failed",
        filename: "broken.csv",
        stored_filename: "stored-broken.csv",
        file_size_bytes: 100,
        status: "failed",
        report: null,
        error_message:
          "The uploaded file is not a valid CSV",
        started_at: "2026-08-06T20:00:00Z",
        completed_at: "2026-08-06T20:00:01Z",
        created_at: "2026-08-06T20:00:00Z",
        updated_at: "2026-08-06T20:00:01Z",
      },
    ]);

    render(<JobHistory />);

    expect(
      await screen.findByText("broken.csv"),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "The uploaded file is not a valid CSV",
      ),
    ).toBeInTheDocument();
  });
});
