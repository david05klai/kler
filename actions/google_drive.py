"""Drive file operations using OAuth and bounded result sizes."""
import io
import json
from pathlib import Path
from core.google_services import get_service

def google_drive(parameters: dict, player=None):
    try:
        from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
        action = parameters.get("action","list")
        service = get_service("drive", authorize=action=="connect")
        if action=="connect":
            return "Google Drive conectado."
        files = service.files()
        file_id = parameters.get("file_id")
        if action in {"download","delete","share","info"} and not file_id:
            raise ValueError("Falta file_id.")
        if action in {"list","search"}:
            query = "trashed = false"
            if action=="search":
                term = str(parameters.get("query","")).replace("\\","\\\\").replace("'","\\'")
                query += f" and name contains '{term}'"
            else:
                folder = str(parameters.get("folder_id","root")).replace("'","")
                query += f" and '{folder}' in parents"
            return json.dumps(files.list(q=query,pageSize=50,fields="files(id,name,mimeType,size,webViewLink)").execute().get("files",[]),ensure_ascii=False)
        if action=="info":
            return json.dumps(files.get(fileId=file_id,fields="id,name,mimeType,size,webViewLink,modifiedTime").execute(),ensure_ascii=False)
        if action=="upload":
            source = Path(parameters["path"]).expanduser().resolve()
            if not source.is_file():
                raise ValueError("La ruta de subida no es un archivo.")
            body = {"name":source.name,"parents":[parameters.get("folder_id","root")]}
            return json.dumps(files.create(body=body,media_body=MediaFileUpload(str(source),resumable=True),fields="id,name,webViewLink").execute(),ensure_ascii=False)
        if action=="create_folder":
            if not str(parameters.get("name","")).strip():
                raise ValueError("Falta el nombre de la carpeta.")
            return json.dumps(files.create(body={"name":parameters["name"],"mimeType":"application/vnd.google-apps.folder","parents":[parameters.get("folder_id","root")]},fields="id,name").execute(),ensure_ascii=False)
        if action=="download":
            info = files.get(fileId=file_id,fields="name,mimeType").execute()
            folder = Path(parameters.get("destination",str(Path.home()/"Downloads"))).expanduser().resolve()
            folder.mkdir(parents=True,exist_ok=True)
            name = Path(info["name"].replace("\\","/")).name
            export = {"application/vnd.google-apps.document":("application/pdf",".pdf"),
                      "application/vnd.google-apps.spreadsheet":("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",".xlsx"),
                      "application/vnd.google-apps.presentation":("application/pdf",".pdf")}
            if info["mimeType"] in export:
                mime,suffix = export[info["mimeType"]]
                request = files.export_media(fileId=file_id,mimeType=mime)
                name += suffix
            else:
                request = files.get_media(fileId=file_id)
            target = folder/name
            if target.exists():
                raise ValueError("Ya existe un archivo con ese nombre en el destino.")
            temporary = target.with_name(target.name+".part")
            try:
                with temporary.open("wb") as stream:
                    downloader = MediaIoBaseDownload(stream,request)
                    done = False
                    while not done:
                        _,done = downloader.next_chunk()
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
            return f"Archivo descargado en {target}"
        if action=="delete":
            if not parameters.get("confirm"):
                return "Falta confirm=true para mover el archivo a la papelera."
            files.update(fileId=file_id,body={"trashed":True}).execute()
            return f"Archivo {file_id} movido a la papelera."
        if action=="share":
            role = parameters.get("role","reader")
            if role not in {"reader","writer","commenter"} or "@" not in parameters.get("email",""):
                raise ValueError("Email o rol inválidos.")
            permission = service.permissions().create(fileId=file_id,body={"type":"user","role":role,"emailAddress":parameters["email"]},fields="id").execute()
            return f"Permiso creado: {permission['id']}"
        raise ValueError("Acción de Drive desconocida.")
    except Exception as exc:
        return f"Error de Drive: {exc}"
