from typing import Annotated, Union

from fastapi import (
    Depends,
    FastAPI,
    Query,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)
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
    "some_token_here": User(
        id=1, username="u1", token="some_token_here", room_id=1,
    ),
    "some_other_token": User(
        id=2, username="u2", token="some_other_token", room_id=1,
    ),
}

message_storage = set()


async def get_user_by_token(
    token: Annotated[str | None, Query()] = None,
) -> User | None:
    if token is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    return USERS.get(token)


@app.post("/produce")
async def post_message() -> dict[str, str]:
    msg = Message(content="Hello!")
    await router.broker.publish(msg, queue="test")
    return {"message": "Message produced"}


@router.subscriber("test")
async def consume(msg: Message, logger: Logger,) -> Message:
    message_storage.add(msg.content)
    logger.info(f"Got a message via rabbitmq: {msg.content}")
    return msg


@app.websocket("/updates/{room_id}")
async def get_updates(
    websocket: WebSocket,
    # Объект получить по токену
    # URL должен включать токен, например
    # ws://127.0.0.1:8000/updates/{room_id}?token=some-token
    user: Annotated[User, Depends(get_user_by_token)],
    room_id: Union[int, None] = None,
) -> None:
    await websocket.accept()
    try:
        while all(
            (
                message_storage,
                user,
                room_id,
                user.room_id == room_id
            )
        ):
            await websocket.send_text(message_storage.pop())
    except WebSocketDisconnect:
        print("Client disconnected")
