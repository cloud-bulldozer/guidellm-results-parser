# GuideLLM Results Parser

A Python tool for parsing GuideLLM benchmark results and extracting key performance metrics. This parser processes benchmark JSON files and outputs structured data including aggregate statistics and per-request timeseries data, with optional OpenSearch indexing support.

## Features

- **Comprehensive Metrics Extraction**: Parses GuideLLM benchmark results and extracts key performance indicators
- **Timeseries Data**: Captures individual request timing data for detailed analysis (opt-in via `--verbose`)
- **OpenSearch Integration**: Optionally index results directly to OpenSearch for visualization and analysis
- **Flexible Output**: Export to JSON files or stdout
- **Container Support**: Includes Containerfile for easy deployment

## Document Types

Each document includes a `metricName` field for unique identification when querying in OpenSearch:

| metricName | Description | When emitted |
|---|---|---|
| `guidellmBenchmarkSummary` | Aggregate metrics for the entire benchmark run | Always (1 per run) |
| `guidellmRequestResult` | Per-request metrics for each successful request | `--verbose` only |
| `guidellmRequestError` | Per-request info for each errored request | `--verbose` only |

## Metrics Extracted

### Summary Document (`guidellmBenchmarkSummary`)

#### Benchmark Identification
- `metricName`: `"guidellmBenchmarkSummary"`
- `uuid`: Unique identifier for the benchmark run
- `hostname`: Hostname of the machine that ran the parser
- `job_name`: Name of the job/benchmark
- `sample`: Sample number for the benchmark
- `guidellm_version`: Version of GuideLLM used
- `timestamp`: ISO 8601 timestamp of benchmark start
- `backend_model`: Model being benchmarked

#### Request Statistics
- `total_requests`: Total number of requests made
- `successful_requests`: Number of successful requests
- `errored_requests`: Number of failed requests
- `incomplete_requests`: Number of incomplete requests

#### Latency Metrics

All latency metrics include: mean, max, p50, p75, p90, p95, p99.

- **Time to First Token (TTFT)**
  - `ttft_mean_ms`, `ttft_max_ms`, `ttft_p50_ms`, `ttft_p75_ms`, `ttft_p90_ms`, `ttft_p95_ms`, `ttft_p99_ms`

- **Inter Token Latency (ITL)**
  - `itl_mean_ms`, `itl_max_ms`, `itl_p50_ms`, `itl_p75_ms`, `itl_p90_ms`, `itl_p95_ms`, `itl_p99_ms`

- **Request Latency**
  - `request_latency_mean_seconds`, `request_latency_max_seconds`, `request_latency_p50_seconds`, `request_latency_p75_seconds`, `request_latency_p90_seconds`, `request_latency_p95_seconds`, `request_latency_p99_seconds`

- **Time per Output Token**
  - `time_per_output_token_mean_ms`, `time_per_output_token_max_ms`, `time_per_output_token_p50_ms`, `time_per_output_token_p75_ms`, `time_per_output_token_p90_ms`, `time_per_output_token_p95_ms`, `time_per_output_token_p99_ms`

#### Throughput Metrics

All throughput metrics include: mean, max, p50, p75, p90, p95, p99.

- **Requests per Second**
  - `throughput_mean_rps`, `throughput_max_rps`, `throughput_p50_rps`, `throughput_p75_rps`, `throughput_p90_rps`, `throughput_p95_rps`, `throughput_p99_rps`

- **Tokens per Second**
  - `tokens_per_second_mean`, `tokens_per_second_max`, `tokens_per_second_p50`, `tokens_per_second_p75`, `tokens_per_second_p90`, `tokens_per_second_p95`, `tokens_per_second_p99`

- **Output Tokens per Second**
  - `output_tokens_per_second_mean`, `output_tokens_per_second_max`, `output_tokens_per_second_p50`, `output_tokens_per_second_p75`, `output_tokens_per_second_p90`, `output_tokens_per_second_p95`, `output_tokens_per_second_p99`

#### Token Configuration
- `prompt_tokens`: Number of prompt tokens per request
- `output_tokens`: Number of output tokens per request

#### Strategy Information
- `strategy`: Benchmark strategy type (e.g., "constant")
- `rate`: Request rate (requests per second)

### Per-Request Documents (verbose mode only)

#### Successful Requests (`guidellmRequestResult`)
- `metricName`: `"guidellmRequestResult"`
- `timestamp`: ISO 8601 timestamp when request started
- `status`: Request status
- `request_latency_seconds`: Total request latency in seconds
- `tokens_per_second`: Total tokens generated per second
- `output_tokens_per_second`: Output tokens generated per second
- `tpot_ms`: Time per output token in milliseconds
- `itl_ms`: Inter-token latency in milliseconds
- `ttft_ms`: Time to first token in milliseconds
- `uuid`, `job_name`, `sample`: Correlation fields

#### Errored Requests (`guidellmRequestError`)
- `metricName`: `"guidellmRequestError"`
- `timestamp`: ISO 8601 timestamp when request started
- `errored`: Boolean indicating request failed
- `completed`: Boolean indicating if request completed
- `uuid`, `job_name`: Correlation fields

## Installation

### Container Build

Build the container image:
```bash
podman build -t guidellm-parser -f Containerfile .
# or with Docker
docker build -t guidellm-parser -f Containerfile .
```

## Usage

### Basic Usage (summary only)

Parse a benchmark file and output the summary to stdout:
```bash
python3 guidellm_parser.py --results benchmarks.json --uuid my-benchmark-001 --job-name "interactive-chat"
```

### Verbose Mode (summary + per-request details)

Include individual request-level data for deeper investigation:
```bash
python3 guidellm_parser.py --results benchmarks.json --uuid my-benchmark-001 --job-name "interactive-chat" --verbose
```

### Save to File

Export results to a JSON file:
```bash
python3 guidellm_parser.py --results benchmarks.json --uuid my-benchmark-001 --job-name "interactive-chat" --output results.json
```

### Index to OpenSearch

Parse and index results directly to OpenSearch:
```bash
python3 guidellm_parser.py \
  --results benchmarks.json \
  --uuid my-benchmark-001 \
  --job-name "interactive-chat" \
  --es-server http://localhost:9200 \
  --es-index benchmark-results
```

With per-request details:
```bash
python3 guidellm_parser.py \
  --results benchmarks.json \
  --uuid my-benchmark-001 \
  --job-name "interactive-chat" \
  --es-server http://localhost:9200 \
  --es-index benchmark-results \
  --verbose
```

### Using with Container

```bash
podman run --rm \
  -v $(pwd):/data:Z \
  guidellm-parser \
  /usr/bin/guidellm_parser.py \
  --results /data/benchmarks.json \
  --uuid my-benchmark-001 \
  --job-name "interactive-chat" \
  --output /data/parsed_results.json
```

## Command-Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--results` | No | `benchmarks.json` | Path to the GuideLLM results file |
| `--uuid` | No | `""` | UUID for the benchmark run |
| `--job-name`, `-j` | No | `""` | Name of the benchmark job |
| `--sample`, `-s` | No | `0` | Sample number |
| `--output`, `-o` | No | stdout | Output file path |
| `--es-server` | No | - | OpenSearch endpoint URL (e.g., http://localhost:9200) |
| `--es-index` | No | - | OpenSearch index name |
| `--verbose`, `-v` | No | `false` | Include per-request details (successful and errored) |

## Output Format

The parser outputs a JSON array where:
- The **first element** is the aggregate summary (`metricName: "guidellmBenchmarkSummary"`)
- **Subsequent elements** (verbose mode only) are per-request entries (`metricName: "guidellmRequestResult"` or `"guidellmRequestError"`)

### Example Output (default, summary only)

```json
[
  {
    "metricName": "guidellmBenchmarkSummary",
    "uuid": "c054eaf6-7b10-4dd5-a462-fbc010f7b09d",
    "hostname": "benchmark-pod-0",
    "job_name": "interactive-chat",
    "sample": 0,
    "guidellm_version": "0.5.2",
    "timestamp": "2025-09-23T23:59:06.125779",
    "strategy": "constant",
    "rate": 10,
    "total_requests": 609,
    "successful_requests": 586,
    "errored_requests": 0,
    "incomplete_requests": 23,
    "prompt_tokens": 128,
    "output_tokens": 128,
    "backend_model": "Qwen/Qwen3-0.6B",
    "ttft_mean_ms": 1006.21,
    "ttft_max_ms": 1025.44,
    "ttft_p50_ms": 1005.89,
    "ttft_p75_ms": 1010.12,
    "ttft_p90_ms": 1015.33,
    "ttft_p95_ms": 1018.56,
    "ttft_p99_ms": 1019.42,
    "itl_mean_ms": 10.42,
    "itl_max_ms": 10.89,
    "itl_p50_ms": 10.39,
    "itl_p75_ms": 10.45,
    "itl_p90_ms": 10.52,
    "itl_p95_ms": 10.55,
    "itl_p99_ms": 10.58,
    "throughput_mean_rps": 9.78,
    "throughput_max_rps": 15.23,
    "throughput_p50_rps": 9.85,
    "throughput_p75_rps": 10.12,
    "throughput_p90_rps": 11.45,
    "throughput_p95_rps": 12.68,
    "throughput_p99_rps": 14.16,
    "request_latency_mean_seconds": 2.33,
    "request_latency_max_seconds": 2.38,
    "request_latency_p50_seconds": 2.33,
    "request_latency_p75_seconds": 2.34,
    "request_latency_p90_seconds": 2.34,
    "request_latency_p95_seconds": 2.35,
    "request_latency_p99_seconds": 2.35,
    "tokens_per_second_mean": 2426.94,
    "tokens_per_second_max": 19500.00,
    "tokens_per_second_p50": 108.50,
    "tokens_per_second_p75": 110.20,
    "tokens_per_second_p90": 112.45,
    "tokens_per_second_p95": 3785.47,
    "tokens_per_second_p99": 17772.47,
    "output_tokens_per_second_mean": 1251.54,
    "output_tokens_per_second_max": 9500.00,
    "output_tokens_per_second_p50": 54.80,
    "output_tokens_per_second_p75": 55.10,
    "output_tokens_per_second_p90": 55.45,
    "output_tokens_per_second_p95": 3480.75,
    "output_tokens_per_second_p99": 8272.79,
    "time_per_output_token_mean_ms": 10.34,
    "time_per_output_token_max_ms": 10.65,
    "time_per_output_token_p50_ms": 10.32,
    "time_per_output_token_p75_ms": 10.38,
    "time_per_output_token_p90_ms": 10.44,
    "time_per_output_token_p95_ms": 10.46,
    "time_per_output_token_p99_ms": 10.50
  }
]
```

### Example Per-Request Output (with --verbose)

```json
[
  { "metricName": "guidellmBenchmarkSummary", "...": "..." },
  {
    "metricName": "guidellmRequestResult",
    "timestamp": "2025-09-23T23:59:06.126977",
    "status": true,
    "request_latency_seconds": 2.331,
    "tokens_per_second": 108.09,
    "output_tokens_per_second": 54.91,
    "tpot_ms": 10.29,
    "itl_ms": 10.37,
    "ttft_ms": 1014.30,
    "uuid": "c054eaf6-7b10-4dd5-a462-fbc010f7b09d",
    "job_name": "interactive-chat",
    "sample": 0
  },
  {
    "metricName": "guidellmRequestError",
    "timestamp": "2025-09-23T23:59:30.445123",
    "errored": true,
    "completed": false,
    "uuid": "c054eaf6-7b10-4dd5-a462-fbc010f7b09d",
    "job_name": "interactive-chat"
  }
]
```

## OpenSearch Queries

Filter documents by type using the `metricName` field:

```json
// Get only summaries
{"query": {"term": {"metricName": "guidellmBenchmarkSummary"}}}

// Get only per-request results
{"query": {"term": {"metricName": "guidellmRequestResult"}}}

// Get only errors
{"query": {"term": {"metricName": "guidellmRequestError"}}}
```

## Integration with GuideLLM

This parser is designed to work with benchmark results from [GuideLLM](https://github.com/vllm-project/guidellm), a performance evaluation tool for large language models. GuideLLM generates comprehensive benchmark results in JSON format, which this parser processes into a structured format suitable for analysis and visualization.

### Typical Workflow

1. Run GuideLLM benchmark:
   ```bash
   guidellm --model your-model --backend openai --rate 10 --max-duration 60s --output-format json > benchmarks.json
   ```

2. Parse the results (summary only):
   ```bash
   python3 guidellm_parser.py --results benchmarks.json --uuid benchmark-001 --job-name "Model Test" --output parsed_results.json
   ```

3. Parse with full request detail:
   ```bash
   python3 guidellm_parser.py --results benchmarks.json --uuid benchmark-001 --job-name "Model Test" --output parsed_results.json --verbose
   ```

4. (Optional) Index to OpenSearch for visualization:
   ```bash
   python3 guidellm_parser.py --results benchmarks.json --uuid benchmark-001 --es-server http://opensearch:9200 --es-index llm-benchmarks
   ```

## Error Handling

The parser includes robust error handling for:
- Missing or invalid JSON files
- Missing benchmark data
- OpenSearch connection failures
- Invalid data structures

Errors are printed to stderr with descriptive messages, and the script exits with a non-zero status code on failure.

## Requirements

- Python 3.6+
- `opensearch-py` (for OpenSearch integration)

## License

This project is released under the [Apache License 2.0](LICENSE).

## Support

For issues or questions, please [open an issue](repository-url/issues) on GitHub.
