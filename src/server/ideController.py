import os
import cherrypy
from cherrypy import request, HTTPError
from cherrypy.lib import static
import simplejson
from ws4py.websocket import WebSocket
from genshi.template import TemplateLoader
from cide.server.identifyController import require_identify


def wrap_opCode(opCode, payload):
  return {'opCode': opCode,
          'data': payload}


def create_file_dump_dict(filename, version, content):
  return {'file':    filename,
          'vers':    version,
          'content': content}


def create_file_version_dict(filename, version, changes):
  return {'file':    filename,
          'vers':    version,
          'changes': changes}


def create_change_add_element_dict(change):
  return {'type': IDEController.CHANGE_ADD_TYPE,
          'pos':  change.position,
          'content': change.data,
          'author': change.author}


def create_change_remove_element_dict(change):
  return {'type': IDEController.CHANGE_REMOVE_TYPE,
          'pos':  change.position,
          'count': change.size,
          'author': change.author}


def create_tree_nodes_dict(nodes):
  return {'nodes': [{'node': name,
                     'isDir': is_dir}
                    for (name, is_dir) in nodes]}


def set_author_bool_in_dict(serialized_changes, user):
  for sc in serialized_changes:
    sc['author'] = (sc['author'] == user)


class IDEController(object):
  """
  Controller of the IDE/Editing part
  """

  IDE_HTML_TEMPLATE = 'edit.html'
  CHANGE_ADD_TYPE = 1
  CHANGE_REMOVE_TYPE = -1

  def __init__(self, app, template_path, logger):
    """
    IDEController initialiser

    @type app: cide.app.python.core.Core
    @type template_path: str
    @type logger: logging.Logger

    @param app: The core application
    @param template_path: Path to the template directory
    @param logger: The CIDE.py logger instance
    """
    self._app = app
    self._loader = TemplateLoader(template_path, auto_reload=True)
    self._logger = logger

    self._logger.debug("IDEController instance created")

    # To respect observer pattern contract, many function must
    # be implemented as tasks callbacks. To simplify reading,
    # required functions will all be aliases to methods
    self.notify_file_edit = self._save_callback
    self.notify_get_project_nodes = self._tree_callback
    self.notify_get_file_content = self._dump_callback

    # Register controller to events
    self._app.register_application_listener(self)
    self.debug_bundle_id = 0

  @staticmethod
  def is_valid_path(path):
    """
    Validates a path string

    @type path: str, unicode or else

    @param path: The object to validate as a path
    """
    return ((type(path) in (str, unicode)) and
            (path == os.path.normpath(path.strip() or '/')) and
            (path.startswith('/')) and
            (not path.endswith('/')))

  @staticmethod
  def is_valid_changes(changes):
    """
    Validates a change array

    @type changes: list or else

    @param changes: The object to validate as a change array
    """
    return (type(changes) is list and
            all(
              (type(c) is dict and

               'type' in c and type(c['type']) is int and
               ((c['type'] == IDEController.CHANGE_ADD_TYPE and
                'content' in c and
                 type(c['content']) in (str, unicode)) or
                (c['type'] == IDEController.CHANGE_REMOVE_TYPE and
                'count' in c and
                 type(c['count']) is int and
                 c['count'] >= 0)) and

               'pos' in c and type(c['pos']) is int and c['pos'] >= 0 and
               len(c.keys()) == 3)
              for c in changes))

  @cherrypy.expose
  @require_identify()
  def index(self):
    """
    IDEController index page generator
    (Path : /ide/ -- /ide/index)

    @return: Template HTML render
    """
    username = cherrypy.session['username']
    self._logger.info("index requested by {0} ({1}:{2})".format(username,
                                                                request.remote.ip,
                                                                request.remote.port))

    tmpl = self._loader.load(IDEController.IDE_HTML_TEMPLATE)
    project_name = self._app.get_project_name()
    stream = tmpl.generate(title=project_name)
    return stream.render('html')

  @cherrypy.expose
  @cherrypy.tools.json_out()
  @cherrypy.tools.json_in()
  @require_identify()
  def open(self):
    """
    Subscribe a client to updates for a given file and send a dump of the file
    If the file doesn't exist, it's created.
    Method : POST
    (Path : /ide/open)

    User must start to buffer changes received for file before requesting open.
    The server will register the user to receive updates, then send the content,
    so the user misses no update. The user will have to detect which updates
    to apply based on the ``version`` sent.

    Input must be JSON of the following format:
      {
        'file':    '<<Filepath of file to open>>'
      }

    Output on the WS will be JSON of the following format:
      {
        'opCode': 'dump',
        'data': {
                  'file':    '<<Filepath of given file>>',
                  'vers':    '<<File version>>',
                  'content': '<<Content of the requested file>>'
                }
      }
      OR
      Invalid path: None + (400 - Invalid path)
    """
    self._logger.debug("Open by {0} ({1}:{2}) JSON: {3}".format(cherrypy.session['username'],
                                                                request.remote.ip,
                                                                request.remote.port,
                                                                request.json))

    filename = request.json['file']
    username = cherrypy.session['username']
    self._logger.info("Open for file {3} requested by {0} ({1}:{2})".format(username,
                                                                            request.remote.ip,
                                                                            request.remote.port,
                                                                            filename))

    if self.is_valid_path(filename):
      self._app.open_file(username, filename)
    else:
      raise HTTPError(400, "Invalid path")

  @cherrypy.expose
  @cherrypy.tools.json_out()
  @cherrypy.tools.json_in()
  @require_identify()
  def close(self):
    """
    Unsubscribe a client to updates for a given file
    Method : PUT
    (Path : /ide/close)

    Input must be JSON of the following format:
      {
        'file':    '<<Filepath of file to close>>'
      }
    """
    self._logger.debug("Close by {0} ({1}:{2}) JSON: {3}".format(cherrypy.session['username'],
                                                                 request.remote.ip,
                                                                 request.remote.port,
                                                                 request.json))

    username = cherrypy.session['username']
    filename = request.json['file']
    self._logger.info("Close for file {3} requested by {0} ({1}:{2})".format(username,
                                                                             request.remote.ip,
                                                                             request.remote.port,
                                                                             filename))

    if self.is_valid_path(filename):
      self._app.unregister_user_to_file(username, filename)
    else:
      raise HTTPError(400, "Invalid path")

  @cherrypy.expose
  @cherrypy.tools.json_out()
  @cherrypy.tools.json_in()
  @require_identify()
  def save(self):
    """
    Receive changes to a file from the client
    Method : PUT
    (Path : /ide/save)

    Input must be JSON of the following format:
      {
        'file':   '<<Filepath of edited file>>',
        'vers':   '<<File version>>',
        'changes': [{
                     'type':    '<<Type of edit (ins | del)>>',
                     'pos':     '<<Position of edit>>',
                     'content': '<<Content of insert | Number of deletes>>'
                   }]
      }

    Output on the WS will be JSON of the following format:
      {
        'opCode': 'save',
        'data': {
                  'file':    '<<Filepath of edited file>>',
                  'vers':    '<<File version>>',
                  'changes': [{
                               'type':    '<<Type of edit (ins | del)>>',
                               'pos':     '<<Position of edit>>',
                               'content': '<<Content of insert | Number of deletes>>'
                               'author':   <<If the user is the author>>
                             }]
                }
      }
    """
    self._logger.debug("Save by {0} ({1}:{2}) JSON: {3}".format(cherrypy.session['username'],
                                                                request.remote.ip,
                                                                request.remote.port,
                                                                request.json))

    username = cherrypy.session['username']
    filename = request.json['file']
    version = request.json['vers']
    changes = request.json['changes']
    self._logger.info("Save for file {3} requested by {0} ({1}:{2})".format(username,
                                                                            request.remote.ip,
                                                                            request.remote.port,
                                                                            filename))
    if self.is_valid_path(filename):
      if self.is_valid_changes(changes):
        # Adds changes into a pool of task
        self._logger.info("Calling app for bundle {0}".format(version))
        self._app.file_edit(filename, [self._app.Change(c['pos'],
                                                        c.get('content') or c.get('count'),
                                                        c['type'] == IDEController.CHANGE_ADD_TYPE)
                                       for c in changes], username)
        self._logger.info("Return from app call for bundle {0}".format(version))

      else:
        raise HTTPError(400, "Invalid changes")
    else:
      raise HTTPError(400, "Invalid path")

  @cherrypy.expose
  @cherrypy.tools.json_out()
  @require_identify()
  def dump(self, filename, **kw):
    """
    Sends the current content of a given file
    Method : GET
    (Path : /ide/dump)

    User must start to buffer changes received for file before requesting dump.
    The server will register the user to receive updates, then send the dump,
    so the user misses no update. The user will have to detect which updates
    to apply based on the ``version`` sent.

    @param filename: Filepath of requested file

    Output on the WS will be JSON of the following format:
      {
        'opCode': 'dump',
        'data': {
                  'file':    '<<Filepath of given file>>',
                  'vers':    '<<File version>>',
                  'content': '<<Content of the requested file>>'
                }
      }
      OR
      Invalid path: None + (400 - Invalid path)
    """
    self._logger.debug("Dump by {0} ({1}:{2}) filename: {3}".format(cherrypy.session['username'],
                                                                    request.remote.ip,
                                                                    request.remote.port,
                                                                    filename))

    username = cherrypy.session['username']
    self._logger.info("Dump of file {3} requested by {0} ({1}:{2})".format(username,
                                                                           request.remote.ip,
                                                                           request.remote.port,
                                                                           filename))

    if self.is_valid_path(filename):
      self._app.get_file_content(filename, username)
    else:
      raise HTTPError(400, "Invalid path")

  @cherrypy.expose
  @cherrypy.tools.json_out()
  @require_identify()
  def tree(self, **kw):
    """
    Sends the files and the directories paths included in the project tree
    Method : GET
    (Path : /ide/tree)

    Output on the WS will be JSON of the following format:
      {
        'opCode': 'tree',
        'data': {
                  'nodes':    [{
                               'node':    '<<Path of the project node>>',
                               'isDir':   '<<Flag to diffenciate directories from file>>'
                              }]
                }
      }
    """
    self._logger.debug("Tree dump by {0} ({1}:{2})".format(cherrypy.session['username'],
                                                           request.remote.ip,
                                                           request.remote.port))

    username = cherrypy.session['username']
    self._logger.info("Tree dump requested by {0} ({1}:{2})".format(username,
                                                                    request.remote.ip,
                                                                    request.remote.port))

    self._app.get_project_nodes(username)

  @cherrypy.expose
  @require_identify()
  def export(self, path, **kw):
    self._logger.debug("Export by {0} ({1}:{2}) path: {3}".format(cherrypy.session['username'],
                                                                  request.remote.ip,
                                                                  request.remote.port,
                                                                  path))

    username = cherrypy.session['username']
    self._logger.info("Export requested by {0} ({1}:{2})".format(username,
                                                                 request.remote.ip,
                                                                 request.remote.port))

    if self.is_valid_path(path) or path == "/":
      future_response = self._app.create_archive(path, username)
    else:
      raise HTTPError(400, "Invalid path")

    # Block until an answer is given
    archive_path = future_response.get()
    if not os.path.exists(archive_path):
      raise HTTPError(500, "Unavailable archive")

    # Store archive name in request to remove it when client download will be completed
    request.archive_path = archive_path
    request.hooks.attach('on_end_request', lambda: os.unlink(request.archive_path))
    # Return archive
    return static.serve_download(archive_path)

  @cherrypy.expose
  @require_identify()
  def ws(self):
    """
    Method must exist to serve as a exposed hook for the websocket
    (Path : /ide/ws)
    """
    username = cherrypy.session['username']
    self._logger.info("WS creation request from {0} ({1}:{2})".format(username,
                                                                      request.remote.ip,
                                                                      request.remote.port))

  """
  Methods
  """

  def _save_callback(self, filename, changes, version, users):
    """
    Sends updates about a file to registered users
    This is the call back from /ide/save PUT-method

    Output on the WS will be JSON of the following format:
      {
        'opCode': 'save',
        'data': {
                  'file':    '<<Filepath of edited file>>',
                  'vers':    '<<File version>>',
                  'changes': [{
                               'type':    '<<Type of edit (ins | del)>>',
                               'pos':     '<<Position of edit>>',
                               'content': '<<Content of insert | Number of deletes>>'
                               'author':   <<If the user is the author>>
                             }]
                }
      }
    """
    serialized_changes = [(create_change_add_element_dict(element) if element.isAdd()
                           else create_change_remove_element_dict(element))
                          for element in changes]

    for user in users:
      set_author_bool_in_dict(serialized_changes, user)

      message_sent = simplejson.dumps(wrap_opCode('save',
                                                  create_file_version_dict(filename,
                                                                           version,
                                                                           serialized_changes)))
      ws = IDEWebSocket.IDEClients.get(user)
      if ws:
        try:
          ws.send(message_sent)
          self._logger.info("{0} ({1}:{2}) WS transfer succeded ({3})".format(user,
                                                                              ws.peer_address[0],
                                                                              ws.peer_address[1],
                                                                              self.debug_bundle_id))
        except:
          self._logger.error("{0} ({1}:{2}) WS transfer failed".format(user,
                                                                       ws.peer_address[0],
                                                                       ws.peer_address[1]))
          # Remove user from every file notify list
          self._app.unregister_user_to_all_files(user)
          # Close websocket
          ws.close(reason='Failed to send update for file {0}'.format(filename))

      else:
        self._logger.error("{0} has no WS in server".format(user))
        # Remove user from every file notify list
        self._app.unregister_user_to_all_files(user)
    ++self.debug_bundle_id

  def _tree_callback(self, nodes, caller):
    """
    Sends the files and the directories paths included in the project tree
    This is the call back from /ide/tree GET-method

    Output on the WS will be JSON of the following format:
      {
        'opCode': 'tree',
        'data': {
                  'nodes':    [{
                               'node':    '<<Path of the project node>>',
                               'isDir':   '<<Flag to diffenciate directories from file>>'
                              }]
                }
      }
    """
    self._logger.info("Tree-callback for {0}".format(caller))

    to_send = simplejson.dumps(wrap_opCode('tree', create_tree_nodes_dict(nodes)))

    ws = IDEWebSocket.IDEClients.get(caller)
    if ws:
      try:
        ws.send(to_send)
        self._logger.info("{0} ({1}:{2}) WS transfer succeded".format(caller,
                                                                      ws.peer_address[0],
                                                                      ws.peer_address[1]))
      except:
        self._logger.error("{0} ({1}:{2}) WS transfer failed".format(caller,
                                                                     ws.peer_address[0],
                                                                     ws.peer_address[1]))
        # Close websocket
        ws.close(reason='Failed to send tree')

    else:
      self._logger.error("{0} has no WS in server".format(caller))

  def _dump_callback(self, result, caller):
    """
    Sends the current content of a given file
    This is the call back from /ide/open and /ide/dump

    Output on the WS will be JSON of the following format:
      {
        'opCode': 'dump',
        'data': {
                  'file':    '<<Filepath of given file>>',
                  'vers':    '<<File version>>',
                  'content': '<<Content of the requested file>>'
                }
      }
    """
    self._logger.info("Tree-callback for {0}".format(caller))
    filename, content, version = result  # TODO Check if result is None

    to_send = simplejson.dumps(wrap_opCode('dump',
                                           create_file_dump_dict(filename, version, content)))

    ws = IDEWebSocket.IDEClients.get(caller)
    if ws:
      try:
        ws.send(to_send)
        self._logger.info("{0} ({1}:{2}) WS transfer succeded".format(caller,
                                                                      ws.peer_address[0],
                                                                      ws.peer_address[1]))
      except:
        self._logger.error("{0} ({1}:{2}) WS transfer failed".format(caller,
                                                                     ws.peer_address[0],
                                                                     ws.peer_address[1]))
        # Close websocket
        ws.close(reason='Failed to send dump')

    else:
      self._logger.error("{0} has no WS in server".format(caller))


class IDEWebSocket(WebSocket):
  """
  WebSocket for the IDEController
  """
  IDEClients = {}

  def __init__(self, *args, **kw):
    WebSocket.__init__(self, *args, **kw)
    self.username = None

  def opened(self):
    self.username = cherrypy.session['username']
    self.IDEClients[self.username] = self
    cherrypy.log("User {0} ({1}) WS connected".format(self.username, self.peer_address))

  def closed(self, code, reason=None):
    # XXX May raise Key Error, but I don't get why...double dc?
    # FIXME Browser doing shenanigans when checking suggestions in URL bar...
    # FIXME Opening a 2nd WS for same users, and triggers 2 closing...hurray.
    # TODO do not create 2 ws for same session?
    try:
      del self.IDEClients[self.username]
    except:
      cherrypy.log("ERROR: WS for {0} was not in dict.".format(self.username))

    cherrypy.log("User {0} ({1}) WS disconnected. Reason: {2}".format(self.username,
                                                                      self.peer_address,
                                                                      reason))

