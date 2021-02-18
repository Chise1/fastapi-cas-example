from typing import Optional

from cas import CASClient
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi.responses import HTMLResponse

app = FastAPI(title=__name__)
from fastapi.responses import RedirectResponse

cas_client = CASClient(
    version=3,
    service_url='http://127.0.0.1:8002/login?next=%2Fprofile',
    server_url='http://127.0.0.1:8000/cas/'
)
app.add_middleware(SessionMiddleware, secret_key="!secret")



@app.get('/')
async def index(request: Request):
    return RedirectResponse(request.url_for('login'))


@app.get('/profile')
async def profile(request: Request):
    print(request.session.get("user"))
    user = request.session.get("user")
    if user:
        return HTMLResponse('Logged in as %s. <a href="/logout">Logout</a>' % user['user'])
    return HTMLResponse('Login required. <a href="/login">Login</a>', status_code=403)


@app.get('/login')
def login(
    request: Request, next: Optional[str] = None,
    ticket: Optional[str] = None):
    if request.session.get("user", None):
        # Already logged in
        return RedirectResponse(request.url_for('profile'))

    # next = request.args.get('next')
    # ticket = request.args.get('ticket')
    if not ticket:
        # No ticket, the request come from end user, send to CAS login
        cas_login_url = cas_client.get_login_url()
        print('CAS login URL: %s', cas_login_url)
        return RedirectResponse(cas_login_url)

    # There is a ticket, the request come from CAS as callback.
    # need call `verify_ticket()` to validate ticket and get user profile.
    print('ticket: %s', ticket)
    print('next: %s', next)

    user, attributes, pgtiou = cas_client.verify_ticket(ticket)

    print(
        'CAS verify ticket response: user: %s, attributes: %s, pgtiou: %s',
        user, attributes, pgtiou)

    if not user:
        return HTMLResponse('Failed to verify ticket. <a href="/login">Login</a>')
    else:  # Login successfully, redirect according `next` query parameter.
        response = RedirectResponse(next)
        request.session['user'] = dict(user=user)
        return response


@app.get('/logout')
def logout(request: Request):
    redirect_url = request.url_for('logout_callback')
    cas_logout_url = cas_client.get_logout_url(redirect_url)
    print('CAS logout URL: %s', cas_logout_url)
    return RedirectResponse(cas_logout_url)


@app.get('/logout_callback')
def logout_callback(request: Request):
    # redirect from CAS logout request after CAS logout successfully
    # response.delete_cookie('username')
    request.session.pop("user", None)
    return HTMLResponse('Logged out from CAS. <a href="/login">Login</a>')


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, port=8002)
