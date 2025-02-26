import click
import logging
from .preprocess import find_gpp_path

def gpp_preprocess(enable_exec: bool=False):
    gpppath = find_gpp_path()

