
INFO:     127.0.0.1:53276 - "POST /api/chat/sessions HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/uvicorn/protocols/http/httptools_impl.py", line 421, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        self.scope, self.receive, self.send
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/uvicorn/middleware/proxy_headers.py", line 62, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/fastapi/applications.py", line 1159, in __call__
    await super().__call__(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/applications.py", line 90, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/middleware/errors.py", line 186, in __call__
    raise exc
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py", line 96, in __call__
    await self.simple_response(scope, receive, send, request_headers=headers)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py", line 154, in simple_response
    await self.app(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/fastapi/middleware/asyncexitstack.py", line 18, in __call__
    await self.app(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/routing.py", line 660, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/routing.py", line 680, in app
    await route.handle(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/routing.py", line 276, in handle
    await self.app(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/fastapi/routing.py", line 134, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/fastapi/routing.py", line 120, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/fastapi/routing.py", line 674, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/fastapi/routing.py", line 328, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/ianbruce/code/war_room/scripts/Vision/backend/api/routes/chat.py", line 63, in create_session
    session = await mgr.create_session(
              ^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
    )
    ^
  File "/Users/ianbruce/code/war_room/scripts/Vision/backend/chat/manager.py", line 60, in create_session
    cur.execute(
    ~~~~~~~~~~~^
        """INSERT INTO chat_sessions (case_id, project_key, system_prompt, status)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        (case_id, project_key, prompt),
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/psycopg2/extras.py", line 236, in execute
    return super().execute(query, vars)
           ~~~~~~~~~~~~~~~^^^^^^^^^^^^^
psycopg2.errors.UndefinedTable: relation "chat_sessions" does not exist
LINE 1: INSERT INTO chat_sessions (case_id, project_key, system_prom...
                    ^

INFO:     127.0.0.1:53287 - "OPTIONS /api/chat/sessions HTTP/1.1" 200 OK
INFO:     127.0.0.1:53287 - "POST /api/chat/sessions HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/uvicorn/protocols/http/httptools_impl.py", line 421, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        self.scope, self.receive, self.send
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/uvicorn/middleware/proxy_headers.py", line 62, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/fastapi/applications.py", line 1159, in __call__
    await super().__call__(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/applications.py", line 90, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/middleware/errors.py", line 186, in __call__
    raise exc
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py", line 96, in __call__
    await self.simple_response(scope, receive, send, request_headers=headers)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py", line 154, in simple_response
    await self.app(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/fastapi/middleware/asyncexitstack.py", line 18, in __call__
    await self.app(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/routing.py", line 660, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/routing.py", line 680, in app
    await route.handle(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/routing.py", line 276, in handle
    await self.app(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/fastapi/routing.py", line 134, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/fastapi/routing.py", line 120, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/fastapi/routing.py", line 674, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/fastapi/routing.py", line 328, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/ianbruce/code/war_room/scripts/Vision/backend/api/routes/chat.py", line 63, in create_session
    session = await mgr.create_session(
              ^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
    )
    ^
  File "/Users/ianbruce/code/war_room/scripts/Vision/backend/chat/manager.py", line 60, in create_session
    cur.execute(
    ~~~~~~~~~~~^
        """INSERT INTO chat_sessions (case_id, project_key, system_prompt, status)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        (case_id, project_key, prompt),
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/Users/ianbruce/code/war_room/scripts/Vision/.venv/lib/python3.14/site-packages/psycopg2/extras.py", line 236, in execute
    return super().execute(query, vars)
           ~~~~~~~~~~~~~~~^^^^^^^^^^^^^
psycopg2.errors.UndefinedTable: relation "chat_sessions" does not exist
LINE 1: INSERT INTO chat_sessions (case_id, project_key, system_prom...
                    ^

[browser] Failed to create session TypeError: NetworkError when attempting to fetch resource.
