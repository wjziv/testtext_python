from typing import Dict, Union
from bs4 import BeautifulSoup
from urllib import parse
import requests
import sys


class TouchstoneTests():
    def __init__(
        self,
        username: str,
        password: str,
        uri: str = 'https://touchstonetests.io',
        login_url: str = 'login',
        login_check_url: str = 'login_check',
        login_payload: dict = None,
        headers: dict = None,
    ):
        """Touchstone API Instance Class

        Unofficial Touchstone API Wrapper.

        Start connection to TouchstoneTests for automated data supply to your account.

        Example:
            with Touchstone(user, pass) as ts:
                ts.upload('filename.txt')

        Attributes:
            username (str): username
            password (str): password
            uri (str): root for all URLs
            login_url (str): url/uri with the login-form
            login_check_url (str): url/uri to send the login payload
            login_payload (dict): alternative payload to send the login page (optional)
            headers (dict): alternative headers to use in all requests (optional)
        """
        self.username = username
        self.password = password
        self.uri = uri
        self.login_url = '/'.join([self.uri, login_url])
        self.login_check_url = '/'.join([self.uri, login_check_url])
        self.login_payload = login_payload
        self.headers = headers

        self._session = None
        self.csrf_token = ''
        self.cookies = None
        self._get_session_tokens()

    def __enter__(self):
        """Begin Touchstone session connection.

        Along with the username and password, a CSRF token isnecessary for the initial payload.
        This is obtained in a quick visit to the main page.
        """
        def check_valid_redirect(response_url):
            mod_response_url = response_url.replace('http://', '').replace('https://', '').strip('/')
            mod_url = self.uri.replace('http://', '').replace('https://', '').strip('/')
            return mod_response_url == mod_url

        self.login_payload = self.login_payload or {
            '_csrf_token': self.csrf_token,
            '_username': self.username,
            '_password': self.password,
            '_submit': 'Log in'
        }

        self.headers = self.headers or {
            'Host': self.uri.replace('https://', ''),
            'Origin': self.uri,
            'Referrer': self.login_url,
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }

        session = requests.Session()
        login_response = session.post(
            self.login_check_url,
            data=self.login_payload,
            headers=self.headers,
            cookies=self.cookies
        )
        assert login_response.ok, requests.exceptions.HTTPError('Non-2XX Response.')
        assert check_valid_redirect(login_response.url), requests.exceptions.ConnectionError('Incorrect credentials.')
        self._session = session
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End Session connection.
        """
        self._session.close()

    def _get_session_tokens(self):
        response = requests.get(self.login_url)
        soup = BeautifulSoup(response.text)
        self.csrf_token = soup.find('input', {'name': '_csrf_token'}).get('value')
        self.cookies = response.cookies
    
    def request(
        self,
        url: str,
        method: str = 'POST',
        payload: dict = None,
        headers: dict = None,
        cookies: Union[dict, requests.cookies.RequestsCookieJar] = None,
        files: Union[str, bytes] = None
    ):
        """POST/GET request dispatcher.
        Unless otherwise specified, 
        """
        if not url.startswith('https://'):
            url = '/'.join([self.uri, url])
        if method.lower() == 'post':
            params, data = None, payload
        elif method.lower() == 'get':
            params, data = payload, None
        else:
            raise requests.exceptions.HTTPError('POST or GET requests only.')
        return self._session.request(
            method=method.upper(),
            url=url,
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            files=files
        )

    def _file_to_bytes(self, data: Union[bytes, str, None] = None, filename: str = ''):
        """Ensure the file provided is ingested properly

        File must be XLS, XLSX, CSV, or TXT.
        10MB max file size.
        """
        assert filename.lower().endswith(('.xls', '.xlsx', '.csv', '.txt')), ValueError("Filetype must be one of: xls, xlsx, csv, txt")
        if isinstance(data, bytes):  # Data is uploaded as CSV/XLSX/TXT bytestream
            pass
        elif isinstance(data, str):  # Data is provided as a filename
            data = open(data, 'rb')
        elif data is None:  # Only filename is provided.
            data = open(filename, 'rb')
        else:
            raise TypeError('Data must be provided in one of the supported formats: Union[bytes, str]')
        assert sys.getsizeof(data) <= 10485760, ValueError('Max file size: 10MB')
        return data


    def upload_data(
        self,
        filename: str,
        data: Union[bytes, str] = None,
        date_format: str = 'Y-m-d',
        initial_upload_url: str = 'import',
        final_upload_url: str = 'ajax-review-columns',
        **kwargs
    ):
        """Upload data to Touchstone

        This method sends file data to Touchstone for inclusion in its SL databases.

        Example:
            with Touchstone(user, pass) as ts:
                ts.upload('filename.txt')

        Attributes:
            filename (str): filename
            data (Union[bytes, str]): the file data to be sent to Touchstone (optional)
            date_format (str): the structure taken by the date in your data.
                Options are on the left, visual description on the right:
                d-m-Y: DD/MM/YYYY
                m-d-Y: MM/DD/YYYY
                Y-m-d: YYYY/MM/DD
                d-m-y: DD/MM/YY
                m-d-y: MM/DD/YY
                y-m-d: YY/MM/DD
            initial_upload_url (str): the url/uri to send the raw data.
            final_upload_url (str): the url/uri to send the column structure/order.

        Todo:
            * Detect when there was an error auto-parsing data on the server.
            * Attempt to correct data headers on the client-side.
            * Automatically detect date-format
        """

        def _initial_upload(url, filename, filedata, **kwargs):
            response = self.request(
                url,
                files={'fileToUpload': (filename, filedata)},
                **kwargs
            )
            assert (response.ok and ('?file_id=' in response.url)), requests.exceptions.HTTPError(f'Invalid response:\n\n{response.text}')
            return response

        def _parse_table_structure(init_response):
            """Provided the response to the initial data upload, determine how it should be structured.
            Touchstone does its own guesswork on how to ingest data.
            If accurate headers are used, the guesswork that is done is correct.

            Parsing assumes Touchstone's work is correct.
            """
            table_data = {}
            soup = BeautifulSoup(init_response.text)
            data_soup = soup.find_all('', {'class': 'review_data'})[0]
            field_soup = data_soup.find_all('th', 'import_field')
            for field in field_soup:
                data_number = field.get('data-number')
                selection = field.find('option', {'selected': 'selected'})
                if selection:
                    col_num = selection.get('value')
                else:
                    col_num = ''
                table_data[f'columns[{data_number}]'] = col_num
            return table_data
        
        def _final_upload(url, data, **kwargs):
            """Send the final table to Touchstone for uploading and inclusion in its SL database.
            """
            response = self.request(
                url,
                'post',
                payload=data,
                **kwargs
            )
            assert response.ok, requests.exceptions.HTTPError('Non-2XX response. Is your input data in the correct format?')
            return response

        data = self._file_to_bytes(data, filename)
        init_response = _initial_upload(initial_upload_url, filename, data, **kwargs)

        table_data = {
            'fid': init_response.url.split('?file_id=')[-1],
            'dateFormat': date_format,
            **_parse_table_structure(init_response)
        }

        final_response = _final_upload(final_upload_url, table_data, **kwargs)
        return final_response
