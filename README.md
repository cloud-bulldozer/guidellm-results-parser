# GuideLLM Results Parser

A Python tool for parsing GuideLLM benchmark results and extracting key performance metrics. This parser processes benchmark JSON files and outputs structured data including aggregate statistics and per-request timeseries data, with optional OpenSearch indexing support.

## Features

- **Comprehensive Metrics Extraction**: Parses GuideLLM benchmark results and extracts key performance indicators
- **Timeseries Data**: Captures individual request timing data for detailed analysis
- **OpenSearch Integration**: Optionally index results directly to OpenSearch for visualization and analysis
- **Flexible Output**: Export to JSON files or stdout
- **Container Support**: Includes Containerfile for easy deployment

## Metrics Extracted

### Aggregate Metrics

The parser extracts the following aggregate metrics from benchmark runs:

#### Benchmark Identification
- `uuid`: Unique identifier for the benchmark run
- `job_name`: Name of the job/benchmark
- `sample`: Sample number for the benchmark
- `guidellm_version`: Version of GuideLLM used to generate the benchmark results
- `timestamp`: ISO 8601 timestamp of benchmark start
- `backend_model`: Model being benchmarked

#### Request Statistics
- `total_requests`: Total number of requests made
- `successful_requests`: Number of successful requests
- `errored_requests`: Number of failed requests
- `incomplete_requests`: Number of incomplete requests

#### Latency Metrics
- **Time to First Token (TTFT)**
  - `ttft_mean_ms`: Mean TTFT in milliseconds
  - `ttft_p99_ms`: 99th percentile TTFT
  
- **Inter Token Latency (ITL)**
  - `itl_mean_ms`: Mean ITL in milliseconds
  - `itl_p99_ms`: 99th percentile ITL

- **Request Latency**
  - `request_latency_mean_seconds`: Mean request latency in seconds
  - `request_latency_p95_seconds`: 95th percentile request latency in seconds
  - `request_latency_p99_seconds`: 99th percentile request latency in seconds

#### Throughput Metrics
- `throughput_mean_rps`: Mean requests per second
- `throughput_p95_rps`: 95th percentile RPS
- `throughput_p99_rps`: 99th percentile RPS

#### Token Metrics
- `prompt_tokens`: Number of prompt tokens
- `output_tokens`: Number of output tokens
- `tokens_per_second_mean`: Mean total tokens per second
- `tokens_per_second_p95`: 95th percentile tokens/sec
- `tokens_per_second_p99`: 99th percentile tokens/sec
- `output_tokens_per_second_mean`: Mean output tokens per second
- `output_tokens_per_second_p95`: 95th percentile output tokens/sec
- `output_tokens_per_second_p99`: 99th percentile output tokens/sec
- `time_per_output_token_mean_ms`: Mean time per output token
- `time_per_output_token_p95_ms`: 95th percentile time per token
- `time_per_output_token_p99_ms`: 99th percentile time per token

#### Strategy Information
- `strategy`: Benchmark strategy type (e.g., "constant")
- `rate`: Request rate (requests per second)

### Timeseries Data

For each individual request (successful or errored), the parser extracts:
- `timestamp`: ISO 8601 timestamp when request started
- `errored`: Boolean indicating if request failed
- `completed`: Boolean indicating if request completed
- `request_latency_seconds`: Total request latency in seconds
- `tokens_per_second`: Total tokens generated per second for this request
- `output_tokens_per_second`: Output tokens generated per second for this request
- `tpot_ms`: Time per output token in milliseconds
- `itl_ms`: Inter-token latency in milliseconds
- `ttft_ms`: Time to first token in milliseconds
- `uuid`: Benchmark UUID (for correlation)
- `job_name`: Job name (for correlation)

## Installation

### Container Build

Build the container image:
```bash
podman build -t guidellm-parser -f Containerfile .
# or with Docker
docker build -t guidellm-parser -f Containerfile .
```

## Usage

### Basic Usage

Parse a benchmark file and output to stdout:
```bash
python3 guidellm_parser.py --results benchmarks.json --uuid my-benchmark-001 --job-name "interactive-chat"
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
| `--output`, `-o` | No | stdout | Output file path |
| `--es-server` | No | - | OpenSearch endpoint URL (e.g., http://localhost:9200) |
| `--es-index` | No | - | OpenSearch index name |

## Output Format

The parser outputs a JSON array where:
- The **first element** is the aggregate summary metrics
- **Subsequent elements** are timeseries entries for individual requests

### Example Output

```json
[
  {
    "uuid": "c054eaf6-7b10-4dd5-a462-fbc010f7b09d",
    "job_name": "interactive-chat",
    "sample": 0,
    "guidellm_version": "0.5.2",
    "timestamp": "2025-09-23T23:59:06.125779",
    "strategy": "constant",
    "rate": 10.0,
    "total_requests": 609,
    "successful_requests": 586,
    "errored_requests": 0,
    "incomplete_requests": 23,
    "prompt_tokens": "128",
    "output_tokens": "128",
    "backend_model": "Qwen/Qwen3-0.6B",
    "ttft_mean_ms": 1006.2143587008272,
    "ttft_p99_ms": 1019.4225311279297,
    "itl_mean_ms": 10.423929083078537,
    "itl_p99_ms": 10.578223100797398,
    "throughput_mean_rps": 9.777764697593275,
    "throughput_p95_rps": 12.67751159149574,
    "throughput_p99_rps": 14.158848470118016,
    "request_latency_mean_seconds": 2.3300955913986363,
    "request_latency_p95_seconds": 2.3453574180603027,
    "request_latency_p99_seconds": 2.3493130207061768,
    "tokens_per_second_mean": 2426.93797445331,
    "tokens_per_second_p95": 3785.4729241877258,
    "tokens_per_second_p99": 17772.474576271186,
    "output_tokens_per_second_mean": 1251.5371956866534,
    "output_tokens_per_second_p95": 3480.7502074688796,
    "output_tokens_per_second_p99": 8272.788954635109,
    "time_per_output_token_mean_ms": 10.342492137116988,
    "time_per_output_token_p95_ms": 10.460831224918365,
    "time_per_output_token_p99_ms": 10.495580732822418
  },
  {
    "timestamp": "2025-09-23T23:59:06.126977",
    "errored": false,
    "completed": true,
    "request_latency_seconds": 2.3312907218933105,
    "tokens_per_second": 108.09462656606951,
    "output_tokens_per_second": 54.90520714467022,
    "tpot_ms": 10.28873398900032,
    "itl_ms": 10.369747642457016,
    "ttft_ms": 1014.298677444458,
    "uuid": "c054eaf6-7b10-4dd5-a462-fbc010f7b09d",
    "job_name": "interactive-chat"
  },
  {
    "timestamp": "2025-09-23T23:59:06.126454",
    "errored": false,
    "completed": true,
    "request_latency_seconds": 2.334320545196533,
    "tokens_per_second": 102.81364335067946,
    "output_tokens_per_second": 54.83394312036238,
    "tpot_ms": 10.307451710104942,
    "itl_ms": 10.388612747192383,
    "ttft_ms": 1014.9099826812744,
    "uuid": "c054eaf6-7b10-4dd5-a462-fbc010f7b09d",
    "job_name": "interactive-chat"
  }
]
```

## Integration with GuideLLM

This parser is designed to work with benchmark results from [GuideLLM](https://github.com/vllm-project/guidellm), a performance evaluation tool for large language models. GuideLLM generates comprehensive benchmark results in JSON format, which this parser processes into a structured format suitable for analysis and visualization.

### Typical Workflow

1. Run GuideLLM benchmark:
   ```bash
   guidellm --model your-model --backend openai --rate 10 --max-duration 60s --output-format json > benchmarks.json
   ```

2. Parse the results:
   ```bash
   python3 guidellm_parser.py --results benchmarks.json --uuid benchmark-001 --job-name "Model Test" --output parsed_results.json
   ```

3. (Optional) Index to OpenSearch for visualization:
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

