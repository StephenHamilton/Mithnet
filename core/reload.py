#!/usr/bin/env python
"""
reload.py - Phenny Module Reloader Module
Copyright 2008, Sean B. Palmer, inamidst.com
Licensed under the Eiffel Forum License 2.

http://inamidst.com/phenny/
"""

import sys, os.path, time, imp
import irc

def f_reload(phenny, input): 
   """Reloads a module, for use by admins only.""" 
   if input.nick not in phenny.ident_admin: return phenny.reply('Requires authorization. Use .auth to identify')

   name = input.group(2)
   if name == phenny.config.owner: 
      return phenny.reply('What?')

   if (not name) or (name == '*'): 
      phenny.setup()
      return phenny.reply('done')

   path = None
   if not sys.modules.has_key(name): 
      return phenny.say('%s: no such module!' % name)
   else:
      phenny.unregister(name)
      path = sys.modules[name].__file__
      del sys.modules[name]

   # Thanks to moot for prodding me on this
   # path = sys.modules[name].__file__
   if path.endswith('.pyc') or path.endswith('.pyo'): 
      path = path[:-1]
   if not os.path.isfile(path): 
      return phenny.say('Found %s, but not the source file' % name)

   module = imp.load_source(name, path)
   sys.modules[name] = module
   if hasattr(module, 'setup'): 
      module.setup(phenny.bot)

   mtime = os.path.getmtime(module.__file__)
   modified = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(mtime))

   phenny.register(name, vars(module))
   phenny.bind_commands()

   phenny.say('%r (version: %s)' % (module, modified))
f_reload.name = 'reload'
f_reload.rule = (['reload'], r'(\S+)?')
f_reload.priority = 'low'
f_reload.thread = False

def f_load(phenny, input):
   # """Loads a module, for use by admins only.""" 
   if input.nick not in phenny.ident_admin: return phenny.reply('Requires authorization. Use .auth to identify')
   
   name = input.group(2)
   if (not name) or (name == phenny.config.owner): 
      return phenny.reply('What?')
   
   if sys.modules.has_key(name): 
      return phenny.say('%s: module already exists! use .reload' % name)
   
   #path = os.path.join('/net_auto/nova/home/2009/mfu2/Public/mithnet/', 'modules', name + '.py')
   path = os.path.join(os.getcwd(), 'modules', name + '.py')
   if not os.path.isfile(path): 
      return phenny.say('%s: no such module!' % name)

   module = imp.load_source(name, path)
   sys.modules[name] = module
   if hasattr(module, 'setup'): 
      module.setup(phenny)

   mtime = os.path.getmtime(module.__file__)
   modified = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(mtime))

   phenny.register(name,vars(module))
   phenny.bind_commands()

   phenny.reply('%r (version: %s)' % (module, modified))
f_load.name = 'load'
f_load.rule = (['load'], r'(\S+)?')
f_load.priority = 'low'
f_load.thread = False

if __name__ == '__main__': 
   print __doc__.strip()
