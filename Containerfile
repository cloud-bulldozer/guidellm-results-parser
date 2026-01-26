FROM ghcr.io/vllm-project/guidellm:v0.5.2

USER root
RUN pip install opensearch-py
COPY --chmod=0755 guidellm_parser.py /usr/bin/guidellm_parser.py
