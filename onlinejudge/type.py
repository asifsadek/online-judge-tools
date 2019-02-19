# Python Version: 3.x
from typing import Callable, List, NamedTuple, NewType, Optional, Tuple

import requests

CredentialsProvider = Callable[[], Tuple[str, str]]


class LoginError(RuntimeError):
    pass


class Service(object):
    def login(self, get_credentials: CredentialsProvider, session: Optional[requests.Session] = None) -> None:
        """
        :param get_credentials: returns a tuple of (username, password)
        :raises LoginError:
        """
        raise NotImplementedError

    def is_logged_in(self, session: Optional[requests.Session] = None) -> bool:
        raise NotImplementedError

    def get_url(self) -> str:
        raise NotImplementedError

    def get_name(self) -> str:
        raise NotImplementedError

    @classmethod
    def from_url(self, s: str) -> Optional['Service']:
        pass


LabeledString = NamedTuple('LabeledString', [('name', str), ('data', str)])
TestCase = NamedTuple('TestCase', [('input', LabeledString), ('output', LabeledString)])

LanguageId = NewType('LanguageId', str)

Language = NamedTuple('Language', [
    ('id', LanguageId),
    ('name', str),
])


class NotLoggedInError(RuntimeError):
    pass


class SubmissionError(RuntimeError):
    pass


class Problem(object):
    def download_sample_cases(self, session: Optional[requests.Session] = None) -> List[TestCase]:
        raise NotImplementedError

    def download_system_cases(self, session: Optional[requests.Session] = None) -> List[TestCase]:
        """
        :raises NotLoggedInError:
        """
        raise NotImplementedError

    def submit_code(self, code: bytes, language_id: LanguageId, filename: Optional[str] = None, session: Optional[requests.Session] = None) -> 'Submission':
        """
        :raises NotLoggedInError:
        :raises SubmissionError:
        """
        raise NotImplementedError

    def get_available_languages(self, session: Optional[requests.Session] = None) -> List[Language]:
        raise NotImplementedError

    def get_url(self) -> str:
        raise NotImplementedError

    def get_service(self) -> Service:
        raise NotImplementedError

    def get_input_format(self, session: Optional[requests.Session] = None) -> Optional[str]:
        raise NotImplementedError

    def get_standings(self, session: Optional[requests.Session] = None) -> Standings:
        raise NotImplementedError

    @classmethod
    def from_url(self, s: str) -> Optional['Problem']:
        pass


class Submission(object):
    def download_code(self, session: Optional[requests.Session] = None) -> bytes:
        raise NotImplementedError

    def get_url(self) -> str:
        raise NotImplementedError

    def get_problem(self) -> Problem:
        raise NotImplementedError

    def get_service(self) -> Service:
        return self.get_problem().get_service()

    @classmethod
    def from_url(cls, s: str) -> Optional['Submission']:
        pass


class CompatibilitySubmission(Submission):
    def __init__(self, url: str, problem: Problem):
        self.url = url
        self.problem = problem

    def get_url(self) -> str:
        return self.url

    def get_problem(self) -> Problem:
        return self.problem


class DummySubmission(Submission):
    def __init__(self, url: str):
        self.url = url

    def get_url(self) -> str:
        return self.url

    def get_problem(self) -> Problem:
        raise Exception
