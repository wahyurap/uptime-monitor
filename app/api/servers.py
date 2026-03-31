import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ping_result import PingResult
from app.models.server import Server
from app.schemas.server import ServerCreate, ServerResponse, ServerUpdate, ServerWithStatus

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get("", response_model=list[ServerWithStatus])
async def list_servers(group: str | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Server)
    if group:
        query = query.where(Server.group_name == group)
    query = query.order_by(Server.name)
    result = await db.execute(query)
    servers = result.scalars().all()

    response = []
    for s in servers:
        # Get last ping
        last_ping_result = await db.execute(
            select(PingResult)
            .where(PingResult.server_id == s.id)
            .order_by(PingResult.timestamp.desc())
            .limit(1)
        )
        last_ping = last_ping_result.scalar_one_or_none()

        status = "unknown"
        latency = None
        last_check = None
        if last_ping:
            status = "up" if last_ping.is_up else "down"
            latency = last_ping.latency_ms
            last_check = last_ping.timestamp

        response.append(ServerWithStatus(
            **ServerResponse.model_validate(s).model_dump(),
            current_status=status,
            last_latency_ms=latency,
            last_check=last_check,
        ))

    return response


@router.post("", response_model=ServerResponse, status_code=201)
async def create_server(data: ServerCreate, db: AsyncSession = Depends(get_db)):
    server = Server(**data.model_dump())
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return server


@router.get("/{server_id}", response_model=ServerWithStatus)
async def get_server(server_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    server = await db.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    last_ping_result = await db.execute(
        select(PingResult)
        .where(PingResult.server_id == server.id)
        .order_by(PingResult.timestamp.desc())
        .limit(1)
    )
    last_ping = last_ping_result.scalar_one_or_none()

    status = "unknown"
    latency = None
    last_check = None
    if last_ping:
        status = "up" if last_ping.is_up else "down"
        latency = last_ping.latency_ms
        last_check = last_ping.timestamp

    return ServerWithStatus(
        **ServerResponse.model_validate(server).model_dump(),
        current_status=status,
        last_latency_ms=latency,
        last_check=last_check,
    )


@router.put("/{server_id}", response_model=ServerResponse)
async def update_server(server_id: uuid.UUID, data: ServerUpdate, db: AsyncSession = Depends(get_db)):
    server = await db.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(server, key, value)

    await db.commit()
    await db.refresh(server)
    return server


@router.delete("/{server_id}", status_code=204)
async def delete_server(server_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    server = await db.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    await db.delete(server)
    await db.commit()
