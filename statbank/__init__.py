__version__ = "0.0.8"

__all__ = ["StatbankClient", "apidata", "apidata_all", "apidata_rotate"]

from .apidata import apidata, apidata_all, apidata_rotate
from .client import StatbankClient
