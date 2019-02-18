# Python Version: 3.x
"""
the module for HackerRank (https://www.hackerrank.com/)
"""

import datetime
import io
import json
import posixpath
import re
import time
import urllib.parse
import zipfile
from typing import *

import bs4
import requests

import onlinejudge._implementation.logging as log
import onlinejudge._implementation.utils as utils
import onlinejudge.dispatch
import onlinejudge.type
from onlinejudge.type import LabeledString, TestCase


@utils.singleton
class HackerRankService(onlinejudge.type.Service):
    def login(self, get_credentials: onlinejudge.type.CredentialsProvider, session: Optional[requests.Session] = None) -> bool:
        session = session or utils.new_default_session()
        url = 'https://www.hackerrank.com/auth/login'
        # get
        resp = utils.request('GET', url, session=session)
        if resp.url != url:
            log.debug('redirected: %s', resp.url)
            log.info('You have already signed in.')
            return True
        # parse
        soup = bs4.BeautifulSoup(resp.content.decode(resp.encoding), utils.html_parser)
        csrftoken = soup.find('meta', attrs={'name': 'csrf-token'}).attrs['content']
        tag = soup.find('input', attrs={'name': 'username'})
        while tag.name != 'form':
            tag = tag.parent
        form = tag
        # post
        username, password = get_credentials()
        form = utils.FormSender(form, url=resp.url)
        form.set('login', username)
        form.set('password', password)
        form.set('remember_me', 'true')
        form.set('fallback', 'true')
        resp = form.request(session, method='POST', action='/rest/auth/login', headers={'X-CSRF-Token': csrftoken})
        resp.raise_for_status()
        log.debug('redirected: %s', resp.url)
        # result
        if '/auth' not in resp.url:
            log.success('You signed in.')
            return True
        else:
            log.failure('You failed to sign in. Wrong user ID or password.')
            return False

    def is_logged_in(self, session: Optional[requests.Session] = None) -> bool:
        session = session or utils.new_default_session()
        url = 'https://www.hackerrank.com/auth/login'
        resp = utils.request('GET', url, session=session)
        log.debug('redirected: %s', resp.url)
        return '/auth' not in resp.url

    def get_url(self) -> str:
        return 'https://www.hackerrank.com/'

    def get_name(self) -> str:
        return 'hackerrank'

    @classmethod
    def from_url(cls, url: str) -> Optional['HackerRankService']:
        # example: https://www.hackerrank.com/dashboard
        result = urllib.parse.urlparse(url)
        if result.scheme in ('', 'http', 'https') \
                and result.netloc in ('hackerrank.com', 'www.hackerrank.com'):
            return cls()
        return None


class HackerRankProblem(onlinejudge.type.Problem):
    def __init__(self, contest_slug: str, challenge_slug: str):
        self.contest_slug = contest_slug
        self.challenge_slug = challenge_slug

    def download_sample_cases(self, session: Optional[requests.Session] = None) -> List[TestCase]:
        log.warning('use --system option')
        raise NotImplementedError

    def download_system_cases(self, session: Optional[requests.Session] = None) -> List[TestCase]:
        session = session or utils.new_default_session()
        # get
        # example: https://www.hackerrank.com/rest/contests/hourrank-1/challenges/beautiful-array/download_testcases
        url = 'https://www.hackerrank.com/rest/contests/{}/challenges/{}/download_testcases'.format(self.contest_slug, self.challenge_slug)
        resp = utils.request('GET', url, session=session, raise_for_status=False)
        if resp.status_code != 200:
            log.error('response: %s', resp.content.decode())
            return []
        # parse
        with zipfile.ZipFile(io.BytesIO(resp.content)) as fh:
            # list names
            names = []  # type: List[str]
            pattern = re.compile(r'(in|out)put/\1put(\d+).txt')
            for filename in sorted(fh.namelist()):  # "input" < "output"
                if filename.endswith('/'):
                    continue
                log.debug('filename: %s', filename)
                m = pattern.match(filename)
                assert m
                if m.group(1) == 'in':
                    names += [m.group(2)]
            # zip samples
            samples = []  # type: List[TestCase]
            for name in names:
                inpath = 'input/input{}.txt'.format(name)
                outpath = 'output/output{}.txt'.format(name)
                indata = fh.read(inpath).decode()
                outdata = fh.read(outpath).decode()
                samples += [TestCase(LabeledString(inpath, indata), LabeledString(outpath, outdata))]
            return samples

    def get_url(self) -> str:
        if self.contest_slug == 'master':
            return 'https://www.hackerrank.com/challenges/{}'.format(self.challenge_slug)
        else:
            return 'https://www.hackerrank.com/contests/{}/challenges/{}'.format(self.contest_slug, self.challenge_slug)

    def get_service(self) -> HackerRankService:
        return HackerRankService()

    @classmethod
    def from_url(cls, url: str) -> Optional['HackerRankProblem']:
        # example: https://www.hackerrank.com/contests/university-codesprint-2/challenges/the-story-of-a-tree
        # example: https://www.hackerrank.com/challenges/fp-hello-world
        result = urllib.parse.urlparse(url)
        if result.scheme in ('', 'http', 'https') \
                and result.netloc in ('hackerrank.com', 'www.hackerrank.com'):
            m = re.match(r'^/contests/([0-9A-Za-z-]+)/challenges/([0-9A-Za-z-]+)$', utils.normpath(result.path))
            if m:
                return cls(m.group(1), m.group(2))
            m = re.match(r'^/challenges/([0-9A-Za-z-]+)$', utils.normpath(result.path))
            if m:
                return cls('master', m.group(1))
        return None

    def _get_model(self, session: Optional[requests.Session] = None) -> Dict[str, Any]:
        session = session or utils.new_default_session()
        # get
        url = 'https://www.hackerrank.com/rest/contests/{}/challenges/{}'.format(self.contest_slug, self.challenge_slug)
        resp = utils.request('GET', url, session=session)
        # parse
        it = json.loads(resp.content.decode())
        log.debug('json: %s', it)
        if not it['status']:
            log.error('get model: failed')
            raise onlinejudge.type.SubmissionError
        return it['model']

    def _get_lang_display_mapping(self, session: Optional[requests.Session] = None) -> Dict[str, str]:
        session = session or utils.new_default_session()
        # get
        url = 'https://hrcdn.net/hackerrank/assets/codeshell/dist/codeshell-cdffcdf1564c6416e1a2eb207a4521ce.js'  # at "Mon Feb  4 14:51:27 JST 2019"
        resp = utils.request('GET', url, session=session)
        # parse
        s = resp.content.decode()
        l = s.index('lang_display_mapping:{c:"C",')
        l = s.index('{', l)
        r = s.index('}', l) + 1
        s = s[l:r]
        log.debug('lang_display_mapping (raw): %s', s)  # this is not a json
        lang_display_mapping = {}
        for lang in s[1:-2].split('",'):
            key, value = lang.split(':"')
            lang_display_mapping[key] = value
        log.debug('lang_display_mapping (parsed): %s', lang_display_mapping)
        return lang_display_mapping

    def get_language_dict(self, session: Optional[requests.Session] = None) -> Dict[str, Dict[str, str]]:
        session = session or utils.new_default_session()
        info = self._get_model(session=session)
        lang_display_mapping = self._get_lang_display_mapping()
        result = {}
        for lang in info['languages']:
            descr = lang_display_mapping.get(lang)
            if descr is None:
                log.warning('display mapping for language `%s\' not found', lang)
                descr = lang
            result[lang] = {'description': descr}
        return result

    def submit_code(self, code: bytes, language: str, session: Optional[requests.Session] = None) -> onlinejudge.type.Submission:
        session = session or utils.new_default_session()
        # get
        resp = utils.request('GET', self.get_url(), session=session)
        # parse
        soup = bs4.BeautifulSoup(resp.content.decode(resp.encoding), utils.html_parser)
        csrftoken = soup.find('meta', attrs={'name': 'csrf-token'}).attrs['content']
        # post
        url = 'https://www.hackerrank.com/rest/contests/{}/challenges/{}/submissions'.format(self.contest_slug, self.challenge_slug)
        payload = {'code': code, 'language': language, 'contest_slug': self.contest_slug}
        log.debug('payload: %s', payload)
        resp = utils.request('POST', url, session=session, json=payload, headers={'X-CSRF-Token': csrftoken})
        # parse
        it = json.loads(resp.content.decode())
        log.debug('json: %s', it)
        if not it['status']:
            log.failure('Submit Code: failed')
            raise onlinejudge.type.SubmissionError
        model_id = it['model']['id']
        url = self.get_url().rstrip('/') + '/submissions/code/{}'.format(model_id)
        log.success('success: result: %s', url)
        return onlinejudge.type.CompatibilitySubmission(url, problem=self)


onlinejudge.dispatch.services += [HackerRankService]
onlinejudge.dispatch.problems += [HackerRankProblem]
