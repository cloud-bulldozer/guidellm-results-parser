#!/usr/bin/env python3
"""
Benchmark Results Parser with OpenSearch Support

This program parses the benchmarks.json file and extracts key performance metrics
including mean and P99 values for TTFT, ITL, throughput, and benchmark parameters.
Supports indexing the results to OpenSearch.
"""

import json
import sys
import argparse
import socket
from datetime import datetime
from typing import Dict, Any, Optional

from opensearchpy import OpenSearch
from opensearchpy.exceptions import ConnectionError, RequestError
from opensearchpy.helpers import bulk


def extract_token_config(spec: Dict[str, Any], config: Dict[str, Any]) -> tuple:
    """
    Extract the configured prompt/output token counts.

    guidellm >= 0.7 records the dataset spec as structured objects under
    config.spec.data, e.g. [{"kind": "synthetic_text", "prompt_tokens": 256,
    "output_tokens": 512, ...}]. Older releases embedded it as a
    "prompt_tokens=256,output_tokens=512" string on benchmark.config.requests.data.

    Args:
        spec: The top-level config.spec dictionary (empty on older releases)
        config: The per-benchmark config dictionary
    Returns:
        Tuple of (prompt_tokens, output_tokens)
    """
    for entry in spec.get('data', []) or []:
        if not isinstance(entry, dict):
            continue
        if entry.get('prompt_tokens') is not None or entry.get('output_tokens') is not None:
            return int(entry.get('prompt_tokens') or 0), int(entry.get('output_tokens') or 0)

    prompt_tokens = 0
    output_tokens = 0
    requests_data = config.get('requests', {})
    requests_data = requests_data.get('data', '') if isinstance(requests_data, dict) else ''
    if isinstance(requests_data, list):
        # Handle list format: ["prompt_tokens=256,output_tokens=512"]
        requests_data = requests_data[0] if requests_data else ''
    if isinstance(requests_data, str) and '=' in requests_data:
        # Handle string format: "['prompt_tokens=256,output_tokens=512']"
        try:
            for part in requests_data.strip("[]'\"").split(','):
                if 'prompt_tokens=' in part:
                    prompt_tokens = int(part.split('=')[1])
                elif 'output_tokens=' in part:
                    output_tokens = int(part.split('=')[1])
        except (ValueError, IndexError):
            pass

    return prompt_tokens, output_tokens


def extract_rate(strategy_config: Dict[str, Any], spec: Dict[str, Any], args: Dict[str, Any]) -> int:
    """
    Extract the configured request rate.

    guidellm >= 0.7 records it on benchmark.config.strategy.rate (and on
    config.spec.profile.rate as a list). Older releases only had args.rate.

    Args:
        strategy_config: The benchmark.config.strategy dictionary
        spec: The top-level config.spec dictionary (empty on older releases)
        args: The top-level args dictionary (empty on newer releases)
    Returns:
        The rate as an integer, or 0 when unavailable
    """
    for candidate in (strategy_config.get('rate'),
                      (spec.get('profile') or {}).get('rate'),
                      args.get('rate'),
                      strategy_config.get('streams')):
        if isinstance(candidate, list):
            candidate = candidate[0] if candidate else None
        if candidate:
            return int(candidate)
    return 0


def parse_benchmarks(file_path: str, uuid: str, job_name: str, sample: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Parse the benchmarks.json file and extract key metrics.
    
    Args:
        file_path: Path to the benchmarks.json file
        uuid: UUID of the benchmark to parse
    Returns:
        Dictionary containing extracted metrics
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File {file_path} not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {e}")
        sys.exit(1)
    
    # Extract benchmark data
    benchmarks = data.get('benchmarks', [])
    if not benchmarks:
        print("Error: No benchmarks found in the file")
        sys.exit(1)
    
    # Get the first benchmark (assuming single benchmark for now)
    benchmark = benchmarks[0]
    
    # Extract metadata for guidellm_version
    metadata = data.get('metadata', {})
    guidellm_version = metadata.get('guidellm_version', '')
    
    # Extract config and args
    config = benchmark.get('config', {})
    args = data.get('args', {})
    # guidellm >= 0.7 moved the invocation spec to a top-level "config.spec"
    spec = data.get('config', {}).get('spec', {})

    prompt_tokens, output_tokens = extract_token_config(spec, config)

    # Extract strategy information
    strategy_config = config.get('strategy', {})
    strategy_type = strategy_config.get('type_', '')

    rate = extract_rate(strategy_config, spec, args)

    # Backend model lives on the benchmark config, or on the run spec in >= 0.7
    backend_model = config.get('backend', {}).get('model', '') or \
        spec.get('backend', {}).get('model', '')

    # Extract basic benchmark info
    summary = {
        # Benchmark identification
        "metricName": "guidellmBenchmarkSummary",
        "uuid": uuid,
        "hostname": socket.gethostname(),
        "job_name": job_name,
        "sample": sample,
        "guidellm_version": guidellm_version,
        
        # Timing information
        "timestamp": datetime.fromtimestamp(benchmark.get('start_time', 0)).isoformat(),
        
        # Strategy information
        "strategy": strategy_type,
        "rate": rate,
        
        # Request totals (from metrics)
        "total_requests": 0,
        "successful_requests": 0,
        "errored_requests": 0,
        "incomplete_requests": 0,
        
        # Token information
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        
        # Backend model (from config.backend.model)
        "backend_model": backend_model,
    }
    
    # Extract metrics from the metrics section
    metrics = benchmark.get('metrics', {})
    
    # Request totals (from metrics.request_totals)
    request_totals = metrics.get('request_totals', {})
    summary.update({
        "total_requests": request_totals.get('total', 0),
        "successful_requests": request_totals.get('successful', 0),
        "errored_requests": request_totals.get('errored', 0),
        "incomplete_requests": request_totals.get('incomplete', 0),
    })
    
    def extract_metric(metric_data, prefix, suffix=""):
        percentiles = metric_data.get('percentiles', {})
        sfx = f"_{suffix}" if suffix else ""
        return {
            f"{prefix}_mean{sfx}": metric_data.get('mean', 0),
            f"{prefix}_max{sfx}": metric_data.get('max', 0),
            f"{prefix}_p50{sfx}": percentiles.get('p50', 0),
            f"{prefix}_p75{sfx}": percentiles.get('p75', 0),
            f"{prefix}_p90{sfx}": percentiles.get('p90', 0),
            f"{prefix}_p95{sfx}": percentiles.get('p95', 0),
            f"{prefix}_p99{sfx}": percentiles.get('p99', 0),
        }

    summary.update(extract_metric(
        metrics.get('time_to_first_token_ms', {}).get('successful', {}), "ttft", "ms"))
    summary.update(extract_metric(
        metrics.get('inter_token_latency_ms', {}).get('successful', {}), "itl", "ms"))
    summary.update(extract_metric(
        metrics.get('requests_per_second', {}).get('successful', {}), "throughput", "rps"))
    summary.update(extract_metric(
        metrics.get('request_latency', {}).get('successful', {}), "request_latency", "seconds"))
    summary.update(extract_metric(
        metrics.get('tokens_per_second', {}).get('successful', {}), "tokens_per_second"))
    summary.update(extract_metric(
        metrics.get('output_tokens_per_second', {}).get('successful', {}), "output_tokens_per_second"))
    summary.update(extract_metric(
        metrics.get('time_per_output_token_ms', {}).get('successful', {}), "time_per_output_token", "ms"))
    
    result = [summary]

    if verbose:
        requests = benchmark.get('requests', {})

        # guidellm >= 0.7 renamed start_time to request_start_time and moved
        # the failure reason onto the request's info object.
        def request_start(request):
            return request.get('request_start_time') or request.get('start_time', 0)

        def request_error(request):
            return (request.get('info') or {}).get('error') or request.get('error', '')

        # benchmark.start_time/end_time bound the measured window, but the
        # request lists also carry the warmup and cooldown requests that
        # metrics.request_totals deliberately excludes. Drop them so the
        # per-request documents agree with the summary. Boundary requests may
        # be classified a request either way, so counts can differ by one.
        window_start = benchmark.get('start_time')
        window_end = benchmark.get('end_time')

        def in_window(request):
            if not window_start or not window_end:
                return True
            return window_start <= request_start(request) <= window_end

        for request in filter(in_window, requests.get('successful') or []):
            result.append({
                "metricName": "guidellmRequestResult",
                "timestamp": datetime.fromtimestamp(request_start(request)).isoformat(),
                "request_latency_seconds": request.get('request_latency', 0),
                "tokens_per_second": request.get('tokens_per_second', 0),
                "output_tokens_per_second": request.get('output_tokens_per_second', 0),
                "tpot_ms": request.get('time_per_output_token_ms', 0),
                "itl_ms": request.get('inter_token_latency_ms', 0),
                "ttft_ms": request.get('time_to_first_token_ms', 0),
                "uuid": uuid,
                "job_name": job_name,
                "sample": sample,
            })

        for request in filter(in_window, (requests.get('errored') or []) + (requests.get('incomplete') or [])):
            result.append({
                "metricName": "guidellmRequestError",
                "timestamp": datetime.fromtimestamp(request_start(request)).isoformat(),
                "request_latency_seconds": request.get('request_latency', 0),
                "error": request_error(request),
                "uuid": uuid,
                "job_name": job_name,
                "sample": sample,
            })

    return result


def index_to_opensearch(data: list, es_server: str, index_name: str) -> bool:
    """
    Index the parsed benchmark data to OpenSearch using bulk indexing.
    
    Args:
        data: List of parsed benchmark documents to index
        es_server: OpenSearch endpoint URL
        index_name: Name of the OpenSearch index
        
    Returns:
        True if successful, False otherwise
    """
    
    try:
        # Create OpenSearch client
        es = OpenSearch([es_server])
        
        # Test connection
        if not es.ping():
            print(f"Error: Cannot connect to OpenSearch at {es_server}", file=sys.stderr)
            return False
        
        # Prepare bulk actions
        actions = [
            {
                "_index": index_name,
                "_source": doc
            }
            for doc in data
        ]
        
        # Perform bulk indexing
        success, failed = bulk(es, actions, raise_on_error=False)
        
        if failed:
            print(f"Warning: {len(failed)} documents failed to index", file=sys.stderr)
        
        print(f"Successfully indexed {success} documents to {index_name}")
        return True
        
    except ConnectionError as e:
        print(f"Error: Failed to connect to OpenSearch: {e}", file=sys.stderr)
        return False
    except RequestError as e:
        print(f"Error: OpenSearch request failed: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: Unexpected error indexing to OpenSearch: {e}", file=sys.stderr)
        return False


def main():
    """Main function to parse benchmarks and output results."""
    parser = argparse.ArgumentParser(description='Parse benchmark results and optionally index to OpenSearch')
    parser.add_argument('--results', help='Path to the guidellm results file', default='benchmarks.json')
    parser.add_argument('--uuid', help='UUID of the benchmark', default='')
    parser.add_argument('--es-server', help='OpenSearch endpoint URL (e.g., http://localhost:9200)')
    parser.add_argument('--es-index', help='OpenSearch index name')
    parser.add_argument('--output', '-o', help='Output file path (default: stdout)')
    parser.add_argument('--job-name', '-j', help='Job Name', default='')
    parser.add_argument('--sample', '-s', help='Sample number', default=0)
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Include per-request details (successful and errored)')

    args = parser.parse_args()

    # Parse benchmarks
    results = parse_benchmarks(args.results, args.uuid, args.job_name, args.sample, args.verbose)
    
    # Index to OpenSearch if endpoint and index are provided
    if args.es_server and args.es_index:
        success = index_to_opensearch(results, args.es_server, args.es_index)
        if not success:
            sys.exit(1)
    else:
        # Output results
        output_json = json.dumps(results, indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output_json)
            print(f"Results written to {args.output}")
        else:
            print(output_json)


if __name__ == "__main__":
    main()
