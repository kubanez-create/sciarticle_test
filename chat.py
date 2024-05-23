from typing import Annotated, Union

from fastapi import Depends, FastAPI, Query, WebSocket, WebSocketException, status
from fastapi.responses import HTMLResponse
from faststream.rabbit.fastapi import Logger, RabbitRouter
from pydantic import BaseModel

router = RabbitRouter("amqp://guest:guest@localhost:5672/")

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <label>Item ID: <input type="text" id="itemId" autocomplete="off" value="foo"/></label>
            <label>Token: <input type="text" id="token" autocomplete="off" value="some-key-token"/></label>
            <button onclick="connect(event)">Connect</button>
            <hr>
            <label>Message: <input type="text" id="messageText" autocomplete="off"/></label>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
        var ws = null;
            function connect(event) {
                var itemId = document.getElementById("itemId")
                var token = document.getElementById("token")
                ws = new WebSocket("ws://localhost:8000/items/" + itemId.value + "/ws?token=" + token.value);
                ws.onmessage = function(event) {
                    var messages = document.getElementById('messages')
                    var message = document.createElement('li')
                    var content = document.createTextNode(event.data)
                    message.appendChild(content)
                    messages.appendChild(message)
                };
                event.preventDefault()
            }
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""

class User(BaseModel):
    id: int
    username: str
    token: str
    room_id: int


USERS = {
    "some_token_here": User(id=1, username="u1", token="some_token_here", room_id=1),
    "some_other_token": User(id=2, username="u2", token="some_other_token", room_id=1),
}


async def get_user_by_token(
    token: Annotated[str | None, Query()] = None,
) -> User | None:
    if token is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    return USERS.get(token)


# TODO Необходимо реализовать эндпоинт POST MESSAGE, который отправляет
# сообщения
# TODO Необходимо реализовать вебсокет, который принимает из верхнего
# эндпоинта сообщения
# Ремарка 1:  сообщения приходят только в комнату, где может состоять
# только 2 юзера
# Ремарка 2:  нельзя использовать любые сторонние клиенты к брокеру
# очередей (в том числе и прямое API), за исключением faststream


@router.subscriber("test")
async def hello(msg: str):
    print("GOT A MESSAGE", msg)
    return {"response": "Hello, Rabbit!"}


@router.after_startup
async def test(app: FastAPI):
    await router.broker.publish("Hello!", "test")

app = FastAPI(lifespan=router.lifespan_context)
app.include_router(router)

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.websocket("/items/{item_id}/ws")
async def get_updates(
    websocket: WebSocket,
    item_id: str,
    # room_id: int,
    # Объект получить по токену
    user: Annotated[User, Depends(get_user_by_token)],
    msg: Union[str, None] = None,
) -> None:
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Received text was: {item_id}")
        await websocket.send_text(f"Text got through websocket: {data}")
        if msg is not None:
            await websocket.send_text(f"Text got through rabbitmq: {msg}")
        await websocket.send_text(f"User id: {user.id}")



