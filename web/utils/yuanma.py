import pygame, random, sys, time
from pygame.locals import *


class SecureCookieSessionInterface(SessionInterface):
    """The default session interface that stores sessions in signed cookies
    through the :mod:`itsdangerous` module.
    """

    salt = 'cookie-session'

    digest_method = staticmethod(hashlib.sha1)

    key_derivation = 'hmac'

    serializer = session_json_serializer
    session_class = SecureCookieSession

    def get_signing_serializer(self, app):
        if not app.secret_key:
            return None
        signer_kwargs = dict(
            key_derivation=self.key_derivation,
            digest_method=self.digest_method
        )
        return URLSafeTimedSerializer(app.secret_key, salt=self.salt,
                                      serializer=self.serializer,
                                      signer_kwargs=signer_kwargs)

    def open_session(self, app, request):
        s = self.get_signing_serializer(app)
        if s is None:
            return None
        val = request.cookies.get(app.session_cookie_name)
        if not val:
            return self.session_class()
        max_age = total_seconds(app.permanent_session_lifetime)
        try:
            data = s.loads(val, max_age=max_age)
            return self.session_class(data)
        except BadSignature:
            return self.session_class()

    def save_session(self, app, session, response):
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)

        if not session:
            if session.modified:
                response.delete_cookie(
                    app.session_cookie_name,
                    domain=domain,
                    path=path
                )

            return

        if session.accessed:
            response.vary.add('Cookie')

        if not self.should_set_cookie(app, session):
            return

        httponly = self.get_cookie_httponly(app)
        secure = self.get_cookie_secure(app)
        samesite = self.get_cookie_samesite(app)
        expires = self.get_expiration_time(app, session)
        val = self.get_signing_serializer(app).dumps(dict(session))
        response.set_cookie(
            app.session_cookie_name,
            val,
            expires=expires,
            httponly=httponly,
            domain=domain,
            path=path,
            secure=secure,
            samesite=samesite
        )


def _default_template_ctx_processor():
    """Default template context processor.  Injects `request`,
    `session` and `g`.
    """
    reqctx = _request_ctx_stack.top
    appctx = _app_ctx_stack.top
    rv = {}
    if appctx is not None:
        rv['g'] = appctx.g
    if reqctx is not None:
        rv['request'] = reqctx.request
        rv['session'] = reqctx.session
    return rv


class Environment(BaseEnvironment):
    """Works like a regular Jinja2 environment but has some additional
    knowledge of how Flask's blueprint works so that it can prepend the
    name of the blueprint to referenced templates if necessary.
    """

    def __init__(self, app, **options):
        if 'loader' not in options:
            options['loader'] = app.create_global_jinja_loader()
        BaseEnvironment.__init__(self, **options)
        self.app = app


class DispatchingJinjaLoader(BaseLoader):
    """A loader that looks for templates in the application and all
    the blueprint folders.
    """

    def __init__(self, app):
        self.app = app

    def get_source(self, environment, template):
        if self.app.config['EXPLAIN_TEMPLATE_LOADING']:
            return self._get_source_explained(environment, template)
        return self._get_source_fast(environment, template)

    def _get_source_explained(self, environment, template):
        attempts = []
        trv = None

        for srcobj, loader in self._iter_loaders(template):
            try:
                rv = loader.get_source(environment, template)
                if trv is None:
                    trv = rv
            except TemplateNotFound:
                rv = None
            attempts.append((loader, srcobj, rv))

        from .debughelpers import explain_template_loading_attempts
        explain_template_loading_attempts(self.app, template, attempts)

        if trv is not None:
            return trv
        raise TemplateNotFound(template)

    def _get_source_fast(self, environment, template):
        for srcobj, loader in self._iter_loaders(template):
            try:
                return loader.get_source(environment, template)
            except TemplateNotFound:
                continue
        raise TemplateNotFound(template)

    def _iter_loaders(self, template):
        loader = self.app.jinja_loader
        if loader is not None:
            yield self.app, loader

        for blueprint in self.app.iter_blueprints():
            loader = blueprint.jinja_loader
            if loader is not None:
                yield blueprint, loader

    def list_templates(self):
        result = set()
        loader = self.app.jinja_loader
        if loader is not None:
            result.update(loader.list_templates())

        for blueprint in self.app.iter_blueprints():
            loader = blueprint.jinja_loader
            if loader is not None:
                for template in loader.list_templates():
                    result.add(template)

        return list(result)


def _render(template, context, app):
    """Renders the template and fires the signal"""

    before_render_template.send(app, template=template, context=context)
    rv = template.render(context)
    template_rendered.send(app, template=template, context=context)
    return rv


def render_template(template_name_or_list, **context):

    ctx = _app_ctx_stack.top
    ctx.app.update_template_context(context)
    return _render(ctx.app.jinja_env.get_or_select_template(template_name_or_list),
                   context, ctx.app)


def render_template_string(source, **context):

    ctx = _app_ctx_stack.top
    ctx.app.update_template_context(context)
    return _render(ctx.app.jinja_env.from_string(source),
                   context, ctx.app)


def make_test_environ_builder(
        app, path='/', base_url=None, subdomain=None, url_scheme=None,
        *args, **kwargs
):
    """Creates a new test builder with some application defaults thrown in."""

    assert (
            not (base_url or subdomain or url_scheme)
            or (base_url is not None) != bool(subdomain or url_scheme)
    ), 'Cannot pass "subdomain" or "url_scheme" with "base_url".'

    if base_url is None:
        http_host = app.config.get('SERVER_NAME') or 'localhost'
        app_root = app.config['APPLICATION_ROOT']

        if subdomain:
            http_host = '{0}.{1}'.format(subdomain, http_host)

        if url_scheme is None:
            url_scheme = app.config['PREFERRED_URL_SCHEME']

        url = url_parse(path)
        base_url = '{scheme}://{netloc}/{path}'.format(
            scheme=url.scheme or url_scheme,
            netloc=url.netloc or http_host,
            path=app_root.lstrip('/')
        )
        path = url.path

        if url.query:
            sep = b'?' if isinstance(url.query, bytes) else '?'
            path += sep + url.query

    if 'json' in kwargs:
        assert 'data' not in kwargs, (
            "Client cannot provide both 'json' and 'data'."
        )

        with app.app_context():
            kwargs['data'] = json_dumps(kwargs.pop('json'))

        if 'content_type' not in kwargs:
            kwargs['content_type'] = 'application/json'

    return EnvironBuilder(path, base_url, *args, **kwargs)


class FlaskClient(Client):


    preserve_context = False

    def __init__(self, *args, **kwargs):
        super(FlaskClient, self).__init__(*args, **kwargs)
        self.environ_base = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "werkzeug/" + werkzeug.__version__
        }

    @contextmanager
    def session_transaction(self, *args, **kwargs):

        if self.cookie_jar is None:
            raise RuntimeError('Session transactions only make sense '
                               'with cookies enabled.')
        app = self.application
        environ_overrides = kwargs.setdefault('environ_overrides', {})
        self.cookie_jar.inject_wsgi(environ_overrides)
        outer_reqctx = _request_ctx_stack.top
        with app.test_request_context(*args, **kwargs) as c:
            session_interface = app.session_interface
            sess = session_interface.open_session(app, c.request)
            if sess is None:
                raise RuntimeError('Session backend did not open a session. '
                                   'Check the configuration')

            _request_ctx_stack.push(outer_reqctx)
            try:
                yield sess
            finally:
                _request_ctx_stack.pop()

            resp = app.response_class()
            if not session_interface.is_null_session(sess):
                session_interface.save_session(app, sess, resp)
            headers = resp.get_wsgi_headers(c.request.environ)
            self.cookie_jar.extract_wsgi(c.request.environ, headers)

    def open(self, *args, **kwargs):
        as_tuple = kwargs.pop('as_tuple', False)
        buffered = kwargs.pop('buffered', False)
        follow_redirects = kwargs.pop('follow_redirects', False)

        if (
                not kwargs and len(args) == 1
                and isinstance(args[0], (EnvironBuilder, dict))
        ):
            environ = self.environ_base.copy()

            if isinstance(args[0], EnvironBuilder):
                environ.update(args[0].get_environ())
            else:
                environ.update(args[0])

            environ['flask._preserve_context'] = self.preserve_context
        else:
            kwargs.setdefault('environ_overrides', {}) \
                ['flask._preserve_context'] = self.preserve_context
            kwargs.setdefault('environ_base', self.environ_base)
            builder = make_test_environ_builder(
                self.application, *args, **kwargs
            )

            try:
                environ = builder.get_environ()
            finally:
                builder.close()

        return Client.open(
            self, environ,
            as_tuple=as_tuple,
            buffered=buffered,
            follow_redirects=follow_redirects
        )

    def __enter__(self):
        if self.preserve_context:
            raise RuntimeError('Cannot nest client invocations')
        self.preserve_context = True
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.preserve_context = False

        top = _request_ctx_stack.top
        if top is not None and top.preserved:
            top.pop()


class View(object):

    methods = None

    provide_automatic_options = None

    decorators = ()

    def dispatch_request(self):

        raise NotImplementedError()

    @classmethod
    def as_view(cls, name, *class_args, **class_kwargs):


        def view(*args, **kwargs):
            self = view.view_class(*class_args, **class_kwargs)
            return self.dispatch_request(*args, **kwargs)

        if cls.decorators:
            view.__name__ = name
            view.__module__ = cls.__module__
            for decorator in cls.decorators:
                view = decorator(view)

        view.view_class = cls
        view.__name__ = name
        view.__doc__ = cls.__doc__
        view.__module__ = cls.__module__
        view.methods = cls.methods
        view.provide_automatic_options = cls.provide_automatic_options
        return view


class MethodViewType(type):


    def __init__(cls, name, bases, d):
        super(MethodViewType, cls).__init__(name, bases, d)

        if 'methods' not in d:
            methods = set()

            for key in http_method_funcs:
                if hasattr(cls, key):
                    methods.add(key.upper())

            if methods:
                cls.methods = methods


class MethodView(with_metaclass(MethodViewType, View)):


    def dispatch_request(self, *args, **kwargs):
        meth = getattr(self, request.method.lower(), None)

        if meth is None and request.method == 'HEAD':
            meth = getattr(self, 'get', None)

        assert meth is not None, 'Unimplemented method %r' % request.method
        return meth(*args, **kwargs)


class JSONMixin(object):
    """Common mixin for both request and response objects to provide JSON
    parsing capabilities.

    .. versionadded:: 1.0
    """

    _cached_json = Ellipsis

    @property
    def is_json(self):
        """Check if the mimetype indicates JSON data, either
        :mimetype:`application/json` or :mimetype:`application/*+json`.

        .. versionadded:: 0.11
        """
        mt = self.mimetype
        return (
            mt == 'application/json'
            or (mt.startswith('application/')) and mt.endswith('+json')
        )

    @property
    def json(self):
        """This will contain the parsed JSON data if the mimetype indicates
        JSON (:mimetype:`application/json`, see :meth:`is_json`), otherwise it
        will be ``None``.
        """
        return self.get_json()

    def _get_data_for_json(self, cache):
        return self.get_data(cache=cache)

    def get_json(self, force=False, silent=False, cache=True):
        """Parse and return the data as JSON. If the mimetype does not indicate
        JSON (:mimetype:`application/json`, see :meth:`is_json`), this returns
        ``None`` unless ``force`` is true. If parsing fails,
        :meth:`on_json_loading_failed` is called and its return value is used
        as the return value.

        :param force: Ignore the mimetype and always try to parse JSON.
        :param silent: Silence parsing errors and return ``None`` instead.
        :param cache: Store the parsed JSON to return for subsequent calls.
        """
        if cache and self._cached_json is not Ellipsis:
            return self._cached_json

        if not (force or self.is_json):
            return None

        # We accept MIME charset against the specification as certain clients
        # have used this in the past. For responses, we assume that if the
        # charset is set then the data has been encoded correctly as well.
        charset = self.mimetype_params.get('charset')

        try:
            data = self._get_data_for_json(cache=cache)
            rv = json.loads(data, encoding=charset)
        except ValueError as e:
            if silent:
                rv = None
            else:
                rv = self.on_json_loading_failed(e)

        if cache:
            self._cached_json = rv

        return rv

    def on_json_loading_failed(self, e):
        """Called if :meth:`get_json` parsing fails and isn't silenced. If
        this method returns a value, it is used as the return value for
        :meth:`get_json`. The default implementation raises a
        :class:`BadRequest` exception.

        .. versionchanged:: 0.10
           Raise a :exc:`BadRequest` error instead of returning an error
           message as JSON. If you want that behavior you can add it by
           subclassing.

        .. versionadded:: 0.8
        """
        if current_app is not None and current_app.debug:
            raise BadRequest('Failed to decode JSON object: {0}'.format(e))

        raise BadRequest()


class Request(RequestBase, JSONMixin):
    """The request object used by default in Flask.  Remembers the
    matched endpoint and view arguments.

    It is what ends up as :class:`~flask.request`.  If you want to replace
    the request object used you can subclass this and set
    :attr:`~flask.Flask.request_class` to your subclass.

    The request object is a :class:`~werkzeug.wrappers.Request` subclass and
    provides all of the attributes Werkzeug defines plus a few Flask
    specific ones.
    """

    #: The internal URL rule that matched the request.  This can be
    #: useful to inspect which methods are allowed for the URL from
    #: a before/after handler (``request.url_rule.methods``) etc.
    #: Though if the request's method was invalid for the URL rule,
    #: the valid list is available in ``routing_exception.valid_methods``
    #: instead (an attribute of the Werkzeug exception :exc:`~werkzeug.exceptions.MethodNotAllowed`)
    #: because the request was never internally bound.
    #:
    #: .. versionadded:: 0.6
    url_rule = None

    #: A dict of view arguments that matched the request.  If an exception
    #: happened when matching, this will be ``None``.
    view_args = None

    #: If matching the URL failed, this is the exception that will be
    #: raised / was raised as part of the request handling.  This is
    #: usually a :exc:`~werkzeug.exceptions.NotFound` exception or
    #: something similar.
    routing_exception = None

    @property
    def max_content_length(self):
        """Read-only view of the ``MAX_CONTENT_LENGTH`` config key."""
        if current_app:
            return current_app.config['MAX_CONTENT_LENGTH']

    @property
    def endpoint(self):
        """The endpoint that matched the request.  This in combination with
        :attr:`view_args` can be used to reconstruct the same or a
        modified URL.  If an exception happened when matching, this will
        be ``None``.
        """
        if self.url_rule is not None:
            return self.url_rule.endpoint

    @property
    def blueprint(self):
        """The name of the current blueprint"""
        if self.url_rule and '.' in self.url_rule.endpoint:
            return self.url_rule.endpoint.rsplit('.', 1)[0]

    def _load_form_data(self):
        RequestBase._load_form_data(self)

        # In debug mode we're replacing the files multidict with an ad-hoc
        # subclass that raises a different error for key errors.
        if (
            current_app
            and current_app.debug
            and self.mimetype != 'multipart/form-data'
            and not self.files
        ):
            from .debughelpers import attach_enctype_error_multidict
            attach_enctype_error_multidict(self)


class Response(ResponseBase, JSONMixin):
    """The response object that is used by default in Flask.  Works like the
    response object from Werkzeug but is set to have an HTML mimetype by
    default.  Quite often you don't have to create this object yourself because
    :meth:`~flask.Flask.make_response` will take care of that for you.

    If you want to replace the response object used you can subclass this and
    set :attr:`~flask.Flask.response_class` to your subclass.

    .. versionchanged:: 1.0
        JSON support is added to the response, like the request. This is useful
        when testing to get the test client response data as JSON.
    """

    default_mimetype = 'text/html'

    def _get_data_for_json(self, cache):
        return self.get_data()

class HomePageTest(TestCase):
    # def test_root_url_resolves_to_home_page_view(self):
    # resolve用于解析url，并将其映射到相应的视图函数。检查解析网站根路径”/"时，是否能找到名为home_page的函数
    # found = resolve('/')
    # self.assertEqual(found.func, home_page)

    def test_home_page_returns_correct_html(self):
        # 测试方法1： 原生测试方法
        # 创建一个HttpRequest对象
        # request = HttpRequest()
        # # 将HttpRequest对象传递给home_page()视图函数，返回response对象
        # response = home_page(request)
        # html = response.content.decode('utf8')
        #
        # self.assertTrue(html.startswith('<!DOCTYPE html>'))
        # self.assertIn('<title>To-Do lists</title>', html)
        # self.assertTrue(html.endswith('</html>'))

        # 测试方法2： 使用Django提供的测试客户端(Test Client)来检查使用那个模板，不用在自己生成HttpRequest
        response = self.client.get('/')

        html = response.content.decode('utf8')

        self.assertTrue(html.startswith('<!DOCTYPE html>'))
        self.assertIn('<title>To-Do lists</title>', html)
        self.assertTrue(html.endswith('</html>'))

        # self.assertTemplateUsed(response, 'home.html')

    def test_uses_home_template(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'home.html')

    # def test_only_save_items_when_necessary(self):
    #     self.client.get('/')
    #     self.assertEqual(Item.objects.count(), 0)

    # def test_display_all_list_items(self):
    """该职责由ListViewTest test_display_all_items（） 实现"""
    #     Item.objects.create(text='itemey 1')
    #     Item.objects.create(text='itemey 2')
    #
    #     response = self.client.get('/')
    #
    #     self.assertIn('itemey 1', response.content.decode())
    #     self.assertIn('itemey 2', response.content.decode())


class NewListTest(TestCase):
    def test_can_save_a_POST_request(self):
        """测试保存一个新的待办事项"""
        # To-Do: 代码异味：POST请求的测试太长了
        response = self.client.post('/lists/new', data={'item_text': 'A new list item'})
        self.assertEqual(Item.objects.count(), 1)
        new_item = Item.objects.first()
        self.assertEqual(new_item.text, 'A new list item')

        # POST请求后应该重定向到首页
        # 将下面的测试职责移到新的单元测试中 test_redirects_after_post
        # self.assertEqual(response.status_code, 302)
        # self.assertEqual(response['location'], '/')
        # self.assertIn('A new list item', response.content.decode())
        # self.assertTemplateUsed(response, 'home.html')

    def test_redirects_after_post(self):
        """测试POST提交后是否重定向到相应页面"""
        response = self.client.post('/lists/new', data={'item_text': 'A new list item'})

        # self.assertEqual(response.status_code, 302)
        # self.assertEqual(response['location'], '/lists/the-only-list-in-the-world/')
        new_list = List.objects.first()
        self.assertRedirects(response, f'/lists/{new_list.id}/')


class ListViewTest(TestCase):
    """
    职责：测试列表视图
    测试内容：
        1. 测试列表是否使用正确的模板
        2. 测试每个列表只包含属于该列表的待办事项
    """

    def test_uses_list_template(self):
        aList = List.objects.create()

        response = self.client.get(f'/lists/{aList.id}/')

        self.assertTemplateUsed(response, 'list.html')

    def test_display_only_items_for_that_list(self):
        """
        测试每个列表只包含属于该列表的待办事项
        :return:
        """
        correct_list = List.objects.create()
        Item.objects.create(text='itemey 1', list=correct_list)
        Item.objects.create(text='itemey 2', list=correct_list)

        other_list = List.objects.create()
        Item.objects.create(text="other list 1", list=other_list)
        Item.objects.create(text="other list 2", list=other_list)

        response = self.client.get(f'/lists/{correct_list.id}/')

        self.assertContains(response, 'itemey 1')
        self.assertContains(response, 'itemey 2')
        self.assertNotContains(response, "other list 1")
        self.assertNotContains(response, "other list 2")

    def test_passes_correct_list_to_template(self):
        other_list = List.objects.create()
        correct_list = List.objects.create()

        response = self.client.get(f'/lists/{correct_list.id}/')

        self.assertEqual(response.context['list'], correct_list)


class ListAndItemModelsTest(TestCase):
    def test_saving_and_retrieving_items(self):
        list_ = List()
        list_.save()

        first_item = Item()
        first_item.text = 'The first (ever) list item'
        first_item.list = list_
        first_item.save()

        second_item = Item()
        second_item.text = "Item the second"
        second_item.list = list_
        second_item.save()

        saved_list = List.objects.first()
        self.assertEqual(saved_list, list_)

        saved_items = Item.objects.all()

        self.assertEqual(saved_items.count(), 2)
        first_saved_item = saved_items[0]
        second_saved_item = saved_items[1]
        self.assertEqual(first_saved_item.text, 'The first (ever) list item')
        self.assertEqual(first_saved_item.list, list_)
        self.assertEqual(second_saved_item.text, 'Item the second')
        self.assertEqual(second_saved_item.list, list_)


class NewItemTest(TestCase):
    """向list中添加item"""

    def test_can_save_a_post_request_to_an_existing_list(self):
        """测试:向一个现存list中添加item"""
        other_list = List.objects.create()
        correct_list = List.objects.create()

        self.client.post(
            f'/lists/{correct_list.id}/add_item',
            data={'item_text': 'A new item for an existing list', 'list_id': f'{correct_list.id}'}
        )
        # 断言：数量，内容
        self.assertEqual(Item.objects.count(), 1)  # 判断添加数据量是否正确
        new_item = Item.objects.first()
        self.assertEqual(new_item.text, 'A new item for an existing list')
        self.assertEqual(new_item.list, correct_list)

    def test_redirects_to_list_view(self):
        other_list = List.objects.create()
        correct_list = List.objects.create()

        response = self.client.post(
            f'/lists/{correct_list.id}/add_item',
            data={'item_text': 'A new item for an existing list'}
        )
        self.assertRedirects(response, f'/lists/{correct_list.id}/')

def home_page(request):
    # 处理完POST请求后一定要重定向
    # if request.method == 'POST':
    #     # new_item_text = request.POST['item_text']
    #     Item.objects.create(text=request.POST['item_text'])
    #     return redirect('/lists/the-only-list-in-the-world/')
    # else:
    #     new_item_text = ''
    # item = Item()
    # item.text = request.POST.get('item_text', '')
    # item.save()
    return render(request, 'home.html')


def view_list(request, list_id):
    a_list = List.objects.get(id=list_id)
    items = Item.objects.filter(list=a_list)
    return render(request, 'list.html', {'list': a_list})


def new_list(request):
    a_list = List.objects.create()
    Item.objects.create(text=request.POST['item_text'], list=a_list)
    return redirect(f'/lists/{a_list.id}/')


def add_item(request, list_id):
    a_list = List.objects.get(id=list_id)
    Item.objects.create(text=request.POST['item_text'], list=a_list)

    return redirect(f'/lists/{list_id}/')

class NewVisitorTest(StaticLiveServerTestCase):
    def setUp(self):
        """setUp方法在各个测试方法之前运行"""
        # 打开浏览器
        self.browser = webdriver.Firefox()
        staging_server = os.environ.get('STAGING_SERVER')
        if staging_server:
            self.live_server_url = 'http://' + staging_server

    def tearDown(self):
        """tearDown方法在各个测试方法之后运行"""
        # 关闭浏览器
        self.browser.quit()

    def wait_for_row_in_list_table(self, row_text):
        """不使用time.sleep()显示等待时间，而使用重试循环"""
        start_time = time.time()
        while True:
            try:
                table = self.browser.find_element_by_id('id_list_table')
                rows = table.find_elements_by_tag_name('tr')
                self.assertIn(row_text, [row.text for row in rows])
                return
            except (AssertionError, WebDriverException) as e:
                if time.time() - start_time > MAX_WAIT:
                    raise e
                time.sleep(0.5)

    def test_can_start_a_list_and_retrieve_it_later(self):
        # Alice听说有一个很酷的在线待办事项应用
        # 她去看了这个应用的首页
        # self.browser.get("http://localhost:8000")
        self.browser.get(self.live_server_url)

        # 她在网页的标题和头部看到了“To-Do”这个词
        self.assertIn('To-Do', self.browser.title)
        # self.fail('Finish the test!')
        header_text = self.browser.find_element_by_tag_name('h1').text
        self.assertIn('To-Do', header_text)

        # 应用请就输入一个待办事项
        inputbox = self.browser.find_element_by_id('id_new_item')
        self.assertEqual(
            inputbox.get_attribute('placeholder'),
            'Enter a to-do item'
        )
        # 爱丽丝在文本矿中输入了"Buy peacock feathers"（购买羽毛球）
        # 爱丽丝的爱好是使用假蝇做饵钓鱼
        inputbox.send_keys('Buy peacock feathers')

        # 她按回车键后，页面更新了
        # 待办事项表格中显示了"1: Buy peacock feathers"
        inputbox.send_keys(keys.Keys.ENTER)
        # time.sleep(2)
        # 使用函数，重构下面的代码
        # table = self.browser.find_element_by_id('id_list_table')
        # rows = table.find_elements_by_tag_name('tr')
        # self.assertTrue(
        #     any(row.text == '1: Buy peacock feathers' for row in rows),
        #     f"New to-do item did not appear in table. Contents were:\n {table.text}"
        # )
        # 将assertTrue改为assertIn
        # self.assertIn('1: Buy peacock feathers', [row.text for row in rows])
        self.wait_for_row_in_list_table('1: Buy peacock feathers')
        # 页面中又显示了一个文本框，可以输入其他的待办事项

        # 她输入了"Use peacock feathers to make a fly"
        # 爱丽丝做事很有条理，再输入一个待办事项
        inputbox = self.browser.find_element_by_id('id_new_item')
        inputbox.send_keys('Use peacock feathers to make a fly')
        inputbox.send_keys(keys.Keys.ENTER)
        # time.sleep(1)
        # 页面再次更新，清单中显示了两个待办事项
        # table = self.browser.find_element_by_id('id_list_table')
        # rows = table.find_elements_by_tag_name('tr')
        # self.assertIn('2: Use peacock feathers to make a fly', [row.text for row in rows])
        self.wait_for_row_in_list_table('2: Use peacock feathers to make a fly')
        # 爱丽丝想知道这个网站是否会记住她的待办事项清单
        # 想让每个都用户都能保存自己的待办事项清单（待办事项列表）
        # 待办事项清单有多个待办事项组成
        # 她看到网站为她生成了一个唯一的URL（每个用户独享一个URL）
        # 而且页面中有一些文字解说功能

    def test_multiple_users_can_start_lists_at_different_urls(self):
        """测试多个用户可以开启不同的待办任务清单列表"""
        # Alice新建一个代办事项清单（列表）
        self.browser.get(self.live_server_url)
        inputbox = self.browser.find_element_by_id('id_new_item')
        inputbox.send_keys('Buy peacock feathers')
        inputbox.send_keys(keys.Keys.ENTER)
        self.wait_for_row_in_list_table('1: Buy peacock feathers')
        # 她注意到清单有唯一的URL
        edith_list_url = self.browser.current_url
        self.assertRegex(edith_list_url, '/lists/.+')

        # 现在一个叫做弗朗西斯的新用户访问了网站
        ## 我们使用一个新浏览器会话
        ## 确保Alice的信息不会从cookie中泄露出去
        self.browser.quit()
        self.browser = webdriver.Firefox()
        # 弗朗西斯访问首页
        self.browser.get(self.live_server_url)
        page_text = self.browser.find_element_by_tag_name('body').text
        self.assertNotIn('Buy peacock feathers', page_text)
        self.assertNotIn('make a fly', page_text)

        # 弗朗西斯输入一个新待办事项，新建一个清单
        inputbox = self.browser.find_element_by_id('id_new_item')
        inputbox.send_keys('Buy milk')
        inputbox.send_keys(keys.Keys.ENTER)
        self.wait_for_row_in_list_table('1: Buy milk')

        # 弗朗西斯获得了她的唯一URL
        francis_list_url = self.browser.current_url
        self.assertRegex(francis_list_url, '/lists/.+')
        self.assertNotEqual(francis_list_url, edith_list_url)

        # 这个页面还是没有Alice的清单
        page_text = self.browser.find_element_by_tag_name('body').text
        self.assertNotIn('Buy peacock feathers', page_text)
        self.assertIn('Buy milk', page_text)

        # self.fail('Finish the test!!')

    def test_layout_and_styling(self):
        # Alice访问首页
        self.browser.get(self.live_server_url)
        self.browser.set_window_size(1024, 768)
        # 她看到输入框完美的居中显示
        inputbox = self.browser.find_element_by_id('id_new_item')
        self.assertAlmostEqual(
            inputbox.location['x'] + inputbox.size['width'] / 2,
            512,
            delta=10
        )


class Bullet1(pygame.sprite.Sprite):
    def __init__(self, positon):
        pygame.sprite.Sprite.__init__(self)

        self.image = pygame.image.load("images/bullet1.png").convert_alpha()
        self.rect = self.image.get_rect()
        self.rect.left, self.rect.top = positon
        self.speed = 12
        self.active = True
        self.mask = pygame.mask.from_surface(self.image)

    def move(self):
        self.rect.top -= self.speed

        if self.rect.top < 0:
            self.active = False

    def reset(self, position):
        self.rect.left, self.rect.top = position
        self.active = True


class Bullet2(pygame.sprite.Sprite):
    def __init__(self, positon):
        pygame.sprite.Sprite.__init__(self)

        self.image = pygame.image.load("images/bullet2.png").convert_alpha()
        self.rect = self.image.get_rect()
        self.rect.left, self.rect.top = positon
        self.speed = 12
        self.active = True
        self.mask = pygame.mask.from_surface(self.image)

    def move(self):
        self.rect.top -= self.speed

        if self.rect.top < 0:
            self.active = False

    def reset(self, position):
        self.rect.left, self.rect.top = position
        self.active = True


class SmallEnemy(pygame.sprite.Sprite):
    def __init__(self, bg_size):
        pygame.sprite.Sprite.__init__(self)

        self.image1 = pygame.image.load("images/enemy1.png").convert_alpha()
        self.destroy_images = []
        self.destroy_images.extend([ \
            pygame.image.load("images/enemy1_down1.png").convert_alpha(), \
            pygame.image.load("images/enemy1_down2.png").convert_alpha(), \
            pygame.image.load("images/enemy1_down3.png").convert_alpha(), \
            pygame.image.load("images/enemy1_down4.png").convert_alpha(), \
            ])
        self.rect = self.image1.get_rect()
        self.width, self.height = bg_size[0], bg_size[1]
        self.speed = 2
        self.active = True
        self.rect.left, self.rect.top = \
            randint(0, self.width - self.rect.width), \
                randint(-5 * self.height, 0)
        self.mask = pygame.mask.from_surface(self.image1)

    def move(self):
        if self.rect.top < self.height:
            self.rect.top += self.speed
        else:
            self.reset()

    def reset(self):
        self.active = True
        self.rect.left, self.rect.top = \
            randint(0, self.width - self.rect.width), \
                randint(-5 * self.height, 0)


class MidEnemy(pygame.sprite.Sprite):
    energy = 8

    def __init__(self, bg_size):
        pygame.sprite.Sprite.__init__(self)

        self.image1 = pygame.image.load("images/enemy2.png").convert_alpha()
        self.image_hit = pygame.image.load("images/enemy2_hit.png").convert_alpha()
        self.destroy_images = []
        self.destroy_images.extend([ \
            pygame.image.load("images/enemy2_down1.png").convert_alpha(), \
            pygame.image.load("images/enemy2_down2.png").convert_alpha(), \
            pygame.image.load("images/enemy2_down3.png").convert_alpha(), \
            pygame.image.load("images/enemy2_down4.png").convert_alpha(), \
            ])
        self.rect = self.image1.get_rect()
        self.width, self.height = bg_size[0], bg_size[1]
        self.speed = 1
        self.active = True
        self.hit = False
        self.energy = MidEnemy.energy
        self.rect.left, self.rect.top = \
            randint(0, self.width - self.rect.width), \
                randint(-5 * self.height, -self.height)
        self.mask = pygame.mask.from_surface(self.image1)

    def move(self):
        if self.rect.top < self.height:
            self.rect.top += self.speed
        else:
            self.reset()

    def reset(self):
        self.active = True
        self.energy = MidEnemy.energy
        self.rect.left, self.rect.top = \
            randint(0, self.width - self.rect.width), \
                randint(-8 * self.height, -self.height)


class BigEnemy(pygame.sprite.Sprite):
    energy = 20

    def __init__(self, bg_size):
        pygame.sprite.Sprite.__init__(self)

        self.image1 = pygame.image.load("images/enemy3_n1.png").convert_alpha()
        self.image2 = pygame.image.load("images/enemy3_n2.png").convert_alpha()
        self.image_hit = pygame.image.load("images/enemy3_hit.png").convert_alpha()
        self.destroy_images = []
        self.destroy_images.extend([ \
            pygame.image.load("images/enemy3_down1.png").convert_alpha(), \
            pygame.image.load("images/enemy3_down2.png").convert_alpha(), \
            pygame.image.load("images/enemy3_down3.png").convert_alpha(), \
            pygame.image.load("images/enemy3_down4.png").convert_alpha(), \
            pygame.image.load("images/enemy3_down5.png").convert_alpha(), \
            pygame.image.load("images/enemy3_down6.png").convert_alpha(), \
            ])
        self.rect = self.image1.get_rect()
        self.width, self.height = bg_size[0], bg_size[1]
        self.speed = 1
        self.active = True
        self.hit = False
        self.energy = BigEnemy.energy
        self.rect.left, self.rect.top = \
            randint(0, self.width - self.rect.width), \
                randint(-10 * self.height, -5 * self.height)
        self.mask = pygame.mask.from_surface(self.image1)

    def move(self):
        if self.rect.top < self.height:
            self.rect.top += self.speed
        else:
            self.reset()

    def reset(self):
        self.energy = BigEnemy.energy
        self.active = True
        self.rect.left, self.rect.top = \
            randint(0, self.width - self.rect.width), \
                randint(-10 * self.height, -5 * self.height)

class MyPlane(pygame.sprite.Sprite):
    def __init__(self, bg_size):
        pygame.sprite.Sprite.__init__(self)

        self.image1 = pygame.image.load("images/me1.png").convert_alpha()
        self.image2 = pygame.image.load("images/me2.png").convert_alpha()
        self.destroy_image = []
        self.destroy_image.extend([\
            pygame.image.load("images/me_destroy_1.png").convert_alpha(),\
            pygame.image.load("images/me_destroy_2.png").convert_alpha(),\
            pygame.image.load("images/me_destroy_3.png").convert_alpha(),\
            pygame.image.load("images/me_destroy_4.png").convert_alpha(),\
        ])
        self.active = True
        self.rect = self.image1.get_rect()
        self.width, self.height = bg_size[0], bg_size[1]
        self.rect.left, self.rect.top = \
                        (self.width - self.rect.width) // 2, \
                        self.height - self.rect.height - 60
        self.speed = 10
        self.mask = pygame.mask.from_surface(self.image1)
        self.invincible = False

    def moveUp(self):
        if self.rect.top > 0:
            self.rect.top -= self.speed
        else:
            self.rect.top = 0

    def moveDown(self):
        if self.rect.bottom < self.height - 60:
            self.rect.top += self.speed
        else:
            self.rect.bottom = self.height - 60
    def moveLeft(self):
        if self.rect.left > 0:
            self.rect.left -= self.speed
        else:
            self.rect.left = 0

    def moveRight(self):
        if self.rect.right < self.width:
            self.rect.left += self.speed
        else:
            self.rect.right = self.width

    def  reset(self):
        self.rect.left, self.rect.top = \
                        (self.width - self.rect.width) // 2, \
                        self.height - self.rect.height - 60
        self.active = True
        self.invincible = True


class Bullet_Supply(pygame.sprite.Sprite):
    def __init__(self, bg_size):
        pygame.sprite.Sprite.__init__(self)

        self.image = pygame.image.load("images/bullet_supply.png").convert_alpha()
        self.rect = self.image.get_rect()
        self.width, self.height = bg_size[0], bg_size[1]
        self.rect.left, self.rect.bottom = \
                        randint(0, self.width - self.rect.width), -100
        self.speed = 5
        self.active = False
        self.mask = pygame.mask.from_surface(self.image)

    def move(self):
        if self.rect.top < self.height:
            self.rect.top += self.speed
        else:
            self.active = False

    def reset(self):
        self.active = True
        self.rect.left, self.rect.bottom = \
                        randint(0, self.width - self.rect.width), -100


class Bomb_Supply(pygame.sprite.Sprite):
    def __init__(self, bg_size):
        pygame.sprite.Sprite.__init__(self)

        self.image = pygame.image.load("images/bomb_supply.png").convert_alpha()
        self.rect = self.image.get_rect()
        self.width, self.height = bg_size[0], bg_size[1]
        self.rect.left, self.rect.bottom = \
                        randint(0, self.width - self.rect.width), -100
        self.speed = 5
        self.active = False
        self.mask = pygame.mask.from_surface(self.image)

    def move(self):
        if self.rect.top < self.height:
            self.rect.top += self.speed
        else:
            self.active = False

    def reset(self):
        self.active = True
        self.rect.left, self.rect.bottom = \
                        randint(0, self.width - self.rect.width), -100


def createDocment(title):
    global document

    document = Document()
    style = document.styles['Normal']
    font = style.font
    font.size = Pt(9)
    document.add_heading(title, 0)


def copyCode(path, depth):
    global lineCount
    global fileCount

    files = os.listdir(path)
    for file in files:  # 遍历文件夹
        if not (os.path.isdir(path + "/" + file)):  # 判断是否是文件夹，不是文件夹才打开
            if not os.path.splitext(file)[1] == ".java" :       # 只拷贝java文件
                continue

            rootFileFp.write("|      " * depth + "+--" + file + "\n")
            # print("|      " * depth + "+--" + file)     #打印文件名
            fileCount += 1
            # 添加一个一级标题
            document.add_heading(file, level=1)

            fp = open(path + "/" + file, encoding="UTF-8")  # 打开文件
            iter_f = iter(fp);
            # 每读取一段写入一次
            paragraph = ""
            for line in iter_f:
                # print(line, end='')
                lineCount = lineCount + 1  # 统计行数
                if line == "\n":
                    document.add_paragraph(paragraph)
                    paragraph = ""
                else:
                    paragraph += line

            fp.close()
        else:
            rootFileFp.write("|      " * depth + "+--" + str(file) + "\n")
            # print("|      " * depth + "+--" + str(file))

            if file == "test" or file == "androidTest" or file == "build":      # 去除单元测试和生成的文件
                continue
            else:
                copyCode(path + "/" + file, depth + 1)

def bar_datazoom_slider() -> Bar:
    c = (
         Bar({"theme": ThemeType.MACARONS})
        .add_xaxis(['United States', 'China', 'Canada', 'Japan', 'South Korea', 'United Kingdom', 'Mexico', 'Taiwan', 'Turkey', 'Philippines', 'Thailand', 'Indonesia', 'Malaysia', 'Germany', 'United Arab Emirates', 'France', 'Singapore', 'Russia', 'Argentina', 'Kuwait', 'Brazil', 'Saudi Arabia', 'Spain', 'Chile', 'Peru', 'India', 'Ireland', 'Switzerland', 'Netherlands', 'Poland', 'Egypt', 'Lebanon', 'Czechia', 'Greece', 'Romania', 'Vietnam', 'New Zealand', 'Puerto Rico', 'Australia', 'Bahrain', 'Denmark', 'Belgium', 'Austria', 'Qatar', 'Sweden', 'Jordan', 'Norway', 'Hungary', 'Oman', 'Colombia'])
        .add_yaxis("全球星巴克门店数量TOP50国家或地区", [13608, 2734, 1468, 1237, 993, 901, 579, 394, 326, 298,289, 268, 234, 160, 144, 132, 130, 109, 108, 106, 102, 102, 101, 96, 89, 88, 73, 61, 59, 53, 31, 29, 28, 28, 27, 25, 24, 24, 22, 21, 21, 19, 18, 18, 18, 17, 17, 16, 12, 11])
        .set_global_opts(
            title_opts=opts.TitleOpts(title="国家或地区星巴克门店数"),
            yaxis_opts=opts.AxisOpts(name="门店数量（家）"),
            xaxis_opts=opts.AxisOpts(name="国家",axislabel_opts=opts.LabelOpts(rotate=-15)),
            datazoom_opts=opts.DataZoomOpts(),
        )
    )
    return c

def map_world() -> Map:
    c = (
        Map()
        .add("国家（门店数）",[list(z)for z in zip(list(temp.country),list(temp['number']))],"world",itemstyle_opts=opts.ItemStyleOpts(color="grey", border_color="#111"))
        .set_series_opts(label_opts=opts.LabelOpts(is_show=False),is_map_symbol_show=False)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="全球星巴克分布地图"),
            visualmap_opts=opts.VisualMapOpts(is_piecewise=True,    pieces=[
        {"min": 10000, "label": "10000+","color": '#EE4000' },
        {"max": 10000, "min": 2000, "label": "2000-10000","color": '#FFA54F' },
        {"max": 2000, "min": 1000, "label": "1000-2000","color": '#FFC1C1' },
        {"max": 1000, "min": 200, "label": "200-1000","color": '	#B4EEB4' },
        {"max": 200, "min": 100, "label": "100-200","color": '	#CAE1FF ' },
        {"max": 100, "min": 0, "label": "0-100","color": '#E6E6FA	' },



    ],),
        )
    )
    return c


def _get_locale_dirs(resources, include_core=True):
    """
    Return a tuple (contrib name, absolute path) for all locale directories,
    optionally including the django core catalog.
    If resources list is not None, filter directories matching resources content.
    """
    contrib_dir = os.path.join(os.getcwd(), 'django', 'contrib')
    dirs = []

    # Collect all locale directories
    for contrib_name in os.listdir(contrib_dir):
        path = os.path.join(contrib_dir, contrib_name, 'locale')
        if os.path.isdir(path):
            dirs.append((contrib_name, path))
            if contrib_name in HAVE_JS:
                dirs.append(("%s-js" % contrib_name, path))
    if include_core:
        dirs.insert(0, ('core', os.path.join(os.getcwd(), 'django', 'conf', 'locale')))

    # Filter by resources, if any
    if resources is not None:
        res_names = [d[0] for d in dirs]
        dirs = [ld for ld in dirs if ld[0] in resources]
        if len(resources) > len(dirs):
            print("You have specified some unknown resources. "
                  "Available resource names are: %s" % (', '.join(res_names),))
            exit(1)
    return dirs


def _tx_resource_for_name(name):
    """ Return the Transifex resource name """
    if name == 'core':
        return "django.core"
    else:
        return "django.contrib-%s" % name


def _check_diff(cat_name, base_path):
    """
    Output the approximate number of changed/added strings in the en catalog.
    """
    po_path = '%(path)s/en/LC_MESSAGES/django%(ext)s.po' % {
        'path': base_path, 'ext': 'js' if cat_name.endswith('-js') else ''}
    p = Popen("git diff -U0 %s | egrep '^[-+]msgid' | wc -l" % po_path,
              stdout=PIPE, stderr=PIPE, shell=True)
    output, errors = p.communicate()
    num_changes = int(output.strip())
    print("%d changed/added messages in '%s' catalog." % (num_changes, cat_name))


def update_catalogs(resources=None, languages=None):
    """
    Update the en/LC_MESSAGES/django.po (main and contrib) files with
    new/updated translatable strings.
    """
    settings.configure()
    django.setup()
    if resources is not None:
        print("`update_catalogs` will always process all resources.")
    contrib_dirs = _get_locale_dirs(None, include_core=False)

    os.chdir(os.path.join(os.getcwd(), 'django'))
    print("Updating en catalogs for Django and contrib apps...")
    call_command('makemessages', locale=['en'])
    print("Updating en JS catalogs for Django and contrib apps...")
    call_command('makemessages', locale=['en'], domain='djangojs')

    # Output changed stats
    _check_diff('core', os.path.join(os.getcwd(), 'conf', 'locale'))
    for name, dir_ in contrib_dirs:
        _check_diff(name, dir_)


def lang_stats(resources=None, languages=None):
    """
    Output language statistics of committed translation files for each
    Django catalog.
    If resources is provided, it should be a list of translation resource to
    limit the output (e.g. ['core', 'gis']).
    """
    locale_dirs = _get_locale_dirs(resources)

    for name, dir_ in locale_dirs:
        print("\nShowing translations stats for '%s':" % name)
        langs = sorted(d for d in os.listdir(dir_) if not d.startswith('_'))
        for lang in langs:
            if languages and lang not in languages:
                continue
            # TODO: merge first with the latest en catalog
            p = Popen("msgfmt -vc -o /dev/null %(path)s/%(lang)s/LC_MESSAGES/django%(ext)s.po" % {
                'path': dir_, 'lang': lang, 'ext': 'js' if name.endswith('-js') else ''},
                stdout=PIPE, stderr=PIPE, shell=True)
            output, errors = p.communicate()
            if p.returncode == 0:
                # msgfmt output stats on stderr
                print("%s: %s" % (lang, errors.strip()))
            else:
                print("Errors happened when checking %s translation for %s:\n%s" % (
                    lang, name, errors))


def fetch(resources=None, languages=None):
    """
    Fetch translations from Transifex, wrap long lines, generate mo files.
    """
    locale_dirs = _get_locale_dirs(resources)
    errors = []

    for name, dir_ in locale_dirs:
        # Transifex pull
        if languages is None:
            call('tx pull -r %(res)s -a -f  --minimum-perc=5' % {'res': _tx_resource_for_name(name)}, shell=True)
            target_langs = sorted(d for d in os.listdir(dir_) if not d.startswith('_') and d != 'en')
        else:
            for lang in languages:
                call('tx pull -r %(res)s -f -l %(lang)s' % {
                    'res': _tx_resource_for_name(name), 'lang': lang}, shell=True)
            target_langs = languages

        # msgcat to wrap lines and msgfmt for compilation of .mo file
        for lang in target_langs:
            po_path = '%(path)s/%(lang)s/LC_MESSAGES/django%(ext)s.po' % {
                'path': dir_, 'lang': lang, 'ext': 'js' if name.endswith('-js') else ''}
            if not os.path.exists(po_path):
                print("No %(lang)s translation for resource %(name)s" % {
                    'lang': lang, 'name': name})
                continue
            call('msgcat --no-location -o %s %s' % (po_path, po_path), shell=True)
            res = call('msgfmt -c -o %s.mo %s' % (po_path[:-3], po_path), shell=True)
            if res != 0:
                errors.append((name, lang))
    if errors:
        print("\nWARNING: Errors have occurred in following cases:")
        for resource, lang in errors:
            print("\tResource %s for language %s" % (resource, lang))
        exit(1)

class Apps:
    """
    A registry that stores the configuration of installed applications.

    It also keeps track of models, e.g. to provide reverse relations.
    """

    def __init__(self, installed_apps=()):
        # installed_apps is set to None when creating the master registry
        # because it cannot be populated at that point. Other registries must
        # provide a list of installed apps and are populated immediately.
        if installed_apps is None and hasattr(sys.modules[__name__], 'apps'):
            raise RuntimeError("You must supply an installed_apps argument.")

        # Mapping of app labels => model names => model classes. Every time a
        # model is imported, ModelBase.__new__ calls apps.register_model which
        # creates an entry in all_models. All imported models are registered,
        # regardless of whether they're defined in an installed application
        # and whether the registry has been populated. Since it isn't possible
        # to reimport a module safely (it could reexecute initialization code)
        # all_models is never overridden or reset.
        self.all_models = defaultdict(OrderedDict)

        # Mapping of labels to AppConfig instances for installed apps.
        self.app_configs = OrderedDict()

        # Stack of app_configs. Used to store the current state in
        # set_available_apps and set_installed_apps.
        self.stored_app_configs = []

        # Whether the registry is populated.
        self.apps_ready = self.models_ready = self.ready = False

        # Lock for thread-safe population.
        self._lock = threading.RLock()
        self.loading = False

        # Maps ("app_label", "modelname") tuples to lists of functions to be
        # called when the corresponding model is ready. Used by this class's
        # `lazy_model_operation()` and `do_pending_operations()` methods.
        self._pending_operations = defaultdict(list)

        # Populate apps and models, unless it's the master registry.
        if installed_apps is not None:
            self.populate(installed_apps)

    def populate(self, installed_apps=None):
        """
        Load application configurations and models.

        Import each application module and then each model module.

        It is thread-safe and idempotent, but not reentrant.
        """
        if self.ready:
            return

        # populate() might be called by two threads in parallel on servers
        # that create threads before initializing the WSGI callable.
        with self._lock:
            if self.ready:
                return

            # An RLock prevents other threads from entering this section. The
            # compare and set operation below is atomic.
            if self.loading:
                # Prevent reentrant calls to avoid running AppConfig.ready()
                # methods twice.
                raise RuntimeError("populate() isn't reentrant")
            self.loading = True

            # Phase 1: initialize app configs and import app modules.
            for entry in installed_apps:
                if isinstance(entry, AppConfig):
                    app_config = entry
                else:
                    app_config = AppConfig.create(entry)
                if app_config.label in self.app_configs:
                    raise ImproperlyConfigured(
                        "Application labels aren't unique, "
                        "duplicates: %s" % app_config.label)

                self.app_configs[app_config.label] = app_config
                app_config.apps = self

            # Check for duplicate app names.
            counts = Counter(
                app_config.name for app_config in self.app_configs.values())
            duplicates = [
                name for name, count in counts.most_common() if count > 1]
            if duplicates:
                raise ImproperlyConfigured(
                    "Application names aren't unique, "
                    "duplicates: %s" % ", ".join(duplicates))

            self.apps_ready = True

            # Phase 2: import models modules.
            for app_config in self.app_configs.values():
                app_config.import_models()

            self.clear_cache()

            self.models_ready = True

            # Phase 3: run ready() methods of app configs.
            for app_config in self.get_app_configs():
                app_config.ready()

            self.ready = True

    def check_apps_ready(self):
        """Raise an exception if all apps haven't been imported yet."""
        if not self.apps_ready:
            from django.conf import settings
            # If "not ready" is due to unconfigured settings, accessing
            # INSTALLED_APPS raises a more helpful ImproperlyConfigured
            # exception.
            settings.INSTALLED_APPS
            raise AppRegistryNotReady("Apps aren't loaded yet.")

    def check_models_ready(self):
        """Raise an exception if all models haven't been imported yet."""
        if not self.models_ready:
            raise AppRegistryNotReady("Models aren't loaded yet.")

    def get_app_configs(self):
        """Import applications and return an iterable of app configs."""
        self.check_apps_ready()
        return self.app_configs.values()

    def get_app_config(self, app_label):
        """
        Import applications and returns an app config for the given label.

        Raise LookupError if no application exists with this label.
        """
        self.check_apps_ready()
        try:
            return self.app_configs[app_label]
        except KeyError:
            message = "No installed app with label '%s'." % app_label
            for app_config in self.get_app_configs():
                if app_config.name == app_label:
                    message += " Did you mean '%s'?" % app_config.label
                    break
            raise LookupError(message)

    # This method is performance-critical at least for Django's test suite.
    @functools.lru_cache(maxsize=None)
    def get_models(self, include_auto_created=False, include_swapped=False):
        """
        Return a list of all installed models.

        By default, the following models aren't included:

        - auto-created models for many-to-many relations without
          an explicit intermediate table,
        - models that have been swapped out.

        Set the corresponding keyword argument to True to include such models.
        """
        self.check_models_ready()

        result = []
        for app_config in self.app_configs.values():
            result.extend(list(app_config.get_models(include_auto_created, include_swapped)))
        return result

    def get_model(self, app_label, model_name=None, require_ready=True):
        """
        Return the model matching the given app_label and model_name.

        As a shortcut, app_label may be in the form <app_label>.<model_name>.

        model_name is case-insensitive.

        Raise LookupError if no application exists with this label, or no
        model exists with this name in the application. Raise ValueError if
        called with a single argument that doesn't contain exactly one dot.
        """
        if require_ready:
            self.check_models_ready()
        else:
            self.check_apps_ready()

        if model_name is None:
            app_label, model_name = app_label.split('.')

        app_config = self.get_app_config(app_label)

        if not require_ready and app_config.models is None:
            app_config.import_models()

        return app_config.get_model(model_name, require_ready=require_ready)

    def register_model(self, app_label, model):
        # Since this method is called when models are imported, it cannot
        # perform imports because of the risk of import loops. It mustn't
        # call get_app_config().
        model_name = model._meta.model_name
        app_models = self.all_models[app_label]
        if model_name in app_models:
            if (model.__name__ == app_models[model_name].__name__ and
                    model.__module__ == app_models[model_name].__module__):
                warnings.warn(
                    "Model '%s.%s' was already registered. "
                    "Reloading models is not advised as it can lead to inconsistencies, "
                    "most notably with related models." % (app_label, model_name),
                    RuntimeWarning, stacklevel=2)
            else:
                raise RuntimeError(
                    "Conflicting '%s' models in application '%s': %s and %s." %
                    (model_name, app_label, app_models[model_name], model))
        app_models[model_name] = model
        self.do_pending_operations(model)
        self.clear_cache()

    def is_installed(self, app_name):
        """
        Check whether an application with this name exists in the registry.

        app_name is the full name of the app e.g. 'django.contrib.admin'.
        """
        self.check_apps_ready()
        return any(ac.name == app_name for ac in self.app_configs.values())

    def get_containing_app_config(self, object_name):
        """
        Look for an app config containing a given object.

        object_name is the dotted Python path to the object.

        Return the app config for the inner application in case of nesting.
        Return None if the object isn't in any registered app config.
        """
        self.check_apps_ready()
        candidates = []
        for app_config in self.app_configs.values():
            if object_name.startswith(app_config.name):
                subpath = object_name[len(app_config.name):]
                if subpath == '' or subpath[0] == '.':
                    candidates.append(app_config)
        if candidates:
            return sorted(candidates, key=lambda ac: -len(ac.name))[0]

    def get_registered_model(self, app_label, model_name):
        """
        Similar to get_model(), but doesn't require that an app exists with
        the given app_label.

        It's safe to call this method at import time, even while the registry
        is being populated.
        """
        model = self.all_models[app_label].get(model_name.lower())
        if model is None:
            raise LookupError(
                "Model '%s.%s' not registered." % (app_label, model_name))
        return model

    @functools.lru_cache(maxsize=None)
    def get_swappable_settings_name(self, to_string):
        """
        For a given model string (e.g. "auth.User"), return the name of the
        corresponding settings name if it refers to a swappable model. If the
        referred model is not swappable, return None.

        This method is decorated with lru_cache because it's performance
        critical when it comes to migrations. Since the swappable settings don't
        change after Django has loaded the settings, there is no reason to get
        the respective settings attribute over and over again.
        """
        for model in self.get_models(include_swapped=True):
            swapped = model._meta.swapped
            # Is this model swapped out for the model given by to_string?
            if swapped and swapped == to_string:
                return model._meta.swappable
            # Is this model swappable and the one given by to_string?
            if model._meta.swappable and model._meta.label == to_string:
                return model._meta.swappable
        return None

    def set_available_apps(self, available):
        """
        Restrict the set of installed apps used by get_app_config[s].

        available must be an iterable of application names.

        set_available_apps() must be balanced with unset_available_apps().

        Primarily used for performance optimization in TransactionTestCase.

        This method is safe in the sense that it doesn't trigger any imports.
        """
        available = set(available)
        installed = {app_config.name for app_config in self.get_app_configs()}
        if not available.issubset(installed):
            raise ValueError(
                "Available apps isn't a subset of installed apps, extra apps: %s"
                % ", ".join(available - installed)
            )

        self.stored_app_configs.append(self.app_configs)
        self.app_configs = OrderedDict(
            (label, app_config)
            for label, app_config in self.app_configs.items()
            if app_config.name in available)
        self.clear_cache()

    def unset_available_apps(self):
        """Cancel a previous call to set_available_apps()."""
        self.app_configs = self.stored_app_configs.pop()
        self.clear_cache()

    def set_installed_apps(self, installed):
        """
        Enable a different set of installed apps for get_app_config[s].

        installed must be an iterable in the same format as INSTALLED_APPS.

        set_installed_apps() must be balanced with unset_installed_apps(),
        even if it exits with an exception.

        Primarily used as a receiver of the setting_changed signal in tests.

        This method may trigger new imports, which may add new models to the
        registry of all imported models. They will stay in the registry even
        after unset_installed_apps(). Since it isn't possible to replay
        imports safely (e.g. that could lead to registering listeners twice),
        models are registered when they're imported and never removed.
        """
        if not self.ready:
            raise AppRegistryNotReady("App registry isn't ready yet.")
        self.stored_app_configs.append(self.app_configs)
        self.app_configs = OrderedDict()
        self.apps_ready = self.models_ready = self.loading = self.ready = False
        self.clear_cache()
        self.populate(installed)

    def unset_installed_apps(self):
        """Cancel a previous call to set_installed_apps()."""
        self.app_configs = self.stored_app_configs.pop()
        self.apps_ready = self.models_ready = self.ready = True
        self.clear_cache()

    def clear_cache(self):
        """
        Clear all internal caches, for methods that alter the app registry.

        This is mostly used in tests.
        """
        # Call expire cache on each model. This will purge
        # the relation tree and the fields cache.
        self.get_models.cache_clear()
        if self.ready:
            # Circumvent self.get_models() to prevent that the cache is refilled.
            # This particularly prevents that an empty value is cached while cloning.
            for app_config in self.app_configs.values():
                for model in app_config.get_models(include_auto_created=True):
                    model._meta._expire_cache()

    def lazy_model_operation(self, function, *model_keys):
        """
        Take a function and a number of ("app_label", "modelname") tuples, and
        when all the corresponding models have been imported and registered,
        call the function with the model classes as its arguments.

        The function passed to this method must accept exactly n models as
        arguments, where n=len(model_keys).
        """
        # Base case: no arguments, just execute the function.
        if not model_keys:
            function()
        # Recursive case: take the head of model_keys, wait for the
        # corresponding model class to be imported and registered, then apply
        # that argument to the supplied function. Pass the resulting partial
        # to lazy_model_operation() along with the remaining model args and
        # repeat until all models are loaded and all arguments are applied.
        else:
            next_model, more_models = model_keys[0], model_keys[1:]

            # This will be executed after the class corresponding to next_model
            # has been imported and registered. The `func` attribute provides
            # duck-type compatibility with partials.
            def apply_next_model(model):
                next_function = partial(apply_next_model.func, model)
                self.lazy_model_operation(next_function, *more_models)
            apply_next_model.func = function

            # If the model has already been imported and registered, partially
            # apply it to the function now. If not, add it to the list of
            # pending operations for the model, where it will be executed with
            # the model class as its sole argument once the model is ready.
            try:
                model_class = self.get_registered_model(*next_model)
            except LookupError:
                self._pending_operations[next_model].append(apply_next_model)
            else:
                apply_next_model(model_class)

    def do_pending_operations(self, model):
        """
        Take a newly-prepared model and pass it to each function waiting for
        it. This is called at the very end of Apps.register_model().
        """
        key = model._meta.app_label, model._meta.model_name
        for function in self._pending_operations.pop(key, []):
            function(model)


class Kcalmath:
    def __init__(self, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11):
        self.b1 = b1
        self.b2 = b2
        self.b3 = b3
        self.b4 = b4
        self.b5 = b5
        self.b6 = b6
        self.b7 = b7
        self.b8 = b8
        self.b9 = b9
        self.b10 = b10
        self.b11 = b11

    def mi(self):

        n = ""
        e = 0.0
        f = 0.0
        n = u.get()
        e = float(m.get())
        f = float(d.get())

        if n == "仰卧起坐":
            self.b1 = f * 10 * e
            g.set(self.b1)

        if n == "散步":
            self.b2 = f * 4.5 * e
            g.set(self.b2)

        if n == "跳绳":
            self.b3 = f * 12 * e
            g.set(self.b3)

        if n == "慢跑":
            self.b4 = f * 8.9 * e
            g.set(self.b4)

        if n == "骑单车":
            self.b5 = f * 13.27 * e
            g.set(self.b5)

        if n == "篮球":
            self.b6 = f * 6.57 * e
            g.set(self.b6)

        if n == "排球":
            self.b7 = f * 8.27 * e
            g.set(self.b7)

        if n == "快跑":
            self.b8 = f * 10.2 * e
            g.set(self.b8)

        if n == "引体向上":
            self.b9 = f * 0.83 * e
            g.set(self.b9)

        if n == "网球":
            self.b10 = f * 6.33 * e
            g.set(self.b10)

        if n == "蛙泳":
            self.b11 = self.f * 4.5 * self.e
            g.set(self.b11)

    def delall(self):
        self.b1 = 0.0
        self.b2 = 0.0
        self.b3 = 0.0
        self.b4 = 0.0
        self.b5 = 0.0
        self.b6 = 0.0
        self.b7 = 0.0
        self.b8 = 0.0
        self.b9 = 0.0
        self.b10 = 0.0
        self.b11 = 0.0

    def sumall(self):

        ofall = self.b1 + self.b2 + self.b3 + self.b4 + self.b5 + self.b6 + self.b7 + self.b8 + self.b9 + self.b10 + self.b11
        t.set(ofall)

    def winquit(self):
        root.destroy()


class Kcalmath:
    def __init__(self, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11, count):
        self.b1 = b1
        self.b2 = b2
        self.b3 = b3
        self.b4 = b4
        self.b5 = b5
        self.b6 = b6
        self.b7 = b7
        self.b8 = b8
        self.b9 = b9
        self.b10 = b10
        self.b11 = b11
        self.count = int(count)

    def mi(self):

        n = ""
        e = 0.0
        f = 0.0
        n = u.get()
        k = m.get()
        kl = d.get()

        if n != "" and k != '' and kl != '':

            e = float(k)
            f = float(kl)

            if n == "仰卧起坐":
                self.b1 = f * 10 * e
                g.set(self.b1)
                tm.showinfo('提示', '你进行[%s]运动消耗了<%f>卡路里' % (n, self.b1))

            if n == "散步":
                self.b2 = f * 4.5 * e
                g.set(self.b2)
                tm.showinfo('提示', '你进行[%s]运动消耗了<%f>卡路里' % (n, self.b2))

            if n == "跳绳":
                self.b3 = f * 12 * e
                g.set(self.b3)
                tm.showinfo('提示', '你进行[%s]运动消耗了<%f>卡路里' % (n, self.b3))

            if n == "慢跑":
                self.b4 = f * 8.9 * e
                g.set(self.b4)
                tm.showinfo('提示', '你进行[%s]运动消耗了<%f>卡路里' % (n, self.b4))

            if n == "骑单车":
                self.b5 = f * 13.27 * e
                g.set(self.b5)
                tm.showinfo('提示', '你进行[%s]运动消耗了<%f>卡路里' % (n, self.b5))

            if n == "篮球":
                self.b6 = f * 6.57 * e
                g.set(self.b6)
                tm.showinfo('提示', '你进行[%s]运动消耗了<%f>卡路里' % (n, self.b6))

            if n == "排球":
                self.b7 = f * 8.27 * e
                g.set(self.b7)
                tm.showinfo('提示', '你进行[%s]运动消耗了<%f>卡路里' % (n, self.b7))

            if n == "快跑":
                self.b8 = f * 10.2 * e
                g.set(self.b8)
                tm.showinfo('提示', '你进行[%s]运动消耗了<%f>卡路里' % (n, self.b8))

            if n == "引体向上":
                self.b9 = f * 0.83 * e
                g.set(self.b9)
                tm.showinfo('提示', '你进行[%s]运动消耗了<%f>卡路里' % (n, self.b9))

            if n == "网球":
                self.b10 = f * 6.33 * e
                g.set(self.b10)
                tm.showinfo('提示', '你进行[%s]运动消耗了<%f>卡路里' % (n, self.b10))

            if n == "蛙泳":
                self.b11 = f * 4.5 * e
                g.set(self.b11)
                tm.showinfo('提示', '你进行[%s]运动消耗了<%f>卡路里' % (n, self.b11))
        else:
            tm.showwarning('提示', '请正确输入')

    def delall(self):
        info = tm.askquestion('提示', '是否要清除缓存数据?')
        if info == 'yes':
            self.b1 = 0.0
            self.b2 = 0.0
            self.b3 = 0.0
            self.b4 = 0.0
            self.b5 = 0.0
            self.b6 = 0.0
            self.b7 = 0.0
            self.b8 = 0.0
            self.b9 = 0.0
            self.b10 = 0.0
            self.b11 = 0.0
            self.count = 0
            tm.showinfo('提示', '缓存数据已清除!')
        else:
            pass

    def sumall(self):
        info = tm.askquestion('提示', '是否要计算所有运动消耗的总热量?')
        if info == 'yes':
            ofall = self.b1 + self.b2 + self.b3 + self.b4 + self.b5 + self.b6 + self.b7 + self.b8 + self.b9 + self.b10 + self.b11
            t.set(ofall)
            tm.showinfo('提示', '你所有运动消耗的总热量为<%f>' % ofall)
        else:
            pass

    def winquit(self):

        info = tm.askquestion('提示', '你确定要退出吗?')
        if info == 'yes':
            root.destroy()
        else:
            pass

    def saveas(self):

        name = ''

        num = 0.0

        name = str(u.get())

        nu = g.get()

        txt = ''
        txt = ti.strftime('%Y年%m月%d日 %H:%M', ti.localtime(ti.time()))

        lines = []

        if nu != '':

            num = float(nu)

            if name != '' and num != None:

                info = tm.askquestion('提示', '是否要保存运动日志?')

                if info == 'yes':

                    f = open("data/sportsdata.txt", 'r')
                    for line in f:
                        lines.append(line)
                    f.close()
                    lsen = len(lines)
                    lines.insert(lsen, "%s--运动记录:运动项目[%s]:消耗的热量为<%f>卡路里\n" % (txt, name, num))
                    s = ''.join(lines)
                    f = open("data/sportsdata.txt", 'w+')
                    f.write(s)
                    f.close()
                    del lines[:]
                    tm.showinfo('提示', '保存成功\n你于%s保存的运动日志的日志号为%d' % (txt, lsen + 1))
                else:
                    pass
            else:
                tm.showwarning('提示', '请正确输入')
        else:
            tm.showwarning('提示', '输入不能为空')

    def savedel(self):

        lines = []

        f = open("data/sportsdata.txt", 'r')
        for line in f:
            lines.append(line)
        f.close()
        lsen = len(lines) - 1
        info = tm.askquestion('提示', '是否要清除上条运动日志?')
        if info == 'yes':
            if lines != []:
                del lines[lsen]
                s = ''.join(lines)
                f = open("data/sportsdata.txt", 'w+')
                f.write(s)
                f.close()
                del lines[:]
                tm.showinfo('提示', '已成功清除上条运动日志')
            else:
                tm.showwarning('提示', '日志为空')
        else:
            del lines[:]
            pass

    def finddata(self):
        lines = []
        f = open("data/sportsdata.txt", 'r')
        for line in f:
            lines.append(line)
        f.close()
        qw = sd.get()
        if qw != '':
            info = tm.askquestion('提示', '是否要查找日志?(日志号为[%s])' % qw)
            if info == 'yes':
                if lines != []:
                    flen = int(sd.get()) - 1
                    sf.set(lines[flen])
                    tm.showinfo('提示', '已打开日志')
                else:
                    tm.showwarning('提示', '日志为空')
            else:
                pass
        else:
            tm.showwarning('注意', '输入不能为空')

    def delfinddata(self):
        lines = []
        f = open("data/sportsdata.txt", 'r')
        for line in f:
            lines.append(line)
        f.close()
        qw = sd.get()
        if qw != '':
            info = tm.askquestion('提示', '是否要删除日志?(日志号为[%s])' % qw)
            if info == 'yes':
                if lines != []:
                    dllen = int(sd.get()) - 1
                    if dllen >= len(lines):
                        tm.showwarning('注意', '没有此日志')
                    else:
                        del lines[dllen]
                        s = ''.join(lines)
                        f = open("data/sportsdata.txt", 'w+')
                        f.write(s)
                        f.close()
                        del lines[:]
                        tm.showinfo('提示', '已删除日志(日志号为[%s])' % qw)
                else:
                    tm.showwarning('注意', '日志为空')
            else:
                pass
        else:
            tm.showwarning('注意', '输入不能为空')

    def opendata(self):
        lines = []
        f = open("data/sportsdata.txt", 'r')
        for line in f:
            lines.append(line)
        f.close()
        qw = len(lines) - self.count
        info = tm.askquestion('提示', '是否打开上条日志?(日志号为[%d])' % qw)
        if info == 'yes':
            if lines != []:
                dlen = len(lines) - 1 - self.count
                sf.set(lines[dlen])
                self.count += 1
                tm.showinfo('提示', '已打开日志(日志号为[%d])' % qw)
            else:
                tm.showwarning('提示', '日志为空')
        else:
            pass

    def delalldata(self):
        info = tm.askquestion('提示', '是否要清除所有运动日志?')
        if info == 'yes':
            f = open("data/sportsdata.txt", 'w')
            f.write("")
            tm.showinfo('提示', '已清除所有日志')
        else:
            pass

    def winupdate(self):
        info = tm.askquestion('提示', '是否要刷新窗口?')
        if info == 'yes':
            mn = ""
            u.set(mn)
            m.set(mn)
            d.set(mn)
            g.set(mn)
            t.set(mn)
            sd.set(mn)
            sf.set(mn)
            self.count = 0
            tm.showinfo('提示', '窗口已刷新')
        else:
            pass

def add_user():     # 用户程序
    k = 0
    while k != 1:
        account = math.floor(1e8*random.random())
        user = users["账户"]
        for i in user:
            if i == account:
                k = 2
                break
        if len(user) >= 100:
            k = 3
            print("用户库已满!")
        if k != 2 and k != 3:
            print("您生成的账户为：", account)
            users["账户"].append(account)
            users["姓名"].append(input("姓名:"))
            users["密码"].append(int(input("密码:")))
            users["地址"].append(input("输入国家,省份,街道,门牌号:"))
            users["存款余额"].append(int(input("存款余额:")))
            users["开户行"].append("中国工商银行北京市平昌分行")
            print("注册成功!")
            k = 1
            print(users["账户"])


def save_money():    # 地址程序
    account = int(input("请输入存款账户:"))
    long = len(users["账户"])
    k = 0
    for i in users["账户"]:
        if i == account:
            moneys = users["存款余额"][k]
            moneys_1 = moneys
            money = int(input("请输入存款金额:"))
            users["存款余额"][k] = money + moneys_1
            print(users["存款余额"])
            return True
        k += 1
    if k == long:
        return False


def graw_money():     # 银行程序
    account = int(input("输入取款账户:"))
    code = int(input("输入密码:"))
    money = int(input("输入取款金额:"))
    k = 0
    g = 0
    ll = 0
    for i in users["账户"]:
        if i == account:
            g = 1
            break
        k += 1
    if g == 1:
        code_1 = users["密码"][k]
        if code == code_1:
            ll = 1
    else:
        print("账户不存在!")
    if g == 1 and ll == 1:
        moneys = users["存款余额"][k]
        if moneys >= money:
            users["存款余额"][k] = moneys - money
        else:
            print("钱不够")


def transfer_accounts():    # 界面程序
    account_1 = int(input("输入转出账户:"))
    account_2 = int(input("输入转入账户:"))
    code = int(input("输入转出账户密码:"))
    money = int(input("输入转出金额:"))
    k = 0
    kk = 0
    g = 0
    gg = 0
    ll = 0
    for i in users["账户"]:
        if i == account_1:
            g = 1
            break
        k += 1
    for i in users["账户"]:
        if i == account_2:
            gg = 1
            break
        kk += 1
    if g == 1 and gg == 1:
        code_1 = users["密码"][k]
        if code == code_1:
            ll = 1
        else:
            print("密码不对！")
    else:
        print("账户不对!")
    if g == 1 and ll == 1 and gg == 1:
        moneys = users["存款余额"][k]
        moneys_1 = users["存款余额"][kk]
        if moneys >= money:
            users["存款余额"][k] = moneys - money
            users["存款余额"][kk] = moneys_1 + money
        else:
            print("钱不够")


def check_account():
    account = int(input("输入查询账户:"))
    code = int(input("输入密码:"))
    k = 0
    g = 0
    for i in users["账户"]:
        if i == account:
            g = 1
            break
        k += 1
    if g == 1:
        code_1 = users["密码"][k]
        if code == code_1:
            print(f"当前账户为：{users['账户'][k]}")
            print(f"当前密码为：{users['密码'][k]}")
            print(f"当前余额为：{users['存款余额'][k]}")
            print(f"当前地址为：{users['地址'][k]}")
            print(f"当前开户行为：{users['开户行'][k]}")
        else:
            print("密码错误!")
    else:
        print("该用户不存在!")


def interface():
    while True:
        print("******************************")
        print("*         中国工商银行          *")
        print("*         账户管理系统          *")
        print("*             V1.0            *")
        print("******************************")
        print("")
        print("*1.开户                        *")
        print("*2.存钱                        *")
        print("*3.取钱                        *")
        print("*4.转账                        *")
        print("*5.查询                        *")
        print("*6.Bye!                       *")
        print("******************************")
        exchange = int(input())
        if exchange == 1:
            add_user()
        elif exchange == 2:
            save_money()
        elif exchange == 3:
            graw_money()
        elif exchange == 4:
            transfer_accounts()
        elif exchange == 5:
            check_account()
        elif exchange == 6:
            break

def check_account():
    def c(styles):
        longs = len(ID)
        xx = 1
        while xx <= longs:
            print(styles[xx-1])
            xx += 1
        gg = input("请输入要查信息：")
        hh = 0
        nn = 0
        for mm in styles[0:longs]:
            if gg == mm:
                print(ID[hh], style[hh], account[hh], money[hh], time[hh],
                      instructions[hh], )
                nn += 1
            hh += 1
        if nn == 0:
            print("无该信息。")
    while True:
        print("1.查询全部  2.按条件查询")
        s = input("输入选择：")
        if s == "1":
            long = len(ID)
            x = 1
            while x <= long:
                print('%-5s\t%-5s\t%-5s\t%-5s\t%-5s\t%-5s\t' % (ID[x-1],  style[x-1], account[x-1], money[x-1],
                      time[x-1], instructions[x-1]))
                x += 1
        elif s == "2":
            while True:
                print("1.ID  2.类别  3.账户  4.金额  5.时间  6.说明")
                ss = input("输入选择：")
                if ss == "1":
                    c(ID)
                    break
                elif ss == "2":
                    c(style)
                    break
                elif ss == "3":
                    c(account)
                    break
                elif ss == "4":
                    c(money)
                    break
                elif ss == "5":
                    c(time)
                    break
                elif ss == "6":
                    c(instructions)
                    break
                else:
                    print("输入错误请重新输入！")
        else:
            print("输入错误请重新输入！")
        break


def del_account():
    ids = int(input("请输入ID:"))
    del ID[ids-1]
    del style[ids-1]
    del account[ids-1]
    del money[ids-1]
    del time[ids-1]
    del instructions[ids-1]
    long = len(ID)
    while ids-1 < long:
        ID[ids-1] = ids
        ids += 1
    print("删除账务成功!")


def edit_account():
    while True:
        print("1.类别  2.账户  3.金额  4.时间  5.说明")
        number = input("请输入要操作的功能序号[1-5]:")
        if number == "1":
            ids = int(input("请输入ID:"))
            style[ids-1] = input("请输入修改内容：")
            break
        elif number == "2":
            ids = int(input("请输入ID:"))
            account[ids-1] = input("请输入修改内容：")
            break
        elif number == "3":
            ids = int(input("请输入ID:"))
            money[ids-1] = input("请输入修改内容：")
            break
        elif number == "4":
            ids = int(input("请输入ID:"))
            time[ids-1] = input("请输入修改内容：")
            break
        elif number == "5":
            ids = int(input("请输入ID:"))
            instructions[ids-1] = input("请输入修改内容：")
            break
        else:
            print("输入错误，请重新输入！")
    print("编辑成功!")


def add_account():
    ID.append(len(ID)+1)
    style.append(input("请输入类别："))
    account.append(input("请输入账户："))
    money.append(input("请输入金额："))
    time.append(input("请输入时间："))
    instructions.append(input("请输入说明："))
    print("添加成功！")


def register():
    count = 0
    while count < 3:
        count += 1
        name = input('请输入登录账户名:')
        code = input('请输入登录账户密码:')
        x = 0
        if name == administrator[0]:
            x = 0
        if name == administrator[1]:
            x = 1
        if name == administrator[x] and code == password[x]:
            while True:
                print("1.添加账务  2.编辑账务  3.删除账务  4.查询账务  5.退出系统")
                number = input("请输入要操作的功能序号[1-5]:")
                if number == "1":
                    add_account()
                elif number == "2":
                    edit_account()
                elif number == "3":
                    del_account()
                elif number == "4":
                    check_account()
                elif number == "5":
                    exit_system()
                    break
                else:
                    print("输入错误，请重新输入")
            break
        else:
            print("您输入的账户名或密码有误请重新登录!")
    if count == 3:
        print("密码输入连续错误三次，结束登录!")


def statistical_number(datas):
    table = datas.sheets()[0]
    number = table.nrows - 1
    print("表格中一共有%d个人。" % number)


def statistical_phone(datas):
    model = ['134', '135', '136', '137', '138', '139', '147', '150', '151', '152', '157',
             '158', '159', '178', '182', '183', '184', '187', '188', ]
    models = ['1703', '1705', '1706']
    link = ['130', '131', '132', '145', '155', '156', '175', '176', '185', '186', '171', ]
    links = ['1704', '1707', '1708', '1709', ]
    telecom = ['133', '149', '153', '173', '177', '180', '181', '189']
    telecoms = ['1700', '1701', '1702']
    tables = datas.sheets()[0]
    table = tables.col_values(colx=5)
    yd = 0
    lt = 0
    dx = 0
    for i in table[1: tables.nrows]:
        k = 0
        for x in model:
            if x == i[0:3]:
                yd += 1
                k = 1
                break
        if k == 0:
            for xx in link:
                if xx == i[0:3]:
                    lt += 1
                    k = 1
                    break
        if k == 0:
            for xxx in telecom:
                if xxx == i[0:3]:
                    dx += 1
                    break
    for g in table[1: tables.nrows]:
        k = 0
        for x in models:
            if x == g[0:4]:
                yd += 1
                k = 1
                break
        if k == 0:
            for xx in links:
                if xx == g[0:4]:
                    lt += 1
                    k = 1
                    break
        if k == 0:
            for xxx in telecoms:
                if xxx == g[0:4]:
                    dx += 1
                    break
    print(f"移动人数占比{yd/(tables.nrows-1)}，联通人数占比{lt/(tables.nrows-1)},电信人数占比{dx/(tables.nrows-1)}。")
    print(f"移动占{yd}人，联通占{lt},电信占{dx}人。")


def gender(datas):
    tables = datas.sheets()[0]
    table = tables.col_values(colx=8)
    n = 0
    o = 0
    for i in table[1: tables.nrows]:
        if i == '男':
            n += 1
        else:
            o += 1
    print(f"公司男生人数为:{n}人, 女生人数为{o}人。")


def age(datas):
    tables = datas.sheets()[0]
    table = tables.col_values(colx=7)
    sums = 0
    for i in table[1: tables.nrows]:
        if i == str(i):
            sums += 1
    print(f"年龄超过45岁人数为{sums}人")


def pay(datas):
    tables = datas.sheets()[0]
    table = tables.col_values(colx=11)
    x = 0
    z = 0
    for i in table[1:tables.nrows]:
        if i > 8000:
            x += 1
        if i < 3000:
            z += 1
    print(f"薪资高于8000元的人员为{x},薪资低于3000元人员为{z}")


def media(datas):
    tables = datas.sheets()[0]
    table = tables.col_values(colx=13)
    x = 0
    for i in table[1:tables.nrows]:
        if i.find('传媒') != -1:
            x += 1
    print(f"去传媒公司的人数为{x}人")


def local(datas):
    tables = datas.sheets()[0]
    table = tables.col_values(colx=9)
    x = 0
    for i in table[1:tables.nrows]:
        if i.find('黑龙江') != -1:
            x += 1
        elif i.find('北京') != -1:
            x += 1
        elif i.find('福建') != -1:
            x += 1
        elif i. find('四川') != -1:
            x += 1
    print(f"疫情高危地区的人数为{x}人")



class Compute:      # 创建一个计算类
    sum = None      # 定义一个属性

    def add(self, a, b):  # 定义一个加法公式
        self.sum = a + b        # 计算加法
        return self.sum         # 返回计算值

    def subtract(self, c, d):     # 定义一个减法
        self.sum = c - d        # 计算减法
        return self.sum         # 返回计算值

    def eliminate(self, e, f):  # 定义一个除法
        self.sum = e/f          # 计算除法
        return self.sum         # 返回计算值

    def pursue(self, g, h):     # 定义一个乘法
        self.sum = g*h          # 计算乘法
        return self.sum         # 返回计算值


class Test(Compute):
    c1 = 12
    c2 = 0
    c3 = -1
    c4 = 999999999999995
    c5 = -1000000000000000
    c6 = 10
    c7 = 0
    c8 = -10
    c9 = 0
    c10 = 72
    c11 = -10

    def add_test(self):
        compute_sums1 = compute.add(6, 6)
        compute_sums2 = compute.add(-6, 6)
        compute_sums3 = compute.add(-6, 5)
        if compute_sums1 == self.c1:
            print("6+6测试结果通过！")
        else:
            print("测试不通过!")
        if compute_sums2 == self.c2:
            print("-6+6测试结果通过！")
        else:
            print("测试不通过!")
        if compute_sums3 == self.c3:
            print("-6+5测试结果通过！")
        else:
            print("测试不通过!")

    def subtract_test(self):
        compute_subtract1 = compute.subtract(1000000000000000, 5)
        compute_subtract2 = compute.subtract(-999999999999999, 1)
        if compute_subtract1 == self.c4:
            print("1000000000000000-5测试结果通过！")
        else:
            print("测试不通过!")
        if compute_subtract2 == self.c5:
            print("-999999999999999+1测试结果通过！")
        else:
            print("测试不通过!")

    def eliminate_test(self):
        compute_eliminate1 = compute.eliminate(10, 1)
        compute_eliminate2 = compute.eliminate(0, 10)
        compute_eliminate3 = compute.eliminate(10, -1)
        if compute_eliminate1 == self.c6:
            print("10/1测试结果通过！")
        else:
            print("测试不通过!")
        if compute_eliminate2 == self.c7:
            print("0/10测试结果通过！")
        else:
            print("测试不通过!")
        if compute_eliminate3 == self.c8:

            print("10/-1测试结果通过！")
        else:
            print("测试不通过!")

    def pursue_test(self):
        compute_pursue1 = compute.pursue(0, 9)
        compute_pursue2 = compute.pursue(8, 9)
        compute_pursue3 = compute.pursue(-1, 10)
        if compute_pursue1 == self.c9:
            print("0*9测试结果通过！")
        else:
            print("测试不通过!")
        if compute_pursue2 == self.c10:
            print("8*9测试结果通过！")
        else:
            print("测试不通过!")
        if compute_pursue3 == self.c11:
            print("-1*10测试结果通过！")
        else:
            print("测试不通过!")