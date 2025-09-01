from pathlib import Path

from agno.workspace.settings import WorkspaceSettings

#
# We define workspace settings using a WorkspaceSettings object
# these values can also be set using environment variables
# Import them into your project using `from workspace.settings import ws_settings`
#
ws_settings = WorkspaceSettings(
    # Workspace name
    ws_name="agent-app",
    # Path to the workspace root
    ws_root=Path(__file__).parent.parent.resolve(),
    # -*- Workspace Environments
    dev_env="dev",
    prd_env="prd",
    # default env for `agno ws` commands
    default_env="dev",
    # -*- Image Settings
    # Repository for images
    image_repo="local",
    #image_repo="375553084988.dkr.ecr.eu-west-2.amazonaws.com",
    
    # 'Name:tag' for the image
    image_name="agent-app",
    # Build images locally
    build_images=True,
    # Push images to the registry
    push_images=True,  # Enable pushing images for production
    # Skip cache when building images
    skip_image_cache=False,
    # Force pull images
    force_pull_images=False,
    # -*- AWS settings
    # Region for AWS resources
    aws_region="eu-west-2",
    # Availability Zones for AWS resources
    aws_az1="eu-west-2a",
    aws_az2="eu-west-2b",
    # Subnets for AWS resources - using actual subnet IDs from your VPC
    aws_subnet_ids=["subnet-0b755cdc0ac9a5541", "subnet-0d709d59297102228"],
    # Security Groups for AWS resources - you need to provide your actual security group IDs
    # aws_security_group_ids=["sg-xyz", "sg-xyz"],
)
