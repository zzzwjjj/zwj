def load_config(**kwargs):
    """
    Wrapper function to load the kube_config.
    It will initially try to load_kube_config from provided path,
    then check if the KUBE_CONFIG_DEFAULT_LOCATION exists
    If neither exists, it will fall back to load_incluster_config
    and inform the user accordingly.

    :param kwargs: A combination of all possible kwargs that
    can be passed to either load_kube_config or
    load_incluster_config functions.
    """
    if "config_file" in kwargs.keys():
        load_kube_config(**kwargs)
    elif "kube_config_path" in kwargs.keys():
        kwargs["config_file"] = kwargs.pop("kube_config_path", None)
        load_kube_config(**kwargs)
    elif exists(expanduser(KUBE_CONFIG_DEFAULT_LOCATION)):
        load_kube_config(**kwargs)
    else:
        print(
            "kube_config_path not provided and "
            "default location ({0}) does not exist. "
            "Using inCluster Config. "
            "This might not work.".format(KUBE_CONFIG_DEFAULT_LOCATION))
        load_incluster_config(**kwargs)

class TimezoneInfo(datetime.tzinfo):
    def __init__(self, h, m):
        self._name = "UTC"
        if h != 0 and m != 0:
            self._name += "%+03d:%2d" % (h, m)
        self._delta = datetime.timedelta(hours=h, minutes=math.copysign(m, h))

    def utcoffset(self, dt):
        return self._delta

    def tzname(self, dt):
        return self._name

    def dst(self, dt):
        return datetime.timedelta(0)


UTC = TimezoneInfo(0, 0)

# ref https://www.ietf.org/rfc/rfc3339.txt
_re_rfc3339 = re.compile(r"(\d\d\d\d)-(\d\d)-(\d\d)"        # full-date
                         r"[ Tt]"                           # Separator
                         r"(\d\d):(\d\d):(\d\d)([.,]\d+)?"  # partial-time
                         r"([zZ ]|[-+]\d\d?:\d\d)?",        # time-offset
                         re.VERBOSE + re.IGNORECASE)
_re_timezone = re.compile(r"([-+])(\d\d?):?(\d\d)?")

MICROSEC_PER_SEC = 1000000

def parse_rfc3339(s):
    if isinstance(s, datetime.datetime):
        # no need to parse it, just make sure it has a timezone.
        if not s.tzinfo:
            return s.replace(tzinfo=UTC)
        return s
    groups = _re_rfc3339.search(s).groups()
    dt = [0] * 7
    for x in range(6):
        dt[x] = int(groups[x])
    us = 0
    if groups[6] is not None:
        partial_sec = float(groups[6].replace(",", "."))
        us = int(MICROSEC_PER_SEC * partial_sec)
    tz = UTC
    if groups[7] is not None and groups[7] != 'Z' and groups[7] != 'z':
        tz_groups = _re_timezone.search(groups[7]).groups()
        hour = int(tz_groups[1])
        minute = 0
        if tz_groups[0] == "-":
            hour *= -1
        if tz_groups[2]:
            minute = int(tz_groups[2])
        tz = TimezoneInfo(hour, minute)
    return datetime.datetime(
        year=dt[0], month=dt[1], day=dt[2],
        hour=dt[3], minute=dt[4], second=dt[5],
        microsecond=us, tzinfo=tz)

class DateUtilTest(unittest.TestCase):

    def _parse_rfc3339_test(self, st, y, m, d, h, mn, s, us):
        actual = parse_rfc3339(st)
        expected = datetime(y, m, d, h, mn, s, us, UTC)
        self.assertEqual(expected, actual)

    def test_parse_rfc3339(self):
        self._parse_rfc3339_test("2017-07-25T04:44:21Z",
                                 2017, 7, 25, 4, 44, 21, 0)
        self._parse_rfc3339_test("2017-07-25 04:44:21Z",
                                 2017, 7, 25, 4, 44, 21, 0)
        self._parse_rfc3339_test("2017-07-25T04:44:21",
                                 2017, 7, 25, 4, 44, 21, 0)
        self._parse_rfc3339_test("2017-07-25T04:44:21z",
                                 2017, 7, 25, 4, 44, 21, 0)
        self._parse_rfc3339_test("2017-07-25T04:44:21+03:00",
                                 2017, 7, 25, 1, 44, 21, 0)
        self._parse_rfc3339_test("2017-07-25T04:44:21-03:00",
                                 2017, 7, 25, 7, 44, 21, 0)

        self._parse_rfc3339_test("2017-07-25T04:44:21,005Z",
                                 2017, 7, 25, 4, 44, 21, 5000)
        self._parse_rfc3339_test("2017-07-25T04:44:21.005Z",
                                 2017, 7, 25, 4, 44, 21, 5000)
        self._parse_rfc3339_test("2017-07-25 04:44:21.0050Z",
                                 2017, 7, 25, 4, 44, 21, 5000)
        self._parse_rfc3339_test("2017-07-25T04:44:21.5",
                                 2017, 7, 25, 4, 44, 21, 500000)
        self._parse_rfc3339_test("2017-07-25T04:44:21.005z",
                                 2017, 7, 25, 4, 44, 21, 5000)
        self._parse_rfc3339_test("2017-07-25T04:44:21.005+03:00",
                                 2017, 7, 25, 1, 44, 21, 5000)
        self._parse_rfc3339_test("2017-07-25T04:44:21.005-03:00",
                                 2017, 7, 25, 7, 44, 21, 5000)

    def test_format_rfc3339(self):
        self.assertEqual(
            format_rfc3339(datetime(2017, 7, 25, 4, 44, 21, 0, UTC)),
            "2017-07-25T04:44:21Z")
        self.assertEqual(
            format_rfc3339(datetime(2017, 7, 25, 4, 44, 21, 0,
                                    TimezoneInfo(2, 0))),
            "2017-07-25T02:44:21Z")
        self.assertEqual(
            format_rfc3339(datetime(2017, 7, 25, 4, 44, 21, 0,
                                    TimezoneInfo(-2, 30))),
            "2017-07-25T07:14:21Z")

class ExecProvider(object):
    """
    Implementation of the proposal for out-of-tree client
    authentication providers as described here --
    https://github.com/kubernetes/community/blob/master/contributors/design-proposals/auth/kubectl-exec-plugins.md

    Missing from implementation:

    * TLS cert support
    * caching
    """

    def __init__(self, exec_config, cwd):
        """
        exec_config must be of type ConfigNode because we depend on
        safe_get(self, key) to correctly handle optional exec provider
        config parameters.
        """
        for key in ['command', 'apiVersion']:
            if key not in exec_config:
                raise ConfigException(
                    'exec: malformed request. missing key \'%s\'' % key)
        self.api_version = exec_config['apiVersion']
        self.args = [exec_config['command']]
        if exec_config.safe_get('args'):
            self.args.extend(exec_config['args'])
        self.env = os.environ.copy()
        if exec_config.safe_get('env'):
            additional_vars = {}
            for item in exec_config['env']:
                name = item['name']
                value = item['value']
                additional_vars[name] = value
            self.env.update(additional_vars)

        self.cwd = cwd or None

    def run(self, previous_response=None):
        is_interactive = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
        kubernetes_exec_info = {
            'apiVersion': self.api_version,
            'kind': 'ExecCredential',
            'spec': {
                'interactive': is_interactive
            }
        }
        if previous_response:
            kubernetes_exec_info['spec']['response'] = previous_response
        self.env['KUBERNETES_EXEC_INFO'] = json.dumps(kubernetes_exec_info)
        process = subprocess.Popen(
            self.args,
            stdout=subprocess.PIPE,
            stderr=sys.stderr if is_interactive else subprocess.PIPE,
            stdin=sys.stdin if is_interactive else None,
            cwd=self.cwd,
            env=self.env,
            universal_newlines=True)
        (stdout, stderr) = process.communicate()
        exit_code = process.wait()
        if exit_code != 0:
            msg = 'exec: process returned %d' % exit_code
            stderr = stderr.strip()
            if stderr:
                msg += '. %s' % stderr
            raise ConfigException(msg)
        try:
            data = json.loads(stdout)
        except ValueError as de:
            raise ConfigException(
                'exec: failed to decode process output: %s' % de)
        for key in ('apiVersion', 'kind', 'status'):
            if key not in data:
                raise ConfigException(
                    'exec: malformed response. missing key \'%s\'' % key)
        if data['apiVersion'] != self.api_version:
            raise ConfigException(
                'exec: plugin api version %s does not match %s' %
                (data['apiVersion'], self.api_version))
        return data['status']


class ExecProviderTest(unittest.TestCase):

    def setUp(self):
        self.input_ok = ConfigNode('test', {
            'command': 'aws-iam-authenticator',
            'args': ['token', '-i', 'dummy'],
            'apiVersion': 'client.authentication.k8s.io/v1beta1',
            'env': None
        })
        self.output_ok = """
        {
            "apiVersion": "client.authentication.k8s.io/v1beta1",
            "kind": "ExecCredential",
            "status": {
                "token": "dummy"
            }
        }
        """

    def test_missing_input_keys(self):
        exec_configs = [ConfigNode('test1', {}),
                        ConfigNode('test2', {'command': ''}),
                        ConfigNode('test3', {'apiVersion': ''})]
        for exec_config in exec_configs:
            with self.assertRaises(ConfigException) as context:
                ExecProvider(exec_config, None)
            self.assertIn('exec: malformed request. missing key',
                          context.exception.args[0])

    @mock.patch('subprocess.Popen')
    def test_error_code_returned(self, mock):
        instance = mock.return_value
        instance.wait.return_value = 1
        instance.communicate.return_value = ('', '')
        with self.assertRaises(ConfigException) as context:
            ep = ExecProvider(self.input_ok, None)
            ep.run()
        self.assertIn('exec: process returned %d' %
                      instance.wait.return_value, context.exception.args[0])

    @mock.patch('subprocess.Popen')
    def test_nonjson_output_returned(self, mock):
        instance = mock.return_value
        instance.wait.return_value = 0
        instance.communicate.return_value = ('', '')
        with self.assertRaises(ConfigException) as context:
            ep = ExecProvider(self.input_ok, None)
            ep.run()
        self.assertIn('exec: failed to decode process output',
                      context.exception.args[0])

    @mock.patch('subprocess.Popen')
    def test_missing_output_keys(self, mock):
        instance = mock.return_value
        instance.wait.return_value = 0
        outputs = [
            """
            {
                "kind": "ExecCredential",
                "status": {
                    "token": "dummy"
                }
            }
            """, """
            {
                "apiVersion": "client.authentication.k8s.io/v1beta1",
                "status": {
                    "token": "dummy"
                }
            }
            """, """
            {
                "apiVersion": "client.authentication.k8s.io/v1beta1",
                "kind": "ExecCredential"
            }
            """
        ]
        for output in outputs:
            instance.communicate.return_value = (output, '')
            with self.assertRaises(ConfigException) as context:
                ep = ExecProvider(self.input_ok, None)
                ep.run()
            self.assertIn('exec: malformed response. missing key',
                          context.exception.args[0])

    @mock.patch('subprocess.Popen')
    def test_mismatched_api_version(self, mock):
        instance = mock.return_value
        instance.wait.return_value = 0
        wrong_api_version = 'client.authentication.k8s.io/v1'
        output = """
        {
            "apiVersion": "%s",
            "kind": "ExecCredential",
            "status": {
                "token": "dummy"
            }
        }
        """ % wrong_api_version
        instance.communicate.return_value = (output, '')
        with self.assertRaises(ConfigException) as context:
            ep = ExecProvider(self.input_ok, None)
            ep.run()
        self.assertIn(
            'exec: plugin api version %s does not match' %
            wrong_api_version,
            context.exception.args[0])

    @mock.patch('subprocess.Popen')
    def test_ok_01(self, mock):
        instance = mock.return_value
        instance.wait.return_value = 0
        instance.communicate.return_value = (self.output_ok, '')
        ep = ExecProvider(self.input_ok, None)
        result = ep.run()
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('token' in result)

    @mock.patch('subprocess.Popen')
    def test_run_in_dir(self, mock):
        instance = mock.return_value
        instance.wait.return_value = 0
        instance.communicate.return_value = (self.output_ok, '')
        ep = ExecProvider(self.input_ok, '/some/directory')
        ep.run()
        self.assertEqual(mock.call_args[1]['cwd'], '/some/directory')

    @mock.patch('subprocess.Popen')
    def test_ok_no_console_attached(self, mock):
        instance = mock.return_value
        instance.wait.return_value = 0
        instance.communicate.return_value = (self.output_ok, '')
        mock_stdout = unittest.mock.patch(
            'sys.stdout', new=None)  # Simulate detached console
        with mock_stdout:
            ep = ExecProvider(self.input_ok, None)
            result = ep.run()
            self.assertTrue(isinstance(result, dict))
            self.assertTrue('token' in result)


def _join_host_port(host, port):
    """Adapted golang's net.JoinHostPort"""
    template = "%s:%s"
    host_requires_bracketing = ':' in host or '%' in host
    if host_requires_bracketing:
        template = "[%s]:%s"
    return template % (host, port)


class InClusterConfigLoader(object):
    def __init__(self,
                 token_filename,
                 cert_filename,
                 try_refresh_token=True,
                 environ=os.environ):
        self._token_filename = token_filename
        self._cert_filename = cert_filename
        self._environ = environ
        self._try_refresh_token = try_refresh_token
        self._token_refresh_period = datetime.timedelta(minutes=1)

    def load_and_set(self, client_configuration=None):
        try_set_default = False
        if client_configuration is None:
            client_configuration = type.__call__(Configuration)
            try_set_default = True
        self._load_config()
        self._set_config(client_configuration)
        if try_set_default:
            Configuration.set_default(client_configuration)

    def _load_config(self):
        if (SERVICE_HOST_ENV_NAME not in self._environ
                or SERVICE_PORT_ENV_NAME not in self._environ):
            raise ConfigException("Service host/port is not set.")

        if (not self._environ[SERVICE_HOST_ENV_NAME]
                or not self._environ[SERVICE_PORT_ENV_NAME]):
            raise ConfigException("Service host/port is set but empty.")

        self.host = ("https://" +
                     _join_host_port(self._environ[SERVICE_HOST_ENV_NAME],
                                     self._environ[SERVICE_PORT_ENV_NAME]))

        if not os.path.isfile(self._token_filename):
            raise ConfigException("Service token file does not exist.")

        self._read_token_file()

        if not os.path.isfile(self._cert_filename):
            raise ConfigException(
                "Service certification file does not exist.")

        with open(self._cert_filename) as f:
            if not f.read():
                raise ConfigException("Cert file exists but empty.")

        self.ssl_ca_cert = self._cert_filename

    def _set_config(self, client_configuration):
        client_configuration.host = self.host
        client_configuration.ssl_ca_cert = self.ssl_ca_cert
        if self.token is not None:
            client_configuration.api_key['authorization'] = self.token
        if not self._try_refresh_token:
            return

        def _refresh_api_key(client_configuration):
            if self.token_expires_at <= datetime.datetime.now():
                self._read_token_file()
            self._set_config(client_configuration)

        client_configuration.refresh_api_key_hook = _refresh_api_key

    def _read_token_file(self):
        with open(self._token_filename) as f:
            content = f.read()
            if not content:
                raise ConfigException("Token file exists but empty.")
            self.token = "bearer " + content
            self.token_expires_at = datetime.datetime.now(
            ) + self._token_refresh_period

def load_incluster_config(client_configuration=None, try_refresh_token=True):
    """
    Use the service account kubernetes gives to pods to connect to kubernetes
    cluster. It's intended for clients that expect to be running inside a pod
    running on kubernetes. It will raise an exception if called from a process
    not running in a kubernetes environment."""
    InClusterConfigLoader(
        token_filename=SERVICE_TOKEN_FILENAME,
        cert_filename=SERVICE_CERT_FILENAME,
        try_refresh_token=try_refresh_token).load_and_set(client_configuration)


class InClusterConfigTest(unittest.TestCase):
    def setUp(self):
        self._temp_files = []

    def tearDown(self):
        for f in self._temp_files:
            os.remove(f)

    def _create_file_with_temp_content(self, content=""):
        handler, name = tempfile.mkstemp()
        self._temp_files.append(name)
        os.write(handler, str.encode(content))
        os.close(handler)
        return name

    def get_test_loader(self,
                        token_filename=None,
                        cert_filename=None,
                        environ=_TEST_ENVIRON):
        if not token_filename:
            token_filename = self._create_file_with_temp_content(_TEST_TOKEN)
        if not cert_filename:
            cert_filename = self._create_file_with_temp_content(_TEST_CERT)
        return InClusterConfigLoader(token_filename=token_filename,
                                     cert_filename=cert_filename,
                                     try_refresh_token=True,
                                     environ=environ)

    def test_join_host_port(self):
        self.assertEqual(_TEST_HOST_PORT,
                         _join_host_port(_TEST_HOST, _TEST_PORT))
        self.assertEqual(_TEST_IPV6_HOST_PORT,
                         _join_host_port(_TEST_IPV6_HOST, _TEST_PORT))

    def test_load_config(self):
        cert_filename = self._create_file_with_temp_content(_TEST_CERT)
        loader = self.get_test_loader(cert_filename=cert_filename)
        loader._load_config()
        self.assertEqual("https://" + _TEST_HOST_PORT, loader.host)
        self.assertEqual(cert_filename, loader.ssl_ca_cert)
        self.assertEqual('bearer ' + _TEST_TOKEN, loader.token)

    def test_refresh_token(self):
        loader = self.get_test_loader()
        config = Configuration()
        loader.load_and_set(config)

        self.assertEqual('bearer ' + _TEST_TOKEN,
                         config.get_api_key_with_prefix('authorization'))
        self.assertEqual('bearer ' + _TEST_TOKEN, loader.token)
        self.assertIsNotNone(loader.token_expires_at)

        old_token = loader.token
        old_token_expires_at = loader.token_expires_at
        loader._token_filename = self._create_file_with_temp_content(
            _TEST_NEW_TOKEN)
        self.assertEqual('bearer ' + _TEST_TOKEN,
                         config.get_api_key_with_prefix('authorization'))

        loader.token_expires_at = datetime.datetime.now()
        self.assertEqual('bearer ' + _TEST_NEW_TOKEN,
                         config.get_api_key_with_prefix('authorization'))
        self.assertEqual('bearer ' + _TEST_NEW_TOKEN, loader.token)
        self.assertGreater(loader.token_expires_at, old_token_expires_at)

    def _should_fail_load(self, config_loader, reason):
        try:
            config_loader.load_and_set()
            self.fail("Should fail because %s" % reason)
        except ConfigException:
            # expected
            pass

    def test_no_port(self):
        loader = self.get_test_loader(
            environ={SERVICE_HOST_ENV_NAME: _TEST_HOST})
        self._should_fail_load(loader, "no port specified")

    def test_empty_port(self):
        loader = self.get_test_loader(environ={
            SERVICE_HOST_ENV_NAME: _TEST_HOST,
            SERVICE_PORT_ENV_NAME: ""
        })
        self._should_fail_load(loader, "empty port specified")

    def test_no_host(self):
        loader = self.get_test_loader(
            environ={SERVICE_PORT_ENV_NAME: _TEST_PORT})
        self._should_fail_load(loader, "no host specified")

    def test_empty_host(self):
        loader = self.get_test_loader(environ={
            SERVICE_HOST_ENV_NAME: "",
            SERVICE_PORT_ENV_NAME: _TEST_PORT
        })
        self._should_fail_load(loader, "empty host specified")

    def test_no_cert_file(self):
        loader = self.get_test_loader(cert_filename="not_exists_file_1123")
        self._should_fail_load(loader, "cert file does not exist")

    def test_empty_cert_file(self):
        loader = self.get_test_loader(
            cert_filename=self._create_file_with_temp_content())
        self._should_fail_load(loader, "empty cert file provided")

    def test_no_token_file(self):
        loader = self.get_test_loader(token_filename="not_exists_file_1123")
        self._should_fail_load(loader, "token file does not exist")

    def test_empty_token_file(self):
        loader = self.get_test_loader(
            token_filename=self._create_file_with_temp_content())
        self._should_fail_load(loader, "empty token file provided")

def _create_temp_file_with_content(content, temp_file_path=None):
    if len(_temp_files) == 0:
        atexit.register(_cleanup_temp_files)
    # Because we may change context several times, try to remember files we
    # created and reuse them at a small memory cost.
    content_key = str(content)
    if content_key in _temp_files:
        return _temp_files[content_key]
    if temp_file_path and not os.path.isdir(temp_file_path):
        os.makedirs(name=temp_file_path)
    fd, name = tempfile.mkstemp(dir=temp_file_path)
    os.close(fd)
    _temp_files[content_key] = name
    with open(name, 'wb') as fd:
        fd.write(content.encode() if isinstance(content, str) else content)
    return name


class FileOrData(object):
    """Utility class to read content of obj[%data_key_name] or file's
     content of obj[%file_key_name] and represent it as file or data.
     Note that the data is preferred. The obj[%file_key_name] will be used iff
     obj['%data_key_name'] is not set or empty. Assumption is file content is
     raw data and data field is base64 string. The assumption can be changed
     with base64_file_content flag. If set to False, the content of the file
     will assumed to be base64 and read as is. The default True value will
     result in base64 encode of the file content after read."""

    def __init__(self, obj, file_key_name, data_key_name=None,
                 file_base_path="", base64_file_content=True,
                 temp_file_path=None):
        if not data_key_name:
            data_key_name = file_key_name + "-data"
        self._file = None
        self._data = None
        self._base64_file_content = base64_file_content
        self._temp_file_path = temp_file_path
        if not obj:
            return
        if data_key_name in obj:
            self._data = obj[data_key_name]
        elif file_key_name in obj:
            self._file = os.path.normpath(
                os.path.join(file_base_path, obj[file_key_name]))

    def as_file(self):
        """If obj[%data_key_name] exists, return name of a file with base64
        decoded obj[%data_key_name] content otherwise obj[%file_key_name]."""
        use_data_if_no_file = not self._file and self._data
        if use_data_if_no_file:
            if self._base64_file_content:
                if isinstance(self._data, str):
                    content = self._data.encode()
                else:
                    content = self._data
                self._file = _create_temp_file_with_content(
                    base64.standard_b64decode(content), self._temp_file_path)
            else:
                self._file = _create_temp_file_with_content(
                    self._data, self._temp_file_path)
        if self._file and not os.path.isfile(self._file):
            raise ConfigException("File does not exist: %s" % self._file)
        return self._file

    def as_data(self):
        """If obj[%data_key_name] exists, Return obj[%data_key_name] otherwise
        base64 encoded string of obj[%file_key_name] file content."""
        use_file_if_no_data = not self._data and self._file
        if use_file_if_no_data:
            with open(self._file) as f:
                if self._base64_file_content:
                    self._data = bytes.decode(
                        base64.standard_b64encode(str.encode(f.read())))
                else:
                    self._data = f.read()
        return self._data

class CommandTokenSource(object):
    def __init__(self, cmd, args, tokenKey, expiryKey):
        self._cmd = cmd
        self._args = args
        if not tokenKey:
            self._tokenKey = '{.access_token}'
        else:
            self._tokenKey = tokenKey
        if not expiryKey:
            self._expiryKey = '{.token_expiry}'
        else:
            self._expiryKey = expiryKey

    def token(self):
        fullCmd = self._cmd + (" ") + " ".join(self._args)
        process = subprocess.Popen(
            [self._cmd] + self._args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True)
        (stdout, stderr) = process.communicate()
        exit_code = process.wait()
        if exit_code != 0:
            msg = 'cmd-path: process returned %d' % exit_code
            msg += "\nCmd: %s" % fullCmd
            stderr = stderr.strip()
            if stderr:
                msg += '\nStderr: %s' % stderr
            raise ConfigException(msg)
        try:
            data = json.loads(stdout)
        except ValueError as de:
            raise ConfigException(
                'exec: failed to decode process output: %s' % de)
        A = namedtuple('A', ['token', 'expiry'])
        return A(
            token=data['credential']['access_token'],
            expiry=parse_rfc3339(data['credential']['token_expiry']))


class KubeConfigLoader(object):

    def __init__(self, config_dict, active_context=None,
                 get_google_credentials=None,
                 config_base_path="",
                 config_persister=None,
                 temp_file_path=None):

        if config_dict is None:
            raise ConfigException(
                'Invalid kube-config. '
                'Expected config_dict to not be None.')
        elif isinstance(config_dict, ConfigNode):
            self._config = config_dict
        else:
            self._config = ConfigNode('kube-config', config_dict)

        self._current_context = None
        self._user = None
        self._cluster = None
        self.set_active_context(active_context)
        self._config_base_path = config_base_path
        self._config_persister = config_persister
        self._temp_file_path = temp_file_path

        def _refresh_credentials_with_cmd_path():
            config = self._user['auth-provider']['config']
            cmd = config['cmd-path']
            if len(cmd) == 0:
                raise ConfigException(
                    'missing access token cmd '
                    '(cmd-path is an empty string in your kubeconfig file)')
            if 'scopes' in config and config['scopes'] != "":
                raise ConfigException(
                    'scopes can only be used '
                    'when kubectl is using a gcp service account key')
            args = []
            if 'cmd-args' in config:
                args = config['cmd-args'].split()
            else:
                fields = config['cmd-path'].split()
                cmd = fields[0]
                args = fields[1:]

            commandTokenSource = CommandTokenSource(
                cmd, args,
                config.safe_get('token-key'),
                config.safe_get('expiry-key'))
            return commandTokenSource.token()

        def _refresh_credentials():
            # Refresh credentials using cmd-path
            if ('auth-provider' in self._user and
                'config' in self._user['auth-provider'] and
                    'cmd-path' in self._user['auth-provider']['config']):
                return _refresh_credentials_with_cmd_path()

            credentials, project_id = google.auth.default(scopes=[
                'https://www.googleapis.com/auth/cloud-platform',
                'https://www.googleapis.com/auth/userinfo.email'
            ])
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)
            return credentials

        if get_google_credentials:
            self._get_google_credentials = get_google_credentials
        else:
            self._get_google_credentials = _refresh_credentials

    def set_active_context(self, context_name=None):
        if context_name is None:
            context_name = self._config['current-context']
        self._current_context = self._config['contexts'].get_with_name(
            context_name)
        if (self._current_context['context'].safe_get('user') and
                self._config.safe_get('users')):
            user = self._config['users'].get_with_name(
                self._current_context['context']['user'], safe=True)
            if user:
                self._user = user['user']
            else:
                self._user = None
        else:
            self._user = None
        self._cluster = self._config['clusters'].get_with_name(
            self._current_context['context']['cluster'])['cluster']

    def _load_authentication(self):
        """Read authentication from kube-config user section if exists.

        This function goes through various authentication methods in user
        section of kube-config and stops if it finds a valid authentication
        method. The order of authentication methods is:

            1. auth-provider (gcp, azure, oidc)
            2. token field (point to a token file)
            3. exec provided plugin
            4. username/password
        """
        if not self._user:
            return
        if self._load_auth_provider_token():
            return
        if self._load_user_token():
            return
        if self._load_from_exec_plugin():
            return
        self._load_user_pass_token()

    def _load_auth_provider_token(self):
        if 'auth-provider' not in self._user:
            return
        provider = self._user['auth-provider']
        if 'name' not in provider:
            return
        if provider['name'] == 'gcp':
            return self._load_gcp_token(provider)
        if provider['name'] == 'azure':
            return self._load_azure_token(provider)
        if provider['name'] == 'oidc':
            return self._load_oid_token(provider)

    def _azure_is_expired(self, provider):
        expires_on = provider['config']['expires-on']
        if expires_on.isdigit():
            return int(expires_on) < time.time()
        else:
            exp_time = time.strptime(expires_on, '%Y-%m-%d %H:%M:%S.%f')
            return exp_time < time.gmtime()

    def _load_azure_token(self, provider):
        if 'config' not in provider:
            return
        if 'access-token' not in provider['config']:
            return
        if 'expires-on' in provider['config']:
            if self._azure_is_expired(provider):
                self._refresh_azure_token(provider['config'])
        self.token = 'Bearer %s' % provider['config']['access-token']
        return self.token

    def _refresh_azure_token(self, config):
        if 'adal' not in globals():
            raise ImportError('refresh token error, adal library not imported')

        tenant = config['tenant-id']
        authority = 'https://login.microsoftonline.com/{}'.format(tenant)
        context = adal.AuthenticationContext(
            authority, validate_authority=True, api_version='1.0'
        )
        refresh_token = config['refresh-token']
        client_id = config['client-id']
        apiserver_id = '00000002-0000-0000-c000-000000000000'
        try:
            apiserver_id = config['apiserver-id']
        except ConfigException:
            # We've already set a default above
            pass
        token_response = context.acquire_token_with_refresh_token(
            refresh_token, client_id, apiserver_id)

        provider = self._user['auth-provider']['config']
        provider.value['access-token'] = token_response['accessToken']
        provider.value['expires-on'] = token_response['expiresOn']
        if self._config_persister:
            self._config_persister()

    def _load_gcp_token(self, provider):
        if (('config' not in provider) or
                ('access-token' not in provider['config']) or
                ('expiry' in provider['config'] and
                 _is_expired(provider['config']['expiry']))):
            # token is not available or expired, refresh it
            self._refresh_gcp_token()

        self.token = "Bearer %s" % provider['config']['access-token']
        if 'expiry' in provider['config']:
            self.expiry = parse_rfc3339(provider['config']['expiry'])
        return self.token

    def _refresh_gcp_token(self):
        if 'config' not in self._user['auth-provider']:
            self._user['auth-provider'].value['config'] = {}
        provider = self._user['auth-provider']['config']
        credentials = self._get_google_credentials()
        provider.value['access-token'] = credentials.token
        provider.value['expiry'] = format_rfc3339(credentials.expiry)
        if self._config_persister:
            self._config_persister()

    def _load_oid_token(self, provider):
        if 'config' not in provider:
            return

        reserved_characters = frozenset(["=", "+", "/"])
        token = provider['config']['id-token']

        if any(char in token for char in reserved_characters):
            # Invalid jwt, as it contains url-unsafe chars
            return

        parts = token.split('.')
        if len(parts) != 3:  # Not a valid JWT
            return

        padding = (4 - len(parts[1]) % 4) * '='
        if len(padding) == 3:
            # According to spec, 3 padding characters cannot occur
            # in a valid jwt
            # https://tools.ietf.org/html/rfc7515#appendix-C
            return

        if PY3:
            jwt_attributes = json.loads(
                base64.urlsafe_b64decode(parts[1] + padding).decode('utf-8')
            )
        else:
            jwt_attributes = json.loads(
                base64.b64decode(parts[1] + padding)
            )

        expire = jwt_attributes.get('exp')

        if ((expire is not None) and
            (_is_expired(datetime.datetime.fromtimestamp(expire,
                                                         tz=UTC)))):
            self._refresh_oidc(provider)

            if self._config_persister:
                self._config_persister()

        self.token = "Bearer %s" % provider['config']['id-token']

        return self.token

    def _refresh_oidc(self, provider):
        config = Configuration()

        if 'idp-certificate-authority-data' in provider['config']:
            ca_cert = tempfile.NamedTemporaryFile(delete=True)

            if PY3:
                cert = base64.b64decode(
                    provider['config']['idp-certificate-authority-data']
                ).decode('utf-8')
            else:
                cert = base64.b64decode(
                    provider['config']['idp-certificate-authority-data'] + "=="
                )

            with open(ca_cert.name, 'w') as fh:
                fh.write(cert)

            config.ssl_ca_cert = ca_cert.name

        elif 'idp-certificate-authority' in provider['config']:
            config.ssl_ca_cert = provider['config']['idp-certificate-authority']

        else:
            config.verify_ssl = False

        client = ApiClient(configuration=config)

        response = client.request(
            method="GET",
            url="%s/.well-known/openid-configuration"
            % provider['config']['idp-issuer-url']
        )

        if response.status != 200:
            return

        response = json.loads(response.data)

        request = OAuth2Session(
            client_id=provider['config']['client-id'],
            token=provider['config']['refresh-token'],
            auto_refresh_kwargs={
                'client_id': provider['config']['client-id'],
                'client_secret': provider['config']['client-secret']
            },
            auto_refresh_url=response['token_endpoint']
        )

        try:
            refresh = request.refresh_token(
                token_url=response['token_endpoint'],
                refresh_token=provider['config']['refresh-token'],
                auth=(provider['config']['client-id'],
                      provider['config']['client-secret']),
                verify=config.ssl_ca_cert if config.verify_ssl else None
            )
        except oauthlib.oauth2.rfc6749.errors.InvalidClientIdError:
            return

        provider['config'].value['id-token'] = refresh['id_token']
        provider['config'].value['refresh-token'] = refresh['refresh_token']

    def _load_from_exec_plugin(self):
        if 'exec' not in self._user:
            return
        try:
            base_path = self._get_base_path(self._cluster.path)
            status = ExecProvider(self._user['exec'], base_path).run()
            if 'token' in status:
                self.token = "Bearer %s" % status['token']
            elif 'clientCertificateData' in status:
                # https://kubernetes.io/docs/reference/access-authn-authz/authentication/#input-and-output-formats
                # Plugin has provided certificates instead of a token.
                if 'clientKeyData' not in status:
                    logging.error('exec: missing clientKeyData field in '
                                  'plugin output')
                    return None
                self.cert_file = FileOrData(
                    status, None,
                    data_key_name='clientCertificateData',
                    file_base_path=base_path,
                    base64_file_content=False,
                    temp_file_path=self._temp_file_path).as_file()
                self.key_file = FileOrData(
                    status, None,
                    data_key_name='clientKeyData',
                    file_base_path=base_path,
                    base64_file_content=False,
                    temp_file_path=self._temp_file_path).as_file()
            else:
                logging.error('exec: missing token or clientCertificateData '
                              'field in plugin output')
                return None
            if 'expirationTimestamp' in status:
                self.expiry = parse_rfc3339(status['expirationTimestamp'])
            return True
        except Exception as e:
            logging.error(str(e))

    def _load_user_token(self):
        base_path = self._get_base_path(self._user.path)
        token = FileOrData(
            self._user, 'tokenFile', 'token',
            file_base_path=base_path,
            base64_file_content=False,
            temp_file_path=self._temp_file_path).as_data()
        if token:
            self.token = "Bearer %s" % token
            return True

    def _load_user_pass_token(self):
        if 'username' in self._user and 'password' in self._user:
            self.token = urllib3.util.make_headers(
                basic_auth=(self._user['username'] + ':' +
                            self._user['password'])).get('authorization')
            return True

    def _get_base_path(self, config_path):
        if self._config_base_path is not None:
            return self._config_base_path
        if config_path is not None:
            return os.path.abspath(os.path.dirname(config_path))
        return ""

    def _load_cluster_info(self):
        if 'server' in self._cluster:
            self.host = self._cluster['server'].rstrip('/')
            if self.host.startswith("https"):
                base_path = self._get_base_path(self._cluster.path)
                self.ssl_ca_cert = FileOrData(
                    self._cluster, 'certificate-authority',
                    file_base_path=base_path,
                    temp_file_path=self._temp_file_path).as_file()
                if 'cert_file' not in self.__dict__:
                    # cert_file could have been provided by
                    # _load_from_exec_plugin; only load from the _user
                    # section if we need it.
                    self.cert_file = FileOrData(
                        self._user, 'client-certificate',
                        file_base_path=base_path,
                        temp_file_path=self._temp_file_path).as_file()
                    self.key_file = FileOrData(
                        self._user, 'client-key',
                        file_base_path=base_path,
                        temp_file_path=self._temp_file_path).as_file()
        if 'insecure-skip-tls-verify' in self._cluster:
            self.verify_ssl = not self._cluster['insecure-skip-tls-verify']
        if 'tls-server-name' in self._cluster:
            self.tls_server_name = self._cluster['tls-server-name']

    def _set_config(self, client_configuration):
        if 'token' in self.__dict__:
            client_configuration.api_key['authorization'] = self.token

            def _refresh_api_key(client_configuration):
                if ('expiry' in self.__dict__ and _is_expired(self.expiry)):
                    self._load_authentication()
                self._set_config(client_configuration)
            client_configuration.refresh_api_key_hook = _refresh_api_key
        # copy these keys directly from self to configuration object
        keys = ['host', 'ssl_ca_cert', 'cert_file', 'key_file', 'verify_ssl','tls_server_name']
        for key in keys:
            if key in self.__dict__:
                setattr(client_configuration, key, getattr(self, key))

    def load_and_set(self, client_configuration):
        self._load_authentication()
        self._load_cluster_info()
        self._set_config(client_configuration)

    def list_contexts(self):
        return [context.value for context in self._config['contexts']]

    @property
    def current_context(self):
        return self._current_context.value

class ConfigNode(object):
    """Remembers each config key's path and construct a relevant exception
    message in case of missing keys. The assumption is all access keys are
    present in a well-formed kube-config."""

    def __init__(self, name, value, path=None):
        self.name = name
        self.value = value
        self.path = path

    def __contains__(self, key):
        return key in self.value

    def __len__(self):
        return len(self.value)

    def safe_get(self, key):
        if (isinstance(self.value, list) and isinstance(key, int) or
                key in self.value):
            return self.value[key]

    def __getitem__(self, key):
        v = self.safe_get(key)
        if v is None:
            raise ConfigException(
                'Invalid kube-config file. Expected key %s in %s'
                % (key, self.name))
        if isinstance(v, dict) or isinstance(v, list):
            return ConfigNode('%s/%s' % (self.name, key), v, self.path)
        else:
            return v

    def get_with_name(self, name, safe=False):
        if not isinstance(self.value, list):
            raise ConfigException(
                'Invalid kube-config file. Expected %s to be a list'
                % self.name)
        result = None
        for v in self.value:
            if 'name' not in v:
                raise ConfigException(
                    'Invalid kube-config file. '
                    'Expected all values in %s list to have \'name\' key'
                    % self.name)
            if v['name'] == name:
                if result is None:
                    result = v
                else:
                    raise ConfigException(
                        'Invalid kube-config file. '
                        'Expected only one object with name %s in %s list'
                        % (name, self.name))
        if result is not None:
            if isinstance(result, ConfigNode):
                return result
            else:
                return ConfigNode(
                    '%s[name=%s]' %
                    (self.name, name), result, self.path)
        if safe:
            return None
        raise ConfigException(
            'Invalid kube-config file. '
            'Expected object with name %s in %s list' % (name, self.name))

class KubeConfigMerger:

    """Reads and merges configuration from one or more kube-config's.
    The property `config` can be passed to the KubeConfigLoader as config_dict.

    It uses a path attribute from ConfigNode to store the path to kubeconfig.
    This path is required to load certs from relative paths.

    A method `save_changes` updates changed kubeconfig's (it compares current
    state of dicts with).
    """

    def __init__(self, paths):
        self.paths = []
        self.config_files = {}
        self.config_merged = None
        if hasattr(paths, 'read'):
            self._load_config_from_file_like_object(paths)
        else:
            self._load_config_from_file_path(paths)

    @property
    def config(self):
        return self.config_merged

    def _load_config_from_file_like_object(self, string):
        if hasattr(string, 'getvalue'):
            config = yaml.safe_load(string.getvalue())
        else:
            config = yaml.safe_load(string.read())

        if config is None:
            raise ConfigException(
                'Invalid kube-config.')
        if self.config_merged is None:
            self.config_merged = copy.deepcopy(config)
        # doesn't need to do any further merging

    def _load_config_from_file_path(self, string):
        for path in string.split(ENV_KUBECONFIG_PATH_SEPARATOR):
            if path:
                path = os.path.expanduser(path)
                if os.path.exists(path):
                    self.paths.append(path)
                    self.load_config(path)
        self.config_saved = copy.deepcopy(self.config_files)

    def load_config(self, path):
        with open(path) as f:
            config = yaml.safe_load(f)

        if config is None:
            raise ConfigException(
                'Invalid kube-config. '
                '%s file is empty' % path)

        if self.config_merged is None:
            config_merged = copy.deepcopy(config)
            for item in ('clusters', 'contexts', 'users'):
                config_merged[item] = []
            self.config_merged = ConfigNode(path, config_merged, path)
        for item in ('clusters', 'contexts', 'users'):
            self._merge(item, config.get(item, []) or [], path)

        if 'current-context' in config:
            self.config_merged.value['current-context'] = config['current-context']

        self.config_files[path] = config

    def _merge(self, item, add_cfg, path):
        for new_item in add_cfg:
            for exists in self.config_merged.value[item]:
                if exists['name'] == new_item['name']:
                    break
            else:
                self.config_merged.value[item].append(ConfigNode(
                    '{}/{}'.format(path, new_item), new_item, path))

    def save_changes(self):
        for path in self.paths:
            if self.config_saved[path] != self.config_files[path]:
                self.save_config(path)
        self.config_saved = copy.deepcopy(self.config_files)

    def save_config(self, path):
        with open(path, 'w') as f:
            yaml.safe_dump(self.config_files[path], f,
                           default_flow_style=False)



def _get_kube_config_loader(
        filename=None,
        config_dict=None,
        persist_config=False,
        **kwargs):
    if config_dict is None:
        kcfg = KubeConfigMerger(filename)
        if persist_config and 'config_persister' not in kwargs:
            kwargs['config_persister'] = kcfg.save_changes

        if kcfg.config is None:
            raise ConfigException(
                'Invalid kube-config file. '
                'No configuration found.')
        return KubeConfigLoader(
            config_dict=kcfg.config,
            config_base_path=None,
            **kwargs)
    else:
        return KubeConfigLoader(
            config_dict=config_dict,
            config_base_path=None,
            **kwargs)


def load_kube_config(config_file=None, context=None,
                     client_configuration=None,
                     persist_config=True,
                     temp_file_path=None):
    """Loads authentication and cluster information from kube-config file
    and stores them in kubernetes.client.configuration.

    :param config_file: Name of the kube-config file.
    :param context: set the active context. If is set to None, current_context
        from config file will be used.
    :param client_configuration: The kubernetes.client.Configuration to
        set configs to.
    :param persist_config: If True, config file will be updated when changed
        (e.g GCP token refresh).
    :param temp_file_path: store temp files path.
    """

    if config_file is None:
        config_file = KUBE_CONFIG_DEFAULT_LOCATION

    loader = _get_kube_config_loader(
        filename=config_file, active_context=context,
        persist_config=persist_config,
        temp_file_path=temp_file_path)

    if client_configuration is None:
        config = type.__call__(Configuration)
        loader.load_and_set(config)
        Configuration.set_default(config)
    else:
        loader.load_and_set(client_configuration)


def load_kube_config_from_dict(config_dict, context=None,
                               client_configuration=None,
                               persist_config=True,
                               temp_file_path=None):
    """Loads authentication and cluster information from config_dict file
    and stores them in kubernetes.client.configuration.

    :param config_dict: Takes the config file as a dict.
    :param context: set the active context. If is set to None, current_context
        from config file will be used.
    :param client_configuration: The kubernetes.client.Configuration to
        set configs to.
    :param persist_config: If True, config file will be updated when changed
        (e.g GCP token refresh).
    :param temp_file_path: store temp files path.
    """
    if config_dict is None:
        raise ConfigException(
            'Invalid kube-config dict. '
            'No configuration found.')

    loader = _get_kube_config_loader(
        config_dict=config_dict, active_context=context,
        persist_config=persist_config,
        temp_file_path=temp_file_path)

    if client_configuration is None:
        config = type.__call__(Configuration)
        loader.load_and_set(config)
        Configuration.set_default(config)
    else:
        loader.load_and_set(client_configuration)


def new_client_from_config(
        config_file=None,
        context=None,
        persist_config=True,
        client_configuration=None):
    """
    Loads configuration the same as load_kube_config but returns an ApiClient
    to be used with any API object. This will allow the caller to concurrently
    talk with multiple clusters.
    """
    if client_configuration is None:
        client_configuration = type.__call__(Configuration)
    load_kube_config(config_file=config_file, context=context,
                     client_configuration=client_configuration,
                     persist_config=persist_config)
    return ApiClient(configuration=client_configuration)


def new_client_from_config_dict(
        config_dict=None,
        context=None,
        persist_config=True,
        temp_file_path=None,
        client_configuration=None):
    """
    Loads configuration the same as load_kube_config_from_dict but returns an ApiClient
    to be used with any API object. This will allow the caller to concurrently
    talk with multiple clusters.
    """
    if client_configuration is None:
        client_configuration = type.__call__(Configuration)
    load_kube_config_from_dict(config_dict=config_dict, context=context,
                               client_configuration=client_configuration,
                               persist_config=persist_config,
                               temp_file_path=temp_file_path)
    return ApiClient(configuration=client_configuration)


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        self._temp_files = []

    def tearDown(self):
        for f in self._temp_files:
            os.remove(f)

    def _create_temp_file(self, content=""):
        handler, name = tempfile.mkstemp()
        self._temp_files.append(name)
        os.write(handler, str.encode(content))
        os.close(handler)
        return name

    def expect_exception(self, func, message_part, *args, **kwargs):
        with self.assertRaises(ConfigException) as context:
            func(*args, **kwargs)
        self.assertIn(message_part, str(context.exception))


class TestFileOrData(BaseTestCase):

    @staticmethod
    def get_file_content(filename):
        with open(filename) as f:
            return f.read()

    def test_file_given_file(self):
        temp_filename = _create_temp_file_with_content(TEST_DATA)
        obj = {TEST_FILE_KEY: temp_filename}
        t = FileOrData(obj=obj, file_key_name=TEST_FILE_KEY)
        self.assertEqual(TEST_DATA, self.get_file_content(t.as_file()))

    def test_file_given_non_existing_file(self):
        temp_filename = NON_EXISTING_FILE
        obj = {TEST_FILE_KEY: temp_filename}
        t = FileOrData(obj=obj, file_key_name=TEST_FILE_KEY)
        self.expect_exception(t.as_file, "does not exist")

    def test_file_given_data(self):
        obj = {TEST_DATA_KEY: TEST_DATA_BASE64}
        t = FileOrData(obj=obj, file_key_name=TEST_FILE_KEY,
                       data_key_name=TEST_DATA_KEY)
        self.assertEqual(TEST_DATA, self.get_file_content(t.as_file()))

    def test_file_given_data_no_base64(self):
        obj = {TEST_DATA_KEY: TEST_DATA}
        t = FileOrData(obj=obj, file_key_name=TEST_FILE_KEY,
                       data_key_name=TEST_DATA_KEY, base64_file_content=False)
        self.assertEqual(TEST_DATA, self.get_file_content(t.as_file()))

    def test_data_given_data(self):
        obj = {TEST_DATA_KEY: TEST_DATA_BASE64}
        t = FileOrData(obj=obj, file_key_name=TEST_FILE_KEY,
                       data_key_name=TEST_DATA_KEY)
        self.assertEqual(TEST_DATA_BASE64, t.as_data())

    def test_data_given_file(self):
        obj = {
            TEST_FILE_KEY: self._create_temp_file(content=TEST_DATA)}
        t = FileOrData(obj=obj, file_key_name=TEST_FILE_KEY)
        self.assertEqual(TEST_DATA_BASE64, t.as_data())

    def test_data_given_file_no_base64(self):
        obj = {
            TEST_FILE_KEY: self._create_temp_file(content=TEST_DATA)}
        t = FileOrData(obj=obj, file_key_name=TEST_FILE_KEY,
                       base64_file_content=False)
        self.assertEqual(TEST_DATA, t.as_data())

    def test_data_given_file_and_data(self):
        obj = {
            TEST_DATA_KEY: TEST_DATA_BASE64,
            TEST_FILE_KEY: self._create_temp_file(
                content=TEST_ANOTHER_DATA)}
        t = FileOrData(obj=obj, file_key_name=TEST_FILE_KEY,
                       data_key_name=TEST_DATA_KEY)
        self.assertEqual(TEST_DATA_BASE64, t.as_data())

    def test_file_given_file_and_data(self):
        obj = {
            TEST_DATA_KEY: TEST_DATA_BASE64,
            TEST_FILE_KEY: self._create_temp_file(
                content=TEST_ANOTHER_DATA)}
        t = FileOrData(obj=obj, file_key_name=TEST_FILE_KEY,
                       data_key_name=TEST_DATA_KEY)
        self.assertEqual(TEST_DATA, self.get_file_content(t.as_file()))

    def test_file_with_custom_dirname(self):
        tempfile = self._create_temp_file(content=TEST_DATA)
        tempfile_dir = os.path.dirname(tempfile)
        tempfile_basename = os.path.basename(tempfile)
        obj = {TEST_FILE_KEY: tempfile_basename}
        t = FileOrData(obj=obj, file_key_name=TEST_FILE_KEY,
                       file_base_path=tempfile_dir)
        self.assertEqual(TEST_DATA, self.get_file_content(t.as_file()))

    def test_create_temp_file_with_content(self):
        self.assertEqual(TEST_DATA,
                         self.get_file_content(
                             _create_temp_file_with_content(TEST_DATA)))
        _cleanup_temp_files()

    def test_file_given_data_bytes(self):
        obj = {TEST_DATA_KEY: TEST_DATA_BASE64.encode()}
        t = FileOrData(obj=obj, file_key_name=TEST_FILE_KEY,
                       data_key_name=TEST_DATA_KEY)
        self.assertEqual(TEST_DATA, self.get_file_content(t.as_file()))

    def test_file_given_data_bytes_no_base64(self):
        obj = {TEST_DATA_KEY: TEST_DATA.encode()}
        t = FileOrData(obj=obj, file_key_name=TEST_FILE_KEY,
                       data_key_name=TEST_DATA_KEY, base64_file_content=False)
        self.assertEqual(TEST_DATA, self.get_file_content(t.as_file()))

    def test_file_given_no_object(self):
        t = FileOrData(obj=None, file_key_name=TEST_FILE_KEY,
                       data_key_name=TEST_DATA_KEY)
        self.assertEqual(t.as_file(), None)

    def test_file_given_no_object_data(self):
        t = FileOrData(obj=None, file_key_name=TEST_FILE_KEY,
                       data_key_name=TEST_DATA_KEY)
        self.assertEqual(t.as_data(), None)

class TestConfigNode(BaseTestCase):

    test_obj = {"key1": "test", "key2": ["a", "b", "c"],
                "key3": {"inner_key": "inner_value"},
                "with_names": [{"name": "test_name", "value": "test_value"},
                               {"name": "test_name2",
                                "value": {"key1", "test"}},
                               {"name": "test_name3", "value": [1, 2, 3]}],
                "with_names_dup": [
                    {"name": "test_name", "value": "test_value"},
                    {"name": "test_name",
                     "value": {"key1", "test"}},
                    {"name": "test_name3", "value": [1, 2, 3]}
    ]}

    def setUp(self):
        super(TestConfigNode, self).setUp()
        self.node = ConfigNode("test_obj", self.test_obj)

    def test_normal_map_array_operations(self):
        self.assertEqual("test", self.node['key1'])
        self.assertEqual(5, len(self.node))

        self.assertEqual("test_obj/key2", self.node['key2'].name)
        self.assertEqual(["a", "b", "c"], self.node['key2'].value)
        self.assertEqual("b", self.node['key2'][1])
        self.assertEqual(3, len(self.node['key2']))

        self.assertEqual("test_obj/key3", self.node['key3'].name)
        self.assertEqual({"inner_key": "inner_value"},
                         self.node['key3'].value)
        self.assertEqual("inner_value", self.node['key3']["inner_key"])
        self.assertEqual(1, len(self.node['key3']))

    def test_get_with_name(self):
        node = self.node["with_names"]
        self.assertEqual(
            "test_value",
            node.get_with_name("test_name")["value"])
        self.assertTrue(
            isinstance(node.get_with_name("test_name2"), ConfigNode))
        self.assertTrue(
            isinstance(node.get_with_name("test_name3"), ConfigNode))
        self.assertEqual("test_obj/with_names[name=test_name2]",
                         node.get_with_name("test_name2").name)
        self.assertEqual("test_obj/with_names[name=test_name3]",
                         node.get_with_name("test_name3").name)

    def test_key_does_not_exists(self):
        self.expect_exception(lambda: self.node['not-exists-key'],
                              "Expected key not-exists-key in test_obj")
        self.expect_exception(lambda: self.node['key3']['not-exists-key'],
                              "Expected key not-exists-key in test_obj/key3")

    def test_get_with_name_on_invalid_object(self):
        self.expect_exception(
            lambda: self.node['key2'].get_with_name('no-name'),
            "Expected all values in test_obj/key2 list to have \'name\' key")

    def test_get_with_name_on_non_list_object(self):
        self.expect_exception(
            lambda: self.node['key3'].get_with_name('no-name'),
            "Expected test_obj/key3 to be a list")

    def test_get_with_name_on_name_does_not_exists(self):
        self.expect_exception(
            lambda: self.node['with_names'].get_with_name('no-name'),
            "Expected object with name no-name in test_obj/with_names list")

    def test_get_with_name_on_duplicate_name(self):
        self.expect_exception(
            lambda: self.node['with_names_dup'].get_with_name('test_name'),
            "Expected only one object with name test_name in "
            "test_obj/with_names_dup list")

class FakeConfig:

    FILE_KEYS = ["ssl_ca_cert", "key_file", "cert_file"]
    IGNORE_KEYS = ["refresh_api_key_hook"]

    def __init__(self, token=None, **kwargs):
        self.api_key = {}
        # Provided by the OpenAPI-generated Configuration class
        self.refresh_api_key_hook = None
        if token:
            self.api_key['authorization'] = token

        self.__dict__.update(kwargs)

    def __eq__(self, other):
        if len(self.__dict__) != len(other.__dict__):
            return
        for k, v in self.__dict__.items():
            if k in self.IGNORE_KEYS:
                continue
            if k not in other.__dict__:
                return
            if k in self.FILE_KEYS:
                if v and other.__dict__[k]:
                    try:
                        with open(v) as f1, open(other.__dict__[k]) as f2:
                            if f1.read() != f2.read():
                                return
                    except OSError:
                        # fall back to only compare filenames in case we are
                        # testing the passing of filenames to the config
                        if other.__dict__[k] != v:
                            return
                else:
                    if other.__dict__[k] != v:
                        return
            else:
                if other.__dict__[k] != v:
                    return
        return True

    def __repr__(self):
        rep = "\n"
        for k, v in self.__dict__.items():
            val = v
            if k in self.FILE_KEYS:
                try:
                    with open(v) as f:
                        val = "FILE: %s" % str.decode(f.read())
                except OSError as e:
                    val = "ERROR: %s" % str(e)
            rep += "\t%s: %s\n" % (k, val)
        return "Config(%s\n)" % rep


class TestKubeConfigLoader(BaseTestCase):
    TEST_KUBE_CONFIG = {
        "current-context": "no_user",
        "contexts": [
            {
                "name": "no_user",
                "context": {
                    "cluster": "default"
                }
            },
            {
                "name": "simple_token",
                "context": {
                    "cluster": "default",
                    "user": "simple_token"
                }
            },
            {
                "name": "gcp",
                "context": {
                    "cluster": "default",
                    "user": "gcp"
                }
            },
            {
                "name": "expired_gcp",
                "context": {
                    "cluster": "default",
                    "user": "expired_gcp"
                }
            },
            {
                "name": "expired_gcp_refresh",
                "context": {
                    "cluster": "default",
                    "user": "expired_gcp_refresh"
                }
            },
            {
                "name": "oidc",
                "context": {
                    "cluster": "default",
                    "user": "oidc"
                }
            },
            {
                "name": "azure",
                "context": {
                    "cluster": "default",
                    "user": "azure"
                }
            },
            {
                "name": "azure_num",
                "context": {
                    "cluster": "default",
                    "user": "azure_num"
                }
            },
            {
                "name": "azure_str",
                "context": {
                    "cluster": "default",
                    "user": "azure_str"
                }
            },
            {
                "name": "azure_num_error",
                "context": {
                    "cluster": "default",
                    "user": "azure_str_error"
                }
            },
            {
                "name": "azure_str_error",
                "context": {
                    "cluster": "default",
                    "user": "azure_str_error"
                }
            },
            {
                "name": "expired_oidc",
                "context": {
                    "cluster": "default",
                    "user": "expired_oidc"
                }
            },
            {
                "name": "expired_oidc_with_idp_ca_file",
                "context": {
                    "cluster": "default",
                    "user": "expired_oidc_with_idp_ca_file"
                }
            },
            {
                "name": "expired_oidc_nocert",
                "context": {
                    "cluster": "default",
                    "user": "expired_oidc_nocert"
                }
            },
            {
                "name": "oidc_contains_reserved_character",
                "context": {
                    "cluster": "default",
                    "user": "oidc_contains_reserved_character"

                }
            },
            {
                "name": "oidc_invalid_padding_length",
                "context": {
                    "cluster": "default",
                    "user": "oidc_invalid_padding_length"

                }
            },
            {
                "name": "user_pass",
                "context": {
                    "cluster": "default",
                    "user": "user_pass"
                }
            },
            {
                "name": "ssl",
                "context": {
                    "cluster": "ssl",
                    "user": "ssl"
                }
            },
            {
                "name": "no_ssl_verification",
                "context": {
                    "cluster": "no_ssl_verification",
                    "user": "ssl"
                }
            },
            {
                "name": "ssl-no_file",
                "context": {
                    "cluster": "ssl-no_file",
                    "user": "ssl-no_file"
                }
            },
            {
                "name": "ssl-local-file",
                "context": {
                    "cluster": "ssl-local-file",
                    "user": "ssl-local-file"
                }
            },
            {
                "name": "non_existing_user",
                "context": {
                    "cluster": "default",
                    "user": "non_existing_user"
                }
            },
            {
                "name": "exec_cred_user",
                "context": {
                    "cluster": "default",
                    "user": "exec_cred_user"
                }
            },
            {
                "name": "exec_cred_user_certificate",
                "context": {
                    "cluster": "ssl",
                    "user": "exec_cred_user_certificate"
                }
            },
            {
                "name": "contexttestcmdpath",
                "context": {
                    "cluster": "clustertestcmdpath",
                    "user": "usertestcmdpath"
                }
            },
            {
                "name": "contexttestcmdpathempty",
                "context": {
                    "cluster": "clustertestcmdpath",
                    "user": "usertestcmdpathempty"
                }
            },
            {
                "name": "contexttestcmdpathscope",
                "context": {
                    "cluster": "clustertestcmdpath",
                    "user": "usertestcmdpathscope"
                }
            },
            {
                "name": "tls-server-name",
                "context": {
                    "cluster": "tls-server-name",
                    "user": "ssl"
                }
            },
        ],
        "clusters": [
            {
                "name": "default",
                "cluster": {
                    "server": TEST_HOST
                }
            },
            {
                "name": "ssl-no_file",
                "cluster": {
                    "server": TEST_SSL_HOST,
                    "certificate-authority": TEST_CERTIFICATE_AUTH,
                }
            },
            {
                "name": "ssl-local-file",
                "cluster": {
                    "server": TEST_SSL_HOST,
                    "certificate-authority": "cert_test",
                }
            },
            {
                "name": "ssl",
                "cluster": {
                    "server": TEST_SSL_HOST,
                    "certificate-authority-data":
                        TEST_CERTIFICATE_AUTH_BASE64,
                    "insecure-skip-tls-verify": False,
                }
            },
            {
                "name": "no_ssl_verification",
                "cluster": {
                    "server": TEST_SSL_HOST,
                    "insecure-skip-tls-verify": True,
                }
            },
            {
                "name": "clustertestcmdpath",
                "cluster": {}
            },
            {
                "name": "tls-server-name",
                "cluster": {
                    "server": TEST_SSL_HOST,
                    "certificate-authority-data":
                        TEST_CERTIFICATE_AUTH_BASE64,
                    "insecure-skip-tls-verify": False,
                    "tls-server-name": TEST_TLS_SERVER_NAME,
                }
            },
        ],
        "users": [
            {
                "name": "simple_token",
                "user": {
                    "token": TEST_DATA_BASE64,
                    "username": TEST_USERNAME,  # should be ignored
                    "password": TEST_PASSWORD,  # should be ignored
                }
            },
            {
                "name": "gcp",
                "user": {
                    "auth-provider": {
                        "name": "gcp",
                        "config": {
                            "access-token": TEST_DATA_BASE64,
                        }
                    },
                    "token": TEST_DATA_BASE64,  # should be ignored
                    "username": TEST_USERNAME,  # should be ignored
                    "password": TEST_PASSWORD,  # should be ignored
                }
            },
            {
                "name": "expired_gcp",
                "user": {
                    "auth-provider": {
                        "name": "gcp",
                        "config": {
                            "access-token": TEST_DATA_BASE64,
                            "expiry": TEST_TOKEN_EXPIRY_PAST,  # always in past
                        }
                    },
                    "token": TEST_DATA_BASE64,  # should be ignored
                    "username": TEST_USERNAME,  # should be ignored
                    "password": TEST_PASSWORD,  # should be ignored
                }
            },
            # Duplicated from "expired_gcp" so test_load_gcp_token_with_refresh
            # is isolated from test_gcp_get_api_key_with_prefix.
            {
                "name": "expired_gcp_refresh",
                "user": {
                    "auth-provider": {
                        "name": "gcp",
                        "config": {
                            "access-token": TEST_DATA_BASE64,
                            "expiry": TEST_TOKEN_EXPIRY_PAST,  # always in past
                        }
                    },
                    "token": TEST_DATA_BASE64,  # should be ignored
                    "username": TEST_USERNAME,  # should be ignored
                    "password": TEST_PASSWORD,  # should be ignored
                }
            },
            {
                "name": "oidc",
                "user": {
                    "auth-provider": {
                        "name": "oidc",
                        "config": {
                            "id-token": TEST_OIDC_LOGIN
                        }
                    }
                }
            },
            {
                "name": "azure",
                "user": {
                    "auth-provider": {
                        "config": {
                            "access-token": TEST_AZURE_TOKEN,
                            "apiserver-id": "00000002-0000-0000-c000-"
                                            "000000000000",
                            "environment": "AzurePublicCloud",
                            "refresh-token": "refreshToken",
                            "tenant-id": "9d2ac018-e843-4e14-9e2b-4e0ddac75433"
                        },
                        "name": "azure"
                    }
                }
            },
            {
                "name": "azure_num",
                "user": {
                    "auth-provider": {
                        "config": {
                            "access-token": TEST_AZURE_TOKEN,
                            "apiserver-id": "00000002-0000-0000-c000-"
                                            "000000000000",
                            "environment": "AzurePublicCloud",
                            "expires-in": "0",
                            "expires-on": "156207275",
                            "refresh-token": "refreshToken",
                            "tenant-id": "9d2ac018-e843-4e14-9e2b-4e0ddac75433"
                        },
                        "name": "azure"
                    }
                }
            },
            {
                "name": "azure_str",
                "user": {
                    "auth-provider": {
                        "config": {
                            "access-token": TEST_AZURE_TOKEN,
                            "apiserver-id": "00000002-0000-0000-c000-"
                                            "000000000000",
                            "environment": "AzurePublicCloud",
                            "expires-in": "0",
                            "expires-on": "2018-10-18 00:52:29.044727",
                            "refresh-token": "refreshToken",
                            "tenant-id": "9d2ac018-e843-4e14-9e2b-4e0ddac75433"
                        },
                        "name": "azure"
                    }
                }
            },
            {
                "name": "azure_str_error",
                "user": {
                    "auth-provider": {
                        "config": {
                            "access-token": TEST_AZURE_TOKEN,
                            "apiserver-id": "00000002-0000-0000-c000-"
                                            "000000000000",
                            "environment": "AzurePublicCloud",
                            "expires-in": "0",
                            "expires-on": "2018-10-18 00:52",
                            "refresh-token": "refreshToken",
                            "tenant-id": "9d2ac018-e843-4e14-9e2b-4e0ddac75433"
                        },
                        "name": "azure"
                    }
                }
            },
            {
                "name": "azure_num_error",
                "user": {
                    "auth-provider": {
                        "config": {
                            "access-token": TEST_AZURE_TOKEN,
                            "apiserver-id": "00000002-0000-0000-c000-"
                                            "000000000000",
                            "environment": "AzurePublicCloud",
                            "expires-in": "0",
                            "expires-on": "-1",
                            "refresh-token": "refreshToken",
                            "tenant-id": "9d2ac018-e843-4e14-9e2b-4e0ddac75433"
                        },
                        "name": "azure"
                    }
                }
            },
            {
                "name": "expired_oidc",
                "user": {
                    "auth-provider": {
                        "name": "oidc",
                        "config": {
                            "client-id": "tectonic-kubectl",
                            "client-secret": "FAKE_SECRET",
                            "id-token": TEST_OIDC_EXPIRED_LOGIN,
                            "idp-certificate-authority-data": TEST_OIDC_CA,
                            "idp-issuer-url": "https://example.org/identity",
                            "refresh-token":
                                "lucWJjEhlxZW01cXI3YmVlcYnpxNGhzk"
                        }
                    }
                }
            },
            {
                "name": "expired_oidc_with_idp_ca_file",
                "user": {
                    "auth-provider": {
                        "name": "oidc",
                        "config": {
                            "client-id": "tectonic-kubectl",
                            "client-secret": "FAKE_SECRET",
                            "id-token": TEST_OIDC_EXPIRED_LOGIN,
                            "idp-certificate-authority": TEST_CERTIFICATE_AUTH,
                            "idp-issuer-url": "https://example.org/identity",
                            "refresh-token":
                                "lucWJjEhlxZW01cXI3YmVlcYnpxNGhzk"
                        }
                    }
                }
            },
            {
                "name": "expired_oidc_nocert",
                "user": {
                    "auth-provider": {
                        "name": "oidc",
                        "config": {
                            "client-id": "tectonic-kubectl",
                            "client-secret": "FAKE_SECRET",
                            "id-token": TEST_OIDC_EXPIRED_LOGIN,
                            "idp-issuer-url": "https://example.org/identity",
                            "refresh-token":
                                "lucWJjEhlxZW01cXI3YmVlcYnpxNGhzk"
                        }
                    }
                }
            },
            {
                "name": "oidc_contains_reserved_character",
                "user": {
                    "auth-provider": {
                        "name": "oidc",
                        "config": {
                            "client-id": "tectonic-kubectl",
                            "client-secret": "FAKE_SECRET",
                            "id-token": TEST_OIDC_CONTAINS_RESERVED_CHARACTERS,
                            "idp-issuer-url": "https://example.org/identity",
                            "refresh-token":
                                "lucWJjEhlxZW01cXI3YmVlcYnpxNGhzk"
                        }
                    }
                }
            },
            {
                "name": "oidc_invalid_padding_length",
                "user": {
                    "auth-provider": {
                        "name": "oidc",
                        "config": {
                            "client-id": "tectonic-kubectl",
                            "client-secret": "FAKE_SECRET",
                            "id-token": TEST_OIDC_INVALID_PADDING_LENGTH,
                            "idp-issuer-url": "https://example.org/identity",
                            "refresh-token":
                                "lucWJjEhlxZW01cXI3YmVlcYnpxNGhzk"
                        }
                    }
                }
            },
            {
                "name": "user_pass",
                "user": {
                    "username": TEST_USERNAME,  # should be ignored
                    "password": TEST_PASSWORD,  # should be ignored
                }
            },
            {
                "name": "ssl-no_file",
                "user": {
                    "token": TEST_DATA_BASE64,
                    "client-certificate": TEST_CLIENT_CERT,
                    "client-key": TEST_CLIENT_KEY,
                }
            },
            {
                "name": "ssl-local-file",
                "user": {
                    "tokenFile": "token_file",
                    "client-certificate": "client_cert",
                    "client-key": "client_key",
                }
            },
            {
                "name": "ssl",
                "user": {
                    "token": TEST_DATA_BASE64,
                    "client-certificate-data": TEST_CLIENT_CERT_BASE64,
                    "client-key-data": TEST_CLIENT_KEY_BASE64,
                }
            },
            {
                "name": "exec_cred_user",
                "user": {
                    "exec": {
                        "apiVersion": "client.authentication.k8s.io/v1beta1",
                        "command": "aws-iam-authenticator",
                        "args": ["token", "-i", "dummy-cluster"]
                    }
                }
            },
            {
                "name": "exec_cred_user_certificate",
                "user": {
                    "exec": {
                        "apiVersion": "client.authentication.k8s.io/v1beta1",
                        "command": "custom-certificate-authenticator",
                        "args": []
                    }
                }
            },
            {
                "name": "usertestcmdpath",
                "user": {
                    "auth-provider": {
                        "name": "gcp",
                        "config": {
                            "cmd-path": "cmdtorun"
                        }
                    }
                }
            },
            {
                "name": "usertestcmdpathempty",
                "user": {
                    "auth-provider": {
                        "name": "gcp",
                        "config": {
                            "cmd-path": ""
                        }
                    }
                }
            },
            {
                "name": "usertestcmdpathscope",
                "user": {
                    "auth-provider": {
                        "name": "gcp",
                        "config": {
                            "cmd-path": "cmd",
                            "scopes": "scope"
                        }
                    }
                }
            }
        ]
    }

    def test_no_user_context(self):
        expected = FakeConfig(host=TEST_HOST)
        actual = FakeConfig()
        KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="no_user").load_and_set(actual)
        self.assertEqual(expected, actual)

    def test_simple_token(self):
        expected = FakeConfig(host=TEST_HOST,
                              token=BEARER_TOKEN_FORMAT % TEST_DATA_BASE64)
        actual = FakeConfig()
        KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="simple_token").load_and_set(actual)
        self.assertEqual(expected, actual)

    def test_load_user_token(self):
        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="simple_token")
        self.assertTrue(loader._load_user_token())
        self.assertEqual(BEARER_TOKEN_FORMAT % TEST_DATA_BASE64, loader.token)

    def test_gcp_no_refresh(self):
        fake_config = FakeConfig()
        self.assertIsNone(fake_config.refresh_api_key_hook)
        KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="gcp",
            get_google_credentials=lambda: _raise_exception(
                "SHOULD NOT BE CALLED")).load_and_set(fake_config)
        # Should now be populated with a gcp token fetcher.
        self.assertIsNotNone(fake_config.refresh_api_key_hook)
        self.assertEqual(TEST_HOST, fake_config.host)
        self.assertEqual(BEARER_TOKEN_FORMAT % TEST_DATA_BASE64,
                         fake_config.api_key['authorization'])

    def test_load_gcp_token_no_refresh(self):
        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="gcp",
            get_google_credentials=lambda: _raise_exception(
                "SHOULD NOT BE CALLED"))
        self.assertTrue(loader._load_auth_provider_token())
        self.assertEqual(BEARER_TOKEN_FORMAT % TEST_DATA_BASE64,
                         loader.token)

    def test_load_gcp_token_with_refresh(self):
        def cred(): return None
        cred.token = TEST_ANOTHER_DATA_BASE64
        cred.expiry = datetime.datetime.utcnow()

        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="expired_gcp",
            get_google_credentials=lambda: cred)
        original_expiry = _get_expiry(loader, "expired_gcp")
        self.assertTrue(loader._load_auth_provider_token())
        new_expiry = _get_expiry(loader, "expired_gcp")
        # assert that the configs expiry actually updates
        self.assertTrue(new_expiry > original_expiry)
        self.assertEqual(BEARER_TOKEN_FORMAT % TEST_ANOTHER_DATA_BASE64,
                         loader.token)

    def test_gcp_refresh_api_key_hook(self):
        class cred_old:
            token = TEST_DATA_BASE64
            expiry = DATETIME_EXPIRY_PAST

        class cred_new:
            token = TEST_ANOTHER_DATA_BASE64
            expiry = DATETIME_EXPIRY_FUTURE
        fake_config = FakeConfig()
        _get_google_credentials = mock.Mock()
        _get_google_credentials.side_effect = [cred_old, cred_new]

        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="expired_gcp_refresh",
            get_google_credentials=_get_google_credentials)
        loader.load_and_set(fake_config)
        original_expiry = _get_expiry(loader, "expired_gcp_refresh")
        # Refresh the GCP token.
        fake_config.refresh_api_key_hook(fake_config)
        new_expiry = _get_expiry(loader, "expired_gcp_refresh")

        self.assertTrue(new_expiry > original_expiry)
        self.assertEqual(BEARER_TOKEN_FORMAT % TEST_ANOTHER_DATA_BASE64,
                         loader.token)

    def test_oidc_no_refresh(self):
        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="oidc",
        )
        self.assertTrue(loader._load_auth_provider_token())
        self.assertEqual(TEST_OIDC_TOKEN, loader.token)

    @mock.patch('kubernetes.config.kube_config.OAuth2Session.refresh_token')
    @mock.patch('kubernetes.config.kube_config.ApiClient.request')
    def test_oidc_with_refresh(self, mock_ApiClient, mock_OAuth2Session):
        mock_response = mock.MagicMock()
        type(mock_response).status = mock.PropertyMock(
            return_value=200
        )
        type(mock_response).data = mock.PropertyMock(
            return_value=json.dumps({
                "token_endpoint": "https://example.org/identity/token"
            })
        )

        mock_ApiClient.return_value = mock_response

        mock_OAuth2Session.return_value = {"id_token": "abc123",
                                           "refresh_token": "newtoken123"}

        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="expired_oidc",
        )
        self.assertTrue(loader._load_auth_provider_token())
        self.assertEqual("Bearer abc123", loader.token)

    @mock.patch('kubernetes.config.kube_config.OAuth2Session.refresh_token')
    @mock.patch('kubernetes.config.kube_config.ApiClient.request')
    def test_oidc_with_idp_ca_file_refresh(self, mock_ApiClient, mock_OAuth2Session):
        mock_response = mock.MagicMock()
        type(mock_response).status = mock.PropertyMock(
            return_value=200
        )
        type(mock_response).data = mock.PropertyMock(
            return_value=json.dumps({
                "token_endpoint": "https://example.org/identity/token"
            })
        )

        mock_ApiClient.return_value = mock_response

        mock_OAuth2Session.return_value = {"id_token": "abc123",
                                           "refresh_token": "newtoken123"}

        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="expired_oidc_with_idp_ca_file",
        )


        self.assertTrue(loader._load_auth_provider_token())
        self.assertEqual("Bearer abc123", loader.token)

    @mock.patch('kubernetes.config.kube_config.OAuth2Session.refresh_token')
    @mock.patch('kubernetes.config.kube_config.ApiClient.request')
    def test_oidc_with_refresh_nocert(
            self, mock_ApiClient, mock_OAuth2Session):
        mock_response = mock.MagicMock()
        type(mock_response).status = mock.PropertyMock(
            return_value=200
        )
        type(mock_response).data = mock.PropertyMock(
            return_value=json.dumps({
                "token_endpoint": "https://example.org/identity/token"
            })
        )

        mock_ApiClient.return_value = mock_response

        mock_OAuth2Session.return_value = {"id_token": "abc123",
                                           "refresh_token": "newtoken123"}

        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="expired_oidc_nocert",
        )
        self.assertTrue(loader._load_auth_provider_token())
        self.assertEqual("Bearer abc123", loader.token)

    def test_oidc_fails_if_contains_reserved_chars(self):
        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="oidc_contains_reserved_character",
        )
        self.assertEqual(
            loader._load_oid_token("oidc_contains_reserved_character"),
            None,
        )

    def test_oidc_fails_if_invalid_padding_length(self):
        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="oidc_invalid_padding_length",
        )
        self.assertEqual(
            loader._load_oid_token("oidc_invalid_padding_length"),
            None,
        )

    def test_azure_no_refresh(self):
        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="azure",
        )
        self.assertTrue(loader._load_auth_provider_token())
        self.assertEqual(TEST_AZURE_TOKEN_FULL, loader.token)

    def test_azure_with_expired_num(self):
        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="azure_num",
        )
        provider = loader._user['auth-provider']
        self.assertTrue(loader._azure_is_expired(provider))

    def test_azure_with_expired_str(self):
        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="azure_str",
        )
        provider = loader._user['auth-provider']
        self.assertTrue(loader._azure_is_expired(provider))

    def test_azure_with_expired_str_error(self):
        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="azure_str_error",
        )
        provider = loader._user['auth-provider']
        self.assertRaises(ValueError, loader._azure_is_expired, provider)

    def test_azure_with_expired_int_error(self):
        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="azure_num_error",
        )
        provider = loader._user['auth-provider']
        self.assertRaises(ValueError, loader._azure_is_expired, provider)

    def test_user_pass(self):
        expected = FakeConfig(host=TEST_HOST, token=TEST_BASIC_TOKEN)
        actual = FakeConfig()
        KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="user_pass").load_and_set(actual)
        self.assertEqual(expected, actual)

    def test_load_user_pass_token(self):
        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="user_pass")
        self.assertTrue(loader._load_user_pass_token())
        self.assertEqual(TEST_BASIC_TOKEN, loader.token)

    def test_ssl_no_cert_files(self):
        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="ssl-no_file")
        self.expect_exception(
            loader.load_and_set,
            "does not exist",
            FakeConfig())

    def test_ssl(self):
        expected = FakeConfig(
            host=TEST_SSL_HOST,
            token=BEARER_TOKEN_FORMAT % TEST_DATA_BASE64,
            cert_file=self._create_temp_file(TEST_CLIENT_CERT),
            key_file=self._create_temp_file(TEST_CLIENT_KEY),
            ssl_ca_cert=self._create_temp_file(TEST_CERTIFICATE_AUTH),
            verify_ssl=True
        )
        actual = FakeConfig()
        KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="ssl").load_and_set(actual)
        self.assertEqual(expected, actual)

    def test_ssl_no_verification(self):
        expected = FakeConfig(
            host=TEST_SSL_HOST,
            token=BEARER_TOKEN_FORMAT % TEST_DATA_BASE64,
            cert_file=self._create_temp_file(TEST_CLIENT_CERT),
            key_file=self._create_temp_file(TEST_CLIENT_KEY),
            verify_ssl=False,
            ssl_ca_cert=None,
        )
        actual = FakeConfig()
        KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="no_ssl_verification").load_and_set(actual)
        self.assertEqual(expected, actual)

    def test_tls_server_name(self):
        expected = FakeConfig(
            host=TEST_SSL_HOST,
            token=BEARER_TOKEN_FORMAT % TEST_DATA_BASE64,
            cert_file=self._create_temp_file(TEST_CLIENT_CERT),
            key_file=self._create_temp_file(TEST_CLIENT_KEY),
            ssl_ca_cert=self._create_temp_file(TEST_CERTIFICATE_AUTH),
            verify_ssl=True,
            tls_server_name=TEST_TLS_SERVER_NAME
        )
        actual = FakeConfig()
        KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="tls-server-name").load_and_set(actual)
        self.assertEqual(expected, actual)

    def test_list_contexts(self):
        loader = KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="no_user")
        actual_contexts = loader.list_contexts()
        expected_contexts = ConfigNode("", self.TEST_KUBE_CONFIG)['contexts']
        for actual in actual_contexts:
            expected = expected_contexts.get_with_name(actual['name'])
            self.assertEqual(expected.value, actual)

    def test_current_context(self):
        loader = KubeConfigLoader(config_dict=self.TEST_KUBE_CONFIG)
        expected_contexts = ConfigNode("", self.TEST_KUBE_CONFIG)['contexts']
        self.assertEqual(expected_contexts.get_with_name("no_user").value,
                         loader.current_context)

    def test_set_active_context(self):
        loader = KubeConfigLoader(config_dict=self.TEST_KUBE_CONFIG)
        loader.set_active_context("ssl")
        expected_contexts = ConfigNode("", self.TEST_KUBE_CONFIG)['contexts']
        self.assertEqual(expected_contexts.get_with_name("ssl").value,
                         loader.current_context)

    def test_ssl_with_relative_ssl_files(self):
        expected = FakeConfig(
            host=TEST_SSL_HOST,
            token=BEARER_TOKEN_FORMAT % TEST_DATA_BASE64,
            cert_file=self._create_temp_file(TEST_CLIENT_CERT),
            key_file=self._create_temp_file(TEST_CLIENT_KEY),
            ssl_ca_cert=self._create_temp_file(TEST_CERTIFICATE_AUTH)
        )
        try:
            temp_dir = tempfile.mkdtemp()
            actual = FakeConfig()
            with open(os.path.join(temp_dir, "cert_test"), "wb") as fd:
                fd.write(TEST_CERTIFICATE_AUTH.encode())
            with open(os.path.join(temp_dir, "client_cert"), "wb") as fd:
                fd.write(TEST_CLIENT_CERT.encode())
            with open(os.path.join(temp_dir, "client_key"), "wb") as fd:
                fd.write(TEST_CLIENT_KEY.encode())
            with open(os.path.join(temp_dir, "token_file"), "wb") as fd:
                fd.write(TEST_DATA_BASE64.encode())
            KubeConfigLoader(
                config_dict=self.TEST_KUBE_CONFIG,
                active_context="ssl-local-file",
                config_base_path=temp_dir).load_and_set(actual)
            self.assertEqual(expected, actual)
        finally:
            shutil.rmtree(temp_dir)

    def test_load_kube_config_from_file_path(self):
        expected = FakeConfig(host=TEST_HOST,
                              token=BEARER_TOKEN_FORMAT % TEST_DATA_BASE64)
        config_file = self._create_temp_file(
            yaml.safe_dump(self.TEST_KUBE_CONFIG))
        actual = FakeConfig()
        load_kube_config(config_file=config_file, context="simple_token",
                         client_configuration=actual)
        self.assertEqual(expected, actual)

    def test_load_kube_config_from_file_like_object(self):
        expected = FakeConfig(host=TEST_HOST,
                              token=BEARER_TOKEN_FORMAT % TEST_DATA_BASE64)
        config_file_like_object = io.StringIO()
        # py3 (won't have unicode) vs py2 (requires it)
        try:
            unicode('')
            config_file_like_object.write(
                unicode(
                    yaml.safe_dump(
                        self.TEST_KUBE_CONFIG),
                    errors='replace'))
        except NameError:
            config_file_like_object.write(
                yaml.safe_dump(
                    self.TEST_KUBE_CONFIG))
        actual = FakeConfig()
        load_kube_config(
            config_file=config_file_like_object,
            context="simple_token",
            client_configuration=actual)
        self.assertEqual(expected, actual)

    def test_load_kube_config_from_dict(self):
        expected = FakeConfig(host=TEST_HOST,
                              token=BEARER_TOKEN_FORMAT % TEST_DATA_BASE64)
        actual = FakeConfig()
        load_kube_config_from_dict(config_dict=self.TEST_KUBE_CONFIG,
                                   context="simple_token",
                                   client_configuration=actual)
        self.assertEqual(expected, actual)

    def test_load_kube_config_from_dict_with_temp_file_path(self):
        expected = FakeConfig(
            host=TEST_SSL_HOST,
            token=BEARER_TOKEN_FORMAT % TEST_DATA_BASE64,
            cert_file=self._create_temp_file(TEST_CLIENT_CERT),
            key_file=self._create_temp_file(TEST_CLIENT_KEY),
            ssl_ca_cert=self._create_temp_file(TEST_CERTIFICATE_AUTH),
            verify_ssl=True
        )
        actual = FakeConfig()
        tmp_path = os.path.join(
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__))),
            'tmp_file_path_test')
        load_kube_config_from_dict(config_dict=self.TEST_KUBE_CONFIG,
                                   context="ssl",
                                   client_configuration=actual,
                                   temp_file_path=tmp_path)
        self.assertFalse(True if not os.listdir(tmp_path) else False)
        self.assertEqual(expected, actual)
        _cleanup_temp_files

    def test_load_kube_config_from_empty_file_like_object(self):
        config_file_like_object = io.StringIO()
        self.assertRaises(
            ConfigException,
            load_kube_config,
            config_file_like_object)

    def test_load_kube_config_from_empty_file(self):
        config_file = self._create_temp_file(
            yaml.safe_dump(None))
        self.assertRaises(
            ConfigException,
            load_kube_config,
            config_file)

    def test_list_kube_config_contexts(self):
        config_file = self._create_temp_file(
            yaml.safe_dump(self.TEST_KUBE_CONFIG))
        contexts, active_context = list_kube_config_contexts(
            config_file=config_file)
        self.assertDictEqual(self.TEST_KUBE_CONFIG['contexts'][0],
                             active_context)
        if PY3:
            self.assertCountEqual(self.TEST_KUBE_CONFIG['contexts'],
                                  contexts)
        else:
            self.assertItemsEqual(self.TEST_KUBE_CONFIG['contexts'],
                                  contexts)

    def test_new_client_from_config(self):
        config_file = self._create_temp_file(
            yaml.safe_dump(self.TEST_KUBE_CONFIG))
        client = new_client_from_config(
            config_file=config_file, context="simple_token")
        self.assertEqual(TEST_HOST, client.configuration.host)
        self.assertEqual(BEARER_TOKEN_FORMAT % TEST_DATA_BASE64,
                         client.configuration.api_key['authorization'])

    def test_new_client_from_config_dict(self):
        client = new_client_from_config_dict(
            config_dict=self.TEST_KUBE_CONFIG, context="simple_token")
        self.assertEqual(TEST_HOST, client.configuration.host)
        self.assertEqual(BEARER_TOKEN_FORMAT % TEST_DATA_BASE64,
                         client.configuration.api_key['authorization'])

    def test_no_users_section(self):
        expected = FakeConfig(host=TEST_HOST)
        actual = FakeConfig()
        test_kube_config = self.TEST_KUBE_CONFIG.copy()
        del test_kube_config['users']
        KubeConfigLoader(
            config_dict=test_kube_config,
            active_context="gcp").load_and_set(actual)
        self.assertEqual(expected, actual)

    def test_non_existing_user(self):
        expected = FakeConfig(host=TEST_HOST)
        actual = FakeConfig()
        KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="non_existing_user").load_and_set(actual)
        self.assertEqual(expected, actual)

    @mock.patch('kubernetes.config.kube_config.ExecProvider.run')
    def test_user_exec_auth(self, mock):
        token = "dummy"
        mock.return_value = {
            "token": token
        }
        expected = FakeConfig(host=TEST_HOST, api_key={
                              "authorization": BEARER_TOKEN_FORMAT % token})
        actual = FakeConfig()
        KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="exec_cred_user").load_and_set(actual)
        self.assertEqual(expected, actual)

    @mock.patch('kubernetes.config.kube_config.ExecProvider.run')
    def test_user_exec_auth_with_expiry(self, mock):
        expired_token = "expired"
        current_token = "current"
        mock.side_effect = [
            {
                "token": expired_token,
                "expirationTimestamp": format_rfc3339(DATETIME_EXPIRY_PAST)
            },
            {
                "token": current_token,
                "expirationTimestamp": format_rfc3339(DATETIME_EXPIRY_FUTURE)
            }
        ]

        fake_config = FakeConfig()
        self.assertIsNone(fake_config.refresh_api_key_hook)

        KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="exec_cred_user").load_and_set(fake_config)
        # The kube config should use the first token returned from the
        # exec provider.
        self.assertEqual(fake_config.api_key["authorization"],
                         BEARER_TOKEN_FORMAT % expired_token)
        # Should now be populated with a method to refresh expired tokens.
        self.assertIsNotNone(fake_config.refresh_api_key_hook)
        # Refresh the token; the kube config should be updated.
        fake_config.refresh_api_key_hook(fake_config)
        self.assertEqual(fake_config.api_key["authorization"],
                         BEARER_TOKEN_FORMAT % current_token)

    @mock.patch('kubernetes.config.kube_config.ExecProvider.run')
    def test_user_exec_auth_certificates(self, mock):
        mock.return_value = {
            "clientCertificateData": TEST_CLIENT_CERT,
            "clientKeyData": TEST_CLIENT_KEY,
        }
        expected = FakeConfig(
            host=TEST_SSL_HOST,
            cert_file=self._create_temp_file(TEST_CLIENT_CERT),
            key_file=self._create_temp_file(TEST_CLIENT_KEY),
            ssl_ca_cert=self._create_temp_file(TEST_CERTIFICATE_AUTH),
            verify_ssl=True)
        actual = FakeConfig()
        KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="exec_cred_user_certificate").load_and_set(actual)
        self.assertEqual(expected, actual)

    @mock.patch('kubernetes.config.kube_config.ExecProvider.run', autospec=True)
    def test_user_exec_cwd(self, mock):
        capture = {}
        def capture_cwd(exec_provider):
            capture['cwd'] = exec_provider.cwd
        mock.side_effect = capture_cwd

        expected = "/some/random/path"
        KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="exec_cred_user",
            config_base_path=expected).load_and_set(FakeConfig())
        self.assertEqual(expected, capture['cwd'])

    def test_user_cmd_path(self):
        A = namedtuple('A', ['token', 'expiry'])
        token = "dummy"
        return_value = A(token, parse_rfc3339(datetime.datetime.now()))
        CommandTokenSource.token = mock.Mock(return_value=return_value)
        expected = FakeConfig(api_key={
                              "authorization": BEARER_TOKEN_FORMAT % token})
        actual = FakeConfig()
        KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="contexttestcmdpath").load_and_set(actual)
        self.assertEqual(expected, actual)

    def test_user_cmd_path_empty(self):
        A = namedtuple('A', ['token', 'expiry'])
        token = "dummy"
        return_value = A(token, parse_rfc3339(datetime.datetime.now()))
        CommandTokenSource.token = mock.Mock(return_value=return_value)
        expected = FakeConfig(api_key={
                              "authorization": BEARER_TOKEN_FORMAT % token})
        actual = FakeConfig()
        self.expect_exception(lambda: KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="contexttestcmdpathempty").load_and_set(actual),
            "missing access token cmd "
            "(cmd-path is an empty string in your kubeconfig file)")

    def test_user_cmd_path_with_scope(self):
        A = namedtuple('A', ['token', 'expiry'])
        token = "dummy"
        return_value = A(token, parse_rfc3339(datetime.datetime.now()))
        CommandTokenSource.token = mock.Mock(return_value=return_value)
        expected = FakeConfig(api_key={
                              "authorization": BEARER_TOKEN_FORMAT % token})
        actual = FakeConfig()
        self.expect_exception(lambda: KubeConfigLoader(
            config_dict=self.TEST_KUBE_CONFIG,
            active_context="contexttestcmdpathscope").load_and_set(actual),
            "scopes can only be used when kubectl is using "
            "a gcp service account key")

    def test__get_kube_config_loader_for_yaml_file_no_persist(self):
        expected = FakeConfig(host=TEST_HOST,
                              token=BEARER_TOKEN_FORMAT % TEST_DATA_BASE64)
        config_file = self._create_temp_file(
            yaml.safe_dump(self.TEST_KUBE_CONFIG))
        actual = _get_kube_config_loader_for_yaml_file(config_file)
        self.assertIsNone(actual._config_persister)

    def test__get_kube_config_loader_for_yaml_file_persist(self):
        expected = FakeConfig(host=TEST_HOST,
                              token=BEARER_TOKEN_FORMAT % TEST_DATA_BASE64)
        config_file = self._create_temp_file(
            yaml.safe_dump(self.TEST_KUBE_CONFIG))
        actual = _get_kube_config_loader_for_yaml_file(config_file,
                                                       persist_config=True)
        self.assertTrue(callable(actual._config_persister))
        self.assertEqual(actual._config_persister.__name__, "save_changes")

    def test__get_kube_config_loader_file_no_persist(self):
        expected = FakeConfig(host=TEST_HOST,
                              token=BEARER_TOKEN_FORMAT % TEST_DATA_BASE64)
        config_file = self._create_temp_file(
            yaml.safe_dump(self.TEST_KUBE_CONFIG))
        actual = _get_kube_config_loader(filename=config_file)
        self.assertIsNone(actual._config_persister)

    def test__get_kube_config_loader_file_persist(self):
        expected = FakeConfig(host=TEST_HOST,
                              token=BEARER_TOKEN_FORMAT % TEST_DATA_BASE64)
        config_file = self._create_temp_file(
            yaml.safe_dump(self.TEST_KUBE_CONFIG))
        actual = _get_kube_config_loader(filename=config_file,
                                         persist_config=True)
        self.assertTrue(callable(actual._config_persister))
        self.assertEqual(actual._config_persister.__name__, "save_changes")

    def test__get_kube_config_loader_dict_no_persist(self):
        expected = FakeConfig(host=TEST_HOST,
                              token=BEARER_TOKEN_FORMAT % TEST_DATA_BASE64)
        actual = _get_kube_config_loader(
            config_dict=self.TEST_KUBE_CONFIG)
        self.assertIsNone(actual._config_persister)


class TestKubernetesClientConfiguration(BaseTestCase):
    # Verifies properties of kubernetes.client.Configuration.
    # These tests guard against changes to the upstream configuration class,
    # since GCP and Exec authorization use refresh_api_key_hook to refresh
    # their tokens regularly.

    def test_refresh_api_key_hook_exists(self):
        self.assertTrue(hasattr(Configuration(), 'refresh_api_key_hook'))

    def test_get_api_key_calls_refresh_api_key_hook(self):
        identifier = 'authorization'
        expected_token = 'expected_token'
        old_token = 'old_token'
        config = Configuration(
            api_key={identifier: old_token},
            api_key_prefix={identifier: 'Bearer'}
        )

        def refresh_api_key_hook(client_config):
            self.assertEqual(client_config, config)
            client_config.api_key[identifier] = expected_token
        config.refresh_api_key_hook = refresh_api_key_hook

        self.assertEqual('Bearer ' + expected_token,
                         config.get_api_key_with_prefix(identifier))


class TestKubeConfigMerger(BaseTestCase):
    TEST_KUBE_CONFIG_SET1 = [{
        "current-context": "no_user",
        "contexts": [
            {
                "name": "no_user",
                "context": {
                    "cluster": "default"
                }
            },
        ],
        "clusters": [
            {
                "name": "default",
                "cluster": {
                    "server": TEST_HOST
                }
            },
        ],
        "users": []
    }, {
        "current-context": "",
        "contexts": [
            {
                "name": "ssl",
                "context": {
                    "cluster": "ssl",
                    "user": "ssl"
                }
            },
            {
                "name": "simple_token",
                "context": {
                    "cluster": "default",
                    "user": "simple_token"
                }
            },
        ],
        "clusters": [
            {
                "name": "ssl",
                "cluster": {
                    "server": TEST_SSL_HOST,
                    "certificate-authority-data":
                        TEST_CERTIFICATE_AUTH_BASE64,
                }
            },
        ],
        "users": [
            {
                "name": "ssl",
                "user": {
                    "token": TEST_DATA_BASE64,
                    "client-certificate-data": TEST_CLIENT_CERT_BASE64,
                    "client-key-data": TEST_CLIENT_KEY_BASE64,
                }
            },
        ]
    }, {
        "current-context": "no_user",
        "contexts": [
            {
                "name": "expired_oidc",
                "context": {
                    "cluster": "default",
                    "user": "expired_oidc"
                }
            },
            {
                "name": "ssl",
                "context": {
                    "cluster": "skipped-part2-defined-this-context",
                    "user": "skipped"
                }
            },
        ],
        "clusters": [
        ],
        "users": [
            {
                "name": "expired_oidc",
                "user": {
                    "auth-provider": {
                        "name": "oidc",
                        "config": {
                            "client-id": "tectonic-kubectl",
                            "client-secret": "FAKE_SECRET",
                            "id-token": TEST_OIDC_EXPIRED_LOGIN,
                            "idp-certificate-authority-data": TEST_OIDC_CA,
                            "idp-issuer-url": "https://example.org/identity",
                            "refresh-token":
                                "lucWJjEhlxZW01cXI3YmVlcYnpxNGhzk"
                        }
                    }
                }
            },
            {
                "name": "simple_token",
                "user": {
                    "token": TEST_DATA_BASE64,
                    "username": TEST_USERNAME,  # should be ignored
                    "password": TEST_PASSWORD,  # should be ignored
                }
            },
        ]
    }, {
        "current-context": "no_user",
    }, {
        # Config with user having cmd-path
        "contexts": [
            {
                "name": "contexttestcmdpath",
                "context": {
                    "cluster": "clustertestcmdpath",
                    "user": "usertestcmdpath"
                }
            }
        ],
        "clusters": [
            {
                "name": "clustertestcmdpath",
                "cluster": {}
            }
        ],
        "users": [
            {
                "name": "usertestcmdpath",
                "user": {
                    "auth-provider": {
                        "name": "gcp",
                        "config": {
                            "cmd-path": "cmdtorun"
                        }
                    }
                }
            }
        ]
    }, {
        "current-context": "no_user",
        "contexts": [
            {
                "name": "no_user",
                "context": {
                    "cluster": "default"
                }
            },
        ],
        "clusters": [
            {
                "name": "default",
                "cluster": {
                    "server": TEST_HOST
                }
            },
        ],
        "users": None
    }]
    # 3 parts with different keys/data to merge
    TEST_KUBE_CONFIG_SET2 = [{
        "clusters": [
            {
                "name": "default",
                "cluster": {
                    "server": TEST_HOST
                }
            },
        ],
    }, {
        "current-context": "simple_token",
        "contexts": [
            {
                "name": "simple_token",
                "context": {
                    "cluster": "default",
                    "user": "simple_token"
                }
            },
        ],
    }, {
        "users": [
            {
                "name": "simple_token",
                "user": {
                    "token": TEST_DATA_BASE64,
                    "username": TEST_USERNAME,
                    "password": TEST_PASSWORD,
                }
            },
        ]
    }]

    def _create_multi_config(self, parts):
        files = []
        for part in parts:
            files.append(self._create_temp_file(yaml.safe_dump(part)))
        return ENV_KUBECONFIG_PATH_SEPARATOR.join(files)

    def test_list_kube_config_contexts(self):
        kubeconfigs = self._create_multi_config(self.TEST_KUBE_CONFIG_SET1)
        expected_contexts = [
            {'context': {'cluster': 'default'}, 'name': 'no_user'},
            {'context': {'cluster': 'ssl', 'user': 'ssl'}, 'name': 'ssl'},
            {'context': {'cluster': 'default', 'user': 'simple_token'},
             'name': 'simple_token'},
            {'context': {'cluster': 'default', 'user': 'expired_oidc'},
             'name': 'expired_oidc'},
            {'context': {'cluster': 'clustertestcmdpath',
                         'user': 'usertestcmdpath'},
             'name': 'contexttestcmdpath'}]

        contexts, active_context = list_kube_config_contexts(
            config_file=kubeconfigs)

        self.assertEqual(contexts, expected_contexts)
        self.assertEqual(active_context, expected_contexts[0])

    def test_new_client_from_config(self):
        kubeconfigs = self._create_multi_config(self.TEST_KUBE_CONFIG_SET1)
        client = new_client_from_config(
            config_file=kubeconfigs, context="simple_token")
        self.assertEqual(TEST_HOST, client.configuration.host)
        self.assertEqual(BEARER_TOKEN_FORMAT % TEST_DATA_BASE64,
                         client.configuration.api_key['authorization'])

    def test_merge_with_context_in_different_file(self):
        kubeconfigs = self._create_multi_config(self.TEST_KUBE_CONFIG_SET2)
        client = new_client_from_config(config_file=kubeconfigs)

        expected_contexts = [
            {'context': {'cluster': 'default', 'user': 'simple_token'},
             'name': 'simple_token'}
        ]
        contexts, active_context = list_kube_config_contexts(
            config_file=kubeconfigs)
        self.assertEqual(contexts, expected_contexts)
        self.assertEqual(active_context, expected_contexts[0])
        self.assertEqual(TEST_HOST, client.configuration.host)
        self.assertEqual(BEARER_TOKEN_FORMAT % TEST_DATA_BASE64,
                         client.configuration.api_key['authorization'])

    def test_save_changes(self):
        kubeconfigs = self._create_multi_config(self.TEST_KUBE_CONFIG_SET1)

        # load configuration, update token, save config
        kconf = KubeConfigMerger(kubeconfigs)
        user = kconf.config['users'].get_with_name('expired_oidc')['user']
        provider = user['auth-provider']['config']
        provider.value['id-token'] = "token-changed"
        kconf.save_changes()

        # re-read configuration
        kconf = KubeConfigMerger(kubeconfigs)
        user = kconf.config['users'].get_with_name('expired_oidc')['user']
        provider = user['auth-provider']['config']

        # new token
        self.assertEqual(provider.value['id-token'], "token-changed")

