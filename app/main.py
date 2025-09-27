from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import zipfile
import io
from pathlib import Path
from typing import List
import shutil

app = FastAPI(title="WLAN Share", description="Simple file sharing over WLAN")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Shared directory path
SHARED_DIR = Path("../shared")
SHARED_DIR.mkdir(exist_ok=True)

def get_file_list():
    files = []
    if SHARED_DIR.exists():
        for file_path in SHARED_DIR.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "size": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2)
                })
    return sorted(files, key=lambda x: x["name"])

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    files = get_file_list()
    return templates.TemplateResponse("index.html", {"request": request, "files": files})

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    filename = file.filename.replace("/", "_").replace("\\", "_")
    file_path = SHARED_DIR / filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"message": f"File '{filename}' uploaded successfully", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = SHARED_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=filename, media_type='application/octet-stream')

@app.get("/zip")
async def download_all_as_zip():
    files = list(SHARED_DIR.glob("*"))
    files = [f for f in files if f.is_file()]
    if not files:
        raise HTTPException(status_code=404, detail="No files to download")
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in files:
            zip_file.write(file_path, file_path.name)
    zip_buffer.seek(0)
    
    return StreamingResponse(
        io.BytesIO(zip_buffer.read()),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=shared_files.zip"}
    )

@app.delete("/delete/{filename}")
async def delete_file(filename: str):
    file_path = SHARED_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        file_path.unlink()
        return {"message": f"File '{filename}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print(" Starting WLAN Share Server...")
    print(" Server will be available at: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
