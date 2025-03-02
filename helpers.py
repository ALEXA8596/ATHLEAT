import random
import string

from flask import redirect, render_template, request, session, url_for
from functools import wraps

def login_required(f):
  """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """

  @wraps(f)
  def decorated_function(*args, **kwargs):
    if session.get("user_id") is None:
      return redirect("/login")
    return f(*args, **kwargs)

  return decorated_function


def generate_token():
  chars = string.ascii_lowercase + string.ascii_uppercase + '0123456789'
  token = ''
  for i in range(10):
    token += random.choice(chars)
  return token
