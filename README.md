GLaDOS
======

A not very exciting slack bot.

Writing plugins
---------------
A plugin consists of a python class based on GladosPluginBase.
It lives in the `plugins/` directory. You can do just about anything you want with plugins.
Each plugin is given a shared SQLAlchemy session (currently SQLite, will change "soon").
Each plugin is also given access to the client's `send` function. For now, this just gives it the actual send function, but may implement queueing or some other fanciness later.
The send function takes at least two arguments: the text to send and the channel to which to send it.
It takes an optional third argument, an attachments array ([see official documentation](https://api.slack.com/docs/attachments)). This argument should be a python array of python dicts.
The function will take care of converting it to JSON.
Plugin methods that have a defined meaning are documented in `plugin_base.py`

Plugins are configured in the `plugins.json` file. For now each plugin is only defined by the file name and the plugin class, but other things may be added in the future.

New! Async plugins
------------------
Now available: async plugins that accept messages to a unix socket and generate messages based on what they receive.
Example usage: reminder plugin that accepts messages from a cron job (see the PDreminder job).
Currently only have the ability to send to the general channel.

Developing
----------
Get the token for your bot integration and dump it into `.slack-token`.
You can run a development version of GLaDOS by running `client.py` but if you want to run GaaS (glados as a service) you should edit `glados.conf` and make a symlink to it in /etc/init.

Contributing
------------
Contributions in the form of updates to the core functionality and plugins are welcome.
Please respect existing conventions within the code and in particular make sure all code passes `flake8` with line length limit 120 before submitting a pull request.

To-do
-----
- Better error handling of crashing plugins
- More restrictive sending of messages
- Move away from SQLite
- Better logging
