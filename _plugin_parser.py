import re
import json
import os
import os.path
from collections import OrderedDict

import caleydo_server.config

cc = caleydo_server.config.view('caleydo_server')

def _replace_variables(s, variables):
  def match(m):
    if m.group(1) in variables:
      return variables[m.group(1)]
    print 'cant resolve ' + m.group(1)
    return '$unresolved$'

  return re.sub(r'\$\{(.*)\}', match, s)

def _unpack_eval(s):
  return re.sub(r'eval!(.*)', '\1', s)

def _unpack_python_eval(s):
  m = re.search(r'eval!(.*)', s)
  if m is None:
    return s
  return eval(m.group(1))


def _resolve_client_config(config, vars):
  config = _replace_variables(config, vars)
  config = _unpack_eval(config)
  return config

def _resolve_server_config(d, vars = {}):
  import six
  if isinstance(d, six.string_types): #not a string
    return _unpack_python_eval(_replace_variables(d, vars))
  elif type(d) == list:
    return [_resolve_server_config(i) for i in d]
  elif type(d) == dict or type(d) == OrderedDict:
    for k,v in d.items():
      d[k] = _resolve_server_config(v)
    return d
  return d

# extend a dictionary recursivly
def _extend(target, w):
  for k,v in w.iteritems():
    if type(v) is dict:
      if k not in target:
        target[k] = _extend({}, v)
      else:
        target[k] = _extend(target[k], v)
    else:
      target[k] = v
  return target

def _list_dirs(dd):
  if not os.path.isdir(dd):
      return []
  return [d for d in os.listdir(dd) if not os.path.isfile(os.path.join(dd,d))]

def _resolve_conflicts(dependencies):
  r = dict()
  for k,v in dependencies.iteritems():
    if type(v) is list:
      print 'resolving versions of ',k,v,'->', ' '.join(v)
      r[k] = ' '.join(v)
    else:
      r[k] = v #single hit
  return r

class Plugin(object):
  def __init__(self, plugindir, p, desc):
    self.id = p
    self.name = desc.get('name', p)
    self.version = desc.get('version', '0.0.1')
    self.folder = os.path.join(plugindir, p)
    self.folder_name = p

class PluginMetaData(object):
  def __init__(self):

    self.plugins = []
    self.caleydo_client_plugins = []
    self.caleydo_server_plugins = []

    self.baseDir = cc.dir
    self.ignored_bower_dependencies = []

    self.requirejs_config = {
      'paths': OrderedDict(),
      'map': OrderedDict(),
      'config': OrderedDict()
    }
    self._bower_configs = None

  def _add_client_extension(self, plugins, plugin_desc):
    if type(plugins) is not list:
      plugins = [ plugins ]
    def fill(p):
      p['folder'] = plugin_desc.folder_name
      if 'id' not in p:
        p['id'] = plugin_desc.id
      if 'version' not in p:
        p['version'] = plugin_desc.version
      if 'name' not in p:
        p['name'] = plugin_desc.name
      return p
    self.caleydo_client_plugins.extend(map(fill, plugins))

  def _add_server_extension(self, plugins, plugin_desc):
    if type(plugins) is not list:
      plugins = [ plugins ]
    def fill(p):
      p['folder'] = plugin_desc.folder_name
      if 'id' not in p:
        p['id'] = plugin_desc.id
      if 'version' not in p:
        p['version'] = plugin_desc.version
      if 'name' not in p:
        p['name'] = plugin_desc.name
      return p
    self.caleydo_server_plugins.extend(map(fill, plugins))

  def _add_requirejs_config(self, rconfig, d):
    _extend(self.requirejs_config, rconfig)

  def _config_requirejs_bower(self, rconfig, d):
    if 'ignore' in rconfig:
      self.ignored_bower_dependencies.extend(rconfig['ignore'])

  def add_plugin(self, plugindir, d):
    metadata_file_abs = plugindir + d + cc.metadata_file
    if not os.path.exists(metadata_file_abs):
      return
    print 'add plugin ' + metadata_file_abs
    with open(metadata_file_abs, 'r') as f:
      metadata = json.load(f)
      p = Plugin(plugindir, d, metadata)
      self.plugins.append(p)
      if 'caleydo' in metadata:
        c = metadata['caleydo']
        if 'plugins' in c:
          pp = c['plugins']
          if 'web' in pp:
            self._add_client_extension(pp['web'], p)
          if 'python' in pp:
            self._add_server_extension(pp['python'], p)
        if 'requirejs-config' in c:
          self._add_requirejs_config(c['requirejs-config'], d)
        if 'requirejs-bower' in c:
          self._config_requirejs_bower(c['requirejs-bower'], d)


  def _add_bower_requirejs_config(self, d, scripts, cssfiles):
    metadata_file_abs = self.baseDir + cc.bower_components + '/' + d + '/.bower.json'
    print 'add bower dependency ' + metadata_file_abs
    with open(metadata_file_abs, 'r') as f:
      metadata = json.load(f)
    if 'main' in metadata:
      script = metadata['main']
      if type(script) is list:
        script = script[0]
      if re.match(r'.*\.js$', script):
        scripts[d] = d + '/' + script[:len(script) - 3]
      elif re.match(r'.*\.css$', script):
        cssfiles[d] = d + '/' + script[:len(script) - 4]

  def derive_bower_requirejs_config(self):
    print 'derive bower config'
    scripts = dict()
    cssfiles = dict()
    for d in _list_dirs(self.baseDir + cc.bower_components):
      if d in self.ignored_bower_dependencies:
        continue
      self._add_bower_requirejs_config(d, scripts, cssfiles)

    self._bower_configs = scripts, cssfiles

  def to_requirejs_config_file(self, main_file=None, base_url=None):
    ccw = caleydo_server.config.view('caleydo_web')

    if main_file is None:
      main_file = ccw.mainFile
    if base_url is None:
      base_url = ccw.baseUrl

    c = {
      'baseUrl': base_url,
      'paths': OrderedDict(),
      'map': OrderedDict(),
      'deps': [ main_file ],
      'config': OrderedDict()
    }
    #extend with the stored one
    _extend(c, self.requirejs_config)

    #inject caleydo registry information
    c['config'][ccw.configPrefix + 'caleydo_web/main'] = {
      'apiUrl': ccw.apiPrefix,
      'apiJSONSuffix': ccw.apiSuffix
    }
    c['config'][ccw.configPrefix + 'caleydo_web/plugin'] = {
      'baseUrl': base_url,
      'plugins': self.caleydo_client_plugins
    }

    #inject bower dependencies
    for d,script in self._bower_configs[0].iteritems():
      value = base_url+ccw.bower_components_url + '/' + script
      c['paths'][d] = value
    for d,css in self._bower_configs[1].iteritems():
      value = self.requirejs_config['map']['*']['css'] + '!' + base_url+ccw.bower_components_url + '/' + css
      c['map']['*'][d] = value

    c = json.dumps(c, indent=2)
    variables = {
      'baseUrl': base_url+ccw.bower_components_url
    }
    c = _resolve_client_config(c, variables)

    full = '/*global require */\r\nrequire.config(' + c + ');'
    return full

  @property
  def server_extensions(self):
    return _resolve_server_config(self.caleydo_server_plugins)

  def parse_dirs(self, plugindirs):
    for d in plugindirs:
      for f in _list_dirs(d):
          self.add_plugin(d, f)

def parse():
  p = PluginMetaData()
  p.parse_dirs(cc.getlist('pluginDirs'))
  p.derive_bower_requirejs_config()

  return p