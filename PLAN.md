# Plan: Raise pp.server To 10/10 Project Quality

This plan turns the current solid codebase into a production-grade service by
hardening request handling, reducing command-execution risk, improving
operational behavior, and tightening CI/release guarantees.

Current baseline:

- `make quality` passes: ruff, format check, `ty`, `uv audit`, and tests.
- Test suite: 87 passing tests.
- Coverage: 99%.
- Main remaining gaps are production hardening, error semantics, process
  isolation, observability, and operational documentation.

## Suggested Implementation Order

1. API input validation and structured errors.
2. ZIP resource limits and conversion timeouts.
3. Shell-free subprocess execution and process isolation.
4. Queue concurrency safety.
5. Observability and operational health checks.
6. CI hardening and documentation.

## 1. Harden `/convert` Input Validation

### Problem

The `/convert` endpoint currently assumes valid form data and decodes the input
directly:

- Missing `data` can raise an internal exception.
- Invalid base64 can raise an internal exception.
- Malformed ZIP input is caught only indirectly inside conversion.
- Unsafe `cmd_options` raises `ValueError` below the route layer.
- Unknown converters currently produce an application-level `"ERROR"` response
  instead of a clear client error.

### Implementation

- Make `data` explicitly required in the FastAPI form declaration.
- Validate `converter` before creating a job directory.
- Validate `cmd_options` in the route layer and map invalid options to `400`.
- Decode base64 using strict validation.
- Verify the decoded payload is a ZIP before writing conversion state.
- Return clear HTTP errors for invalid client input:
  - `400` for invalid base64.
  - `400` for invalid ZIP.
  - `400` for unsafe command options.
  - `404` or `422` for unknown/unavailable converter.
- Add a small request-validation helper to keep the route readable.

### Tests

- Missing `data` returns FastAPI validation error.
- Invalid base64 returns `400`.
- Non-ZIP base64 payload returns `400`.
- Unknown converter returns a documented client error.
- Unsafe `cmd_options` returns `400`.
- Valid conversion path still passes.

### Acceptance Criteria

- No expected bad client input produces a `500`.
- Error responses are deterministic and documented.
- Existing valid clients keep working.

## 2. Replace Shell Command Execution

### Problem

`util.run()` uses `asyncio.create_subprocess_shell()`. Although
`cmd_options` is sanitized, shell execution remains a high-risk pattern because
converter commands are assembled as interpolated strings.

### Implementation

- Introduce a structured command representation in `config.toml`, for example:
  - `convert_args = ["prince", "{cmd_options}", "--baseurl", "{base_url}", ...]`
  - or split fixed converter arguments from user-provided options.
- Change `util.run()` to accept `list[str]` and call
  `asyncio.create_subprocess_exec()`.
- Parse user-supplied `cmd_options` with `shlex.split()` after validation.
- Keep a compatibility layer for existing string config while migrating each
  converter definition.
- Log a safely quoted command preview for diagnostics.
- Remove or strictly limit shell-string execution once all converters use argv.

### Tests

- Unit test that `util.run()` receives and executes argv lists.
- Test each converter command builder produces expected argv.
- Test unsafe shell metacharacters are rejected.
- Test quoted user options are parsed predictably.

### Acceptance Criteria

- Normal conversion no longer uses a shell.
- Shell metacharacters have no execution semantics.
- Converter command construction remains readable and testable.

## 3. Add ZIP Resource Limits

### Problem

ZIP extraction currently prevents path traversal, which is good, but it does
not enforce resource limits. A malicious or accidental oversized archive can
consume disk, CPU, memory, or inode resources.

### Implementation

- Add configurable limits:
  - Maximum encoded request size.
  - Maximum decoded ZIP size.
  - Maximum number of ZIP entries.
  - Maximum total uncompressed size.
  - Maximum single-file uncompressed size.
  - Maximum path length.
  - Optional allowed entry types or blocked special files.
- Validate ZIP metadata before extraction.
- During extraction, count actual extracted bytes as a second line of defense.
- Add settings through environment variables with documented defaults.
- Return `413 Payload Too Large` when limits are exceeded.

### Tests

- ZIP with too many files is rejected.
- ZIP with excessive total uncompressed size is rejected.
- ZIP with excessive single-file size is rejected.
- ZIP path traversal remains rejected.
- Valid realistic ZIP still converts.

### Acceptance Criteria

- Resource limits are enforced before expensive work starts.
- Limits are configurable without code changes.
- Rejections are logged with enough detail for operators.

## 4. Add Conversion Timeouts

### Problem

Converter subprocesses can hang or run for too long. The service currently waits
for process completion without a timeout.

### Implementation

- Add a configurable conversion timeout, for example
  `PP_CONVERSION_TIMEOUT_SECONDS`.
- Wrap subprocess execution with `asyncio.wait_for()`.
- On timeout:
  - Terminate the child process.
  - Escalate to kill if it does not exit quickly.
  - Capture partial stdout/stderr.
  - Return a structured timeout error.
- Include timeout duration in logs and metrics.

### Tests

- A command that sleeps beyond the timeout is terminated.
- Timeout response is stable and does not look like a successful conversion.
- Partial output is preserved when possible.
- Normal fast commands are unaffected.

### Acceptance Criteria

- No conversion can run indefinitely.
- Timed-out jobs are cleaned up safely.
- Operators can tune timeout without code changes.

## 5. Improve Process Isolation

### Problem

Converters process untrusted user-supplied HTML, CSS, XML, fonts, and images.
Even if command execution is safe, converter processes can still read files,
access network resources, or inherit sensitive environment variables depending
on the converter and deployment.

### Implementation

- Run subprocesses with an explicit minimal environment.
- Set `cwd` to the per-job work directory.
- Avoid passing unrelated environment variables to converters.
- Add optional environment allowlist configuration.
- Document recommended production isolation:
  - Containerized converter execution.
  - Non-root user.
  - Read-only filesystem outside spool directory.
  - Network egress policy if converters do not need network access.
- Consider per-converter isolation options where supported.

### Tests

- Subprocess receives only expected environment variables.
- Converter command runs with expected working directory.
- Existing converter discovery still works.

### Acceptance Criteria

- The default runtime environment is intentionally constrained.
- Production deployment guidance explains the remaining trust boundary.

## 6. Make Queue Cleanup Concurrency-Safe

### Problem

Queue cleanup is global and time-based. It may delete directories while another
request is using them if timestamps or cleanup timing line up badly. Job IDs are
timestamp-based and include the raw converter name.

### Implementation

- Use UUID-based job IDs instead of timestamp-only IDs.
- Sanitize converter names if they remain part of job paths.
- Add an active-job marker file or in-memory active-job registry.
- Make cleanup skip active jobs.
- Use atomic directory creation.
- Add cleanup error handling so one bad path does not abort the whole cleanup.
- Consider separating `incoming`, `active`, `done`, and `failed` job states.

### Tests

- Cleanup skips active job directories.
- Cleanup removes stale inactive directories.
- Cleanup tolerates missing paths or race-like deletion.
- Job ID generation cannot contain path separators.

### Acceptance Criteria

- Cleanup cannot delete a currently running job.
- Job paths are unambiguous and safe.
- Cleanup behavior is observable and tested.

## 7. Introduce Structured API Errors

### Problem

The conversion endpoint returns `{"status": "ERROR"}` for converter failures,
while other endpoints use HTTP exceptions. This makes client handling less
consistent and makes operational diagnosis harder.

### Implementation

- Define an error response model with fields such as:
  - `code`
  - `message`
  - `details`
  - `request_id`
  - `job_id`
- Use HTTP status codes consistently:
  - `400` invalid request.
  - `404` converter unavailable.
  - `413` payload too large.
  - `422` semantically invalid conversion request.
  - `504` conversion timeout.
  - `502` converter process failure.
  - `500` unexpected server error.
- Preserve compatibility if needed:
  - Option A: keep current success payload, improve only error HTTP status.
  - Option B: support legacy error envelope behind a compatibility flag.
- Document the final API error contract in OpenAPI and README.

### Tests

- Each major error type returns expected status and error code.
- Successful conversion response remains unchanged unless intentionally versioned.
- OpenAPI schema contains the documented error models.

### Acceptance Criteria

- API clients can handle failures by HTTP status and stable error code.
- Logs and responses can be correlated through request/job IDs.

## 8. Add Production Observability

### Problem

The service logs conversion activity, but lacks structured request correlation,
metrics, and health signals suitable for production monitoring.

### Implementation

- Add request ID middleware.
- Include request ID and job ID in conversion logs.
- Add structured log fields for:
  - converter name.
  - duration.
  - status.
  - timeout.
  - input size.
  - output size.
- Add optional metrics endpoint, for example Prometheus format:
  - conversion count by converter/status.
  - conversion duration histogram.
  - timeout count.
  - active job count.
- Split health checks:
  - `/health` for lightweight process health.
  - `/ready` for spool writability and optional converter availability.
  - `/converter-versions` remains diagnostic and potentially slower.

### Tests

- Request ID is present in responses.
- Logs include request/job correlation fields.
- Metrics increment on success and failure.
- Readiness fails when spool directory is not writable.

### Acceptance Criteria

- A production operator can answer: what failed, how often, how long it took,
  which converter was involved, and which request/job caused it.

## 9. Strengthen CI

### Problem

The local quality gate is strong, but CI can be improved. The SAST target uses
`|| true`, coverage has no enforced minimum, and package/container validation
can be more explicit.

### Implementation

- Make Bandit/SAST fail CI after reviewing and documenting intentional skips.
- Add coverage threshold, for example `--cov-fail-under=95`.
- Add package build validation:
  - `uv build`.
  - Inspect sdist/wheel contents.
  - Install built wheel in a clean environment.
- Add Docker build checks for maintained Dockerfiles.
- Add Python matrix only for supported stable Python versions.
- Cache `uv` dependencies in CI.
- Consider adding pre-commit in CI if contributors use hooks locally.

### Tests

- CI workflow runs lint, type check, audit, SAST, coverage, build, and tests.
- Build artifacts install and expose expected console scripts.
- Docker build jobs pass or are explicitly scoped to maintained images.

### Acceptance Criteria

- CI catches security, packaging, and coverage regressions.
- CI signal is actionable and not diluted by ignored failures.

## 10. Document Operational Limits And Deployment

### Problem

The README gives a good overview, but production operation needs explicit limits,
security assumptions, and deployment guidance.

### Implementation

- Document all environment variables:
  - spool directory.
  - ZIP limits.
  - conversion timeout.
  - converter-specific flags.
  - process environment allowlist.
- Document API behavior:
  - request format.
  - response format.
  - error codes.
  - size limits.
- Add production deployment guidance:
  - reverse proxy upload limits.
  - worker count.
  - spool volume sizing.
  - cleanup policy.
  - container isolation.
  - converter installation checks.
- Add troubleshooting section:
  - converter not found.
  - timeout.
  - malformed ZIP.
  - permission problems.
  - missing fonts/assets.
- Ensure docs and OpenAPI examples match implementation.

### Tests

- Generate OpenAPI after API changes.
- Add documentation examples to tests where practical.
- Verify documented environment defaults match code.

### Acceptance Criteria

- A new operator can deploy the service with clear security and sizing
  expectations.
- API clients can implement against documented examples without reading source.

## Final 10/10 Definition

The project reaches 10/10 when:

- `make quality` passes.
- Coverage remains at or above the configured threshold.
- Bad client input never produces accidental `500` responses.
- Conversion execution avoids shell interpretation.
- ZIP and subprocess resource limits are enforced.
- Queue cleanup is safe under concurrent requests.
- Error responses are structured and documented.
- Logs, metrics, health, and readiness are production useful.
- CI validates linting, typing, tests, coverage, security, packaging, and
  supported deployment artifacts.
- README/developer docs match the implemented behavior.
