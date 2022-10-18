#!/usr/bin/env python3

from .uttrekk import StatbankUttrekksBeskrivelse
from .transfer import StatbankTransfer
from .batchtransfer import StatbankBatchTransfer

from datetime import datetime as dt
from datetime import timedelta as td
import pandas as pd
import ipywidgets as widgets
import os

class StatbankClient:
    def __init__(self,
            loaduser = "",
            date: dt = dt.now() + td(days=1),
            shortuser: str = "",
            cc: str = "",
            bcc: str = "",
            overwrite: str = '1',
            approve: str = '2',
            validation: bool = True,
            ):
        self.loaduser = loaduser
        self.date = date
        self.shortuser = shortuser
        self.cc = cc
        self.bcc = bcc
        self.overwrite = overwrite
        self.approve = approve
        self.validation = validation
        self._validate_params_init()

    def __str__(self):
        pass

    def __repr__(self):
        pass

    def date_picker(self) -> None:
        self.datepicker =  widgets.DatePicker(
            description='Date for publish',
            disabled=False,
            value=self.date
        )
        display(self.datepicker)

    def set_date(self) -> None:
        self.date = self.datepicker.value
        print("Publishing date set to:", self.date)

    def get_description(self) -> StatbankUttrekksBeskrivelse:
        pass

    def validate(self, 
                 dfs: pd.DataFrame, 
                 table_id: str = "00000") -> dict:
        pass

    def validate_batch(self, data: dict) -> dict:
        pass

    def transfer(self,
                 dfs: pd.DataFrame, 
                 table_id: str = "00000") -> StatbankTransfer:
        pass

    def transfer_batch(self) -> StatbankBatchTransfer:
        pass

    def _validate_params_action(self) -> None:
        pass

    def _validate_params_init(self) -> None:
        if not self.loaduser or not isinstance(self.loaduser, str):
            raise TypeError('Please pass in "loaduser" as a string.')
        if not self.shortuser:
            self.shortuser = os.environ['JUPYTERHUB_USER'].split("@")[0]
        if not self.cc:
            self.cc = self.shortuser
        if not self.bcc:
            self.bcc = self.cc
        if self.overwrite not in ['0', '1']:
            raise ValueError("(String) Set overwrite to either '0' = no overwrite (dublicates give errors), or  '1' = automatic overwrite")
        if self.apporve not in ['0', '1', '2']:
            raise ValueError("(String) Set approve to either '0' = manual, '1' = automatic (immediatly), or '2' = JIT-automatic (just-in-time)")
            