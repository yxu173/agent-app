from os import getenv

from agno.aws.app.fastapi import FastApi
from agno.aws.app.streamlit import Streamlit
from agno.aws.resource.ec2 import InboundRule, SecurityGroup
from agno.aws.resource.ecs import EcsCluster
# AwsReference removed - no longer needed without load balancer
from agno.aws.resource.s3 import S3Bucket
from agno.aws.resource.secret import SecretsManager
from agno.aws.resources import AwsResources
from agno.docker.resource.image import DockerImage
from agno.docker.resources import DockerResources

from workspace.settings import ws_settings

#
# -*- Resources for the Production Environment
# Optimized for 5-person team with minimal cloud costs
# - CPU: 256 (0.25 vCPU) - minimum for AWS Fargate
# - Memory: 512 MB - minimum for AWS Fargate  
# - Auto-scaling: 1-2 instances based on CPU utilization
# - Single worker processes to minimize resource usage
# - Direct access to services (no load balancer for cost savings)
#
# Estimated monthly cost for 5 users (24/7):
# - ECS Fargate: ~$15-25/month (0.25 vCPU + 0.5GB RAM)
# - Data transfer: ~$5-10/month
# - Total: ~$20-35/month (load balancer removed)
#
# Skip resource deletion when running `ag ws down` (set to True after initial deployment)
skip_delete = False
# Save resource outputs to workspace/outputs
save_output = True

# -*- Production image
prd_image = DockerImage(
    name=f"{ws_settings.image_repo}/{ws_settings.image_name}",
    tag="latest",  # use already-pushed image tag
    enabled=False,  # skip building; pull from ECR
    path=str(ws_settings.ws_root),
    platforms=["linux/amd64", "linux/arm64"],
    # Push images after building
    push_image=False,
)

# -*- S3 bucket for production data (set enabled=True when needed)
prd_bucket = S3Bucket(
    name=f"{ws_settings.prd_key}-storage",
    enabled=False,
    acl="private",
    skip_delete=skip_delete,
    save_output=save_output,
)

# -*- Secrets for production application
prd_secret = SecretsManager(
    name=f"{ws_settings.prd_key}-secrets",
    group="app",
    # Create secret from workspace/secrets/prd_app_secrets.yml
    secret_files=[ws_settings.ws_root.joinpath("workspace/secrets/prd_app_secrets.yml")],
    skip_delete=skip_delete,
    save_output=save_output,
)

# Load balancer removed to reduce costs - direct access to services
# -*- Security Group for the application (direct access without load balancer)
prd_sg = SecurityGroup(
    name=f"{ws_settings.prd_key}-sg",
    group="app",
    description="Security group for the production application - direct access",
    inbound_rules=[
        InboundRule(
            description="Allow HTTP traffic to FastAPI server",
            port=8000,
            cidr_ip="0.0.0.0/0",
        ),
        InboundRule(
            description="Allow HTTP traffic to Streamlit app",
            port=8501,
            cidr_ip="0.0.0.0/0",
        ),
    ],
    subnets=ws_settings.aws_subnet_ids,
    skip_delete=skip_delete,
    save_output=save_output,
)

# -*- ECS cluster
prd_ecs_cluster = EcsCluster(
    name=f"{ws_settings.prd_key}-cluster",
    ecs_cluster_name=ws_settings.prd_key,
    capacity_providers=["FARGATE"],
    skip_delete=skip_delete,
    save_output=save_output,
)

# -*- Build container environment
container_env = {
    "RUNTIME_ENV": "prd",
    # Get the OpenAI API key from the local environment
    "OPENAI_API_KEY": getenv("OPENAI_API_KEY"),
    "OPENROUTER_API_KEY": getenv("OPENROUTER_API_KEY"),
    # Enable monitoring
  #  "AGNO_MONITOR": "False",
  #  "AGNO_API_KEY": getenv("AGNO_API_KEY"),
    # SQLite database configuration
    "DB_FILE": "/tmp/agent_app.db",
    # Migrate database on startup using alembic
    "MIGRATE_DB": True,
}

# -*- Streamlit running on ECS
prd_streamlit = Streamlit(
    name=f"{ws_settings.prd_key}-ui-v3",
    group="app",
    image=prd_image,
    command="streamlit run ui/Home.py",
    port_number=8501,
    # Minimal resources for 5 users - ultra-low cost configuration
    ecs_task_cpu="256",  # 0.25 vCPU - minimum for Fargate
    ecs_task_memory="512",  # 0.5 GB RAM - minimum for Fargate
    ecs_service_count=1,  # Single instance for cost optimization
    ecs_cluster=prd_ecs_cluster,
    aws_secrets=[prd_secret],
    subnets=ws_settings.aws_subnet_ids,
    security_groups=[prd_sg],
    # Load balancer removed to reduce costs - direct access to service
    create_load_balancer=False,
    env_vars=container_env,
    skip_delete=skip_delete,
    save_output=save_output,
    # Do not wait for the service to stabilize
    wait_for_create=False,
    # Do not wait for the service to be deleted
    wait_for_delete=False,
    # Auto-scaling configuration for cost optimization
    auto_scaling_min_capacity=1,  # Minimum 1 instance
    auto_scaling_max_capacity=2,  # Maximum 2 instances for 5 users
    auto_scaling_target_cpu_utilization=70,  # Scale up at 70% CPU
)

# -*- FastApi running on ECS
prd_fastapi = FastApi(
    name=f"{ws_settings.prd_key}-api-v3",
    group="api",
    image=prd_image,
    command="uvicorn api.main:app --workers 1 --timeout-keep-alive 30",  # Single worker with optimized keep-alive
    port_number=8000,
    # Minimal resources for 5 users - ultra-low cost configuration
    ecs_task_cpu="256",  # 0.25 vCPU - minimum for Fargate
    ecs_task_memory="512",  # 0.5 GB RAM - minimum for Fargate
    ecs_service_count=1,  # Single instance for cost optimization
    ecs_cluster=prd_ecs_cluster,
    aws_secrets=[prd_secret],
    subnets=ws_settings.aws_subnet_ids,
    security_groups=[prd_sg],
    # Load balancer removed to reduce costs - direct access to service
    create_load_balancer=False,
    health_check_path="/v1/health",
    env_vars=container_env,
    skip_delete=skip_delete,
    save_output=save_output,
    # Do not wait for the service to stabilize
    wait_for_create=False,
    # Do not wait for the service to be deleted
    wait_for_delete=False,
    # Auto-scaling configuration for cost optimization
    auto_scaling_min_capacity=1,  # Minimum 1 instance
    auto_scaling_max_capacity=2,  # Maximum 2 instances for 5 users
    auto_scaling_target_cpu_utilization=70,  # Scale up at 70% CPU
)

# -*- Production DockerResources
prd_docker_resources = DockerResources(
    env=ws_settings.prd_env,
    network=ws_settings.ws_name,
    resources=[prd_image],
)

# -*- Production AwsResources
prd_aws_config = AwsResources(
    env=ws_settings.prd_env,
    apps=[prd_streamlit, prd_fastapi],
    resources=(
        prd_sg,
        prd_secret,
        prd_ecs_cluster,
        prd_bucket,
    ),
)
