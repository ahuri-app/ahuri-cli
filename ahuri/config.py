import os
import json
from .utils import *

# Assigning Variables
home = os.getenv("LOCALAPPDATA") if os.name == "nt" else os.getenv("HOME")
_config = os.path.join(home, ".config")
config_dir = os.path.join(_config, "ahuri-cli")
config = os.path.join(config_dir, "config.json")
reset_str = """{
    "api_url": "http://18.169.99.65:81",
    "time_format": "%H:%M",
    "user": {
        "token": null
    },
    "ws_url": "ws://18.169.99.65:81/ws"
}"""

def reset(p=True, verbose=False) -> None:
    """
    Function to reset config.

    Args:
        p (bool, optional): whether to print main output or not. Defaults to True.
        verbose (bool, optional): whether show more output or not. Defaults to False.
    """
    if verbose:
        log("Writing config file")
    with open(config, "w") as configfile:
        configfile.write(reset_str)
    
    if p:
        print("Reset config file!")
    elif verbose:
        log("Reset config file!")

def check() -> None:
    """
    Function to check the config directories and config file when the program starts.
    """
    try:
        if os.path.exists(home):
            if os.path.exists(_config):
                if os.path.exists(config_dir):
                    if os.path.exists(config):
                        with open(config, "r") as configfile:
                            try:
                                if type(json.load(configfile)) != dict:
                                    raise TypeError
                            except:
                                print("Config file seems to be broken... Resetting config.")
                                broken = True
                            else:
                                broken = False
                        if broken:
                            reset(p=False)
                    else:
                        reset(p=False)
                else:
                    os.mkdir(config_dir)
                    reset(p=False)
            else:
                os.mkdir(_config)
                os.mkdir(config_dir)
                reset(p=False)
        else:
            os.mkdir(home)
            os.mkdir(_config)
            os.mkdir(config_dir)
            reset(p=False)
    except:
        pass

def get(variable: str, default=None, verbose=False):
    """
    Function to get value of a variable from the config
    file.

    Args:
        variable (str): variable name to get
        default (Any, optional): The default value that will be returned if the variable is not found. Defaults to None.
        verbose (bool, optional): whether show more output or not. Defaults to False.

    Returns:
        Any: default
    """
    if verbose:
        log("Reading config file")
    with open(config, "r") as configfile:
        configjson = json.load(configfile)
    result = configjson.get(variable)
    return default if result == None else result

def set(variable: str, value=None, verbose=False) -> dict:
    """
    Set value to a variable in config file.

    Args:
        variable (str): variable to set value to
        value (Any): value to set
        verbose (bool, optional): whether show more output or not. Defaults to False.

    Returns:
        dict: config in dictionary
    """
    if verbose:
        log("Reading config file")
    with open(config, "r") as configfile:
        configjson = json.load(configfile)
    configjson[variable] = value
    
    if verbose:
        log("Writing config file")
    with open(config, "w") as configfile:
        json.dump(configjson, configfile, sort_keys=True, indent=4)
    return configjson