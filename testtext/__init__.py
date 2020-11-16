import io
import requests
import sys

from bs4 import BeautifulSoup
from typing import Union

__doc__ = """Unofficial TestText API Wrapper"""
__all__ = [
    '__doc__',
    'TestText'
]


class TestText():
    url: str = 'https://testtext.com'
    start_uri: str = '/login'
    login_uri: str = '/login'
    upload_uri: str = '/upload'
    start_check: str = ''
    login_check: str = 'Start Your Test'
    upload_check: str = 'ROLL BACK'

    def __init__(
        self,
        username: str,
        password: str,
        headers: dict = {},
    ):
        """TestText API Instance Class

        Unofficial TestText API Wrapper.

        Start connection to TestText for automated data supply to your account.

        Example:
            with TestText(user, pass) as ts:
                ts.upload('filename.txt')

        Class Parameters (All provided.):
            url (str): root for all URLs
            start_uri (str): suffix to request session initialization
            login_uri (str): suffix to request session login
            upload_uri (str): suffix to request session upload
            start_check (str): sub-string to search for which flags successful session-init.
            login_check (str): sub-string to search for which flags successful login.
            upload_check (str): sub-string to search for which flags successful upload.

        Attributes:
            username (str): username
            password (str): password
            headers (str): persistent, user-provided headers if applicable (optional)

        """
        self.username = username
        self.password = password

        self.session: requests.Session = requests.Session()
        self.session.headers.update(headers)

    def __enter__(self):
        """Begin TestText session connection.

        Along with the username and password, a CSRF token is necessary for the initial payload.
        This is obtained in a quick visit to the main page.
        """

        def get_csrf_token(response: requests.Response):
            token_soup = (
                BeautifulSoup(start_response.content)
                .find('input', {'name': 'csrf_token'})
            ) or {}
            return token_soup.get('value')

        start_response = self.session.get(self.url + self.start_uri)
        login_response = self.session.post(
            self.url + self.login_uri,
            data={
                'submit': 'Login',
                'email': self.username,
                'password': self.password,
                'csrf_token': get_csrf_token(start_response)
            }
        )
        if not self._successful(start_response, self.start_check):
            raise ValueError(f'Unsuccessful Session Init. Is this the correct URL?:\n{self.url}')
        if not self._successful(login_response, self.login_check):
            raise ValueError('Unsuccessful Login. Check the provided credentials.')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End Session connection.
        """
        self.session.close()

    def _successful(self, response: requests.Response, check: str):
        return check in response.text

    def request(self, *args, **kwargs):
        return self.session.request(*args, **kwargs)

    def upload(self, file: Union[str, bytes, io.BytesIO], max_bytes=10000000):
        """Upload a file by name or bytes.
        There are no file-formatting chceks on the client-side.
        Unknown server limit on filesize. Default maxsize is arbitrary.

        FILE DETAILS:
        - Files are expected to be formatted as a TSV.
        - Date formatting is expected as "YYYY-MM-DD"

        Arguments:
            file {Union[str, bytes, io.BytesIO]} -- filename, bytestream, bytes

        Raises:
            ValueError: Invalid file argument
        """

        def parse_file_type(f):

            def check_file_size(file_obj):
                if isinstance(file_obj, tuple):
                    if sys.getsizeof(file_obj[1]) > max_bytes:
                        raise ValueError(f'File too large. Max size: {max_bytes}')
                else:
                    if sys.getsizeof(file_obj) > max_bytes:
                        raise ValueError(f'File too large. Max size: {max_bytes}')
                    return file_obj

            if isinstance(f, str):
                if f.rpartition('.')[-1].lower() == 'tsv' and len(f) > 4:
                    f = open(f, 'rb')
                else:
                    f = ('filename.tsv', f)

            elif isinstance(f, bytes):
                f = ('filename.tsv', f)
            elif isinstance(f, io.Bytes):
                f = ('filename.tsv', f.getvalue())
            else:
                raise ValueError('file argument may only be string, bytes, or io.BytesIO object.')
            return check_file_size(f)

        file = parse_file_type(file)
        upload_response = self.session.post(
            self.url + self.upload_uri,
            headers={'Referer': self.url + self.upload_uri},
            files={'file': file}
        )

        if isinstance(file, (io.TextIOWrapper, io.BufferedReader)):
            file.close()

        if not self._successful(upload_response, self.upload_check):
            raise ValueError('Unsucccessful Upload.')
        else:
            results = {
                'failures': 0  # TODO: Parse upload_response for error count.
            }
            return results
