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
    email_upload_uri: str = '/upload'
    sms_upload_uri: str = '/uploadsms'
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
            email_upload_uri (str): suffix to request session email upload
            sms_upload_uri (str): suffix to request session sms upload
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
        if not self.username and self.password:
            raise ValueError(f'Unsuccessful Login. Missing either/both user/pass. (username: {self.username})')

        def get_csrf_token(response: requests.Response):
            token_soup = (
                BeautifulSoup(response.content, 'html.parser')
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
            raise ValueError(f'Unsuccessful Login. Check the provided credentials. (username: {self.username})')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End Session connection.
        """
        self.session.close()

    def _successful(self, response: requests.Response, check: str):
        return check in response.text

    def _get_failure_reason(self, response: requests.Response, content_type: str):
        if response.text == 'unauthorized':
            detail = ' (sms upload might not be permitted)' if content_type.lower() == 'sms' else ''
            return 'unauthorized' + detail

        soup = BeautifulSoup(response.content, 'html.parser')
        result = soup.find('div', {'role': 'alert'})
        if result:
            return result.get_text(strip=True)
        else:
            return 'Unknown reason.'

    def request(self, *args, **kwargs):
        return self.session.request(*args, **kwargs)

    def upload(
        self,
        file_data: Union[str, bytes, io.BytesIO, io.TextIOWrapper, io.BufferedReader],
        max_bytes=10000000,
        content_type='email'
    ):
        """Upload a file by name or bytes.
        There are no file-formatting chceks on the client-side.
        Unknown server limit on filesize. Default maxsize is arbitrary.

        FILE DETAILS:
        - Files are expected to be formatted as a TSV.
        - Date formatting is expected as "YYYY-MM-DD"

        Arguments:
            file {Union[str, bytes, io.BytesIO, io.TextIOWrapper, io.BufferedReader]} -- filename, bytestream, bytes, opened file wrapper

        Raises:
            ValueError: Invalid file argument
        """

        def get_upload_uri(content_type: str):
            if content_type.lower() == 'email':
                return self.email_upload_uri
            elif content_type.lower() == 'sms':
                return self.sms_upload_uri
            else:
                raise ValueError('content_type must be either one of: ["email", "sms"]')

        def parse_file_type(f):

            def check_file_size(file_object):
                if isinstance(file_object, tuple):
                    too_big = sys.getsizeof(file_object[1]) > max_bytes
                else:
                    too_big = sys.getsizeof(file_object) > max_bytes

                if too_big:
                    raise ValueError(f'File too large. Max size: {max_bytes}')

            if isinstance(f, (io.TextIOWrapper, io.BufferedReader)):
                pass
            elif isinstance(f, str):
                if f.rpartition('.')[-1].lower() == 'tsv' and len(f) > 4:
                    f = open(f, 'rb')
                else:
                    f = ('filename.tsv', f)
            elif isinstance(f, bytes):
                f = ('filename.tsv', f)
            elif isinstance(f, io.BytesIO):
                f = ('filename.tsv', f.getvalue())
            else:
                raise ValueError('file argument may only be string, bytes, or io.BytesIO object.')
            check_file_size(f)
            return f

        upload_uri = get_upload_uri(content_type)

        file_data = parse_file_type(file_data)
        upload_response = self.session.post(
            self.url + upload_uri,
            headers={'Referer': self.url + upload_uri},
            files={'file': file_data}
        )

        if isinstance(file_data, (io.TextIOWrapper, io.BufferedReader)):
            file_data.close()

        if not self._successful(upload_response, self.upload_check):
            reason = self._get_failure_reason(upload_response, content_type)
            raise ValueError(f'Unsucccessful Upload: {reason}')
        else:
            return {
                'failures': 0,  # TODO: Parse upload_response for error count.
                'response': upload_response
            }
