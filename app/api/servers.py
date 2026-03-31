import csv
import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ping_result import PingResult
from app.models.server import Server
from app.schemas.server import ServerCreate, ServerResponse, ServerUpdate, ServerWithStatus

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get("", response_model=list[ServerWithStatus])
async def list_servers(group: str | None = None, tag: str | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Server)
    if group:
        query = query.where(Server.group_name == group)
    if tag:
        from sqlalchemy import text
        query = query.where(text(f"'{tag}' = ANY(tags)"))
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


@router.post("/bulk/import", response_model=dict, tags=["bulk"])
async def bulk_import_csv(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """
    Bulk import servers from CSV file.
    CSV format: name,ip_address,group_name,tags,ping_interval

    Example:
        name,ip_address,group_name,tags,ping_interval
        Web1,192.168.1.1,KSO_FH,web;production,60
        DNS1,8.8.8.8,KSO_HW,dns;external,120
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV format")

    try:
        content = await file.read()
        text = content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(text))

        if not reader.fieldnames or not all(f in reader.fieldnames for f in ['name', 'ip_address']):
            raise HTTPException(status_code=400, detail="CSV must have 'name' and 'ip_address' columns")

        created = 0
        skipped = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):  # start=2 because header is row 1
            try:
                name = row.get('name', '').strip()
                ip = row.get('ip_address', '').strip()
                group = row.get('group_name', '').strip() or None
                tags_str = row.get('tags', '').strip()
                ping_interval = int(row.get('ping_interval', 60) or 60)

                if not name or not ip:
                    errors.append(f"Row {row_num}: name and ip_address required")
                    skipped += 1
                    continue

                # Parse tags (comma or semicolon separated)
                tags = [t.strip() for t in tags_str.replace(',', ';').split(';') if t.strip()] if tags_str else []

                server = Server(
                    name=name,
                    ip_address=ip,
                    group_name=group,
                    tags=tags,
                    ping_interval=ping_interval,
                    is_active=True,
                )
                db.add(server)
                created += 1

            except ValueError as e:
                errors.append(f"Row {row_num}: {str(e)}")
                skipped += 1
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                skipped += 1

        await db.commit()

        return {
            "success": True,
            "created": created,
            "skipped": skipped,
            "errors": errors[:10],  # Return first 10 errors
            "total_errors": len(errors),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV parsing error: {str(e)}")


@router.get("/bulk/template", tags=["bulk"])
async def get_csv_template():
    """Get CSV template for bulk import"""
    template = """name,ip_address,group_name,tags,ping_interval
Web Server 1,192.168.1.1,KSO_FH,web;production,60
Web Server 2,192.168.1.2,KSO_FH,web;production,60
DNS Server,8.8.8.8,KSO_HW,dns;external,120
Mail Server,mail.example.com,KSO_ZTE,mail;critical,30"""
    return {"template": template, "format": "CSV"}
