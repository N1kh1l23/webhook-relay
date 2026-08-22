from arq.connections import ArqRedis
from fastapi import Request


async def get_redis(request: Request) -> ArqRedis:
    return request.app.state.redis
