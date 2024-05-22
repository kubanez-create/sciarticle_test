from typing import Annotated
from fastapi import (
    Depends,
    FastAPI,
    Query,
    WebSocket,
    WebSocketException,
    status
)
from pydantic import BaseModel

from faststream.rabbit.fastapi import RabbitRouter, Logger

app = FastAPI()
router = RabbitRouter("amqp://guest:guest@localhost:5672/")

class User(BaseModel):
    id: int
    token: str

USERS = {
    "some_token_here": User(id=1, token="some_token_here"),
    "some_other_token": User(id=2, token="some_other_token")
}

async def get_user_by_token(
    websocket: WebSocket,
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

@router.publisher("queue1")
async def post_message(logger: Logger, message: str) -> dict[str, str]:
    logger.info(message)
    return {"response": message}


@router.subscriber("queue1")
@app.websocket('/updates/{room_id}')
async def get_updates(
      websocket: WebSocket,
      message: str,
      # Объект получить по токену
      user: Annotated[User, Depends(get_user_by_token)],
    ):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")