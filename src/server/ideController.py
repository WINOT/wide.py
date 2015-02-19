import json
import cherrypy
from ws4py.websocket import WebSocket
from genshi.template import TemplateLoader


class IDEController(object):
  """
  Controller of the IDE/Editing part
  """

  def __init__(self, template_path, logger):
    """
    IDEController initialiser

    @param template_path: Path to the template directory
    @param logger: The CIDE.py logger instance
    """
    self._loader = TemplateLoader(template_path, auto_reload=True)

    self._logger = logger

    # XXX Temp dummy vars
    self.data = "xzczxc"

    self._logger.debug("IDEController instance created")

  @cherrypy.expose
  def index(self):
    #return "Hello world"
    # TODO Return page/template render for the IDE part
    tmpl = self._loader.load('edit.html')
    # # set args in generate as key1=val1, key2=val2
    stream = tmpl.generate()
    return stream.render('html')

  @cherrypy.expose
  @cherrypy.tools.json_in()
  @cherrypy.tools.json_out()
  def save(self):
    json_data = cherrypy.request.json

    content = ""
    self.data += content

    # Send as json representation
    ret = json.dumps(dict(test=self.data, othervar=2))
    for user in IDEWebSocket.IDEClients:
      user.send(ret)

    # Return default structure {code, status, merrage}
    return {} # ok for now

  @cherrypy.expose
  @cherrypy.tools.json_out()
  @cherrypy.tools.json_in()
  def open(self):
    return {'file':    "dummy",
            'vers':    0,
            'content': "Hello world from controller"}

  @cherrypy.expose
  def refreshEdit(self):
    return self.data

  @cherrypy.expose
  def ws(self):
    """
    Method must exist to serve as a exposed hook for the websocket
    """
    self._logger.info("WS creation request from {0}:{1}".format(cherrypy.request.remote.ip,
                                                                cherrypy.request.remote.port))


class IDEWebSocket(WebSocket):
  IDEClients = set()

  def __init__(self, *args, **kw):
    WebSocket.__init__(self, *args, **kw)
    self.IDEClients.add(self)

  def closed(self, code, reason=None):
    self.IDEClients.remove(self)

