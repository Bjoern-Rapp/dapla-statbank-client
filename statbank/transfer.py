#!/usr/bin/env python3

import json
import math
import os
import urllib
from datetime import datetime as dt
from datetime import timedelta as td

import pandas as pd
import requests as r

from .auth import StatbankAuth


class StatbankTransfer(StatbankAuth):
    """
    Class for talking with the "transfer-API",
    which actually recieves the data from the user and sends it to Statbank.
    ...

    Attributes
    ----------
    data : pd.DataFrame or list of pd.DataFrames
        Number of DataFrames needs to match the number of "deltabeller" in the uttakksbeskrivelse.
        Data-shape can be validated before transfer with the Uttakksbeskrivelses-class.
    loaduser : str
        Username for Statbanken, not the same as "tbf" or "common personal username" in other SSB-systems
    tabellid: str
        The numeric id of the table, matching the one found on the website.
        Should be a 5-length numeric-string. Alternativley it should be
        possible to send in the "hovedtabellnavn" instead of the tabellid.
    tbf : str
        The abbrivation of username at ssb. Three letters, like "cfc"
    publisering : str
        Date for publishing the transfer. Shape should be "yyyy-mm-dd", like "2022-01-01".
        Statbanken only allows publishing four months into the future?
    fagansvarlig1 : str
        First person to be notified by email of transfer. Defaults to the same as "tbf"
    fagansvarlig2 : str
        Second person to be notified by email of transfer. Defaults to the same as "tbf"
    overskriv_data : str
        "0" = no overwrite
        "1" = overwrite
    godkjenn_data : str
        "0" = manual approval
        "1" = automatic approval at transfer-time (immediately)
        "2" = JIT (Just In Time), approval right before publishing time
    validation : bool
        Set to True, if you want the python-validation code to run user-side.
        Set to False, if its slow and unnecessary.
    boundary : str
        String that defines the splitting of the body in the transfer-post-request.
        Kept here for uniform choice through the class.
    urls : dict
        Urls for transfer, observing the result etc.,
        built from environment variables in Dapla-environment
    headers: dict
        Might be deleted without warning.
        Temporarily holds the Authentication for the request.
    params: dict
        This dict will be built into the url in the post request.
        Keep it in this nice shape for later introspection.
    body: str
        The data parsed into the body-shape the Statbank-API expects in the transfer-post-request.
    response: requests.response
        The resulting response from the transfer-request. Headers might be deleted without warning.
    delay:
        Not editable, please dont try. Indicates if the Transfer has been sent yet, or not.

    Methods
    -------
    transfer():
        If Transfer was delayed, you can make the transfer by calling this method.
    _validate_original_parameters():
        Validating "pure" parameters on the way into the class.
    _build_urls():
        INHERITED - See description under StatbankAuth
    _build_headers():
        INHERITED - See description under StatbankAuth
    _build_params():
        Builds the params to be attached to the url
    _validate_datatype():
        Validates the data to be a dict of strings and Dataframes.
    _body_from_data():
        Converts data to .body for the transfer request to add to json/data/body.
    _handle_response():
        Handles the response back from the transfer post-request
    __init__():
    """

    def __init__(
        self,
        data: dict,
        tabellid: str = None,
        loaduser: str = "",
        bruker_trebokstaver: str = "",
        publisering: dt = dt.now() + td(days=1),  # noqa: B008
        fagansvarlig1: str = "",
        fagansvarlig2: str = "",
        auto_overskriv_data: str = "1",
        auto_godkjenn_data: str = "2",
        validation: bool = True,
        delay: bool = False,
        headers=None,
    ):
        self.data = data
        self.tabellid = tabellid
        if loaduser:
            self.loaduser = loaduser
        else:
            raise ValueError("You must set loaduser as a parameter")

        if bruker_trebokstaver:
            self.tbf = bruker_trebokstaver
        else:
            self.tbf = os.environ["JUPYTERHUB_USER"].split("@")[0]
        if fagansvarlig1:
            self.fagansvarlig1 = fagansvarlig1
        else:
            self.fagansvarlig1 = os.environ["JUPYTERHUB_USER"].split("@")[0]
        if fagansvarlig2:
            self.fagansvarlig2 = fagansvarlig2
        else:
            self.fagansvarlig2 = os.environ["JUPYTERHUB_USER"].split("@")[0]

        if isinstance(publisering, str):
            self.publisering = publisering
        else:
            self.publisering = publisering.strftime("%Y-%m-%d")

        self.overskriv_data = auto_overskriv_data
        self.godkjenn_data = auto_godkjenn_data
        self.validation = validation
        self.__delay = delay

        self.boundary = "12345"
        if validation:
            self._validate_original_parameters()

        self.urls = self._build_urls()
        if not self.delay:
            if headers:
                self.transfer(headers)
            else:
                self.transfer()

    def transfer(self, headers: dict = {}):  # noqa: B006
        """The headers-parameter is for a future implemention of a possible BatchTransfer, dont use it please."""
        # In case transfer has already happened, dont transfer again
        if hasattr(self, "oppdragsnummer"):
            raise ValueError(
                f"Already transferred?\n{self.urls['gui'] + self.oppdragsnummer} \nRemake the StatbankTransfer-object if intentional. "
            )
        if not headers:
            self.headers = self._build_headers()
        else:
            self.headers = headers
        try:
            self.params = self._build_params()
            self._validate_datatype()
            self.body = self._body_from_data()

            url_load_params = self.urls["loader"] + urllib.parse.urlencode(self.params)
            self.response = self._make_transfer_request(url_load_params)
            print(self.response)
            if self.response.status_code == 200:
                del (
                    self.response.request.headers
                )  # Auth is stored here also, for some reason
        finally:
            del self.headers  # Cleaning up auth-storing
            self.__delay = False
        self._handle_response()

    def __str__(self):
        if self.delay:
            return f"Overføring for statbanktabell {self.tabellid}. \nloaduser: {self.loaduser}.\nIkke overført enda."
        else:
            return f"""Overføring for statbanktabell {self.tabellid}.
    loaduser: {self.loaduser}.
    Publisering: {self.publisering}.
    Lastelogg: {self.urls['gui'] + self.oppdragsnummer}"""

    def __repr__(self):
        return f'StatbankTransfer([data], tabellid="{self.tabellid}", loaduser="{self.loaduser}")'

    @property
    def delay(self):
        return self.__delay

    def to_json(self, path: str = "") -> dict:
        """If path is provided, tries to write to it,
        otherwise will return a json-string for you to handle like you wish.
        """
        print(
            "Warning, some nested, deeper data-structures like dataframes and other class-objects will not be serialized"
        )
        json_content = json.dumps(self.__dict__, default=lambda o: "<not serializable>")
        # If path provided write to it, otherwise return the string-content
        if path:
            print(f"Writing to {path}")
            with open(path, mode="w") as json_file:
                json_file.write(json_content)
        else:
            return json.dumps(json_content)

    def _validate_original_parameters(self) -> None:
        # Date should not be on the weekend?

        if not isinstance(self.loaduser, str) or not self.loaduser:
            raise ValueError("Du må sette en loaduser korrekt")

        for _, tbf in enumerate([self.tbf, self.fagansvarlig1, self.fagansvarlig2]):

            if len(tbf) != 3 or not isinstance(tbf, str):
                raise ValueError(
                    f'Brukeren {tbf} - "trebokstavsforkortelse" - må være tre bokstaver...'
                )

        if not isinstance(self.publisering, dt):
            if not self._valid_date_form(self.publisering):
                raise ValueError("Skriv inn datoformen for publisering som 1900-01-01")

        if self.overskriv_data not in ["0", "1"]:
            raise ValueError(
                "(Strengverdi) Sett overskriv_data til enten '0' = ingen overskriving (dubletter gir feil), eller  '1' = automatisk overskriving"
            )

        if self.godkjenn_data not in ["0", "1", "2"]:
            raise ValueError(
                "(Strengverdi) Sett godkjenn_data til enten '0' = manuell, '1' = automatisk (umiddelbart), eller '2' = JIT-automatisk (just-in-time)"
            )

    def _validate_datatype(self):
        for deltabell_name, deltabell_data in self.data.items():
            if not isinstance(deltabell_name, str):
                raise TypeError(f"{deltabell_name} is not a string.")
            if not isinstance(deltabell_data, pd.DataFrame):
                raise TypeError(
                    f"Data for {deltabell_name}, must be a pandas DataFrame"
                )

    @staticmethod
    def _round_up(n, decimals=0):
        """Python uses "round to even" as default, wanted behaviour is "round up".
        So let's implement our own."""
        multiplier = 10**decimals
        return math.ceil(n * multiplier) / multiplier

    def _body_from_data(self) -> str:
        # Data should be a iterable of pd.DataFrames at this point, reshape to body
        for filename, elem in self.data.items():
            # Replace all nans in data
            elem = elem.fillna("")
            body = f"--{self.boundary}"
            body += f"\nContent-Disposition:form-data; filename={filename}"
            body += "\nContent-type:text/plain\n\n"
            body += elem.to_csv(sep=";", index=False, header=False)
        body += f"\n--{self.boundary}--"
        body = body.replace("\n", "\r\n")  # Statbank likes this?
        return body

    @staticmethod
    def _valid_date_form(date) -> bool:
        if (date[:4] + date[5:7] + date[8:]).isdigit() and (date[4] + date[7]) == "--":
            return True
        return False

    def _build_params(self) -> dict:
        if isinstance(self.publisering, dt):
            self.publisering = self.publisering.strftime("%Y-%m-%d")
        return {
            "initialier": self.tbf,
            "hovedtabell": self.tabellid,
            "publiseringsdato": self.publisering,
            "fagansvarlig1": self.fagansvarlig1,
            "fagansvarlig2": self.fagansvarlig2,
            "auto_overskriv_data": self.overskriv_data,
            "auto_godkjenn_data": self.godkjenn_data,
        }

    def _make_transfer_request(
        self,
        url_params: str,
    ):
        return r.post(url_params, headers=self.headers, data=self.body)

    def _handle_response(self) -> None:
        response_json = json.loads(self.response.text)
        if self.response.status_code == 200:
            response_message = response_json["TotalResult"]["Message"]
            try:
                self.oppdragsnummer = response_message.split("lasteoppdragsnummer:")[
                    1
                ].split(" =")[0]
            except Exception:
                raise ValueError(response_json)
            if not self.oppdragsnummer.isdigit():
                raise ValueError(
                    f"Lasteoppdragsnummer: {self.oppdragsnummer} er ikke ett rent nummer."
                )

            publiseringdato = dt.strptime(
                response_message.split("Publiseringsdato '")[1].split("',")[0],
                "%d.%m.%Y %H:%M:%S",
            )
            publiseringstime = int(
                response_message.split("Publiseringstid '")[1].split(":")[0]
            )
            publiseringsminutt = int(
                response_message.split("Publiseringstid '")[1]
                .split(":")[1]
                .split("'")[0]
            )
            publisering = publiseringdato + td(
                0, (publiseringstime * 3600 + publiseringsminutt * 60)
            )
            print(f"Publisering satt til: {publisering.strftime('%Y-%m-%d %H:%M')}")
            print(
                f"Følg med på lasteloggen (tar noen minutter): {self.urls['gui'] + self.oppdragsnummer}"
            )
            print(f"Og evt APIen?: {self.urls['api'] + self.oppdragsnummer}")
            self.response_json = response_json
        else:
            print(
                "Take a closer look at StatbankTransfer.response.text for more info about connection issues."
            )
            raise ConnectionError(response_json)
