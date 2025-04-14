import json
import boto3
from collections import defaultdict


def get_regions(all_regions: bool = False) -> list[str]:
    """Get a list of available AWS regions. It will get the enabled regions by default."""
    return [
        _["RegionName"]
        for _ in boto3.client('ec2').describe_regions(AllRegions=all_regions)["Regions"]
    ]


def get_instance_types(region: str) -> list[str]:
    """Get a list of available EC2 instance types in a region."""
    return [
        _["InstanceType"]
        for page in boto3.client('ec2', region_name=region).get_paginator("describe_instance_types").paginate()
        for _ in page["InstanceTypes"]
    ]


def group_instance_types_by_family(instance_types: list[str]) -> dict[str, list[str]]:
    """Group instance types by family."""
    instance_types_by_family = defaultdict(list)

    for instance_type in instance_types:
        family = instance_type.split(".")[0]
        instance_types_by_family[family].append(instance_type)

    return dict(sorted(instance_types_by_family.items()))


def get_instance_az_availability(instance_type: str, region: str) -> list[str]:
    """Get the list of availability zones where an instance type is available in a region."""
    return sorted(
        [
            _["Location"][-1]
            for _ in boto3.client('ec2', region_name=region).describe_instance_type_offerings(
                LocationType="availability-zone",
                Filters=[{"Name": "instance-type", "Values": [instance_type]}]
            )["InstanceTypeOfferings"]
        ]
    )


if __name__ == "__main__":
    data = {}

    for region in get_regions():
        data[region] = {}
        instance_types = get_instance_types(region)
        instance_types_by_family = group_instance_types_by_family(instance_types)

        for instance_type_family in instance_types_by_family:
            data[region][instance_type_family] = {}

            for instance_type in instance_types_by_family[instance_type_family]:
                data[region][instance_type_family][instance_type] = get_instance_az_availability(instance_type, region)
                print(f"{region} - {instance_type_family} - {instance_type}: {data[region][instance_type_family][instance_type]}")

    with open("metadata/ec2_instance_types.json", "w") as f:
        json.dump(data, f, indent=4)
