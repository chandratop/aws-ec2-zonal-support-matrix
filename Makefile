.PHONY: refresh refresh-all

# Fetch all enabled regions (default profile)
refresh:
	python scripts/fetch_metadata.py

# Fetch specific regions only (faster, useful during dev)
# Usage: make refresh-regions REGIONS="us-east-1 eu-west-1"
refresh-regions:
	python scripts/fetch_metadata.py --regions $(REGIONS)

# Include disabled / opt-in regions
refresh-all:
	python scripts/fetch_metadata.py --all-regions

# Override AWS profile
# Usage: make refresh PROFILE=my-other-profile
ifdef PROFILE
PROFILE_ARG := --profile $(PROFILE)
refresh refresh-all refresh-regions: EXTRA := $(PROFILE_ARG)
endif
