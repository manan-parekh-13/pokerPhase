import os
from dotenv import load_dotenv


def load_environment(env):
    env_file = os.path.join('../environment', f"{env}.env")
    load_dotenv(dotenv_path=env_file, override=True)
