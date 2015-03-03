import os
import cherrypy
from cherrypy import request
import simplejson
from ws4py.websocket import WebSocket
from genshi.template import TemplateLoader
from cide.server.identifyController import require_identify
import uuid  # XXX Temp for fake session id... Could be used for real?


# Will be changed to httpErrors
def create_argument_error_msg(arg):
  return {'code': 400, 
          'message': "Invalid argument provided : " + str(arg)}

def create_file_dump_dict(filename, version, content):
  return {'file':    filename,
          'vers':    version,
          'content': content}

def create_file_version_dict(filename, version, changes):
  return {'file':    filename,
          'vers':    version,
          'changes': changes}

def create_tree_nodes_dict(nodes):
  return {'nodes': [{'node': name,
                     'isDir': is_dir}
                     for (name, is_dir) in nodes]}

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

    @type app: cide.app.python.core
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

    # Register controller to events
    self._app.register_application_listener(self)

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
    if not cherrypy.session.get('username'):
      cherrypy.session['username'] = uuid.uuid4()  # XXX Session should be set by the id/auth module

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

    @return: JSON of the following format:
      {
        'file':    '<<Filepath of given file>>',
        'vers':    '<<File version>>',
        'content': '<<Content of the requested file>>'
      }
    """
    if not cherrypy.session.get('username'):
      cherrypy.session['username'] = uuid.uuid4()  # XXX Session should be set by the id/auth module

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

    # TODO Check if we have a WS before subscribing?
    if self.is_valid_path(filename):
      self._app.register_user_to_file(username, filename)
      content, version = self._app.get_file_content(filename)
      # Dump content 
      result = create_file_dump_dict(filename, version, content)
    else:
      result = create_argument_error_msg(filename)
    return result

  @cherrypy.expose
  @cherrypy.tools.json_out()
  @cherrypy.tools.json_in()
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
    if not cherrypy.session.get('username'):
      cherrypy.session['username'] = uuid.uuid4()  # XXX Session should be set by the id/auth module

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

    result = None
    if self.is_valid_path(filename):
      self._app.unregister_user_to_file(username, filename)
    else:
      result = create_argument_error_msg(filename)
    return result

  @cherrypy.expose
  @cherrypy.tools.json_out()
  @cherrypy.tools.json_in()
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
        'file':    '<<Filepath of edited file>>',
        'vers':    '<<File version>>',
        'changes': [{
                     'type':    '<<Type of edit (ins | del)>>',
                     'pos':     '<<Position of edit>>',
                     'content': '<<Content of insert | Number of deletes>>'
                   }]
      }

    @return: ok: Nothing + (200)
             File doesn't exist: Nothing + (404 - Not found)
             Version is too old: Nothing + (410 - Gone)
    """
    if not cherrypy.session.get('username'):
      cherrypy.session['username'] = uuid.uuid4()  # XXX Session should be set by the id/auth module

    self._logger.debug("Save by {0} ({1}:{2}) JSON: {3}".format(cherrypy.session['username'],
                                                                request.remote.ip,
                                                                request.remote.port,
                                                                request.json))

    username = cherrypy.session['username']
    filename = request.json['file']
    changes = request.json['changes']
    self._logger.info("Save for file {3} requested by {0} ({1}:{2})".format(username,
                                                                            request.remote.ip,
                                                                            request.remote.port,
                                                                            filename))
    result = None
    if self.is_valid_path(filename):
      if self.is_valid_changes(changes):
        # Adds changes into a pool of task
        self._app.file_edit(filename, [self._app.Change(
                                        c['pos'],
                                        c.get('content') or c.get('count'),
                                        c['type'] == IDEController.CHANGE_ADD_TYPE)
                                      for c in changes])

      else:
        result = create_argument_error_msg(changes)
    else:
      result = create_argument_error_msg(filename)
    return result

  @cherrypy.expose
  @cherrypy.tools.json_out()
  def dump(self, filename):
    """
    Sends the current content of a given file
    Method : GET
    (Path : /ide/dump)

    User must start to buffer changes received for file before requesting dump.
    The server will register the user to receive updates, then send the dump,
    so the user misses no update. The user will have to detect which updates
    to apply based on the ``version`` sent.

    @param filename: Filepath of requested file

    @return: JSON of the following format:
      {
        'file':    '<<Filepath of given file>>',
        'vers':    '<<File version>>',
        'content': '<<Content of the requested file>>'
      }
      OR
      File doesn't exist: Nothing + (404 Not found)
    """
    if not cherrypy.session.get('username'):
      cherrypy.session['username'] = uuid.uuid4()  # XXX Session should be set by the id/auth module

    self._logger.debug("Dump by {0} ({1}:{2}) filename: {3}".format(cherrypy.session['username'],
                                                                    request.remote.ip,
                                                                    request.remote.port,
                                                                    filename))

    username = cherrypy.session['username']
    self._logger.info("Dump of file {3} requested by {0} ({1}:{2})".format(username,
                                                                           request.remote.ip,
                                                                           request.remote.port,
                                                                           filename))
    result = None
    if self.is_valid_path(filename):
      
      # TODO Check for exceptions
      content, version = self._app.get_file_content(filename)
      result = create_file_dump_dict(filename, version, content)
    else:
      result = create_argument_error_msg(filename)

    return result

  @cherrypy.expose
  @cherrypy.tools.json_out()
  def tree(self):
    """
    Sends the files and the directories paths included in the project tree
    Method : GET
    (Path : /ide/tree)

    @return: JSON of the following format:
      {
        'nodes':    [{
                     'node':    '<<Path of the project node>>',
                     'isDir':   '<<Flag to diffenciate directories from file>>'
                    }]
      }
    """
    if not cherrypy.session.get('username'):
      cherrypy.session['username'] = uuid.uuid4()  # XXX Session should be set by the id/auth module

    self._logger.debug("Tree dump by {0} ({1}:{2})".format(cherrypy.session['username'],
                                                                    request.remote.ip,
                                                                    request.remote.port))

    username = cherrypy.session['username']
    self._logger.info("Tree dump requested by {0} ({1}:{2})".format(username,
                                                                    request.remote.ip,
                                                                    request.remote.port))
    
    nodes = self._app.get_project_nodes()
    return create_tree_nodes_dict(nodes)

  @cherrypy.expose
  def ws(self):
    """
    Method must exist to serve as a exposed hook for the websocket
    (Path : /ide/ws)
    """
    if not cherrypy.session.get('username'):
      cherrypy.session['username'] = uuid.uuid4()  # XXX Session should be set by the id/auth module

    # TODO do not create 2 ws for same session?
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
        'file':    '<<Filepath of edited file>>',
        'vers':    '<<File version>>',
        'changes': [{
                     'type':    '<<Type of edit (ins | del)>>',
                     'pos':     '<<Position of edit>>',
                     'content': '<<Content of insert | Number of deletes>>'
                   }]
      }
    """

    temp_message = ("Temp msg from controller until "
                    "c++ module will return applied modifications")
    changes = [dict(type=self.CHANGE_ADD_TYPE, pos=0, content=temp_message)]

    for user in users:
      ws = IDEWebSocket.IDEClients.get(user)
      if ws:
        try:
          ws.send(simplejson.dumps(create_file_version_dict(filename, 
                                                            version, 
                                                            changes)))
        except:
          self._logger.error("{0} ({1}:{2}) WS transfer failed".format(username,
                                                                       request.remote.ip,
                                                                       request.remote.port))
          # Remove user from file notify list
          self._app.unregister_user_to_file(user, filename)

      else:
        self._logger.error("{0} ({1}:{2}) has no WS in server".format(username,
                                                                      request.remote.ip,
                                                                      request.remote.port))
        # Remove user from file notify list
        self._app.unregister_user_to_file(user, filename)


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
    try:
      del self.IDEClients[self.username]
    except:
      cherrypy.log("ERROR: WS for {0} was not in dict.".format(self.username))

    cherrypy.log("User {0} ({1}) WS disconnected".format(self.username, self.peer_address))

