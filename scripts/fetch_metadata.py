#!/usr/bin/env python3
"""
Fetch EC2 instance type AZ availability for all enabled AWS regions.

Uses DescribeInstanceTypeOfferings (LocationType=availability-zone) — one
paginated call per region instead of one call per instance type, making it
roughly 100-500x faster than the naive per-instance-type approach.

Usage:
    python scripts/fetch_metadata.py
    python scripts/fetch_metadata.py --regions us-east-1 eu-west-1
    python scripts/fetch_metadata.py --profile my-profile --all-regions

AWS CLI equivalent (single region / instance type check):
    aws ec2 describe-instance-type-offerings \
        --region eu-west-1 \
        --location-type availability-zone \
        --filters "Name=instance-type,Values=c8a.xlarge" \
        --query 'InstanceTypeOfferings[*].Location' \
        --output table \
        --profile aws-cloudport-administrator-109667701036
"""

import json
import argparse
from datetime import datetime, timezone
from collections import defaultdict

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound


DEFAULT_PROFILE = "aws-cloudport-administrator-109667701036"
DEFAULT_OUTPUT = "metadata/ec2_instance_types.json"


def get_regions(session: boto3.Session, all_regions: bool = False) -> list[str]:
    """Return sorted list of enabled (or all) AWS region names."""
    ec2 = session.client("ec2")
    return sorted(
        r["RegionName"]
        for r in ec2.describe_regions(AllRegions=all_regions)["Regions"]
    )


def fetch_region_offerings(session: boto3.Session, region: str) -> dict:
    """
    Return { family: { instance_type: [sorted_zone_letters] } } for a region.

    Fetches all AZ-level offerings in a single paginated sweep. The zone value
    stored is just the trailing letter (e.g. "a" from "eu-west-1a") so the
    matrix renders uniformly across regions.
    """
    ec2 = session.client("ec2", region_name=region)
    paginator = ec2.get_paginator("describe_instance_type_offerings")

    offerings: list[dict] = []
    for page in paginator.paginate(LocationType="availability-zone"):
        offerings.extend(page["InstanceTypeOfferings"])

    region_data: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    for item in offerings:
        instance_type = item["InstanceType"]   # e.g. "c8a.xlarge"
        zone_letter = item["Location"][-1]     # "a" from "eu-west-1a"
        family = instance_type.split(".")[0]   # "c8a"
        region_data[family][instance_type].append(zone_letter)

    return {
        family: {
            itype: sorted(set(azs))
            for itype, azs in sorted(types.items())
        }
        for family, types in sorted(region_data.items())
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch EC2 instance type AZ availability and write to JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
        help=f"AWS profile name (default: {DEFAULT_PROFILE})",
    )
    parser.add_argument(
        "--regions",
        nargs="+",
        metavar="REGION",
        help="Specific regions to fetch (default: all enabled regions)",
    )
    parser.add_argument(
        "--all-regions",
        action="store_true",
        help="Include disabled / opt-in regions",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    try:
        session = boto3.Session(profile_name=args.profile)
    except ProfileNotFound:
        print(f"Error: AWS profile '{args.profile}' not found in ~/.aws/credentials")
        raise SystemExit(1)

    try:
        regions = args.regions or get_regions(session, args.all_regions)
    except (ClientError, NoCredentialsError) as exc:
        print(f"Error listing regions: {exc}")
        raise SystemExit(1)

    print(f"Profile : {args.profile}")
    print(f"Regions : {len(regions)}")
    print()

    result: dict = {
        "_meta": {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "profile": args.profile,
            "region_count": len(regions),
            "errors": [],
        }
    }

    for i, region in enumerate(regions, 1):
        print(f"[{i:>3}/{len(regions)}] {region} ...", end=" ", flush=True)
        try:
            result[region] = fetch_region_offerings(session, region)
            families = len(result[region])
            instances = sum(len(v) for v in result[region].values())
            print(f"{instances} types / {families} families")
        except ClientError as exc:
            msg = exc.response["Error"]["Message"]
            print(f"SKIPPED — {msg}")
            result["_meta"]["errors"].append({"region": region, "error": msg})
        except Exception as exc:
            print(f"SKIPPED — {exc}")
            result["_meta"]["errors"].append({"region": region, "error": str(exc)})

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    errors = result["_meta"]["errors"]
    print(f"\nWritten → {args.output}")
    if errors:
        print(f"Skipped {len(errors)} region(s): {[e['region'] for e in errors]}")


if __name__ == "__main__":
    main()
