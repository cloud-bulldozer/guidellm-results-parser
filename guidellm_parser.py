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
    
    # Extract token information from config.requests.data (list format)
    prompt_tokens = 0
    output_tokens = 0
    requests_data = config.get('requests', {}).get('data', '')
    if isinstance(requests_data, str):
        # Handle string format: "['prompt_tokens=256,output_tokens=512']"
        if '=' in requests_data:
            try:
                # Extract from string representation
                data_str = requests_data.strip("[]'\"")
                if '=' in data_str:
                    parts = data_str.split(',')
                    for part in parts:
                        if 'prompt_tokens=' in part:
                            prompt_tokens = int(part.split('=')[1])
                        elif 'output_tokens=' in part:
                            output_tokens = int(part.split('=')[1])
            except (ValueError, IndexError):
                pass
    elif isinstance(requests_data, list) and len(requests_data) > 0:
        # Handle list format: ["prompt_tokens=256,output_tokens=512"]
        data_str = requests_data[0]
        if '=' in data_str:
            parts = data_str.split(',')
            for part in parts:
                if 'prompt_tokens=' in part:
                    prompt_tokens = int(part.split('=')[1])
                elif 'output_tokens=' in part:
                    output_tokens = int(part.split('=')[1])
    
    # Extract strategy information
    strategy_config = config.get('strategy', {})
    strategy_type = strategy_config.get('type_', '')
    
    # Extract rate from args (it's a list)
    rate = 0
    rate_list = args.get('rate', [])
    if isinstance(rate_list, list) and len(rate_list) > 0:
        rate = int(rate_list[0])
    elif strategy_config.get('streams'):
        # Fallback to streams if rate not available
        rate = int(strategy_config.get('streams', 0))
    
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
        "backend_model": config.get('backend', {}).get('model', ''),
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

        for request in requests.get('successful', []):
            result.append({
                "metricName": "guidellmRequestResult",
                "timestamp": datetime.fromtimestamp(request.get('start_time', 0)).isoformat(),
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

        for request in requests.get('errored', []) + requests.get('incomplete', []):
            result.append({
                "metricName": "guidellmRequestError",
                "timestamp": datetime.fromtimestamp(request.get('start_time', 0)).isoformat(),
                "request_latency_seconds": request.get('request_latency', 0),
                "error": request.get('error', ''),
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
