from os import getenv

from agno.docker.app.fastapi import FastApi
from agno.docker.app.streamlit import Streamlit
from agno.docker.resource.image import DockerImage
from agno.docker.resources import DockerResources

from workspace.settings import ws_settings

#
# -*- Resources for the Development Environment
#

# -*- Dev image
dev_image = DockerImage(
    name=f"{ws_settings.image_repo}/{ws_settings.image_name}",
    tag=ws_settings.dev_env,
    enabled=ws_settings.build_images,
    path=str(ws_settings.ws_root),
    # Do not push images after building
    push_image=ws_settings.push_images,
)

# -*- Container environment
container_env = {
    "RUNTIME_ENV": "dev",
    # Get the OpenAI API key and Exa API key from the local environment
    "OPENAI_API_KEY": getenv("OPENAI_API_KEY"),
   # "EXA_API_KEY": getenv("EXA_API_KEY"),
    # Enable monitoring
    #"AGNO_MONITOR": "True",
    #"AGNO_API_KEY": getenv("AGNO_API_KEY"),
    # SQLite database configuration
    "DB_FILE": "tmp/agent_app.db",
    # Migrate database on startup using alembic
    "MIGRATE_DB": True,
}

# -*- Streamlit running on port 8501:8501
dev_streamlit = Streamlit(
    name=f"{ws_settings.ws_name}-ui",
    image=dev_image,
    command="streamlit run ui/Home.py",
    port_number=8501,
    debug_mode=True,
    mount_workspace=True,
    streamlit_server_headless=True,
    env_vars=container_env,
    use_cache=True,
    # Read secrets from secrets/dev_app_secrets.yml
    secrets_file=ws_settings.ws_root.joinpath("workspace/secrets/dev_app_secrets.yml"),
)

# -*- FastApi running on port 8000:8000
dev_fastapi = FastApi(
    name=f"{ws_settings.ws_name}-api",
    image=dev_image,
    command="uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload",
    port_number=8000,
    debug_mode=True,
    mount_workspace=True,
    env_vars=container_env,
    use_cache=True,
    # Read secrets from secrets/dev_app_secrets.yml
    secrets_file=ws_settings.ws_root.joinpath("workspace/secrets/dev_app_secrets.yml"),
)

# -*- Dev DockerResources
dev_docker_resources = DockerResources(
    env=ws_settings.dev_env,
    network=ws_settings.ws_name,
    apps=[dev_streamlit, dev_fastapi],
)
