from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.dependencies import AsyncSessionDep
from app.schemas import FileData
from app.services import FriendlyFileNameService

router = APIRouter()


@router.get("/files/{task_id}")
async def download_file(
    task_id: str,
    session: AsyncSessionDep,
) -> FileResponse:
    """
    Endpoint to serve the downloaded file.
    """
    friendly_filename: FriendlyFileNameService = FriendlyFileNameService(task_id, session)
    data: FileData = await friendly_filename.get_file_data()
    return FileResponse(
        path=data.file_disk_path,
        filename=data.friendly_name,
        media_type='application/octet-stream',
    )
