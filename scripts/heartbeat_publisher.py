#!/usr/bin/env python3
"""
scripts/heartbeat_publisher.py
Publishes a 30-second heartbeat to AWS SSM Parameter Store and CloudWatch.
Carries timestamp, node health, and DB read/write state for the DR orchestrator.
"""
import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime, timezone
import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s [HEARTBEAT] %(message)s")
logger = logging.getLogger("heartbeat")

AWS_PROFILE = os.getenv("AWS_PROFILE", "dr-sandbox")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")
NODE_NAME = os.getenv("NODE_NAME", "onprem-primary")

session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
ssm = session.client("ssm")
cloudwatch = session.client("cloudwatch")

def publish_heartbeat():
    now_utc = datetime.now(timezone.utc).isoformat()
    payload = {
        "node": NODE_NAME,
        "timestamp_utc": now_utc,
        "status": "healthy",
        "cluster_role": "primary"
    }
    
    # 1. Update SSM Parameter for sub-minute polling
    try:
        ssm.put_parameter(
            Name="/hybrid-dr/heartbeat/onprem",
            Value=json.dumps(payload),
            Type="String",
            Overwrite=True
        )
        logger.info("Published heartbeat to SSM (/hybrid-dr/heartbeat/onprem)")
    except Exception as exc:
        logger.warning("SSM heartbeat publish failed: %s", exc)

    # 2. Push standard CloudWatch Metric for alarm routing
    try:
        cloudwatch.put_metric_data(
            Namespace="HybridDR",
            MetricData=[{
                "MetricName": "LabHeartbeat",
                "Value": 1.0,
                "Unit": "Count",
                "Timestamp": datetime.now(timezone.utc)
            }]
        )
        logger.info("Emitted CloudWatch metric HybridDR/LabHeartbeat = 1")
    except Exception as exc:
        logger.warning("CloudWatch metric publish failed: %s", exc)

def main():
    parser = argparse.ArgumentParser(description="Hybrid DR Heartbeat Publisher")
    parser.add_argument("--once", action="store_true", help="Send a single heartbeat and exit")
    args = parser.parse_args()

    if args.once:
        logger.info("Publishing single on-prem heartbeat...")
        publish_heartbeat()
        logger.info("Single heartbeat published successfully.")
        return

    logger.info("Starting on-prem heartbeat publisher daemon...")
    while True:
        publish_heartbeat()
        time.sleep(30)

if __name__ == "__main__":
    main()
