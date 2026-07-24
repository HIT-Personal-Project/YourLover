from core.config import Config



config_path = "config.json"


def LoadConfig() -> Config:
    return Config()



def SaveConfig(config: Config) -> None:
    pass