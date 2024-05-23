from typing import Annotated, Union

from fastapi import Depends, FastAPI, Query, Request, WebSocket, WebSocketException, status
from faststream.rabbit.fastapi import Logger, RabbitRouter
from pydantic import BaseModel

router = RabbitRouter("amqp://guest:guest@localhost:5672/")
app = FastAPI(lifespan=router.lifespan_context)
app.include_router(router)

class User(BaseModel):
    id: int
    username: str
    token: str
    room_id: int

class Message(BaseModel):
    content: str


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

@app.post("/produce")
async def post_message():
    msg = Message(content="Hello!")
    await router.broker.publish(msg, queue="test")
    return {"message": "Message produced"}

@router.subscriber("test")
@app.websocket("/updates/{room_id}")
async def get_updates(
    websocket: WebSocket,
    # Объект получить по токену
    user: Annotated[User, Depends(get_user_by_token)],
    room_id: Union[int, None] = None,
    msg: Union[Message, None] = None,
) -> None:
    await websocket.accept()
    while True:
        if user and msg and user.room_id == room_id:
            await websocket.send_text(msg.content)
