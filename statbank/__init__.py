__version__ = "1.0.1"

__all__ = ["StatbankClient", "apidata", "apidata_all", "apidata_rotate"]

from .apidata import apidata, apidata_all, apidata_rotate
from .client import StatbankClient
